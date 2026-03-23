"""Typing indicator renovado cada 4s con error handling."""

import asyncio

from telegram import Bot
from telegram.error import BadRequest, Forbidden
from telegram.constants import ChatAction


async def keep_typing(chat_id: int, bot: Bot) -> None:
    """Envía typing cada 4s hasta que la task se cancele."""
    while True:
        try:
            await bot.send_chat_action(chat_id, ChatAction.TYPING)
        except (Forbidden, BadRequest):
            return  # Bot removido o sin permisos
        except Exception:
            return  # Cualquier otro error, dejar de intentar
        await asyncio.sleep(4)


async def with_typing(chat_id: int, bot: Bot, coro):
    """Ejecuta una corrutina mientras muestra typing indicator."""
    typing_task = asyncio.create_task(keep_typing(chat_id, bot))
    try:
        result = await coro
    finally:
        typing_task.cancel()
        try:
            await typing_task
        except asyncio.CancelledError:
            pass
    return result
