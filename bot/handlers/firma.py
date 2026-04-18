"""Handler de /firma: muestra el nombre hebreo de un ángel del Shem
HaMephorash sobre pergamino, con coro, atributo y salmo.

A diferencia de /angel (que enseña el ángel e interpreta una pregunta con
su lente), /firma es **solo la estampa**: la firma sagrada del ángel lista
para meditar, imprimir, tatuar o contemplar.

Modos:
- /firma → aleatorio
- /firma <nombre|número> → firma específica

Sin LLM. €0 API. Respuesta inmediata con imagen 1024x1536.

Datos: SHEM de data/shem_datos.py (72 ángeles).
Imágenes: assets/shem_firmas/NN.png (generadas con
scripts/generate_shem_firmas.py).
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger
from telegram import Update
from telegram.error import BadRequest, Forbidden
from telegram.ext import ContextTypes

from bot.config import Settings
from bot.handlers.angel import (
    _find_angel,
    _get_random_angel,
    _load_data,
    _normalize,
)
from bot.messages import LIMIT_MESSAGES
from bot.middleware import middleware_check
from bot.typing import get_thread_id


_ASSETS_DIR = Path(__file__).parent.parent.parent / "assets"


def _firma_path(angel_number: int) -> Path | None:
    """Devuelve el path de la firma del ángel si existe.

    Las firmas se generan con scripts/generate_shem_firmas.py y se guardan
    en assets/shem_firmas/NN.png.
    """
    path = _ASSETS_DIR / "shem_firmas" / f"{angel_number:02d}.png"
    return path if path.exists() else None


async def firma_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler de /firma — envía la firma hebrea del ángel sobre pergamino."""
    settings: Settings = context.bot_data["settings"]
    if not await middleware_check(update, context, settings):
        return

    _load_data()
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    msg = update.message

    args = context.args if context.args else []

    # Resolver ángel
    angel: dict | None = None
    if not args or _normalize(args[0]) == "aleatorio":
        angel = _get_random_angel(user_id)
    else:
        angel = _find_angel(args[0])
        if angel is None:
            await msg.reply_text(
                LIMIT_MESSAGES.get(
                    "angel_not_found",
                    "Ese ángel no está en el Shem HaMephorash. Prueba con otro nombre o un número del 1 al 72.",
                ),
                reply_to_message_id=msg.message_id,
            )
            return

    firma = _firma_path(angel["number"])
    if firma is None:
        logger.warning(
            f"Firma no encontrada para {angel['name']} (#{angel['number']})"
        )
        await msg.reply_text(
            f"No tengo la firma de {angel['name']} en el archivo. "
            "Ejecuta scripts/generate_shem_firmas.py.",
            reply_to_message_id=msg.message_id,
        )
        return

    caption = (
        f"🔺 Firma de {angel['name']}\n"
        f"Nº {angel['number']} · {angel['choir']} · "
        f"{angel.get('name_hebrew', '')}"
    )
    try:
        with open(firma, "rb") as f:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=f,
                caption=caption,
                message_thread_id=thread_id,
                reply_to_message_id=msg.message_id,
            )
        logger.info(
            f"Firma: user={user_id} → #{angel['number']} {angel['name']} ({angel['choir']})"
        )
    except (BadRequest, Forbidden) as e:
        logger.warning(f"No se pudo enviar firma de {angel['name']}: {e}")
        await msg.reply_text(
            "No pude enviar la firma. Intenta de nuevo en un momento.",
            reply_to_message_id=msg.message_id,
        )
