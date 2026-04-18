"""Handler de /sello: muestra SOLO el sigilo de un demonio Goetia, sin retrato ni ficha.

Útil para:
- Tatuajes, prints, grabados.
- Meditación / evocación sin "ruido" visual.
- Copy-paste limpio del símbolo.

Tres modos:
- /sello → aleatorio
- /sello <nombre|número> → sigilo específico
- Sin LLM: €0 API, respuesta inmediata.

Datos: reutiliza GOETIA de data/goetia_datos.py y los sigilos de
assets/goetia_sigils/NN.png (72 PNG de Wikimedia, dominio público).
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger
from telegram import Update
from telegram.error import BadRequest, Forbidden
from telegram.ext import ContextTypes

from bot.config import Settings
from bot.handlers.demonio import (
    _find_demon,
    _get_random_demon,
    _load_data,
    _normalize,
    _sigil_path,
)
from bot.messages import LIMIT_MESSAGES
from bot.middleware import middleware_check
from bot.typing import get_thread_id


async def sello_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler de /sello — envía solo el sigilo canónico del demonio."""
    settings: Settings = context.bot_data["settings"]
    if not await middleware_check(update, context, settings):
        return

    _load_data()
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    msg = update.message

    args = context.args if context.args else []

    # Resolver demonio
    demon: dict | None = None
    if not args or _normalize(args[0]) == "aleatorio":
        demon = _get_random_demon(user_id)
    else:
        demon = _find_demon(args[0])
        if demon is None:
            await msg.reply_text(
                LIMIT_MESSAGES.get(
                    "demon_not_found",
                    "Ese demonio no habita en el Ars Goetia. Prueba con otro nombre o un número del 1 al 72.",
                ),
                reply_to_message_id=msg.message_id,
            )
            return

    sigil = _sigil_path(demon["number"])
    if sigil is None:
        logger.warning(f"Sello no encontrado para {demon['name']} (#{demon['number']})")
        await msg.reply_text(
            f"No tengo el sello de {demon['name']} en el archivo. Prueba con otro.",
            reply_to_message_id=msg.message_id,
        )
        return

    caption = (
        f"🔻 Sello de {demon['name']}\n"
        f"Nº {demon['number']} · {demon['rank']} del Infierno"
    )
    try:
        with open(sigil, "rb") as f:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=f,
                caption=caption,
                message_thread_id=thread_id,
                reply_to_message_id=msg.message_id,
            )
        logger.info(f"Sello: user={user_id} → #{demon['number']} {demon['name']}")
    except (BadRequest, Forbidden) as e:
        logger.warning(f"No se pudo enviar sello de {demon['name']}: {e}")
        await msg.reply_text(
            "No pude enviar el sello. Intenta de nuevo en un momento.",
            reply_to_message_id=msg.message_id,
        )
