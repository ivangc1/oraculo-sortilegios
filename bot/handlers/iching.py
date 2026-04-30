"""Handler de I Ching: tirada → hexagrama (con/sin derivado) → interpretación."""

from telegram import Update
from telegram.error import BadRequest, Forbidden
from telegram.ext import ContextTypes

from bot.concurrency import is_user_busy, mark_user_busy, release_user
from bot.config import Settings
from bot.handlers._pipeline import run_interpretation
from bot.limits import check_limits
from bot.messages import LIMIT_MESSAGES
from bot.middleware import middleware_check
from bot.typing import get_thread_id
from database import users as db_users
from generators.iching import generate_hexagram, build_drawn_data
from images.hexagram_renderer import render_hexagram, build_caption, build_text_fallback
from service.interpreter import InterpreterService
from service.models import InterpretationRequest, UserProfile


async def iching_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para /iching — ejecuta directamente (no hay sub-variantes)."""
    settings: Settings = context.bot_data["settings"]
    if not await middleware_check(update, context, settings):
        return

    user_id = update.effective_user.id
    user = await db_users.get_user(user_id)
    # Registro opcional — guests permitidos

    await iching_execute(update, context, question=None)


async def iching_execute(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
    question: str | None = None,
) -> None:
    """Ejecuta consulta de I Ching completa."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_reply_markup(reply_markup=None)

    settings: Settings = context.bot_data["settings"]
    user_id = (query.from_user if query else update.effective_user).id
    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)

    user = await db_users.get_user(user_id)
    # Registro opcional — guests permitidos

    if is_user_busy(user_id):
        msg = LIMIT_MESSAGES["request_in_progress"]
        if query:
            await query.edit_message_text(msg)
        else:
            await context.bot.send_message(
                chat_id=chat_id, text=msg,
                message_thread_id=thread_id,
                reply_to_message_id=update.message.message_id,
            )
        return

    limit_key = await check_limits(user_id, "iching", settings)
    if limit_key:
        msg = LIMIT_MESSAGES[limit_key]
        if query:
            await query.edit_message_text(msg)
        else:
            await context.bot.send_message(
                chat_id=chat_id, text=msg,
                message_thread_id=thread_id,
                reply_to_message_id=update.message.message_id,
            )
        return

    mark_user_busy(user_id)
    try:
        # 1. Generar hexagrama
        hexagram = generate_hexagram()

        # 2. Renderizar imagen
        jpeg_buffer = render_hexagram(hexagram)
        caption = build_caption(hexagram)

        if jpeg_buffer:
            try:
                photo_msg = await context.bot.send_photo(chat_id, photo=jpeg_buffer, caption=caption,
                                                           message_thread_id=thread_id)
            except (BadRequest, Forbidden):
                photo_msg = await context.bot.send_message(chat_id, text=build_text_fallback(hexagram),
                                                           message_thread_id=thread_id)
            finally:
                jpeg_buffer.close()
        else:
            photo_msg = await context.bot.send_message(chat_id, text=build_text_fallback(hexagram),
                                                       message_thread_id=thread_id)

        # 3. Interpretación
        profile = UserProfile.from_db_or_guest(user, update)

        # Extra data con info del hexagrama para el sub-prompt
        extra = {
            "hexagrama_primario": f"{hexagram['primary']}. {hexagram['primary_name']} ({hexagram.get('primary_spanish', '')})",
            "lineas": ", ".join(str(l) for l in hexagram["lines"]),
        }
        if hexagram["mutable_lines"]:
            extra["lineas_mutables"] = ", ".join(str(l) for l in hexagram["mutable_lines"])
            extra["hexagrama_derivado"] = f"{hexagram['derived']}. {hexagram['derived_name']} ({hexagram.get('derived_spanish', '')})"
        else:
            extra["lineas_mutables"] = "Ninguna — situación estable, sin transformación"

        request = InterpretationRequest(
            mode="iching", variant="hexagrama",
            question=question, user_profile=profile,
            max_tokens=settings.get_max_tokens("iching", "hexagrama"),
            effort=settings.get_effort("iching", "hexagrama"),
            extra_data=extra,
        )

        interpreter: InterpreterService = context.bot_data["interpreter_service"]
        await run_interpretation(
            bot=context.bot,
            chat_id=chat_id,
            thread_id=thread_id,
            user_id=user_id,
            settings=settings,
            interpreter=interpreter,
            request=request,
            mode="iching",
            variant="hexagrama",
            drawn_data=build_drawn_data(hexagram),
            anchor_msg=photo_msg,
        )

    finally:
        release_user(user_id)
