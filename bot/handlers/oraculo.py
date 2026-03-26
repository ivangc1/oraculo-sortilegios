"""Handler del oráculo libre: pregunta directa → Sonnet interpreta."""

import asyncio

from loguru import logger
from telegram import Update
from telegram.error import BadRequest, Forbidden
from telegram.ext import ContextTypes

from bot.concurrency import is_user_busy, mark_user_busy, release_user, get_semaphore
from bot.config import Settings
from bot.formatting import format_and_split
from bot.keyboards import feedback_keyboard
from bot.limits import check_limits, record_cooldown
from bot.messages import LIMIT_MESSAGES
from bot.middleware import middleware_check
from bot.typing import with_typing
from database import usage as db_usage
from database import users as db_users
from service.interpreter import InterpreterService
from service.models import InterpretationRequest, UserProfile


async def oraculo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para /oraculo — pide pregunta con ForceReply."""
    settings: Settings = context.bot_data["settings"]
    if not await middleware_check(update, context, settings):
        return

    user = await db_users.get_user(update.effective_user.id)
    # Registro opcional — guests permitidos

    # Verificar si la pregunta viene inline: /oraculo ¿pregunta?
    text = update.message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) > 1 and len(parts[1].strip()) > 1:
        context.user_data["oraculo_user"] = user
        context.user_data["oraculo_question"] = parts[1].strip()
        await _execute_oraculo(update, context, user, parts[1].strip(), settings)
        return

    thread_id = update.effective_message.message_thread_id
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="¿Qué quieres preguntarle al oráculo?",
        reply_to_message_id=update.message.message_id,
        message_thread_id=thread_id,
    )
    context.user_data["oraculo_awaiting_question"] = True
    context.user_data["oraculo_user"] = user


async def oraculo_question_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Recibe pregunta del oráculo vía ForceReply."""
    if not context.user_data.get("oraculo_awaiting_question"):
        return

    settings: Settings = context.bot_data["settings"]
    user = context.user_data.get("oraculo_user")
    question = update.message.text

    if not question:
        return

    context.user_data["oraculo_awaiting_question"] = False
    await _execute_oraculo(update, context, user, question.strip(), settings)


async def _execute_oraculo(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
    user: dict | None, question: str, settings: Settings,
) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    thread_id = update.effective_message.message_thread_id

    if is_user_busy(user_id):
        await context.bot.send_message(chat_id, text=LIMIT_MESSAGES["request_in_progress"],
                                       message_thread_id=thread_id)
        return

    limit_key = await check_limits(user_id, "oraculo", settings)
    if limit_key:
        await context.bot.send_message(chat_id, text=LIMIT_MESSAGES[limit_key],
                                       message_thread_id=thread_id)
        return

    # Sanitizar pregunta
    if len(question) > settings.MAX_QUESTION_LENGTH:
        question = question[:settings.MAX_QUESTION_LENGTH]

    mark_user_busy(user_id)
    try:
        profile = UserProfile.from_db_or_guest(user, update)

        request = InterpretationRequest(
            mode="oraculo", variant="libre",
            question=question, user_profile=profile,
            max_tokens=settings.get_max_tokens("oraculo", "libre"),
            effort=settings.get_effort("oraculo", "libre"),
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
            await context.bot.send_message(
                chat_id, text=LIMIT_MESSAGES.get(error_key, LIMIT_MESSAGES["api_error"]),
                message_thread_id=thread_id)
            return

        text = response.text
        if response.truncated:
            text += LIMIT_MESSAGES["truncated"]

        chunks = format_and_split(text, use_blockquote=False)
        text_msg = None
        for i, chunk in enumerate(chunks):
            text_msg = await context.bot.send_message(
                chat_id, text=chunk, parse_mode="HTML",
                message_thread_id=thread_id)

        # drawn_data: solo longitud de pregunta (privacidad)
        drawn_data = {"question_length": len(question)}
        usage_id = await db_usage.record_usage(
            user_id=user_id, mode="oraculo", variant="libre",
            tokens_input=response.tokens_input, tokens_output=response.tokens_output,
            cost_usd=response.cost_usd, cached=response.cached, truncated=response.truncated,
            drawn_data=drawn_data,
        )

        if text_msg:
            try:
                await context.bot.send_message(
                    chat_id, text="¿Qué te ha parecido la lectura?",
                    reply_markup=feedback_keyboard(usage_id),
                    reply_to_message_id=text_msg.message_id,
                    message_thread_id=thread_id)
            except (BadRequest, Forbidden):
                pass

        record_cooldown(user_id)
    finally:
        release_user(user_id)
        context.user_data.pop("oraculo_user", None)
        context.user_data.pop("oraculo_question", None)
