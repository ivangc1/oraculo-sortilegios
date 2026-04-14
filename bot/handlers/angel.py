"""Handler de /angel: consulta los 72 ángeles del Shem HaMephorash.

Tres modos:
- /angel → aleatorio
- /angel aleatorio → explícito aleatorio
- /angel vehuiah / /angel 1 → búsqueda por nombre o número

Datos en data/shem_datos.py (72 entradas).
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

# Cache global
_SHEM: list | None = None
_GOETIA: list | None = None

# Anti-repetición: user_id -> último número mostrado
_LAST_ANGEL: dict[int, int] = {}


def _load_data() -> None:
    """Carga perezosa de los datos de Shem y Goetia."""
    global _SHEM, _GOETIA
    if _SHEM is not None and _GOETIA is not None:
        return

    base = Path(__file__).parent.parent.parent / "data"

    shem_path = base / "shem_datos.py"
    with open(shem_path, encoding="utf-8") as f:
        source = f.read()
    ns: dict = {}
    exec(compile(source, str(shem_path), "exec"), ns)
    _SHEM = ns.get("SHEM", [])

    goetia_path = base / "goetia_datos.py"
    with open(goetia_path, encoding="utf-8") as f:
        source = f.read()
    ns = {}
    exec(compile(source, str(goetia_path), "exec"), ns)
    _GOETIA = ns.get("GOETIA", [])

    logger.info(
        f"Shem cargada: {len(_SHEM)} ángeles, "
        f"Goetia cargada: {len(_GOETIA)} demonios"
    )


def _normalize(s: str) -> str:
    """Normaliza texto para búsqueda: sin acentos, lowercase, strip."""
    s = s.strip().lower()
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _find_angel(query: str) -> dict | None:
    """Busca un ángel por número o nombre (tolerante a mayúsculas y acentos)."""
    _load_data()
    if not query:
        return None

    q = _normalize(query)

    # Por número
    if q.isdigit():
        n = int(q)
        if 1 <= n <= len(_SHEM):
            return _SHEM[n - 1]
        return None

    # Por nombre o variante
    for a in _SHEM:
        if _normalize(a["name"]) == q:
            return a
        for variant in a.get("name_variants", []):
            if _normalize(variant) == q:
                return a
    return None


def _get_random_angel(user_id: int) -> dict:
    """Devuelve un ángel aleatorio, evitando repetir el último del user."""
    _load_data()
    last = _LAST_ANGEL.get(user_id)
    candidates = [a for a in _SHEM if a["number"] != last]
    chosen = _rng.choice(candidates) if candidates else _rng.choice(_SHEM)
    _LAST_ANGEL[user_id] = chosen["number"]
    return chosen


def _format_angel(angel: dict) -> str:
    """Formatea la ficha de un ángel para mostrar en Telegram."""
    # Buscar demonio correspondiente para mostrar el par
    demon_num = angel.get("corresponding_demon")
    demon_ref = ""
    if demon_num and _GOETIA and 1 <= demon_num <= len(_GOETIA):
        demon = _GOETIA[demon_num - 1]
        demon_ref = f"\n\n🔻 [[T]]Demonio correspondiente:[[/T]] [[C]]{demon['name']}[[/C]] ({demon['rank']}) — /demonio {demon_num}"

    lines = [
        f"🔺 [[T]]Nº {angel['number']} — {angel['name']}[[/T]] {angel.get('name_hebrew', '')}",
        f"[[C]]{angel['choir']}[[/C]]",
        "",
        f"✨ [[T]]Atributo divino:[[/T]] {angel['attribute']}",
        "",
        f"📖 [[T]]Salmo:[[/T]] {angel['psalm']}",
        "",
        f"📅 [[T]]Regencia:[[/T]] {angel['day_regency']} · {angel['hour_regency']}",
        "",
        f"💫 [[T]]Virtud:[[/T]] {angel['virtue']}",
        "",
        f"📜 [[T]]Descripción:[[/T]] {angel['description']}",
    ]

    text = "\n".join(lines) + demon_ref
    return text


async def angel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler de /angel — consulta ángel del Shem HaMephorash."""
    settings: Settings = context.bot_data["settings"]
    if not await middleware_check(update, context, settings):
        return

    _load_data()
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    msg = update.message

    args = context.args if context.args else []

    if not args or (len(args) == 1 and _normalize(args[0]) == "aleatorio"):
        angel = _get_random_angel(user_id)
    else:
        query = " ".join(args)
        angel = _find_angel(query)

        if angel is None:
            await msg.reply_text(
                LIMIT_MESSAGES["angel_not_found"],
                reply_to_message_id=msg.message_id,
            )
            return
        _LAST_ANGEL[user_id] = angel["number"]

    text = _format_angel(angel)
    chunks = format_and_split(
        text, use_blockquote=settings.use_blockquote_for("angel", "consulta"),
    )

    for chunk in chunks:
        await context.bot.send_message(
            chat_id=chat_id,
            text=chunk,
            parse_mode="HTML",
            message_thread_id=thread_id,
            reply_to_message_id=msg.message_id,
        )

    logger.info(f"Ángel consultado: user={user_id} → {angel['number']} ({angel['name']})")
