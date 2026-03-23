"""ConversationHandler para onboarding, actualizar perfil y nombre completo en DM.

Seguridad:
  - Solo funciona en chat privado (DM)
  - Comandos de tirada durante el flujo se ignoran (filters.COMMAND en fallbacks)
  - ForceReply en cada paso
  - Timeout 5 min
  - /cancelaroraculo cancela
"""

import re
from datetime import datetime

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

from bot.messages import LIMIT_MESSAGES
from database import users as db_users
from service.calculators.numerologia import life_path

# Estados
DM_ASK_ALIAS, DM_ASK_DATE, DM_ASK_TIME, DM_ASK_CITY, DM_CONFIRM_CITY = range(5)
DM_UPD_CHOOSE, DM_UPD_TIME, DM_UPD_CITY, DM_UPD_CONFIRM_CITY = range(5, 9)
DM_ASK_FULLNAME = 9

_DATE_RE = re.compile(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})$")
_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")


# ============================================================
# ONBOARDING EN DM
# ============================================================

async def start_dm_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicio de onboarding en DM (llamado desde start.py deep link)."""
    user_id = update.effective_user.id

    # Ya registrado?
    user = await db_users.get_user(user_id)
    if user and user["onboarding_complete"]:
        await update.message.reply_text(
            f"Ya te conozco, {user['alias']}. Vuelve a La Taberna y usa /tarot o lo que quieras."
        )
        return ConversationHandler.END

    # Onboarding incompleto? Retomar
    partial = await db_users.get_incomplete_onboarding(user_id)
    if partial:
        context.user_data["onb_alias"] = partial["alias"]
        context.user_data["onb_date"] = partial["birth_date"]
        await update.message.reply_text(
            f"Retomamos donde lo dejaste, {partial['alias']}.\n"
            "¿A qué hora naciste? (HH:MM en formato 24h)\n"
            "Si no lo sabes, escribe «no sé».",
            reply_markup=ForceReply(selective=True),
        )
        return DM_ASK_TIME

    await update.message.reply_text(
        "Vamos a conocernos. Esto queda entre tú y yo.\n"
        "¿Cómo quieres que te llame? (alias, apodo, lo que uses)",
        reply_markup=ForceReply(selective=True),
    )
    return DM_ASK_ALIAS


async def dm_ask_alias(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe alias."""
    alias = update.message.text.strip()
    if len(alias) < 1 or len(alias) > 50:
        await update.message.reply_text(
            "El alias debe tener entre 1 y 50 caracteres.",
            reply_markup=ForceReply(selective=True),
        )
        return DM_ASK_ALIAS

    context.user_data["onb_alias"] = alias
    await update.message.reply_text(
        f"Bien, {alias}. ¿Cuándo naciste? (DD/MM/AAAA)",
        reply_markup=ForceReply(selective=True),
    )
    return DM_ASK_DATE


async def dm_ask_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe fecha de nacimiento."""
    text = update.message.text.strip()
    match = _DATE_RE.match(text)
    if not match:
        await update.message.reply_text(
            LIMIT_MESSAGES["invalid_date"],
            reply_markup=ForceReply(selective=True),
        )
        return DM_ASK_DATE

    day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
    try:
        datetime(year, month, day)
    except ValueError:
        await update.message.reply_text(
            LIMIT_MESSAGES["invalid_date"],
            reply_markup=ForceReply(selective=True),
        )
        return DM_ASK_DATE

    if year < 1900 or year > datetime.now().year:
        await update.message.reply_text(
            "El año debe estar entre 1900 y el actual.",
            reply_markup=ForceReply(selective=True),
        )
        return DM_ASK_DATE

    birth_date = f"{day:02d}/{month:02d}/{year}"
    context.user_data["onb_date"] = birth_date

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
    return DM_ASK_TIME


async def dm_ask_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
        return DM_ASK_CITY

    match = _TIME_RE.match(text)
    if not match:
        await update.message.reply_text(
            LIMIT_MESSAGES["invalid_time"],
            reply_markup=ForceReply(selective=True),
        )
        return DM_ASK_TIME

    hour, minute = int(match.group(1)), int(match.group(2))
    if hour > 23 or minute > 59:
        await update.message.reply_text(
            LIMIT_MESSAGES["invalid_time"],
            reply_markup=ForceReply(selective=True),
        )
        return DM_ASK_TIME

    context.user_data["onb_time"] = f"{hour:02d}:{minute:02d}"

    await update.message.reply_text(
        "¿En qué ciudad naciste?\n"
        "Si prefieres no decirlo, escribe «paso».",
        reply_markup=ForceReply(selective=True),
    )
    return DM_ASK_CITY


async def dm_ask_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe ciudad (opcional). Geocoding con Nominatim."""
    text = update.message.text.strip().lower()

    if text in ("paso", "no", "-", "no sé", "no se", "ns"):
        await _complete_dm_onboarding(update, context, city_result=None)
        return ConversationHandler.END

    try:
        from service.calculators.geocoding import geocode_city
        result = await geocode_city(update.message.text.strip())
    except Exception:
        result = None

    if result is None:
        await update.message.reply_text(
            "No puedo verificar esa ciudad ahora. Escribe «paso» para continuar sin ciudad, "
            "o inténtalo de nuevo.",
            reply_markup=ForceReply(selective=True),
        )
        return DM_ASK_CITY

    context.user_data["onb_city_result"] = {
        "city_name": result.city_name,
        "lat": result.lat,
        "lon": result.lon,
        "timezone": result.timezone,
    }

    await update.message.reply_text(
        f"¿Te refieres a {result.city_name}?",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Sí", callback_data="dmonb:city_yes"),
                InlineKeyboardButton("No, otra", callback_data="dmonb:city_no"),
            ]
        ]),
    )
    return DM_CONFIRM_CITY


async def dm_confirm_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Callback de confirmacion de ciudad."""
    query = update.callback_query
    await query.answer()

    if query.data == "dmonb:city_yes":
        city_result = context.user_data.get("onb_city_result")
        try:
            await query.edit_message_text("Ciudad confirmada.")
        except Exception:
            pass
        await _complete_dm_onboarding(update, context, city_result=city_result)
        return ConversationHandler.END

    try:
        await query.edit_message_text(
            "Escríbelo más completo (ej: Santiago de Chile, Santiago de Compostela)."
        )
    except Exception:
        pass
    await context.bot.send_message(
        update.effective_chat.id,
        "¿En qué ciudad naciste? (sé más específico)",
        reply_markup=ForceReply(selective=True),
    )
    return DM_ASK_CITY


async def _complete_dm_onboarding(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
    city_result: dict | None,
) -> None:
    """Completa onboarding en DM."""
    user_id = update.effective_user.id
    username = update.effective_user.username
    alias = context.user_data.get("onb_alias", "Desconocido")
    birth_date = context.user_data.get("onb_date", "01/01/2000")
    birth_time = context.user_data.get("onb_time")

    birth_city = birth_lat = birth_lon = birth_timezone = None
    if city_result:
        birth_city = city_result["city_name"]
        birth_lat = city_result["lat"]
        birth_lon = city_result["lon"]
        birth_timezone = city_result["timezone"]

    # Signo solar
    sun_sign = None
    try:
        from service.calculators.sun_sign import get_sun_sign
        if "/" in birth_date:
            parts = birth_date.split("/")
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
        else:
            parts = birth_date.split("-")
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])

        hour, minute = 12, 0
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

    # Camino de vida
    lp = None
    try:
        lp = life_path(birth_date)
    except Exception:
        pass

    # Crear/reemplazar usuario
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

    lines = [f"✅ Registrado, {alias}."]
    if sun_sign:
        lines.append(f"Sol en {sun_sign}.")
    if lp is not None:
        lines.append(f"Camino de vida: {lp}.")
    lines.append("\nVuelve a La Taberna y usa /tarot, /runa, /iching o lo que te apetezca.")

    await context.bot.send_message(update.effective_chat.id, text=" ".join(lines))

    for key in ("onb_alias", "onb_date", "onb_time", "onb_city_result", "dm_deep_link"):
        context.user_data.pop(key, None)

    logger.info(f"DM onboarding completed: user_id={user_id}, alias={alias}")


# ============================================================
# ACTUALIZAR PERFIL EN DM
# ============================================================

async def start_dm_update_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicio de actualizar perfil en DM."""
    user_id = update.effective_user.id
    user = await db_users.get_user(user_id)
    if not user or not user["onboarding_complete"]:
        await update.message.reply_text(
            "No te tengo registrado. Usa /consulta en La Taberna primero."
        )
        return ConversationHandler.END

    context.user_data["upd_user_id"] = user_id
    await update.message.reply_text(
        "¿Qué quieres actualizar?",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Hora de nacimiento", callback_data="dmupd:time"),
                InlineKeyboardButton("Ciudad de nacimiento", callback_data="dmupd:city"),
            ],
        ]),
    )
    return DM_UPD_CHOOSE


async def dm_upd_choose(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "dmupd:time":
        try:
            await query.edit_message_text("Actualizar hora de nacimiento")
        except Exception:
            pass
        await context.bot.send_message(
            update.effective_chat.id,
            "Escribe tu hora de nacimiento (HH:MM en formato 24h):",
            reply_markup=ForceReply(selective=True),
        )
        return DM_UPD_TIME

    if query.data == "dmupd:city":
        try:
            await query.edit_message_text("Actualizar ciudad de nacimiento")
        except Exception:
            pass
        await context.bot.send_message(
            update.effective_chat.id,
            "Escribe tu ciudad de nacimiento:",
            reply_markup=ForceReply(selective=True),
        )
        return DM_UPD_CITY

    return ConversationHandler.END


async def dm_upd_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    match = _TIME_RE.match(text)
    if not match:
        await update.message.reply_text(
            LIMIT_MESSAGES["invalid_time"],
            reply_markup=ForceReply(selective=True),
        )
        return DM_UPD_TIME

    hour, minute = int(match.group(1)), int(match.group(2))
    if hour > 23 or minute > 59:
        await update.message.reply_text(
            LIMIT_MESSAGES["invalid_time"],
            reply_markup=ForceReply(selective=True),
        )
        return DM_UPD_TIME

    user_id = context.user_data.get("upd_user_id", update.effective_user.id)
    new_time = f"{hour:02d}:{minute:02d}"
    await db_users.update_profile(user_id, birth_time=new_time)

    await update.message.reply_text(
        f"✅ Hora actualizada a {new_time}. Vuelve a La Taberna."
    )
    context.user_data.pop("upd_user_id", None)
    return ConversationHandler.END


async def dm_upd_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()

    try:
        from service.calculators.geocoding import geocode_city
        result = await geocode_city(text)
    except Exception:
        result = None

    if result is None:
        await update.message.reply_text(
            "No puedo verificar esa ciudad ahora. Inténtalo de nuevo o escribe /cancelaroraculo.",
            reply_markup=ForceReply(selective=True),
        )
        return DM_UPD_CITY

    context.user_data["upd_city_result"] = {
        "city_name": result.city_name,
        "lat": result.lat,
        "lon": result.lon,
        "timezone": result.timezone,
    }

    await update.message.reply_text(
        f"¿Te refieres a {result.city_name}?",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Sí", callback_data="dmupd:city_yes"),
                InlineKeyboardButton("No, otra", callback_data="dmupd:city_no"),
            ],
        ]),
    )
    return DM_UPD_CONFIRM_CITY


async def dm_upd_confirm_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "dmupd:city_yes":
        city = context.user_data.get("upd_city_result", {})
        user_id = context.user_data.get("upd_user_id", query.from_user.id)
        await db_users.update_profile(
            user_id,
            birth_city=city.get("city_name"),
            birth_lat=city.get("lat"),
            birth_lon=city.get("lon"),
            birth_timezone=city.get("timezone"),
        )
        try:
            await query.edit_message_text("✅ Ciudad actualizada. Vuelve a La Taberna.")
        except Exception:
            pass
        context.user_data.pop("upd_user_id", None)
        context.user_data.pop("upd_city_result", None)
        return ConversationHandler.END

    try:
        await query.edit_message_text(
            "Escribe la ciudad con más detalle (ej: Santiago de Chile)."
        )
    except Exception:
        pass
    await context.bot.send_message(
        update.effective_chat.id,
        "Escribe tu ciudad de nacimiento:",
        reply_markup=ForceReply(selective=True),
    )
    return DM_UPD_CITY


# ============================================================
# SET FULLNAME EN DM (para numerologia)
# ============================================================

async def start_dm_set_fullname(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Registrar nombre completo de nacimiento en DM."""
    user_id = update.effective_user.id
    user = await db_users.get_user(user_id)
    if not user or not user["onboarding_complete"]:
        await update.message.reply_text(
            "No te tengo registrado. Usa /consulta en La Taberna primero."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "¿Cuál es tu nombre completo de nacimiento? (tal como aparece en tu certificado)\n"
        "Este dato se usa para numerología y queda en privado.",
        reply_markup=ForceReply(selective=True),
    )
    return DM_ASK_FULLNAME


async def dm_ask_fullname(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe nombre completo."""
    name = update.message.text.strip()
    if len(name) < 2 or len(name) > 100:
        await update.message.reply_text(
            "El nombre debe tener entre 2 y 100 caracteres.",
            reply_markup=ForceReply(selective=True),
        )
        return DM_ASK_FULLNAME

    user_id = update.effective_user.id
    await db_users.update_profile(user_id, full_birth_name=name)

    await update.message.reply_text(
        f"✅ Nombre registrado. Vuelve a La Taberna y usa /numerologia."
    )
    context.user_data.pop("dm_deep_link", None)
    logger.info(f"Fullname set in DM: user_id={user_id}")
    return ConversationHandler.END


# ============================================================
# CANCEL + TIMEOUT
# ============================================================

async def dm_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """/cancelaroraculo en DM."""
    await update.message.reply_text(LIMIT_MESSAGES["cancelled"])
    for key in ("onb_alias", "onb_date", "onb_time", "onb_city_result",
                "upd_user_id", "upd_city_result", "dm_deep_link"):
        context.user_data.pop(key, None)
    return ConversationHandler.END


async def dm_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Timeout del flujo DM."""
    if update and update.effective_chat:
        try:
            await context.bot.send_message(
                update.effective_chat.id,
                LIMIT_MESSAGES["onboarding_timeout"],
            )
        except Exception:
            pass
    for key in ("onb_alias", "onb_date", "onb_time", "onb_city_result",
                "upd_user_id", "upd_city_result", "dm_deep_link"):
        context.user_data.pop(key, None)
    return ConversationHandler.END


async def dm_ignore_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ignora comandos de tirada durante el flujo de datos en DM."""
    await update.message.reply_text(
        "Estamos a mitad de algo. Termina esto primero o usa /cancelaroraculo."
    )


# ============================================================
# BUILD HANDLERS
# ============================================================

def build_dm_onboarding_handler() -> ConversationHandler:
    """ConversationHandler para onboarding en DM (deep link)."""
    # Filtro: solo DMs
    dm_filter = filters.ChatType.PRIVATE

    return ConversationHandler(
        entry_points=[
            # /start con parametro "onboarding" (el dispatch lo hace start.py)
            CommandHandler("start", lambda u, c: start_dm_onboarding(u, c),
                           filters=dm_filter),
        ],
        states={
            DM_ASK_ALIAS: [
                MessageHandler(dm_filter & filters.TEXT & ~filters.COMMAND, dm_ask_alias),
            ],
            DM_ASK_DATE: [
                MessageHandler(dm_filter & filters.TEXT & ~filters.COMMAND, dm_ask_date),
            ],
            DM_ASK_TIME: [
                MessageHandler(dm_filter & filters.TEXT & ~filters.COMMAND, dm_ask_time),
            ],
            DM_ASK_CITY: [
                MessageHandler(dm_filter & filters.TEXT & ~filters.COMMAND, dm_ask_city),
            ],
            DM_CONFIRM_CITY: [
                CallbackQueryHandler(dm_confirm_city, pattern=r"^dmonb:city_"),
            ],
            # Update profile states
            DM_UPD_CHOOSE: [
                CallbackQueryHandler(dm_upd_choose, pattern=r"^dmupd:(time|city)$"),
            ],
            DM_UPD_TIME: [
                MessageHandler(dm_filter & filters.TEXT & ~filters.COMMAND, dm_upd_time),
            ],
            DM_UPD_CITY: [
                MessageHandler(dm_filter & filters.TEXT & ~filters.COMMAND, dm_upd_city),
            ],
            DM_UPD_CONFIRM_CITY: [
                CallbackQueryHandler(dm_upd_confirm_city, pattern=r"^dmupd:city_"),
            ],
            # Set fullname
            DM_ASK_FULLNAME: [
                MessageHandler(dm_filter & filters.TEXT & ~filters.COMMAND, dm_ask_fullname),
            ],
            ConversationHandler.TIMEOUT: [
                MessageHandler(filters.ALL, dm_timeout),
            ],
        },
        fallbacks=[
            CommandHandler("cancelaroraculo", dm_cancel),
            # Ignorar comandos de tirada durante el flujo
            MessageHandler(dm_filter & filters.COMMAND, dm_ignore_command),
        ],
        conversation_timeout=300,
        name="dm_onboarding",
        persistent=True,
        per_user=True,
        per_chat=True,
        per_message=False,
    )
