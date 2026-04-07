"""Handler de runas: menú → tirada → imagen → interpretación → feedback."""

import asyncio

from loguru import logger
from telegram import Update
from telegram.error import BadRequest, Forbidden
from telegram.ext import ContextTypes

from bot.concurrency import is_user_busy, mark_user_busy, release_user, get_semaphore
from bot.config import Settings
from bot.formatting import format_and_split
from bot.keyboards import feedback_keyboard, runas_keyboard
from bot.limits import check_limits, record_cooldown
from bot.messages import LIMIT_MESSAGES
from bot.middleware import middleware_check
from bot.typing import get_thread_id, with_typing
from database import usage as db_usage
from database import users as db_users
from generators.runas import build_drawn_data, draw_runes
from images.rune_renderer import render_rune_with_label, compose_runes
from service.interpreter import InterpreterService
from service.models import DrawnItem, InterpretationRequest, UserProfile


async def runas_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para /runa — muestra menú de variantes."""
    settings: Settings = context.bot_data["settings"]
    if not await middleware_check(update, context, settings):
        return

    user_id = update.effective_user.id
    user = await db_users.get_user(user_id)
    # Registro opcional — guests permitidos

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="¿Qué tipo de tirada rúnica quieres?",
        reply_markup=runas_keyboard(),
        message_thread_id=get_thread_id(update),
        reply_to_message_id=update.message.message_id,
    )


async def runas_execute(
    update: Update, context: ContextTypes.DEFAULT_TYPE, variant: str,
    question: str | None = None,
) -> None:
    """Ejecuta tirada de runas completa."""
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
        if query:
            await query.edit_message_text(LIMIT_MESSAGES["request_in_progress"])
        return

    limit_key = await check_limits(user_id, "runas", settings)
    if limit_key:
        if query:
            await query.edit_message_text(LIMIT_MESSAGES[limit_key])
        return

    mark_user_busy(user_id)
    try:
        # 1. Generar tirada
        runes = draw_runes(variant)

        # 2. Renderizar imágenes de runas
        rune_images = []
        for rune in runes:
            label = rune.get("position", rune["name"])
            if rune["inverted"]:
                label += " ↓"
            img = render_rune_with_label(rune["id"], label)
            if rune["inverted"]:
                # Invertir la parte de la runa (no la etiqueta)
                from PIL import Image as PILImage
                rune_part = img.crop((0, 0, img.width, img.height - 40))
                rune_part = rune_part.rotate(180, expand=False)
                img.paste(rune_part, (0, 0))
            rune_images.append(img)

        # 3. Componer y enviar
        jpeg_buffer = compose_runes(rune_images)

        # Caption
        caption_parts = []
        for r in runes:
            inv = " (invertida)" if r["inverted"] else ""
            pos = r.get("position", "")
            caption_parts.append(f"{pos}: {r['name']}{inv}" if pos else f"{r['name']}{inv}")
        caption = "\n".join(caption_parts)

        if jpeg_buffer:
            try:
                photo_msg = await context.bot.send_photo(chat_id, photo=jpeg_buffer, caption=caption,
                                                           message_thread_id=thread_id)
            except (BadRequest, Forbidden):
                photo_msg = await context.bot.send_message(chat_id, text=f"ᚱ Tu tirada:\n{caption}",
                                                           message_thread_id=thread_id)
            finally:
                jpeg_buffer.close()
        else:
            photo_msg = await context.bot.send_message(chat_id, text=f"ᚱ Tu tirada:\n{caption}",
                                                       message_thread_id=thread_id)

        # 4. Interpretación
        profile = UserProfile.from_db_or_guest(user, update)

        drawn_items = [
            DrawnItem(id=r["id"], name=r["name"], inverted=r["inverted"], position=r.get("position"))
            for r in runes
        ]

        request = InterpretationRequest(
            mode="runas", variant=variant, drawn_items=drawn_items,
            question=question, user_profile=profile,
            max_tokens=settings.get_max_tokens("runas", variant),
            effort=settings.get_effort("runas", variant),
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
                                           reply_to_message_id=photo_msg.message_id,
                                           message_thread_id=thread_id)
            return

        if response.error:
            error_key = {"timeout": "queue_timeout", "rate_limit": "rate_limit",
                         "empty_response": "empty_response"}.get(response.error, "api_error")
            await context.bot.send_message(chat_id, text=LIMIT_MESSAGES.get(error_key, LIMIT_MESSAGES["api_error"]),
                                           reply_to_message_id=photo_msg.message_id,
                                           message_thread_id=thread_id)
            return

        text = response.text
        if response.truncated:
            text += LIMIT_MESSAGES["truncated"]

        chunks = format_and_split(text, use_blockquote=settings.use_blockquote_for("runas", variant))
        text_msg = None
        for i, chunk in enumerate(chunks):
            reply_to = photo_msg.message_id if i == 0 else (text_msg.message_id if text_msg else None)
            text_msg = await context.bot.send_message(chat_id, text=chunk, parse_mode="HTML",
                                                      reply_to_message_id=reply_to,
                                                      message_thread_id=thread_id)

        drawn_data = build_drawn_data(runes)
        usage_id = await db_usage.record_usage(
            user_id=user_id, mode="runas", variant=variant,
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
