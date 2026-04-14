"""Handler de /demonio: consulta los 72 demonios del Ars Goetia.

Tres modos:
- /demonio → aleatorio
- /demonio aleatorio → explícito aleatorio
- /demonio bael / /demonio 1 → búsqueda por nombre o número

Datos en data/goetia_datos.py (72 entradas).
Anti-repetición por usuario (no repite el último mostrado a ese user).
"""

from __future__ import annotations

import random
import unicodedata
from pathlib import Path

from loguru import logger
from telegram import Update
from telegram.ext import ContextTypes

from bot.config import Settings
from bot.formatting import format_and_split
from bot.messages import LIMIT_MESSAGES
from bot.middleware import middleware_check
from bot.typing import get_thread_id

_rng = random.SystemRandom()

# Cache global de datos
_GOETIA: list | None = None
_SHEM: list | None = None

# Anti-repetición: user_id -> último número mostrado
_LAST_DEMON: dict[int, int] = {}


def _load_data() -> None:
    """Carga perezosa de los datos de Goetia y Shem."""
    global _GOETIA, _SHEM
    if _GOETIA is not None and _SHEM is not None:
        return

    base = Path(__file__).parent.parent.parent / "data"

    goetia_path = base / "goetia_datos.py"
    with open(goetia_path, encoding="utf-8") as f:
        source = f.read()
    ns: dict = {}
    exec(compile(source, str(goetia_path), "exec"), ns)
    _GOETIA = ns.get("GOETIA", [])

    shem_path = base / "shem_datos.py"
    with open(shem_path, encoding="utf-8") as f:
        source = f.read()
    ns = {}
    exec(compile(source, str(shem_path), "exec"), ns)
    _SHEM = ns.get("SHEM", [])

    logger.info(
        f"Goetia cargada: {len(_GOETIA)} demonios, "
        f"Shem cargada: {len(_SHEM)} ángeles"
    )


def _normalize(s: str) -> str:
    """Normaliza texto para búsqueda: sin acentos, lowercase, strip."""
    s = s.strip().lower()
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _find_demon(query: str) -> dict | None:
    """Busca un demonio por número o nombre (tolerante a mayúsculas y acentos)."""
    _load_data()
    if not query:
        return None

    q = _normalize(query)

    # Por número
    if q.isdigit():
        n = int(q)
        if 1 <= n <= len(_GOETIA):
            return _GOETIA[n - 1]
        return None

    # Por nombre o variante
    for d in _GOETIA:
        if _normalize(d["name"]) == q:
            return d
        for variant in d.get("name_variants", []):
            if _normalize(variant) == q:
                return d
    return None


def _get_random_demon(user_id: int) -> dict:
    """Devuelve un demonio aleatorio, evitando repetir el último del user."""
    _load_data()
    last = _LAST_DEMON.get(user_id)
    candidates = [d for d in _GOETIA if d["number"] != last]
    chosen = _rng.choice(candidates) if candidates else _rng.choice(_GOETIA)
    _LAST_DEMON[user_id] = chosen["number"]
    return chosen


def _format_demon(demon: dict) -> str:
    """Formatea la ficha de un demonio para mostrar en Telegram.

    Usa marcadores [[T]] y [[C]] que format_and_split convierte a HTML.
    """
    # Buscar ángel correspondiente para mostrar el par
    angel_num = demon.get("corresponding_angel")
    angel_ref = ""
    if angel_num and _SHEM and 1 <= angel_num <= len(_SHEM):
        angel = _SHEM[angel_num - 1]
        angel_ref = f"\n\n🔺 [[T]]Ángel correspondiente:[[/T]] [[C]]{angel['name']}[[/C]] ({angel['choir']}) — /angel {angel_num}"

    # Regencia
    regencia_parts = []
    if demon.get("day_night"):
        regencia_parts.append(demon["day_night"].capitalize())
    if demon.get("planet"):
        regencia_parts.append(demon["planet"])
    if demon.get("zodiac"):
        regencia_parts.append(demon["zodiac"])
    if demon.get("element"):
        regencia_parts.append(demon["element"])
    regencia = " · ".join(regencia_parts)

    lines = [
        f"🔻 [[T]]Nº {demon['number']} — {demon['name']}[[/T]]",
        f"[[C]]{demon['rank']} del Infierno · {demon['legions']} legiones[[/C]]",
        "",
        f"⚡ [[T]]Regencia:[[/T]] {regencia}",
        "",
        f"👁 [[T]]Apariencia:[[/T]] {demon['appearance']}",
        "",
        f"💀 [[T]]Poderes:[[/T]] {demon['powers']}",
        "",
        f"📜 [[T]]Descripción:[[/T]] {demon['description']}",
    ]

    text = "\n".join(lines) + angel_ref
    return text


async def demonio_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler de /demonio — consulta demonio del Ars Goetia."""
    settings: Settings = context.bot_data["settings"]
    if not await middleware_check(update, context, settings):
        return

    _load_data()
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    msg = update.message

    # Parsear args
    args = context.args if context.args else []

    if not args or (len(args) == 1 and _normalize(args[0]) == "aleatorio"):
        demon = _get_random_demon(user_id)
    else:
        # Intentar buscar por el primer argumento (puede ser nombre compuesto si hay espacios)
        query = " ".join(args)
        demon = _find_demon(query)

        if demon is None:
            await msg.reply_text(
                LIMIT_MESSAGES["demon_not_found"],
                reply_to_message_id=msg.message_id,
            )
            return
        # Actualizar anti-repetición también en búsquedas directas
        _LAST_DEMON[user_id] = demon["number"]

    # Formatear y enviar
    text = _format_demon(demon)
    chunks = format_and_split(
        text, use_blockquote=settings.use_blockquote_for("demonio", "consulta"),
    )

    for chunk in chunks:
        await context.bot.send_message(
            chat_id=chat_id,
            text=chunk,
            parse_mode="HTML",
            message_thread_id=thread_id,
            reply_to_message_id=msg.message_id,
        )

    logger.info(f"Demonio consultado: user={user_id} → {demon['number']} ({demon['name']})")
