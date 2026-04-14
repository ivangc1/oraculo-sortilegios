"""Handler de /demonio: consulta los 72 demonios del Ars Goetia.

Cuatro modos:
- /demonio → aleatorio sin pregunta
- /demonio <nombre|numero|aleatorio> → selección sin pregunta
- /demonio <nombre|numero> <pregunta> → selección + LLM interpreta
- /demonio <pregunta> → aleatorio + LLM interpreta

Sin pregunta: solo ficha estática (€0 API).
Con pregunta: ficha + interpretación LLM usando los atributos del demonio
como lente contextual.

Datos en data/goetia_datos.py (72 entradas). Anti-repetición por usuario.
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

# Cache global
_GOETIA: list | None = None
_SHEM: list | None = None

# Anti-repetición por usuario
_LAST_DEMON: dict[int, int] = {}


def _load_data() -> None:
    """Carga perezosa de datos de Goetia y Shem."""
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

    if q.isdigit():
        n = int(q)
        if 1 <= n <= len(_GOETIA):
            return _GOETIA[n - 1]
        return None

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


def _parse_args(args: list[str], user_id: int) -> tuple[dict, str | None]:
    """Parsea los argumentos del comando.

    Returns:
        (demon, question): el demonio seleccionado y pregunta opcional.

    Casos:
    - [] → random, sin pregunta
    - ["aleatorio"] → random, sin pregunta
    - ["aleatorio", ...pregunta] → random, con pregunta
    - ["bael"] → Bael, sin pregunta
    - ["bael", ...pregunta] → Bael, con pregunta
    - ["1"] → demonio 1, sin pregunta
    - [...pregunta que no es nombre] → random, con pregunta
    """
    _load_data()

    if not args:
        return _get_random_demon(user_id), None

    first = args[0]

    # Explícito "aleatorio"
    if _normalize(first) == "aleatorio":
        demon = _get_random_demon(user_id)
        question = " ".join(args[1:]).strip() if len(args) > 1 else None
        return demon, question or None

    # Probar si el primero es un nombre/número válido
    demon = _find_demon(first)
    if demon is not None:
        _LAST_DEMON[user_id] = demon["number"]
        question = " ".join(args[1:]).strip() if len(args) > 1 else None
        return demon, question or None

    # No es un demonio → tratar todo como pregunta, random
    return _get_random_demon(user_id), " ".join(args).strip()


def _sigil_path(demon_number: int) -> Path | None:
    """Devuelve el path del sello del demonio si existe, None si no.

    Los sellos se descargan con scripts/download_sigils.py y se guardan
    en assets/goetia_sigils/NN.png (nombrado por número de demonio).
    """
    path = (
        Path(__file__).parent.parent.parent
        / "assets" / "goetia_sigils" / f"{demon_number:02d}.png"
    )
    return path if path.exists() else None


def _format_demon(demon: dict) -> str:
    """Formatea la ficha de un demonio para Telegram (marcadores [[T]][[C]])."""
    angel_num = demon.get("corresponding_angel")
    angel_ref = ""
    if angel_num and _SHEM and 1 <= angel_num <= len(_SHEM):
        angel = _SHEM[angel_num - 1]
        angel_ref = f"\n\n🔺 [[T]]Ángel correspondiente:[[/T]] [[C]]{angel['name']}[[/C]] ({angel['choir']}) — /angel {angel_num}"

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

    return "\n".join(lines) + angel_ref


async def demonio_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler de /demonio — ficha estática, opcionalmente con interpretación LLM."""
    settings: Settings = context.bot_data["settings"]
    if not await middleware_check(update, context, settings):
        return

    _load_data()
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    msg = update.message

    args = context.args if context.args else []

    # Parsear: si el primero es un token reservado (nombre/número/aleatorio),
    # lo procesamos; si no, todo es pregunta → random.
    if args:
        first = args[0]
        if _normalize(first) != "aleatorio":
            # Comprobar si el primero es un demonio válido antes de parsear
            candidate = _find_demon(first)
            if candidate is None and len(args) >= 1:
                # No es un demonio. Todo el texto es pregunta → random.
                # EXCEPCIÓN: si hay solo 1 argumento (p.ej. "bael" malescrito),
                # lo tratamos como not_found explícito.
                if len(args) == 1:
                    await msg.reply_text(
                        LIMIT_MESSAGES["demon_not_found"],
                        reply_to_message_id=msg.message_id,
                    )
                    return

    demon, question = _parse_args(args, user_id)

    # 1. Enviar sello (si existe localmente)
    sigil = _sigil_path(demon["number"])
    if sigil:
        try:
            with open(sigil, "rb") as f:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=f,
                    caption=f"🔻 Sello de {demon['name']}",
                    message_thread_id=thread_id,
                    reply_to_message_id=msg.message_id,
                )
        except (BadRequest, Forbidden) as e:
            logger.warning(f"No se pudo enviar sello de {demon['name']}: {e}")
            # Continuar con la ficha igual

    # 2. Enviar ficha estática
    ficha_text = _format_demon(demon)
    chunks = format_and_split(
        ficha_text, use_blockquote=settings.use_blockquote_for("demonio", "consulta"),
    )
    for chunk in chunks:
        await context.bot.send_message(
            chat_id=chat_id,
            text=chunk,
            parse_mode="HTML",
            message_thread_id=thread_id,
            reply_to_message_id=msg.message_id,
        )

    # 2. Sin pregunta: terminar aquí
    if not question:
        logger.info(f"Demonio consultado (sin pregunta): user={user_id} → {demon['number']} ({demon['name']})")
        return

    # 3. Con pregunta: verificar concurrencia y límites, llamar LLM
    if is_user_busy(user_id):
        await context.bot.send_message(
            chat_id, text=LIMIT_MESSAGES["request_in_progress"],
            message_thread_id=thread_id,
        )
        return

    limit_key = await check_limits(user_id, "demonio", settings)
    if limit_key:
        await context.bot.send_message(
            chat_id, text=LIMIT_MESSAGES[limit_key],
            message_thread_id=thread_id,
        )
        return

    # Sanitizar pregunta
    if len(question) > settings.MAX_QUESTION_LENGTH:
        question = question[:settings.MAX_QUESTION_LENGTH]

    mark_user_busy(user_id)
    try:
        user = await db_users.get_user(user_id)
        profile = UserProfile.from_db_or_guest(user, update)

        request = InterpretationRequest(
            mode="demonio", variant="consulta",
            question=question, user_profile=profile,
            max_tokens=settings.get_max_tokens("demonio", "consulta"),
            effort=settings.get_effort("demonio", "consulta"),
            extra_data={"demon": demon},
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
            text, use_blockquote=settings.use_blockquote_for("demonio", "consulta"),
        )
        text_msg = None
        for chunk in chunks:
            text_msg = await context.bot.send_message(
                chat_id, text=chunk, parse_mode="HTML",
                message_thread_id=thread_id,
            )

        drawn_data = {
            "demon_number": demon["number"],
            "demon_name": demon["name"],
            "question_length": len(question),
        }
        usage_id = await db_usage.record_usage(
            user_id=user_id, mode="demonio", variant="consulta",
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
            f"Demonio con pregunta: user={user_id} → {demon['number']} "
            f"({demon['name']}) | pregunta='{question[:50]}'"
        )
    finally:
        release_user(user_id)
