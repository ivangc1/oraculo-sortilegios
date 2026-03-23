"""Handler completo de tarot: menú → tirada → imagen → interpretación → feedback."""

import asyncio

from loguru import logger
from telegram import ForceReply, Update
from telegram.error import BadRequest, Forbidden
from telegram.ext import ContextTypes

from bot.concurrency import is_user_busy, mark_user_busy, release_user, get_semaphore
from bot.config import Settings
from bot.feedback import handle_feedback
from bot.formatting import format_and_split
from bot.keyboards import (
    feedback_keyboard,
    question_keyboard,
    tarot_keyboard,
)
from bot.limits import check_limits, record_cooldown
from bot.messages import LIMIT_MESSAGES
from bot.middleware import middleware_check
from bot.typing import with_typing
from database import usage as db_usage
from database import users as db_users
from generators.tarot import build_drawn_data, draw_tarot
from images.tarot_composer import build_caption, build_text_fallback, compose_tarot
from service.interpreter import InterpreterService
from service.models import DrawnItem, InterpretationRequest, UserProfile


async def tarot_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para /tarot — menu de variantes o smart selection con texto inline."""
    settings: Settings = context.bot_data["settings"]
    if not await middleware_check(update, context, settings):
        return

    user_id = update.effective_user.id
    user = await db_users.get_user(user_id)
    if not user or not user["onboarding_complete"]:
        await update.message.reply_text(
            LIMIT_MESSAGES["not_registered"],
            reply_to_message_id=update.message.message_id,
        )
        return

    # Smart selection: /tarot pregunta directa
    if context.args:
        question = " ".join(context.args)
        from service.smart_selector import select_variant, variant_label
        variant = select_variant(question)
        label = variant_label(variant)

        # Verificar limites antes de ejecutar
        if is_user_busy(user_id):
            await update.message.reply_text(LIMIT_MESSAGES["request_in_progress"],
                                            reply_to_message_id=update.message.message_id)
            return
        limit_key = await check_limits(user_id, "tarot", settings)
        if limit_key:
            await update.message.reply_text(LIMIT_MESSAGES[limit_key],
                                            reply_to_message_id=update.message.message_id)
            return

        mark_user_busy(user_id)
        try:
            await update.message.reply_text(
                f"🎯 El Pezuñento ha elegido: {label}",
                reply_to_message_id=update.message.message_id,
            )
            await _execute_tarot_reading(update, context, user, variant, question, settings)
        finally:
            release_user(user_id)
        return

    await update.message.reply_text(
        "Elige tu tirada:",
        reply_markup=tarot_keyboard(),
        reply_to_message_id=update.message.message_id,
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
    if not user or not user["onboarding_complete"]:
        await query.edit_message_text(LIMIT_MESSAGES["not_registered"])
        return

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
            await query.edit_message_text("Tirando las cartas...")
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
    chat_id = query.message.chat_id

    # Preguntar si tiene pregunta (q:y / q:n → tarot_question_callback)
    await query.edit_message_text(
        "¿Tienes alguna pregunta para las cartas?",
        reply_markup=question_keyboard(),
    )

    # Guardar datos para el flujo de pregunta (callback + ForceReply)
    context.user_data["tarot_variant"] = variant
    context.user_data["tarot_user"] = user


async def tarot_question_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, answer: str
) -> None:
    """Callback de respuesta a '¿Tienes pregunta?'"""
    query = update.callback_query
    await query.answer()

    variant = context.user_data.get("tarot_variant")
    user = context.user_data.get("tarot_user")
    settings: Settings = context.bot_data["settings"]

    if not variant or not user:
        await query.edit_message_text("Ha habido un error. Vuelve a intentarlo con /tarot.")
        return

    if answer == "yes":
        await query.edit_message_text("Escribe tu pregunta:")
        # ForceReply para que el bot reciba la respuesta en grupo con privacy mode
        await query.message.reply_text(
            "Escribe tu pregunta para las cartas:",
            reply_markup=ForceReply(selective=True),
        )
        context.user_data["tarot_awaiting_question"] = True
        return

    # Sin pregunta → ejecutar tirada directamente
    await query.edit_message_text("Tirando las cartas...")
    await _execute_tarot_reading(update, context, user, variant, None, settings)


async def tarot_question_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Recibe texto de pregunta de tarot (via ForceReply)."""
    if not context.user_data.get("tarot_awaiting_question"):
        return

    settings: Settings = context.bot_data["settings"]
    variant = context.user_data.get("tarot_variant")
    user = context.user_data.get("tarot_user")
    question = update.message.text
    is_smart = context.user_data.get("tarot_smart_mode", False)

    if not user:
        return

    context.user_data["tarot_awaiting_question"] = False
    context.user_data.pop("tarot_smart_mode", None)

    # Sanitizar pregunta
    if question and len(question) > settings.MAX_QUESTION_LENGTH:
        question = question[:settings.MAX_QUESTION_LENGTH]

    # Smart mode: seleccionar variante por keywords
    if is_smart and question:
        from service.smart_selector import select_variant, variant_label
        variant = select_variant(question)
        label = variant_label(variant)
        await update.message.reply_text(
            f"🎯 El Pezuñento ha elegido: {label}",
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
    user_id = user["telegram_user_id"]

    # El usuario puede no estar marcado como busy si viene de question flow
    was_busy = is_user_busy(user_id)
    if not was_busy:
        mark_user_busy(user_id)

    try:
        # 1. Generar tirada
        cards = draw_tarot(variant)

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
                )
            except (BadRequest, Forbidden) as e:
                logger.error(f"Failed to send photo: {e}")
                photo_msg = await context.bot.send_message(
                    chat_id,
                    text=build_text_fallback(variant, cards),
                )
            finally:
                jpeg_buffer.close()
        else:
            photo_msg = await context.bot.send_message(
                chat_id,
                text=build_text_fallback(variant, cards),
            )

        # 4. Construir request de interpretación
        profile = UserProfile(
            alias=user["alias"],
            sun_sign=user.get("sun_sign"),
            moon_sign=user.get("moon_sign"),
            ascendant=user.get("ascendant"),
            lunar_nakshatra=user.get("lunar_nakshatra"),
            life_path=user.get("life_path"),
        )

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
            drawn_items=drawn_items,
            question=question,
            user_profile=profile,
            max_tokens=settings.get_max_tokens("tarot", variant),
            effort=settings.get_effort("tarot", variant),
        )

        # 5. Interpretar con typing + timeout global
        interpreter: InterpreterService = context.bot_data["interpreter_service"]
        semaphore = get_semaphore()

        async def _interpret():
            async with semaphore:
                return await interpreter.interpret(request)

        try:
            response = await asyncio.wait_for(
                with_typing(chat_id, context.bot, _interpret()),
                timeout=settings.QUEUE_TIMEOUT,
            )
        except asyncio.TimeoutError:
            await context.bot.send_message(
                chat_id,
                text=LIMIT_MESSAGES["queue_timeout"],
                reply_to_message_id=photo_msg.message_id,
            )
            return

        # 6. Manejar errores
        if response.error:
            error_key = {
                "timeout": "queue_timeout",
                "rate_limit": "rate_limit",
                "empty_response": "empty_response",
            }.get(response.error, "api_error")
            from bot.messages import LIMIT_MESSAGES as msgs
            await context.bot.send_message(
                chat_id,
                text=msgs.get(error_key, msgs["api_error"]),
                reply_to_message_id=photo_msg.message_id,
            )
            return

        # 7. Formatear y enviar texto como reply a la foto
        text = response.text
        if response.truncated:
            text += LIMIT_MESSAGES["truncated"]

        chunks = format_and_split(text, spoiler=settings.USE_SPOILER)

        text_msg = None
        for i, chunk in enumerate(chunks):
            reply_to = photo_msg.message_id if i == 0 else (text_msg.message_id if text_msg else None)
            text_msg = await context.bot.send_message(
                chat_id,
                text=chunk,
                parse_mode="HTML",
                reply_to_message_id=reply_to,
            )

        # 8. Registrar uso y enviar feedback
        drawn_data = build_drawn_data(cards)
        usage_id = await db_usage.record_usage(
            user_id=user_id,
            mode="tarot",
            variant=variant,
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
            cost_usd=response.cost_usd,
            cached=response.cached,
            truncated=response.truncated,
            drawn_data=drawn_data,
        )

        # 9. Feedback inline keyboard
        if text_msg:
            try:
                await context.bot.send_message(
                    chat_id,
                    text="¿Qué te ha parecido la lectura?",
                    reply_markup=feedback_keyboard(usage_id),
                    reply_to_message_id=text_msg.message_id,
                )
            except (BadRequest, Forbidden):
                pass

        # 10. Registrar cooldown
        record_cooldown(user_id)

    finally:
        if not was_busy:
            release_user(user_id)

    # Limpiar user_data
    context.user_data.pop("tarot_variant", None)
    context.user_data.pop("tarot_user", None)
    context.user_data.pop("tarot_awaiting_question", None)
    context.user_data.pop("tarot_smart_mode", None)


async def tarot_smart_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Callback para 'El Pezuñento elige'. Pide pregunta via ForceReply."""
    query = update.callback_query
    await query.answer()

    settings: Settings = context.bot_data["settings"]
    user_id = query.from_user.id

    user = await db_users.get_user(user_id)
    if not user or not user["onboarding_complete"]:
        await query.edit_message_text(LIMIT_MESSAGES["not_registered"])
        return

    if is_user_busy(user_id):
        await query.edit_message_text(LIMIT_MESSAGES["request_in_progress"])
        return

    limit_key = await check_limits(user_id, "tarot", settings)
    if limit_key:
        await query.edit_message_text(LIMIT_MESSAGES[limit_key])
        return

    await query.edit_message_text(
        "Escribe tu pregunta y yo decido qué tirada te conviene:"
    )
    await query.message.reply_text(
        "¿Qué quieres saber?",
        reply_markup=ForceReply(selective=True),
    )
    context.user_data["tarot_awaiting_question"] = True
    context.user_data["tarot_smart_mode"] = True
    context.user_data["tarot_user"] = user
