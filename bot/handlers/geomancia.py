"""Handler de geomancia: 1 figura o escudo completo."""

import asyncio

from loguru import logger
from telegram import Update
from telegram.error import BadRequest, Forbidden
from telegram.ext import ContextTypes

from bot.concurrency import is_user_busy, mark_user_busy, release_user, get_semaphore
from bot.config import Settings
from bot.formatting import format_and_split
from bot.keyboards import feedback_keyboard, geomancia_keyboard
from bot.limits import check_limits, record_cooldown
from bot.messages import LIMIT_MESSAGES
from bot.middleware import middleware_check
from bot.typing import with_typing
from database import usage as db_usage
from database import users as db_users
from generators.geomancia import (
    build_drawn_data_shield, build_drawn_data_single,
    generate_figure, generate_shield,
)
from images.geomancy_renderer import (
    build_caption_shield, build_caption_single,
    build_text_fallback_shield, build_text_fallback_single,
    render_shield, render_single_figure,
)
from service.interpreter import InterpreterService
from service.models import DrawnItem, InterpretationRequest, UserProfile


async def geomancia_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    if not await middleware_check(update, context, settings):
        return
    user = await db_users.get_user(update.effective_user.id)
    if not user or not user["onboarding_complete"]:
        await update.message.reply_text(LIMIT_MESSAGES["not_registered"],
                                        reply_to_message_id=update.message.message_id)
        return
    await update.message.reply_text("¿Qué tipo de consulta geomántica quieres?",
                                    reply_markup=geomancia_keyboard(),
                                    reply_to_message_id=update.message.message_id)


async def geomancia_execute(
    update: Update, context: ContextTypes.DEFAULT_TYPE, variant: str,
    question: str | None = None,
) -> None:
    query = update.callback_query
    if query:
        await query.answer()

    settings: Settings = context.bot_data["settings"]
    user_id = (query.from_user if query else update.effective_user).id
    chat_id = update.effective_chat.id

    user = await db_users.get_user(user_id)
    if not user or not user["onboarding_complete"]:
        return

    if is_user_busy(user_id):
        if query:
            await query.edit_message_text(LIMIT_MESSAGES["request_in_progress"])
        return

    limit_key = await check_limits(user_id, "geomancia", settings)
    if limit_key:
        if query:
            await query.edit_message_text(LIMIT_MESSAGES[limit_key])
        return

    mark_user_busy(user_id)
    try:
        if variant == "1_figura":
            figure = generate_figure()
            jpeg_buffer = render_single_figure(figure)
            caption = build_caption_single(figure)
            fallback = build_text_fallback_single(figure)
            drawn_data = build_drawn_data_single(figure)
            drawn_items = [DrawnItem(id=figure["name"], name=figure.get("spanish", figure["name"]),
                                     position="figura_1")]
            extra_data = {"figura": f"{figure.get('spanish', figure['name'])} ({figure['element']} / {figure['planet']})"}
        else:
            shield = generate_shield()
            jpeg_buffer = render_shield(shield)
            caption = build_caption_shield(shield)
            fallback = build_text_fallback_shield(shield)
            drawn_data = build_drawn_data_shield(shield)
            drawn_items = []
            for g in ("mothers", "daughters", "nieces", "witnesses"):
                for fig in shield[g]:
                    drawn_items.append(DrawnItem(id=fig["name"],
                                                 name=fig.get("spanish", fig["name"]),
                                                 position=fig["position"]))
            drawn_items.append(DrawnItem(id=shield["judge"]["name"],
                                         name=shield["judge"].get("spanish", shield["judge"]["name"]),
                                         position="Juez"))
            extra_data = {
                "madres": ", ".join(f.get("spanish", f["name"]) for f in shield["mothers"]),
                "hijas": ", ".join(f.get("spanish", f["name"]) for f in shield["daughters"]),
                "sobrinas": ", ".join(f.get("spanish", f["name"]) for f in shield["nieces"]),
                "testigo_derecho": shield["witnesses"][0].get("spanish", shield["witnesses"][0]["name"]),
                "testigo_izquierdo": shield["witnesses"][1].get("spanish", shield["witnesses"][1]["name"]),
                "juez": shield["judge"].get("spanish", shield["judge"]["name"]),
                "reconciliador": shield["reconciler"].get("spanish", shield["reconciler"]["name"]),
            }

        # Enviar imagen
        if jpeg_buffer:
            try:
                photo_msg = await context.bot.send_photo(chat_id, photo=jpeg_buffer, caption=caption)
            except (BadRequest, Forbidden):
                photo_msg = await context.bot.send_message(chat_id, text=fallback)
            finally:
                jpeg_buffer.close()
        else:
            photo_msg = await context.bot.send_message(chat_id, text=fallback)

        # Interpretación
        profile = UserProfile(alias=user["alias"], sun_sign=user.get("sun_sign"),
                              life_path=user.get("life_path"))
        request = InterpretationRequest(
            mode="geomancia", variant=variant, drawn_items=drawn_items,
            question=question, user_profile=profile,
            max_tokens=settings.get_max_tokens("geomancia", variant),
            effort=settings.get_effort("geomancia", variant),
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
                                           reply_to_message_id=photo_msg.message_id)
            return

        if response.error:
            error_key = {"timeout": "queue_timeout", "rate_limit": "rate_limit",
                         "empty_response": "empty_response"}.get(response.error, "api_error")
            await context.bot.send_message(chat_id, text=LIMIT_MESSAGES.get(error_key, LIMIT_MESSAGES["api_error"]),
                                           reply_to_message_id=photo_msg.message_id)
            return

        text = response.text
        if response.truncated:
            text += LIMIT_MESSAGES["truncated"]

        chunks = format_and_split(text, use_blockquote=settings.USE_BLOCKQUOTE)
        text_msg = None
        for i, chunk in enumerate(chunks):
            reply_to = photo_msg.message_id if i == 0 else (text_msg.message_id if text_msg else None)
            text_msg = await context.bot.send_message(chat_id, text=chunk, parse_mode="HTML",
                                                      reply_to_message_id=reply_to)

        usage_id = await db_usage.record_usage(
            user_id=user_id, mode="geomancia", variant=variant,
            tokens_input=response.tokens_input, tokens_output=response.tokens_output,
            cost_usd=response.cost_usd, cached=response.cached, truncated=response.truncated,
            drawn_data=drawn_data,
        )

        if text_msg:
            try:
                await context.bot.send_message(chat_id, text="¿Qué te ha parecido la lectura?",
                                               reply_markup=feedback_keyboard(usage_id),
                                               reply_to_message_id=text_msg.message_id)
            except (BadRequest, Forbidden):
                pass

        record_cooldown(user_id)
    finally:
        release_user(user_id)
