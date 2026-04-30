"""Handler del oráculo libre: pregunta directa → Sonnet interpreta."""

import time

from telegram import Update
from telegram.ext import ContextTypes

from bot.concurrency import is_user_busy, mark_user_busy, release_user
from bot.config import Settings
from bot.handlers._pipeline import run_interpretation
from bot.limits import check_limits
from bot.messages import LIMIT_MESSAGES
from bot.middleware import middleware_check
from bot.typing import get_thread_id
from database import users as db_users
from service.interpreter import InterpreterService
from service.models import InterpretationRequest, UserProfile


async def oraculo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para /oraculo — pide pregunta al usuario."""
    settings: Settings = context.bot_data["settings"]
    if not await middleware_check(update, context, settings):
        return

    user = await db_users.get_user(update.effective_user.id)
    # Registro opcional — guests permitidos

    # Verificar si la pregunta viene inline: /oraculo ¿pregunta?
    text = update.message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) > 1 and len(parts[1].strip()) > 1:
        await _execute_oraculo(update, context, user, parts[1].strip(), settings)
        return

    thread_id = get_thread_id(update)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="¿Qué quieres preguntarle al oráculo?\n\n(Tienes 5 minutos antes de que el oráculo se aburra y cierre la mesa.)",
        message_thread_id=thread_id,
    )
    # Solo guardamos el flag de awaiting; releemos el user al usar para evitar
    # serializar el dict completo de DB en el pickle (frágil ante schema changes).
    from bot.awaiting import clear_other_awaiting
    clear_other_awaiting(context.user_data, except_key="oraculo_awaiting_question")
    context.user_data["oraculo_awaiting_question"] = time.time()


async def oraculo_question_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Recibe pregunta del oráculo vía texto libre."""
    if not context.user_data.get("oraculo_awaiting_question"):
        return

    settings: Settings = context.bot_data["settings"]
    question = update.message.text

    if not question:
        return

    # Releer perfil del usuario en cada uso (no se persiste en pickle).
    user = await db_users.get_user(update.effective_user.id)

    context.user_data["oraculo_awaiting_question"] = False
    await _execute_oraculo(update, context, user, question.strip(), settings)


async def _execute_oraculo(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
    user: dict | None, question: str, settings: Settings,
) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)

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

        # drawn_data: solo longitud de pregunta (privacidad)
        await run_interpretation(
            bot=context.bot,
            chat_id=chat_id,
            thread_id=thread_id,
            user_id=user_id,
            settings=settings,
            interpreter=interpreter,
            request=request,
            mode="oraculo",
            variant="libre",
            drawn_data={"question_length": len(question)},
        )
    finally:
        release_user(user_id)
