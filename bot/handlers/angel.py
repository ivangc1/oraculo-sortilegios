"""Handler de /angel: consulta los 72 ángeles del Shem HaMephorash.

Cuatro modos:
- /angel → aleatorio sin pregunta
- /angel <nombre|numero|aleatorio> → selección sin pregunta
- /angel <nombre|numero> <pregunta> → selección + LLM interpreta
- /angel <pregunta> → aleatorio + LLM interpreta

Sin pregunta: solo ficha estática (€0 API).
Con pregunta: ficha + interpretación LLM usando los atributos del ángel
como lente contextual.

Datos en data/shem_datos.py (72 entradas). Anti-repetición por usuario.
"""

from __future__ import annotations

import asyncio
import random
import unicodedata
from pathlib import Path

from loguru import logger
from telegram import Update
from telegram.error import BadRequest, Forbidden
from telegram.ext import ContextTypes

from bot.concurrency import is_user_busy, mark_user_busy, release_user, get_semaphore
from bot.config import Settings
from bot.formatting import format_and_split
from bot.keyboards import feedback_keyboard
from bot.limits import check_limits, record_cooldown
from bot.messages import LIMIT_MESSAGES
from bot.middleware import middleware_check
from bot.typing import get_thread_id, with_typing
from database import usage as db_usage
from database import users as db_users
from service.interpreter import InterpreterService
from service.models import InterpretationRequest, UserProfile

_rng = random.SystemRandom()

_SHEM: list | None = None
_GOETIA: list | None = None

_LAST_ANGEL: dict[int, int] = {}


def _load_data() -> None:
    """Carga perezosa de datos de Shem y Goetia."""
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

    if q.isdigit():
        n = int(q)
        if 1 <= n <= len(_SHEM):
            return _SHEM[n - 1]
        return None

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


def _parse_args(args: list[str], user_id: int) -> tuple[dict, str | None]:
    """Parsea args. Devuelve (angel, pregunta_opcional)."""
    _load_data()

    if not args:
        return _get_random_angel(user_id), None

    first = args[0]

    if _normalize(first) == "aleatorio":
        angel = _get_random_angel(user_id)
        question = " ".join(args[1:]).strip() if len(args) > 1 else None
        return angel, question or None

    angel = _find_angel(first)
    if angel is not None:
        _LAST_ANGEL[user_id] = angel["number"]
        question = " ".join(args[1:]).strip() if len(args) > 1 else None
        return angel, question or None

    return _get_random_angel(user_id), " ".join(args).strip()


def _format_angel(angel: dict) -> str:
    """Formatea la ficha de un ángel para Telegram."""
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

    return "\n".join(lines) + demon_ref


async def angel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler de /angel — ficha estática + opcional interpretación LLM."""
    settings: Settings = context.bot_data["settings"]
    if not await middleware_check(update, context, settings):
        return

    _load_data()
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    msg = update.message

    args = context.args if context.args else []

    # Si hay un solo argumento y no matchea, es not_found explícito
    if args:
        first = args[0]
        if _normalize(first) != "aleatorio":
            candidate = _find_angel(first)
            if candidate is None and len(args) == 1:
                await msg.reply_text(
                    LIMIT_MESSAGES["angel_not_found"],
                    reply_to_message_id=msg.message_id,
                )
                return

    angel, question = _parse_args(args, user_id)

    # 1. Ficha estática siempre
    ficha_text = _format_angel(angel)
    chunks = format_and_split(
        ficha_text, use_blockquote=settings.use_blockquote_for("angel", "consulta"),
    )
    for chunk in chunks:
        await context.bot.send_message(
            chat_id=chat_id,
            text=chunk,
            parse_mode="HTML",
            message_thread_id=thread_id,
            reply_to_message_id=msg.message_id,
        )

    # 2. Sin pregunta: terminar
    if not question:
        logger.info(f"Ángel consultado (sin pregunta): user={user_id} → {angel['number']} ({angel['name']})")
        return

    # 3. Con pregunta: concurrencia + LLM
    if is_user_busy(user_id):
        await context.bot.send_message(
            chat_id, text=LIMIT_MESSAGES["request_in_progress"],
            message_thread_id=thread_id,
        )
        return

    limit_key = await check_limits(user_id, "angel", settings)
    if limit_key:
        await context.bot.send_message(
            chat_id, text=LIMIT_MESSAGES[limit_key],
            message_thread_id=thread_id,
        )
        return

    if len(question) > settings.MAX_QUESTION_LENGTH:
        question = question[:settings.MAX_QUESTION_LENGTH]

    mark_user_busy(user_id)
    try:
        user = await db_users.get_user(user_id)
        profile = UserProfile.from_db_or_guest(user, update)

        request = InterpretationRequest(
            mode="angel", variant="consulta",
            question=question, user_profile=profile,
            max_tokens=settings.get_max_tokens("angel", "consulta"),
            effort=settings.get_effort("angel", "consulta"),
            extra_data={"angel": angel},
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
            await context.bot.send_message(
                chat_id, text=LIMIT_MESSAGES["queue_timeout"],
                message_thread_id=thread_id,
            )
            return

        if response.error:
            error_key = {
                "timeout": "queue_timeout", "rate_limit": "rate_limit",
                "empty_response": "empty_response",
            }.get(response.error, "api_error")
            await context.bot.send_message(
                chat_id, text=LIMIT_MESSAGES.get(error_key, LIMIT_MESSAGES["api_error"]),
                message_thread_id=thread_id,
            )
            return

        text = response.text
        if response.truncated:
            text += LIMIT_MESSAGES["truncated"]

        chunks = format_and_split(
            text, use_blockquote=settings.use_blockquote_for("angel", "consulta"),
        )
        text_msg = None
        for chunk in chunks:
            text_msg = await context.bot.send_message(
                chat_id, text=chunk, parse_mode="HTML",
                message_thread_id=thread_id,
            )

        drawn_data = {
            "angel_number": angel["number"],
            "angel_name": angel["name"],
            "question_length": len(question),
        }
        usage_id = await db_usage.record_usage(
            user_id=user_id, mode="angel", variant="consulta",
            tokens_input=response.tokens_input, tokens_output=response.tokens_output,
            cost_usd=response.cost_usd, cached=response.cached, truncated=response.truncated,
            drawn_data=drawn_data,
        )

        if text_msg:
            try:
                await context.bot.send_message(
                    chat_id, text="¿Qué te ha parecido la lectura?",
                    reply_markup=feedback_keyboard(usage_id),
                    reply_to_message_id=text_msg.message_id,
                    message_thread_id=thread_id,
                )
            except (BadRequest, Forbidden):
                pass

        record_cooldown(user_id)
        logger.info(
            f"Ángel con pregunta: user={user_id} → {angel['number']} "
            f"({angel['name']}) | pregunta='{question[:50]}'"
        )
    finally:
        release_user(user_id)
