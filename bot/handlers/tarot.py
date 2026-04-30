"""Handler completo de tarot: menú → tirada → imagen → interpretación → feedback."""

import time

from loguru import logger
from telegram import Update
from telegram.error import BadRequest, Forbidden
from telegram.ext import ContextTypes

from bot.awaiting import clear_other_awaiting
from bot.concurrency import is_user_busy, mark_user_busy, release_user
from bot.config import Settings
from bot.handlers._pipeline import run_interpretation
from bot.keyboards import (
    question_keyboard,
    tarot_deck_keyboard,
    tarot_keyboard,
)
from bot.limits import check_limits
from bot.messages import LIMIT_MESSAGES
from bot.middleware import middleware_check
from bot.typing import get_thread_id
from database import users as db_users
from generators.tarot import build_drawn_data, draw_tarot, get_deck_label
from images.tarot_composer import build_caption, build_text_fallback, compose_tarot
from service.interpreter import InterpreterService
from service.models import DrawnItem, InterpretationRequest, UserProfile


async def tarot_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para /tirartarot — menu de variantes o smart selection con texto inline."""
    settings: Settings = context.bot_data["settings"]
    if not await middleware_check(update, context, settings):
        return

    user_id = update.effective_user.id
    user = await db_users.get_user(user_id)
    # Registro opcional — guests permitidos

    # Smart selection: /tirartarot pregunta directa
    if context.args:
        question = " ".join(context.args)
        from service.smart_selector import select_variant, variant_label
        variant = select_variant(question)
        label = variant_label(variant)

        # Verificar limites antes de ejecutar
        thread_id = get_thread_id(update)
        if is_user_busy(user_id):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=LIMIT_MESSAGES["request_in_progress"],
                message_thread_id=thread_id,
                reply_to_message_id=update.message.message_id,
            )
            return
        limit_key = await check_limits(user_id, "tarot", settings)
        if limit_key:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=LIMIT_MESSAGES[limit_key],
                message_thread_id=thread_id,
                reply_to_message_id=update.message.message_id,
            )
            return

        mark_user_busy(user_id)
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"🎯 El Pezuñento ha elegido: {label}",
                message_thread_id=thread_id,
                reply_to_message_id=update.message.message_id,
            )
            await _execute_tarot_reading(update, context, user, variant, question, settings)
        finally:
            release_user(user_id)
        return

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Elige tu mazo:",
        reply_markup=tarot_deck_keyboard(),
        message_thread_id=get_thread_id(update),
        reply_to_message_id=update.message.message_id,
    )


async def tarot_deck_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, deck: str,
) -> None:
    """Callback de selección de mazo → muestra menú de variantes."""
    query = update.callback_query
    await query.answer()

    context.user_data["tarot_deck"] = deck
    deck_label = get_deck_label(deck)
    await query.edit_message_text(
        f"{deck_label} — Elige tu tirada:",
        reply_markup=tarot_keyboard(),
    )


async def tarot_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, variant: str,
    skip_question: bool = False,
) -> None:
    """Procesa callback de variante tarot. Flujo completo."""
    query = update.callback_query
    await query.answer()

    settings: Settings = context.bot_data["settings"]
    user_id = query.from_user.id

    # Verificar registro
    user = await db_users.get_user(user_id)
    # Registro opcional — guests permitidos

    # Bloqueo concurrente
    if is_user_busy(user_id):
        await query.edit_message_text(LIMIT_MESSAGES["request_in_progress"])
        return

    # Limites
    limit_key = await check_limits(user_id, "tarot", settings)
    if limit_key:
        await query.edit_message_text(LIMIT_MESSAGES[limit_key])
        return

    if skip_question:
        # Tirada del dia: ejecutar sin pregunta
        mark_user_busy(user_id)
        try:
            await query.edit_message_text("Tirando las cartas...", reply_markup=None)
            await _execute_tarot_reading(update, context, user, variant, None, settings)
        finally:
            release_user(user_id)
        return

    mark_user_busy(user_id)
    try:
        await _process_tarot(update, context, user, variant, settings)
    finally:
        release_user(user_id)


async def _process_tarot(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user: dict,
    variant: str,
    settings: Settings,
) -> None:
    """Flujo completo: pregunta → tirada → imagen → interpretación → feedback."""
    query = update.callback_query

    # Preguntar si tiene pregunta (q:y / q:n → tarot_question_callback)
    await query.edit_message_text(
        "¿Tienes alguna pregunta para las cartas?",
        reply_markup=question_keyboard(),
    )

    # Solo guardamos el variant; el user lo releemos en cada uso para no
    # serializar el dict completo de DB en pickle (frágil ante schema changes).
    context.user_data["tarot_variant"] = variant


async def tarot_question_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, answer: str
) -> None:
    """Callback de respuesta a '¿Tienes pregunta?'"""
    query = update.callback_query
    await query.answer()

    variant = context.user_data.get("tarot_variant")
    settings: Settings = context.bot_data["settings"]

    if not variant:
        await query.edit_message_text("Ha habido un error. Vuelve a intentarlo con /tirartarot.")
        return

    if answer == "yes":
        # Editamos el mensaje existente (no crea mensaje nuevo → no aparece en general)
        # El handler de texto captura la respuesta vía user_data flag
        await query.edit_message_text(
            "✍️ Escribe tu pregunta para las cartas:\n\n"
            "(Tienes 5 minutos antes de que el oráculo se aburra y cierre la mesa.)",
            reply_markup=None,
        )
        clear_other_awaiting(context.user_data, except_key="tarot_awaiting_question")
        context.user_data["tarot_awaiting_question"] = time.time()
        return

    # Sin pregunta → ejecutar tirada directamente
    user = await db_users.get_user(query.from_user.id)
    await query.edit_message_text("Tirando las cartas...", reply_markup=None)
    await _execute_tarot_reading(update, context, user, variant, None, settings)


async def tarot_question_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Recibe texto de pregunta de tarot."""
    if not context.user_data.get("tarot_awaiting_question"):
        return

    settings: Settings = context.bot_data["settings"]
    variant = context.user_data.get("tarot_variant")
    user = await db_users.get_user(update.effective_user.id)  # release de pickle
    question = update.message.text
    is_smart = context.user_data.get("tarot_smart_mode", False)

    # user puede ser None (guest) — from_db_or_guest lo maneja
    context.user_data["tarot_awaiting_question"] = False
    context.user_data.pop("tarot_smart_mode", None)

    # Sanitizar pregunta

    # Smart mode: seleccionar variante por keywords
    if is_smart and question:
        from service.smart_selector import select_variant, variant_label
        variant = select_variant(question)
        label = variant_label(variant)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🎯 El Pezuñento ha elegido: {label}",
            message_thread_id=get_thread_id(update),
            reply_to_message_id=update.message.message_id,
        )

    if not variant:
        return

    await _execute_tarot_reading(update, context, user, variant, question, settings)


async def _execute_tarot_reading(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user: dict,
    variant: str,
    question: str | None,
    settings: Settings,
) -> None:
    """Ejecuta tirada completa: genera → imagen → API → formateo → envío."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    thread_id = get_thread_id(update)

    # El usuario puede no estar marcado como busy si viene de question flow
    was_busy = is_user_busy(user_id)
    if not was_busy:
        mark_user_busy(user_id)

    try:
        # 1. Generar tirada
        deck = context.user_data.get("tarot_deck", "rws")
        cards = draw_tarot(variant, deck=deck)

        # 2. Componer imagen
        jpeg_buffer = compose_tarot(variant, cards)
        caption = build_caption(variant, cards)

        # 3. Enviar imagen (o fallback texto)
        if jpeg_buffer:
            try:
                photo_msg = await context.bot.send_photo(
                    chat_id,
                    photo=jpeg_buffer,
                    caption=caption,
                    message_thread_id=thread_id,
                )
            except (BadRequest, Forbidden) as e:
                logger.error(f"Failed to send photo: {e}")
                photo_msg = await context.bot.send_message(
                    chat_id,
                    text=build_text_fallback(variant, cards),
                    message_thread_id=thread_id,
                )
            finally:
                jpeg_buffer.close()
        else:
            photo_msg = await context.bot.send_message(
                chat_id,
                text=build_text_fallback(variant, cards),
                message_thread_id=thread_id,
            )

        # 4. Construir request de interpretación
        profile = UserProfile.from_db_or_guest(user, update)

        drawn_items = [
            DrawnItem(
                id=c["id"],
                name=c["name"],
                inverted=c["inverted"],
                position=c.get("position"),
            )
            for c in cards
        ]

        request = InterpretationRequest(
            mode="tarot",
            variant=variant,
            deck=deck,
            drawn_items=drawn_items,
            question=question,
            user_profile=profile,
            max_tokens=settings.get_max_tokens("tarot", variant),
            effort=settings.get_effort("tarot", variant),
        )

        # 5-10. Pipeline LLM común (interpret + chunks + record + feedback + cooldown)
        interpreter: InterpreterService = context.bot_data["interpreter_service"]
        await run_interpretation(
            bot=context.bot,
            chat_id=chat_id,
            thread_id=thread_id,
            user_id=user_id,
            settings=settings,
            interpreter=interpreter,
            request=request,
            mode="tarot",
            variant=variant,
            drawn_data=build_drawn_data(cards),
            anchor_msg=photo_msg,
        )

    finally:
        if not was_busy:
            release_user(user_id)

    # Limpiar user_data
    context.user_data.pop("tarot_variant", None)
    context.user_data.pop("tarot_awaiting_question", None)
    context.user_data.pop("tarot_smart_mode", None)
    context.user_data.pop("tarot_deck", None)


async def tarot_smart_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Callback para 'El Pezuñento elige'. Pide pregunta al usuario."""
    query = update.callback_query
    await query.answer()

    settings: Settings = context.bot_data["settings"]
    user_id = query.from_user.id

    if is_user_busy(user_id):
        await query.edit_message_text(LIMIT_MESSAGES["request_in_progress"])
        return

    limit_key = await check_limits(user_id, "tarot", settings)
    if limit_key:
        await query.edit_message_text(LIMIT_MESSAGES[limit_key])
        return

    await query.edit_message_text(
        "Escribe tu pregunta y yo decido qué tirada te conviene:\n\n(Tienes 5 minutos antes de que el oráculo se aburra y cierre la mesa.)"
    )
    clear_other_awaiting(context.user_data, except_key="tarot_awaiting_question")
    context.user_data["tarot_awaiting_question"] = time.time()
    context.user_data["tarot_smart_mode"] = True
