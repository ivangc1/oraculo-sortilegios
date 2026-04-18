"""Handler de /invocar: Claude adopta la personalidad del demonio o ángel.

A diferencia de /demonio y /angel (que interpretan CON la entidad como lente),
/invocar hace que Claude HABLE COMO la entidad, en primera persona, con su
personalidad canónica. SIEMPRE llama al LLM — esa es la semántica de "invocar".

Modos de uso:
- /invocar <nombre> [pregunta]
    Busca en GOETIA primero, luego en SHEM. Si el nombre es ambiguo no lo
    habrá — los nombres de demonios y ángeles nunca coinciden.

- /invocar demonio <nombre|número> [pregunta]
- /invocar angel <nombre|número> [pregunta]
    Fuerza el tipo. Útil con números (1-72 existe en ambos sets).

- /invocar <número> [pregunta]
    Por defecto trata el número como demonio Goetia.

Sin pregunta: el ente se presenta en primera persona — manifestación inaugural
(el LLM se llama igualmente; /invocar no existiría si no fuera así).
Con pregunta: el ente responde en primera persona como ese ser.

Reutiliza:
- _find_demon, _get_random_demon, _load_data, _normalize, _demon_image_path,
  _format_demon   desde bot.handlers.demonio
- _find_angel, _get_random_angel, _format_angel   desde bot.handlers.angel
"""

from __future__ import annotations

import asyncio

from loguru import logger
from telegram import Update
from telegram.error import BadRequest, Forbidden
from telegram.ext import ContextTypes

from bot.concurrency import get_semaphore, is_user_busy, mark_user_busy, release_user
from bot.config import Settings
from bot.formatting import format_and_split
from bot.handlers.angel import (
    _find_angel,
    _format_angel,
    _get_random_angel,
    _load_data as _load_angel_data,
)
from bot.handlers.demonio import (
    _demon_image_path,
    _find_demon,
    _format_demon,
    _get_random_demon,
    _load_data as _load_demon_data,
    _normalize,
)
from bot.handlers.firma import _firma_path
from bot.keyboards import feedback_keyboard
from bot.limits import check_limits, record_cooldown
from bot.messages import LIMIT_MESSAGES
from bot.middleware import middleware_check
from bot.typing import get_thread_id, with_typing
from database import usage as db_usage
from database import users as db_users
from service.interpreter import InterpreterService
from service.models import InterpretationRequest, UserProfile


_TYPE_KEYWORDS_DEMON = {"demonio", "demon", "demono"}
_TYPE_KEYWORDS_ANGEL = {"angel", "ángel", "angeles", "shem"}


def _parse_invocar_args(
    args: list[str], user_id: int
) -> tuple[dict | None, str, str | None, str | None]:
    """Parsea los args de /invocar.

    Returns:
        (entity, entity_type, question, error_key)

        - entity: dict con la entidad invocada, o None si error.
        - entity_type: "demonio" | "angel" | "" (si error).
        - question: str | None — la pregunta opcional.
        - error_key: clave de LIMIT_MESSAGES para rechazar, o None si OK.
    """
    _load_demon_data()
    _load_angel_data()

    if not args:
        # Sin args: aleatorio entre demonio o ángel (50/50)
        import random
        if random.SystemRandom().random() < 0.5:
            return _get_random_demon(user_id), "demonio", None, None
        else:
            return _get_random_angel(user_id), "angel", None, None

    # Detectar tipo explícito en el primer token
    first = _normalize(args[0])
    forced_type: str | None = None
    rest = args
    if first in _TYPE_KEYWORDS_DEMON:
        forced_type = "demonio"
        rest = args[1:]
    elif first in _TYPE_KEYWORDS_ANGEL:
        forced_type = "angel"
        rest = args[1:]

    if not rest:
        # Solo se dio "demonio" o "angel" sin identificador → aleatorio del tipo
        if forced_type == "demonio":
            return _get_random_demon(user_id), "demonio", None, None
        if forced_type == "angel":
            return _get_random_angel(user_id), "angel", None, None
        return None, "", None, "invocar_not_found"

    identifier = rest[0]
    question = " ".join(rest[1:]).strip() if len(rest) > 1 else None
    question = question or None

    # Resolver según tipo forzado o detección automática
    if forced_type == "demonio":
        demon = _find_demon(identifier)
        if demon is None:
            return None, "", None, "demon_not_found"
        return demon, "demonio", question, None

    if forced_type == "angel":
        angel = _find_angel(identifier)
        if angel is None:
            return None, "", None, "angel_not_found"
        return angel, "angel", question, None

    # Sin tipo forzado: número por defecto demonio, nombre cruza ambos
    if _normalize(identifier).isdigit():
        demon = _find_demon(identifier)
        if demon is not None:
            return demon, "demonio", question, None
        return None, "", None, "invocar_not_found"

    demon = _find_demon(identifier)
    if demon is not None:
        return demon, "demonio", question, None

    angel = _find_angel(identifier)
    if angel is not None:
        return angel, "angel", question, None

    # Primer token no matchea nada; tratar todo como pregunta + aleatorio demonio
    full_text = " ".join(args).strip()
    return _get_random_demon(user_id), "demonio", full_text or None, None


async def _send_entity_image(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    thread_id: int | None,
    reply_to: int,
    entity: dict,
    entity_type: str,
) -> None:
    """Envía la imagen de la entidad (carta demonio o placeholder ángel)."""
    if entity_type == "demonio":
        image_path, image_type = _demon_image_path(entity["number"])
        if image_path is None:
            return
        caption = (
            f"🔻 Invocación de {entity['name']}\n"
            f"Nº {entity['number']} · {entity['rank']} del Infierno · "
            f"{entity['legions']} legiones"
        )
        try:
            with open(image_path, "rb") as f:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=f,
                    caption=caption,
                    message_thread_id=thread_id,
                    reply_to_message_id=reply_to,
                )
        except (BadRequest, Forbidden) as e:
            logger.warning(
                f"No se pudo enviar {image_type} de {entity['name']}: {e}"
            )
        return

    # Ángel: enviar la firma hebrea del Shem (assets/shem_firmas/NN.png)
    firma = _firma_path(entity["number"])
    caption = (
        f"🔺 Invocación de {entity['name']}\n"
        f"Nº {entity['number']} · {entity['choir']} · "
        f"{entity.get('name_hebrew', '')}"
    )
    if firma is not None:
        try:
            with open(firma, "rb") as f:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=f,
                    caption=caption,
                    message_thread_id=thread_id,
                    reply_to_message_id=reply_to,
                )
            return
        except (BadRequest, Forbidden) as e:
            logger.warning(f"No se pudo enviar firma de {entity['name']}: {e}")
            # fallback a mensaje de texto
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=caption,
            message_thread_id=thread_id,
            reply_to_message_id=reply_to,
        )
    except (BadRequest, Forbidden):
        pass


async def invocar_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler de /invocar — Claude habla como la entidad invocada."""
    settings: Settings = context.bot_data["settings"]
    if not await middleware_check(update, context, settings):
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    msg = update.message

    args = context.args if context.args else []
    entity, entity_type, question, error_key = _parse_invocar_args(args, user_id)

    if error_key or entity is None:
        await msg.reply_text(
            LIMIT_MESSAGES.get(
                error_key or "invocar_not_found",
                "No pude identificar a esa entidad. Usa /invocar <nombre> o /invocar demonio|angel <nombre|número>.",
            ),
            reply_to_message_id=msg.message_id,
        )
        return

    # 1. Imagen + header de invocación
    await _send_entity_image(
        context, chat_id, thread_id, msg.message_id, entity, entity_type,
    )

    # 2. Ficha estática de la entidad
    ficha_text = (
        _format_demon(entity) if entity_type == "demonio" else _format_angel(entity)
    )
    chunks = format_and_split(
        ficha_text,
        use_blockquote=settings.use_blockquote_for("invocar", "consulta"),
    )
    for chunk in chunks:
        await context.bot.send_message(
            chat_id=chat_id, text=chunk, parse_mode="HTML",
            message_thread_id=thread_id, reply_to_message_id=msg.message_id,
        )

    # 3. Sin pregunta: mismo patrón que /oraculo. Mostrar welcome custom
    #    del ente y guardar estado por 5 min esperando la pregunta del
    #    invocante por texto libre. Al llegar la pregunta, el handler
    #    invocar_question_text disparará el LLM con la personalidad inyectada.
    if not question:
        import time
        welcome = _build_invocation_welcome(entity, entity_type)
        await context.bot.send_message(
            chat_id=chat_id,
            text=welcome,
            parse_mode="HTML",
            message_thread_id=thread_id,
        )
        context.user_data["invocar_awaiting_question"] = time.time()
        context.user_data["invocar_user"] = await db_users.get_user(user_id)
        context.user_data["invocar_entity"] = entity
        context.user_data["invocar_entity_type"] = entity_type
        logger.info(
            f"Invocar pending: user={user_id} → "
            f"{entity_type} {entity['number']} ({entity['name']})"
        )
        return

    # 4. Con pregunta inline: ejecutar LLM inmediatamente.
    await _execute_invocar_llm(
        update, context, user_id, chat_id, thread_id, msg,
        entity, entity_type, question, settings,
    )


def _build_invocation_welcome(entity: dict, entity_type: str) -> str:
    """Construye el mensaje de bienvenida personalizado por ente cuando
    /invocar se llama sin pregunta. Distinto del welcome genérico de
    /oraculo — cada demonio/ángel tiene su propia manifestación.
    """
    name = entity["name"]
    personality = entity.get("personality") or ""
    # Primera frase de personality como apertura en la voz del ente
    first_sentence = personality.split(".")[0].strip() if personality else ""

    if entity_type == "demonio":
        rank = entity.get("rank", "espíritu")
        legions = entity.get("legions", "?")
        header = f"🔻 <b>{name}</b> se manifiesta ante ti."
        subtitle = f"<i>{rank} del Infierno · {legions} legiones.</i>"
    else:  # angel
        choir = entity.get("choir", "coro angélico")
        attribute = entity.get("attribute", "")
        header = f"🔺 <b>{name}</b> desciende ante ti."
        subtitle = f"<i>{choir} · {attribute}.</i>"

    voice_line = f"<blockquote>{first_sentence}.</blockquote>" if first_sentence else ""

    prompt_line = (
        "¿Qué quieres preguntarle?\n"
        "<i>(Tienes 5 minutos antes de que se disipe y el portal se cierre.)</i>"
    )

    return "\n\n".join(filter(None, [header, subtitle, voice_line, prompt_line]))


async def _execute_invocar_llm(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    chat_id: int,
    thread_id: int | None,
    msg,
    entity: dict,
    entity_type: str,
    question: str,
    settings: Settings,
) -> None:
    """Ejecuta la llamada al LLM con la personalidad del ente ya determinada."""
    if is_user_busy(user_id):
        await context.bot.send_message(
            chat_id, text=LIMIT_MESSAGES["request_in_progress"],
            message_thread_id=thread_id,
        )
        return

    limit_key = await check_limits(user_id, "invocar", settings)
    if limit_key:
        await context.bot.send_message(
            chat_id, text=LIMIT_MESSAGES[limit_key],
            message_thread_id=thread_id,
        )
        return

    if len(question) > settings.MAX_QUESTION_LENGTH:
        question = question[: settings.MAX_QUESTION_LENGTH]

    mark_user_busy(user_id)
    try:
        user = await db_users.get_user(user_id)
        profile = UserProfile.from_db_or_guest(user, update)

        request = InterpretationRequest(
            mode="invocar",
            variant="consulta",
            question=question,
            user_profile=profile,
            max_tokens=settings.get_max_tokens("invocar", "consulta"),
            effort=settings.get_effort("invocar", "consulta"),
            extra_data={"entity": entity, "entity_type": entity_type},
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
            error_key_api = {
                "timeout": "queue_timeout",
                "rate_limit": "rate_limit",
                "empty_response": "empty_response",
            }.get(response.error, "api_error")
            await context.bot.send_message(
                chat_id,
                text=LIMIT_MESSAGES.get(error_key_api, LIMIT_MESSAGES["api_error"]),
                message_thread_id=thread_id,
            )
            return

        text = response.text
        if response.truncated:
            text += LIMIT_MESSAGES["truncated"]

        chunks = format_and_split(
            text, use_blockquote=settings.use_blockquote_for("invocar", "consulta"),
        )
        text_msg = None
        for chunk in chunks:
            text_msg = await context.bot.send_message(
                chat_id, text=chunk, parse_mode="HTML",
                message_thread_id=thread_id,
            )

        drawn_data = {
            "entity_type": entity_type,
            "entity_number": entity["number"],
            "entity_name": entity["name"],
            "question_length": len(question),
        }
        usage_id = await db_usage.record_usage(
            user_id=user_id, mode="invocar", variant="consulta",
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
            cost_usd=response.cost_usd, cached=response.cached,
            truncated=response.truncated, drawn_data=drawn_data,
        )

        if text_msg:
            try:
                await context.bot.send_message(
                    chat_id, text="¿Qué te ha parecido la invocación?",
                    reply_markup=feedback_keyboard(usage_id),
                    reply_to_message_id=text_msg.message_id,
                    message_thread_id=thread_id,
                )
            except (BadRequest, Forbidden):
                pass

        record_cooldown(user_id)
        logger.info(
            f"Invocar con pregunta: user={user_id} → "
            f"{entity_type} {entity['number']} ({entity['name']}) | "
            f"pregunta='{question[:50]}'"
        )
    finally:
        release_user(user_id)


async def invocar_question_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Recibe la pregunta del invocante vía texto libre cuando hay un
    /invocar pendiente. Dispara el LLM con la personalidad del ente
    que estaba aguardando en context.user_data.
    """
    if not context.user_data.get("invocar_awaiting_question"):
        return

    settings: Settings = context.bot_data["settings"]
    entity = context.user_data.get("invocar_entity")
    entity_type = context.user_data.get("invocar_entity_type")
    question = update.message.text

    if not question or not entity or not entity_type:
        return

    # Limpia el estado pendiente
    context.user_data["invocar_awaiting_question"] = False
    context.user_data["invocar_entity"] = None
    context.user_data["invocar_entity_type"] = None

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    msg = update.message

    await _execute_invocar_llm(
        update, context, user_id, chat_id, thread_id, msg,
        entity, entity_type, question.strip(), settings,
    )
