"""Handler de numerología: informe + compatibilidad.

full_birth_name pedido solo la primera vez que se usa /numerologia (ForceReply).
Compatibilidad solo pide segunda fecha (camino de vida), no nombre.
"""

import asyncio

from loguru import logger
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest, Forbidden
from telegram.ext import ContextTypes

from bot.concurrency import is_user_busy, mark_user_busy, release_user, get_semaphore
from bot.config import Settings
from bot.formatting import format_and_split
from bot.keyboards import feedback_keyboard, numerologia_keyboard
from bot.limits import check_limits, record_cooldown
from bot.messages import LIMIT_MESSAGES
from bot.middleware import middleware_check
from bot.typing import with_typing
from database import usage as db_usage
from database import users as db_users
from service.calculators.numerologia import compatibility, full_report
from service.interpreter import InterpreterService
from service.models import InterpretationRequest, UserProfile


async def numerologia_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    if not await middleware_check(update, context, settings):
        return
    user = await db_users.get_user(update.effective_user.id)
    if not user or not user["onboarding_complete"]:
        await update.message.reply_text(LIMIT_MESSAGES["not_registered"],
                                        reply_to_message_id=update.message.message_id)
        return
    await update.message.reply_text("¿Qué quieres consultar?",
                                    reply_markup=numerologia_keyboard(),
                                    reply_to_message_id=update.message.message_id)


async def numerologia_informe_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Callback para informe numerológico. Pide nombre completo si falta."""
    query = update.callback_query
    await query.answer()

    settings: Settings = context.bot_data["settings"]
    user_id = query.from_user.id
    user = await db_users.get_user(user_id)
    if not user or not user["onboarding_complete"]:
        await query.edit_message_text(LIMIT_MESSAGES["not_registered"])
        return

    # ¿Tiene full_birth_name? → redirigir a DM para privacidad
    if not user.get("full_birth_name"):
        bot_username = (await context.bot.get_me()).username
        await query.edit_message_text(
            "Para el informe numerológico necesito tu nombre completo de nacimiento.\n"
            "Vamos al privado para que no quede aquí.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "📝 Registrar nombre",
                    url=f"https://t.me/{bot_username}?start=set_fullname",
                )],
            ]),
        )
        return

    # Ya tiene nombre → ejecutar
    await _execute_informe(update, context, user, settings)


async def numerologia_name_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Recibe nombre completo vía ForceReply."""
    if not context.user_data.get("numerologia_awaiting_name"):
        return

    settings: Settings = context.bot_data["settings"]
    user_id = update.effective_user.id
    name = update.message.text.strip()

    if len(name) < 2:
        await update.message.reply_text("Ese nombre es muy corto. Escribe tu nombre completo.")
        return

    context.user_data["numerologia_awaiting_name"] = False

    # Guardar en DB
    await db_users.update_full_birth_name(user_id, name)
    user = await db_users.get_user(user_id)

    await _execute_informe(update, context, user, settings)


async def _execute_informe(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
    user: dict, settings: Settings,
) -> None:
    """Ejecuta informe numerológico completo."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    thread_id = update.effective_message.message_thread_id

    if is_user_busy(user_id):
        await context.bot.send_message(chat_id, text=LIMIT_MESSAGES["request_in_progress"],
                                       message_thread_id=thread_id)
        return

    limit_key = await check_limits(user_id, "numerologia", settings)
    if limit_key:
        await context.bot.send_message(chat_id, text=LIMIT_MESSAGES[limit_key],
                                       message_thread_id=thread_id)
        return

    mark_user_busy(user_id)
    try:
        report = full_report(user["birth_date"], user.get("full_birth_name"))

        profile = UserProfile(alias=user["alias"], sun_sign=user.get("sun_sign"),
                              life_path=user.get("life_path"))

        extra_data = {
            "camino_de_vida": report["life_path"],
            "año_personal": report["personal_year"],
            "mes_personal": report["personal_month"],
        }
        if "expression" in report:
            extra_data["expresion"] = report["expression"]
            extra_data["alma"] = report["soul"]
            extra_data["personalidad"] = report["personality"]

        drawn_data = report.copy()

        request = InterpretationRequest(
            mode="numerologia", variant="informe",
            user_profile=profile,
            max_tokens=settings.get_max_tokens("numerologia", "informe"),
            effort=settings.get_effort("numerologia", "informe"),
            extra_data=extra_data,
        )

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
            await context.bot.send_message(chat_id, text=LIMIT_MESSAGES["queue_timeout"],
                                           message_thread_id=thread_id)
            return

        if response.error:
            error_key = {"timeout": "queue_timeout", "rate_limit": "rate_limit",
                         "empty_response": "empty_response"}.get(response.error, "api_error")
            await context.bot.send_message(chat_id, text=LIMIT_MESSAGES.get(error_key, LIMIT_MESSAGES["api_error"]),
                                           message_thread_id=thread_id)
            return

        text = response.text
        if response.truncated:
            text += LIMIT_MESSAGES["truncated"]

        chunks = format_and_split(text, use_blockquote=False)
        text_msg = None
        for i, chunk in enumerate(chunks):
            text_msg = await context.bot.send_message(chat_id, text=chunk, parse_mode="HTML",
                                                      message_thread_id=thread_id)

        usage_id = await db_usage.record_usage(
            user_id=user_id, mode="numerologia", variant="informe",
            tokens_input=response.tokens_input, tokens_output=response.tokens_output,
            cost_usd=response.cost_usd, cached=response.cached, truncated=response.truncated,
            drawn_data=drawn_data,
        )

        if text_msg:
            try:
                await context.bot.send_message(chat_id, text="¿Qué te ha parecido la lectura?",
                                               reply_markup=feedback_keyboard(usage_id),
                                               reply_to_message_id=text_msg.message_id,
                                               message_thread_id=thread_id)
            except (BadRequest, Forbidden):
                pass

        record_cooldown(user_id)
    finally:
        release_user(user_id)


async def numerologia_compat_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Callback para compatibilidad. Pide segunda fecha (ForceReply)."""
    query = update.callback_query
    await query.answer()

    settings: Settings = context.bot_data["settings"]
    user_id = query.from_user.id
    user = await db_users.get_user(user_id)
    if not user or not user["onboarding_complete"]:
        await query.edit_message_text(LIMIT_MESSAGES["not_registered"])
        return

    await query.edit_message_text(
        "Para la compatibilidad necesito la fecha de nacimiento de la otra persona.\n\n"
        "Escribe la fecha (DD/MM/AAAA):"
    )
    context.user_data["numerologia_awaiting_compat_date"] = True


async def numerologia_compat_date_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Recibe segunda fecha para compatibilidad vía ForceReply."""
    if not context.user_data.get("numerologia_awaiting_compat_date"):
        return

    settings: Settings = context.bot_data["settings"]
    user_id = update.effective_user.id
    date_text = update.message.text.strip()

    context.user_data["numerologia_awaiting_compat_date"] = False

    # Validar fecha
    try:
        parts = date_text.split("/")
        if len(parts) != 3:
            raise ValueError("Formato inválido")
        day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
        if not (1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2025):
            raise ValueError("Fecha fuera de rango")
    except (ValueError, IndexError):
        await update.message.reply_text(LIMIT_MESSAGES["invalid_date"])
        context.user_data["numerologia_awaiting_compat_date"] = True
        return

    user = await db_users.get_user(user_id)
    if not user:
        return

    chat_id = update.effective_chat.id
    thread_id = update.effective_message.message_thread_id

    if is_user_busy(user_id):
        await context.bot.send_message(chat_id, text=LIMIT_MESSAGES["request_in_progress"],
                                       message_thread_id=thread_id)
        return

    limit_key = await check_limits(user_id, "numerologia", settings)
    if limit_key:
        await context.bot.send_message(chat_id, text=LIMIT_MESSAGES[limit_key],
                                       message_thread_id=thread_id)
        return

    mark_user_busy(user_id)
    try:
        compat = compatibility(user["birth_date"], date_text)

        profile = UserProfile(alias=user["alias"], sun_sign=user.get("sun_sign"),
                              life_path=user.get("life_path"))

        extra_data = {
            "camino_vida_consultante": compat["life_path_1"],
            "camino_vida_otra_persona": compat["life_path_2"],
        }

        request = InterpretationRequest(
            mode="numerologia", variant="compatibilidad",
            user_profile=profile,
            max_tokens=settings.get_max_tokens("numerologia", "compatibilidad"),
            effort=settings.get_effort("numerologia", "compatibilidad"),
            extra_data=extra_data,
        )

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
            await context.bot.send_message(chat_id, text=LIMIT_MESSAGES["queue_timeout"],
                                           message_thread_id=thread_id)
            return

        if response.error:
            error_key = {"timeout": "queue_timeout", "rate_limit": "rate_limit",
                         "empty_response": "empty_response"}.get(response.error, "api_error")
            await context.bot.send_message(chat_id, text=LIMIT_MESSAGES.get(error_key, LIMIT_MESSAGES["api_error"]),
                                           message_thread_id=thread_id)
            return

        text = response.text
        if response.truncated:
            text += LIMIT_MESSAGES["truncated"]

        chunks = format_and_split(text, use_blockquote=False)
        text_msg = None
        for i, chunk in enumerate(chunks):
            text_msg = await context.bot.send_message(chat_id, text=chunk, parse_mode="HTML",
                                                      message_thread_id=thread_id)

        usage_id = await db_usage.record_usage(
            user_id=user_id, mode="numerologia", variant="compatibilidad",
            tokens_input=response.tokens_input, tokens_output=response.tokens_output,
            cost_usd=response.cost_usd, cached=response.cached, truncated=response.truncated,
            drawn_data=compat,
        )

        if text_msg:
            try:
                await context.bot.send_message(chat_id, text="¿Qué te ha parecido la lectura?",
                                               reply_markup=feedback_keyboard(usage_id),
                                               reply_to_message_id=text_msg.message_id,
                                               message_thread_id=thread_id)
            except (BadRequest, Forbidden):
                pass

        record_cooldown(user_id)
    finally:
        release_user(user_id)
