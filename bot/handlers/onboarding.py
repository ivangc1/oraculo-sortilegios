"""ConversationHandler de onboarding completo.

Flujo: /consulta → alias → fecha nacimiento → hora (opcional) → ciudad (opcional)
- ForceReply en TODOS los pasos que esperan texto libre
- Timeout 5 min
- /cancelaroraculo en cualquier paso
- Retomar desde SQLite si incompleto (post-restart)
- PicklePersistence mantiene estado entre mensajes
- Simultáneo: per_user=True (default de ConversationHandler)
"""

import re
from datetime import datetime, timezone

from loguru import logger
from telegram import ForceReply, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.config import Settings
from bot.messages import LIMIT_MESSAGES
from database import users as db_users
from service.calculators.numerologia import life_path

# Estados del ConversationHandler
ASK_ALIAS, ASK_DATE, ASK_TIME, ASK_CITY, CONFIRM_CITY = range(5)

# Regex para validar fecha DD/MM/AAAA
_DATE_RE = re.compile(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})$")
# Regex para hora HH:MM
_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")


async def consulta_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """/consulta — inicia onboarding o redirige si ya registrado."""
    settings: Settings = context.bot_data["settings"]

    # Verificar chat permitido (no middleware completo para no bloquear DM /start)
    chat = update.effective_chat
    if chat.type == "private":
        await update.message.reply_text(LIMIT_MESSAGES["dm_only_group"])
        return ConversationHandler.END

    if chat.id != settings.ALLOWED_CHAT_ID:
        return ConversationHandler.END

    user_id = update.effective_user.id

    # ¿Ya registrado?
    user = await db_users.get_user(user_id)
    if user and user["onboarding_complete"]:
        await update.message.reply_text(
            f"Ya te tengo fichado, {user['alias']}. Usa /tarot, /runa, /iching o lo que quieras.",
            reply_to_message_id=update.message.message_id,
        )
        return ConversationHandler.END

    # ¿Onboarding incompleto? Retomar desde donde se quedó
    partial = await db_users.get_incomplete_onboarding(user_id)
    if partial:
        # Tiene alias y fecha, falta hora/ciudad
        context.user_data["onb_alias"] = partial["alias"]
        context.user_data["onb_date"] = partial["birth_date"]
        await update.message.reply_text(
            f"Retomamos donde lo dejaste, {partial['alias']}.\n"
            "¿A qué hora naciste? (HH:MM en formato 24h)\n"
            "Si no lo sabes, escribe «no sé».",
            reply_markup=ForceReply(selective=True),
            reply_to_message_id=update.message.message_id,
        )
        return ASK_TIME

    # Nuevo onboarding → redirigir a DM para privacidad
    bot_username = (await context.bot.get_me()).username
    await update.message.reply_text(
        "No te conozco, forastero. Vamos al privado para que tus datos no anden por aquí.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "📝 Registrarme",
                url=f"https://t.me/{bot_username}?start=onboarding",
            )],
        ]),
        reply_to_message_id=update.message.message_id,
    )
    return ConversationHandler.END


async def ask_alias(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe alias del usuario."""
    alias = update.message.text.strip()

    if len(alias) < 1 or len(alias) > 50:
        await update.message.reply_text(
            "El alias debe tener entre 1 y 50 caracteres. Inténtalo de nuevo.",
            reply_markup=ForceReply(selective=True),
        )
        return ASK_ALIAS

    context.user_data["onb_alias"] = alias

    await update.message.reply_text(
        f"Bien, {alias}. ¿Cuándo naciste? (DD/MM/AAAA)",
        reply_markup=ForceReply(selective=True),
    )
    return ASK_DATE


async def ask_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe fecha de nacimiento."""
    text = update.message.text.strip()
    match = _DATE_RE.match(text)

    if not match:
        await update.message.reply_text(
            LIMIT_MESSAGES["invalid_date"],
            reply_markup=ForceReply(selective=True),
        )
        return ASK_DATE

    day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))

    # Validar rango
    try:
        datetime(year, month, day)
    except ValueError:
        await update.message.reply_text(
            LIMIT_MESSAGES["invalid_date"],
            reply_markup=ForceReply(selective=True),
        )
        return ASK_DATE

    if year < 1900 or year > datetime.now().year:
        await update.message.reply_text(
            "El año debe estar entre 1900 y el actual.",
            reply_markup=ForceReply(selective=True),
        )
        return ASK_DATE

    birth_date = f"{day:02d}/{month:02d}/{year}"
    context.user_data["onb_date"] = birth_date

    # Guardar parcial en SQLite (para retomar si restart)
    await db_users.save_partial_onboarding(
        user_id=update.effective_user.id,
        username=update.effective_user.username,
        alias=context.user_data["onb_alias"],
        birth_date=birth_date,
    )

    await update.message.reply_text(
        "¿A qué hora naciste? (HH:MM en formato 24h)\n"
        "Si no lo sabes, escribe «no sé».",
        reply_markup=ForceReply(selective=True),
    )
    return ASK_TIME


async def ask_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe hora de nacimiento (opcional)."""
    text = update.message.text.strip().lower()

    if text in ("no sé", "no se", "nose", "no lo sé", "no lo se", "ns", "-", "no"):
        context.user_data["onb_time"] = None
        await update.message.reply_text(
            "Sin hora, la carta natal será aproximada.\n"
            "¿En qué ciudad naciste?\n"
            "Si prefieres no decirlo, escribe «paso».",
            reply_markup=ForceReply(selective=True),
        )
        return ASK_CITY

    match = _TIME_RE.match(text)
    if not match:
        await update.message.reply_text(
            LIMIT_MESSAGES["invalid_time"],
            reply_markup=ForceReply(selective=True),
        )
        return ASK_TIME

    hour, minute = int(match.group(1)), int(match.group(2))
    if hour > 23 or minute > 59:
        await update.message.reply_text(
            LIMIT_MESSAGES["invalid_time"],
            reply_markup=ForceReply(selective=True),
        )
        return ASK_TIME

    context.user_data["onb_time"] = f"{hour:02d}:{minute:02d}"

    await update.message.reply_text(
        "¿En qué ciudad naciste?\n"
        "Si prefieres no decirlo, escribe «paso».",
        reply_markup=ForceReply(selective=True),
    )
    return ASK_CITY


async def ask_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe ciudad de nacimiento (opcional). Geocoding con Nominatim."""
    text = update.message.text.strip().lower()

    if text in ("paso", "no", "-", "no sé", "no se", "ns"):
        # Sin ciudad
        await _complete_onboarding(update, context, city_result=None)
        return ConversationHandler.END

    # Geocoding
    try:
        from service.calculators.geocoding import geocode_city
        result = await geocode_city(update.message.text.strip())
    except Exception:
        result = None

    if result is None:
        await update.message.reply_text(
            LIMIT_MESSAGES["nominatim_down"],
            reply_markup=ForceReply(selective=True),
        )
        return ASK_CITY

    # Confirmar ciudad (ciudades homónimas)
    context.user_data["onb_city_result"] = {
        "city_name": result.city_name,
        "lat": result.lat,
        "lon": result.lon,
        "timezone": result.timezone,
    }

    # Mostrar nombre completo para confirmar
    short_name = result.city_name.split(",")[0].strip() if "," in result.city_name else result.city_name
    await update.message.reply_text(
        f"¿Te refieres a {result.city_name}?",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Sí", callback_data="onb:city_yes"),
                InlineKeyboardButton("No, otra ciudad", callback_data="onb:city_no"),
            ]
        ]),
    )
    return CONFIRM_CITY


async def confirm_city_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Callback de confirmación de ciudad."""
    query = update.callback_query
    await query.answer()

    if query.data == "onb:city_yes":
        city_result = context.user_data.get("onb_city_result")
        try:
            await query.edit_message_text(f"Ciudad confirmada.")
        except Exception:
            pass
        await _complete_onboarding(update, context, city_result=city_result)
        return ConversationHandler.END

    # No, otra ciudad
    try:
        await query.edit_message_text(
            "Escríbelo más completo, por ejemplo: Santiago de Chile, Santiago de Compostela."
        )
    except Exception:
        pass
    await query.message.reply_text(
        "¿En qué ciudad naciste? (sé más específico)",
        reply_markup=ForceReply(selective=True),
    )
    return ASK_CITY


async def _complete_onboarding(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
    city_result: dict | None,
) -> None:
    """Completa el onboarding: calcula signos, guarda en DB."""
    user_id = update.effective_user.id
    username = update.effective_user.username
    alias = context.user_data.get("onb_alias", "Desconocido")
    birth_date = context.user_data.get("onb_date", "01/01/2000")
    birth_time = context.user_data.get("onb_time")

    # Datos de ciudad
    birth_city = None
    birth_lat = None
    birth_lon = None
    birth_timezone = None
    if city_result:
        birth_city = city_result["city_name"]
        birth_lat = city_result["lat"]
        birth_lon = city_result["lon"]
        birth_timezone = city_result["timezone"]

    # Calcular signo solar
    sun_sign = None
    try:
        from service.calculators.sun_sign import get_sun_sign
        if "/" in birth_date:
            parts = birth_date.split("/")
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
        else:
            parts = birth_date.split("-")
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])

        hour = 12
        minute = 0
        if birth_time:
            tp = birth_time.split(":")
            hour, minute = int(tp[0]), int(tp[1])

        sun_sign = get_sun_sign(
            year, month, day, hour, minute,
            lat=birth_lat or 40.4168,
            lon=birth_lon or -3.7038,
            tz_str=birth_timezone or "Europe/Madrid",
        )
    except Exception as e:
        logger.warning(f"Sun sign calculation failed: {e}")

    # Calcular camino de vida
    lp = None
    try:
        lp = life_path(birth_date)
    except Exception:
        pass

    # Borrar parcial si existe y crear completo
    existing = await db_users.get_user(user_id)
    if existing:
        await db_users.delete_user(user_id)

    await db_users.create_user(
        user_id=user_id,
        username=username,
        alias=alias,
        birth_date=birth_date,
        birth_time=birth_time,
        birth_city=birth_city,
        birth_lat=birth_lat,
        birth_lon=birth_lon,
        birth_timezone=birth_timezone,
        sun_sign=sun_sign,
        life_path=lp,
    )

    # Mensaje de bienvenida
    lines = [f"Registrado, {alias}."]
    if sun_sign:
        lines.append(f"Sol en {sun_sign}.")
    if lp is not None:
        lines.append(f"Camino de vida: {lp}.")
    lines.append("\nUsa /tarot, /runa, /iching o lo que te apetezca.")

    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id, text=" ".join(lines))

    # Limpiar user_data
    for key in ("onb_alias", "onb_date", "onb_time", "onb_city_result"):
        context.user_data.pop(key, None)

    logger.info(f"Onboarding completed: user_id={user_id}, alias={alias}")


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """/cancelaroraculo — cancela el onboarding."""
    await update.message.reply_text(
        LIMIT_MESSAGES["cancelled"],
        reply_to_message_id=update.message.message_id,
    )
    for key in ("onb_alias", "onb_date", "onb_time", "onb_city_result"):
        context.user_data.pop(key, None)
    return ConversationHandler.END


async def timeout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Timeout del ConversationHandler (5 min)."""
    if update and update.effective_user:
        try:
            chat_id = update.effective_chat.id
            await context.bot.send_message(chat_id, text=LIMIT_MESSAGES["onboarding_timeout"])
        except Exception:
            pass
    for key in ("onb_alias", "onb_date", "onb_time", "onb_city_result"):
        context.user_data.pop(key, None)
    return ConversationHandler.END


def build_onboarding_handler() -> ConversationHandler:
    """Construye el ConversationHandler de onboarding."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("consulta", consulta_command),
        ],
        states={
            ASK_ALIAS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_alias),
            ],
            ASK_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_date),
            ],
            ASK_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_time),
            ],
            ASK_CITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_city),
            ],
            CONFIRM_CITY: [
                CallbackQueryHandler(confirm_city_callback, pattern=r"^onb:city_"),
            ],
            ConversationHandler.TIMEOUT: [
                MessageHandler(filters.ALL, timeout_handler),
            ],
        },
        fallbacks=[
            CommandHandler("cancelaroraculo", cancel_command),
        ],
        conversation_timeout=300,  # 5 minutos
        name="onboarding",
        persistent=True,
        per_user=True,
        per_chat=True,
        per_message=False,
    )
