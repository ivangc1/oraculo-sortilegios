"""Pipeline común de interpretación LLM compartido por todos los handlers de modo.

Concentra la secuencia que se duplicaba en 9 handlers: llamada al interpreter
con timeout + typing, mapeo de errores a mensajes, troceo y envío de la
respuesta, registro de uso, prompt de feedback y registro de cooldown.

Pre-condiciones (responsabilidad del caller):
- middleware_check + check_limits + is_user_busy ya pasados.
- mark_user_busy ya invocado; release_user en su propio `finally`.
- request preparado con mode/variant/drawn_items/extra_data según el dominio.

Variantes de presentación:
- `anchor_msg=None`: handlers sin foto previa (oraculo, demonio, angel,
  numerologia). Chunks y errores se envían flat, sin `reply_to`.
- `anchor_msg=<Message>`: handlers con foto/resumen previo (tarot, runas,
  iching, geomancia, natal). Errores y primer chunk responden al anchor;
  chunks siguientes encadenan al chunk anterior.
"""

from __future__ import annotations

import asyncio

from telegram.error import BadRequest, Forbidden

from bot.concurrency import get_semaphore
from bot.config import Settings
from bot.formatting import format_and_split
from bot.keyboards import feedback_keyboard
from bot.limits import record_cooldown
from bot.messages import LIMIT_MESSAGES
from bot.typing import with_typing
from database import usage as db_usage
from service.interpreter import InterpreterService
from service.models import InterpretationRequest


_ERROR_KEY_MAP = {
    "timeout": "queue_timeout",
    "rate_limit": "rate_limit",
    "empty_response": "empty_response",
}


async def run_interpretation(
    *,
    bot,
    chat_id: int,
    thread_id: int | None,
    user_id: int,
    settings: Settings,
    interpreter: InterpreterService,
    request: InterpretationRequest,
    mode: str,
    variant: str,
    drawn_data: dict,
    anchor_msg=None,
) -> bool:
    """Ejecuta la pipeline. Devuelve True si la interpretación se entregó al
    usuario (éxito), False si se cortó por timeout o error de la API."""
    semaphore = get_semaphore()
    anchor_id = anchor_msg.message_id if anchor_msg else None

    async def _interpret():
        async with semaphore:
            return await interpreter.interpret(request)

    try:
        response = await asyncio.wait_for(
            with_typing(chat_id, bot, _interpret()),
            timeout=settings.QUEUE_TIMEOUT,
        )
    except asyncio.TimeoutError:
        await bot.send_message(
            chat_id,
            text=LIMIT_MESSAGES["queue_timeout"],
            reply_to_message_id=anchor_id,
            message_thread_id=thread_id,
        )
        return False

    if response.error:
        error_key = _ERROR_KEY_MAP.get(response.error, "api_error")
        await bot.send_message(
            chat_id,
            text=LIMIT_MESSAGES.get(error_key, LIMIT_MESSAGES["api_error"]),
            reply_to_message_id=anchor_id,
            message_thread_id=thread_id,
        )
        # Registrar el coste de los intentos fallidos para que `/stats`
        # refleje el gasto real contra Anthropic. response.cost_usd suma
        # todos los intentos (incluyendo el empty que precede al retry).
        if response.cost_usd > 0 or response.tokens_input > 0:
            await db_usage.record_usage(
                user_id=user_id,
                mode=mode,
                variant=f"{variant}:{response.error}",
                tokens_input=response.tokens_input,
                tokens_output=response.tokens_output,
                cost_usd=response.cost_usd,
                cached=response.cached,
                truncated=False,
                drawn_data={**drawn_data, "error": response.error},
            )
        return False

    text = (response.text or "").strip()
    if not text:
        # Respuesta sin error pero vacía: tratar como `empty_response` para
        # que el usuario reciba un mensaje claro en vez de un BadRequest de
        # Telegram al intentar enviar texto vacío.
        await bot.send_message(
            chat_id,
            text=LIMIT_MESSAGES["empty_response"],
            reply_to_message_id=anchor_id,
            message_thread_id=thread_id,
        )
        if response.cost_usd > 0 or response.tokens_input > 0:
            await db_usage.record_usage(
                user_id=user_id,
                mode=mode,
                variant=f"{variant}:empty",
                tokens_input=response.tokens_input,
                tokens_output=response.tokens_output,
                cost_usd=response.cost_usd,
                cached=response.cached,
                truncated=False,
                drawn_data={**drawn_data, "error": "empty_after_strip"},
            )
        return False

    if response.truncated:
        text += LIMIT_MESSAGES["truncated"]

    chunks = format_and_split(text, use_blockquote=settings.use_blockquote_for(mode, variant))
    text_msg = None
    for i, chunk in enumerate(chunks):
        if anchor_id is None:
            reply_to = None
        else:
            reply_to = anchor_id if i == 0 else (text_msg.message_id if text_msg else None)
        text_msg = await bot.send_message(
            chat_id,
            text=chunk,
            parse_mode="HTML",
            reply_to_message_id=reply_to,
            message_thread_id=thread_id,
        )

    usage_id = await db_usage.record_usage(
        user_id=user_id,
        mode=mode,
        variant=variant,
        tokens_input=response.tokens_input,
        tokens_output=response.tokens_output,
        cost_usd=response.cost_usd,
        cached=response.cached,
        truncated=response.truncated,
        drawn_data=drawn_data,
    )

    if text_msg:
        try:
            await bot.send_message(
                chat_id,
                text="¿Qué te ha parecido la lectura?",
                reply_markup=feedback_keyboard(usage_id),
                reply_to_message_id=text_msg.message_id,
                message_thread_id=thread_id,
            )
        except (BadRequest, Forbidden):
            pass

    record_cooldown(user_id)
    return True
