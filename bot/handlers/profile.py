"""Handlers de perfil: /miperfil, /actualizarperfil, /borrarme.

/actualizarperfil: ConversationHandler para actualizar hora y/o ciudad.
ForceReply en cada paso. Geocoding con Nominatim caido -> salida limpia.
"""

import re

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
from bot.middleware import middleware_check
from database import users as db_users

# Estados para /actualizarperfil
UPD_CHOOSE, UPD_TIME, UPD_CITY, UPD_CONFIRM_CITY = range(4)

_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")


async def miperfil_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra perfil del usuario."""
    settings: Settings = context.bot_data["settings"]
    if not await middleware_check(update, context, settings):
        return

    user = await db_users.get_user(update.effective_user.id)
    if not user or not user["onboarding_complete"]:
        await update.message.reply_text(
            LIMIT_MESSAGES["not_registered"],
            reply_to_message_id=update.message.message_id,
        )
        return

    lines = [
        f"📋 Tu perfil, {user['alias']}:",
        f"",
        f"Fecha de nacimiento: {user['birth_date']}",
    ]
    if user.get("birth_time"):
        lines.append(f"Hora: {user['birth_time']}")
    if user.get("birth_city"):
        lines.append(f"Ciudad: {user['birth_city']}")
    if user.get("sun_sign"):
        lines.append(f"Sol: {user['sun_sign']}")
    if user.get("moon_sign"):
        lines.append(f"Luna: {user['moon_sign']}")
    if user.get("ascendant"):
        lines.append(f"Ascendente: {user['ascendant']}")
    if user.get("lunar_nakshatra"):
        lines.append(f"Nakshatra: {user['lunar_nakshatra']}")
    if user.get("life_path") is not None:
        lines.append(f"Camino de vida: {user['life_path']}")
    if user.get("full_birth_name"):
        lines.append(f"Nombre completo: {user['full_birth_name']}")

    lines.append("")
    lines.append("✏️ /actualizarperfil para cambiar datos")
    lines.append("🗑 /borrarme para eliminar tu perfil")

    await update.message.reply_text(
        "\n".join(lines),
        reply_to_message_id=update.message.message_id,
    )


async def borrarme_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Elimina perfil del usuario (cascade borra usage_log y feedback)."""
    settings: Settings = context.bot_data["settings"]
    if not await middleware_check(update, context, settings):
        return

    user = await db_users.get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text(
            "No tienes perfil que borrar, forastero.",
            reply_to_message_id=update.message.message_id,
        )
        return

    await db_users.delete_user(update.effective_user.id)
    await update.message.reply_text(
        "Borrado. Como si nunca hubieras pasado por aquí. Si vuelves, /consulta.",
        reply_to_message_id=update.message.message_id,
    )


# === /actualizarperfil ===

async def actualizarperfil_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """/actualizarperfil — elige qué actualizar."""
    settings: Settings = context.bot_data["settings"]
    if not await middleware_check(update, context, settings):
        return ConversationHandler.END

    user = await db_users.get_user(update.effective_user.id)
    if not user or not user["onboarding_complete"]:
        await update.message.reply_text(
            LIMIT_MESSAGES["not_registered"],
            reply_to_message_id=update.message.message_id,
        )
        return ConversationHandler.END

    # Redirigir a DM para privacidad
    bot_username = (await context.bot.get_me()).username
    await update.message.reply_text(
        "Vamos al privado. Tus datos no tienen que andar por aquí.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "✏️ Actualizar perfil",
                url=f"https://t.me/{bot_username}?start=update_profile",
            )],
        ]),
        reply_to_message_id=update.message.message_id,
    )
    return ConversationHandler.END


async def upd_choose_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "upd:time":
        try:
            await query.edit_message_text(
                "¿A qué hora naciste? (HH:MM en formato 24h)")
        except Exception:
            pass
        await query.message.reply_text(
            "Escribe tu hora de nacimiento (HH:MM):",
            reply_markup=ForceReply(selective=True),
        )
        return UPD_TIME

    if query.data == "upd:city":
        try:
            await query.edit_message_text(
                "¿En qué ciudad naciste?")
        except Exception:
            pass
        await query.message.reply_text(
            "Escribe tu ciudad de nacimiento:",
            reply_markup=ForceReply(selective=True),
        )
        return UPD_CITY

    return ConversationHandler.END


async def upd_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe nueva hora."""
    text = update.message.text.strip()
    match = _TIME_RE.match(text)
    if not match:
        await update.message.reply_text(
            LIMIT_MESSAGES["invalid_time"],
            reply_markup=ForceReply(selective=True),
        )
        return UPD_TIME

    hour, minute = int(match.group(1)), int(match.group(2))
    if hour > 23 or minute > 59:
        await update.message.reply_text(
            LIMIT_MESSAGES["invalid_time"],
            reply_markup=ForceReply(selective=True),
        )
        return UPD_TIME

    user_id = update.effective_user.id  # Siempre ID real
    new_time = f"{hour:02d}:{minute:02d}"
    await db_users.update_profile(user_id, birth_time=new_time)

    await update.message.reply_text(
        f"Hora actualizada a {new_time}.",
        reply_to_message_id=update.message.message_id,
    )
    return ConversationHandler.END


async def upd_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe nueva ciudad. Geocoding con Nominatim."""
    text = update.message.text.strip()

    try:
        from service.calculators.geocoding import geocode_city
        result = await geocode_city(text)
    except Exception:
        result = None

    if result is None:
        await update.message.reply_text(
            LIMIT_MESSAGES["nominatim_down"],
            reply_markup=ForceReply(selective=True),
        )
        return UPD_CITY

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
                InlineKeyboardButton("Si", callback_data="upd:city_yes"),
                InlineKeyboardButton("No, otra ciudad", callback_data="upd:city_no"),
            ],
        ]),
    )
    return UPD_CONFIRM_CITY


async def upd_confirm_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "upd:city_yes":
        city = context.user_data.get("upd_city_result", {})
        user_id = query.from_user.id  # Siempre ID real
        await db_users.update_profile(
            user_id,
            birth_city=city.get("city_name"),
            birth_lat=city.get("lat"),
            birth_lon=city.get("lon"),
            birth_timezone=city.get("timezone"),
        )
        try:
            await query.edit_message_text("Ciudad actualizada.")
        except Exception:
            pass
        context.user_data.pop("upd_city_result", None)
        return ConversationHandler.END

    # No, otra ciudad
    try:
        await query.edit_message_text(
            "Escribe la ciudad con mas detalle (ej: Santiago de Chile).")
    except Exception:
        pass
    await query.message.reply_text(
        "Escribe tu ciudad de nacimiento:",
        reply_markup=ForceReply(selective=True),
    )
    return UPD_CITY


async def upd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        LIMIT_MESSAGES["cancelled"],
        reply_to_message_id=update.message.message_id,
    )
    context.user_data.pop("upd_city_result", None)
    return ConversationHandler.END


def build_update_profile_handler() -> ConversationHandler:
    """Construye ConversationHandler para /actualizarperfil."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("actualizarperfil", actualizarperfil_command),
        ],
        states={
            UPD_CHOOSE: [
                CallbackQueryHandler(upd_choose_callback, pattern=r"^upd:(time|city)$"),
            ],
            UPD_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, upd_time),
            ],
            UPD_CITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, upd_city),
            ],
            UPD_CONFIRM_CITY: [
                CallbackQueryHandler(upd_confirm_city, pattern=r"^upd:city_"),
            ],
        },
        fallbacks=[
            CommandHandler("cancelaroraculo", upd_cancel),
        ],
        conversation_timeout=300,
        name="update_profile",
        persistent=True,
        per_user=True,
        per_chat=True,
        per_message=False,
    )
