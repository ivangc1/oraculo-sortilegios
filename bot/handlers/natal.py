"""Handler de cartas natales (tropical y védica).

Sin hora → carta simplificada (sin ascendente ni casas).
"""

from loguru import logger
from telegram import Update
from telegram.ext import ContextTypes

from bot.concurrency import is_user_busy, mark_user_busy, release_user
from bot.config import Settings
from bot.handlers._pipeline import run_interpretation
from bot.limits import check_limits
from bot.messages import LIMIT_MESSAGES
from bot.middleware import middleware_check
from bot.typing import get_thread_id
from database import users as db_users
from service.calculators.dates import parse_birth_date
from service.interpreter import InterpreterService
from service.models import InterpretationRequest, UserProfile


async def natal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para /natal — carta tropical directa."""
    settings: Settings = context.bot_data["settings"]
    if not await middleware_check(update, context, settings):
        return
    user = await db_users.get_user(update.effective_user.id)
    if not user or not user["onboarding_complete"]:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=LIMIT_MESSAGES["not_registered"],
            message_thread_id=get_thread_id(update),
            reply_to_message_id=update.message.message_id,
        )
        return
    await _execute_natal(update, context, user, "tropical", settings)


async def vedica_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para /vedica — carta védica directa."""
    settings: Settings = context.bot_data["settings"]
    if not await middleware_check(update, context, settings):
        return
    user = await db_users.get_user(update.effective_user.id)
    if not user or not user["onboarding_complete"]:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=LIMIT_MESSAGES["not_registered"],
            message_thread_id=get_thread_id(update),
            reply_to_message_id=update.message.message_id,
        )
        return
    await _execute_natal(update, context, user, "vedica", settings)


async def natal_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, variant: str,
) -> None:
    """Callback desde menú natal."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_reply_markup(reply_markup=None)
    settings: Settings = context.bot_data["settings"]
    user_id = query.from_user.id
    user = await db_users.get_user(user_id)
    if not user or not user["onboarding_complete"]:
        await query.edit_message_text(LIMIT_MESSAGES["not_registered"])
        return
    await _execute_natal(update, context, user, variant, settings)


async def _execute_natal(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
    user: dict, variant: str, settings: Settings,
) -> None:
    """Ejecuta cálculo + interpretación de carta natal."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)

    if is_user_busy(user_id):
        await context.bot.send_message(chat_id, text=LIMIT_MESSAGES["request_in_progress"],
                                       message_thread_id=thread_id)
        return

    limit_key = await check_limits(user_id, "natal", settings)
    if limit_key:
        await context.bot.send_message(chat_id, text=LIMIT_MESSAGES[limit_key],
                                       message_thread_id=thread_id)
        return

    # Verificar datos necesarios
    if not user.get("birth_lat") or not user.get("birth_lon"):
        await context.bot.send_message(
            chat_id,
            text="Necesito tu ciudad de nacimiento para la carta natal. Usa /actualizarperfil.",
            message_thread_id=thread_id,
        )
        return

    mark_user_busy(user_id)
    try:
        day, month, year = parse_birth_date(user["birth_date"])

        hour = None
        minute = None
        if user.get("birth_time"):
            tp = user["birth_time"].split(":")
            hour, minute = int(tp[0]), int(tp[1])

        lat = user["birth_lat"]
        lon = user["birth_lon"]
        tz_str = user.get("birth_timezone", "UTC")

        # Calcular natal
        if variant == "tropical":
            from service.calculators.natal_tropical import calculate_natal_tropical, build_drawn_data, is_available
            if not is_available():
                await context.bot.send_message(chat_id, text="El módulo de natales no está disponible ahora.",
                                               message_thread_id=thread_id)
                return
            natal_data = calculate_natal_tropical(
                user["alias"], year, month, day, hour, minute, lat, lon, tz_str,
            )
            drawn_data = build_drawn_data(natal_data)
            mode_variant = "tropical"
        else:
            from service.calculators.natal_vedica import calculate_natal_vedica, build_drawn_data, is_available
            if not is_available():
                await context.bot.send_message(chat_id, text="El módulo de natales no está disponible ahora.",
                                               message_thread_id=thread_id)
                return
            natal_data = calculate_natal_vedica(
                user["alias"], year, month, day, hour, minute, lat, lon, tz_str,
            )
            drawn_data = build_drawn_data(natal_data)
            mode_variant = "vedica"

        # Info previa al usuario
        simplified_note = ""
        if natal_data.get("simplified"):
            simplified_note = "\n(Sin hora de nacimiento — carta simplificada, sin ascendente ni casas)"

        summary_lines = [f"🪐 Carta natal {variant}:"]
        summary_lines.append(f"Sol: {natal_data['sun']}")
        summary_lines.append(f"Luna: {natal_data['moon']}")
        if natal_data.get("ascendant"):
            summary_lines.append(f"Ascendente: {natal_data['ascendant']}")
        if natal_data.get("nakshatra"):
            summary_lines.append(f"Nakshatra: {natal_data['nakshatra']}")
        if natal_data.get("mahadasha"):
            summary_lines.append(f"Mahadasha: {natal_data['mahadasha']}")
        if natal_data.get("house_system"):
            summary_lines.append(f"Sistema: {natal_data['house_system']}")
        summary_lines.append(simplified_note)

        summary_msg = await context.bot.send_message(chat_id, text="\n".join(summary_lines),
                                                       message_thread_id=thread_id)

        # Interpretar
        profile = UserProfile(
            alias=user["alias"], sun_sign=user.get("sun_sign"),
            moon_sign=user.get("moon_sign"), ascendant=user.get("ascendant"),
            life_path=user.get("life_path"),
        )

        extra_data = _build_extra_data(natal_data, variant)

        request = InterpretationRequest(
            mode="natal", variant=mode_variant,
            user_profile=profile,
            max_tokens=settings.get_max_tokens("natal", mode_variant),
            effort=settings.get_effort("natal", mode_variant),
            extra_data=extra_data,
        )

        interpreter: InterpreterService = context.bot_data["interpreter_service"]
        await run_interpretation(
            bot=context.bot,
            chat_id=chat_id,
            thread_id=thread_id,
            user_id=user_id,
            settings=settings,
            interpreter=interpreter,
            request=request,
            mode="natal",
            variant=mode_variant,
            drawn_data=drawn_data,
            anchor_msg=summary_msg,
        )

    except Exception as e:
        logger.error(f"Natal calculation error: {e}")
        await context.bot.send_message(chat_id, text=LIMIT_MESSAGES["api_error"],
                                       message_thread_id=thread_id)
    finally:
        release_user(user_id)


def _build_extra_data(natal_data: dict, variant: str) -> dict:
    """Construye extra_data para el sub-prompt."""
    extra = {
        "sol": natal_data["sun"],
        "luna": natal_data["moon"],
    }
    if natal_data.get("ascendant"):
        extra["ascendente"] = natal_data["ascendant"]
    if natal_data.get("house_system"):
        extra["sistema_casas"] = natal_data["house_system"]
    if natal_data.get("simplified"):
        extra["sin_hora"] = "Carta simplificada (mediodía como aproximación). Sin ascendente ni casas."

    # Planetas
    if natal_data.get("planets"):
        planet_lines = []
        for pname, pdata in natal_data["planets"].items():
            line = f"{pname}: {pdata['sign']} {pdata['position']}°"
            if pdata.get("house"):
                line += f" ({pdata['house']})"
            if pdata.get("retrograde"):
                line += " R"
            planet_lines.append(line)
        extra["planetas"] = "\n".join(planet_lines)

    # Aspectos (limitar a los más importantes)
    if natal_data.get("aspects"):
        aspect_lines = []
        for a in natal_data["aspects"][:15]:
            aspect_lines.append(f"{a['p1']} {a['aspect']} {a['p2']} (orbe {a['orbit']}°)")
        extra["aspectos"] = "\n".join(aspect_lines)

    # Védica
    if natal_data.get("nakshatra"):
        extra["nakshatra_lunar"] = natal_data["nakshatra"]
    if natal_data.get("mahadasha"):
        extra["mahadasha"] = natal_data["mahadasha"]
    if natal_data.get("antardasha"):
        extra["antardasha"] = natal_data["antardasha"]

    return extra
