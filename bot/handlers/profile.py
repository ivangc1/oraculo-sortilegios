"""Handlers de perfil: /miperfil, /actualizarperfil, /borrarme.

`/actualizarperfil` redirige al privado y el flujo real (elegir qué
actualizar, validar hora, geocoding de ciudad, etc.) está en
`bot/handlers/dm_onboarding.py` con sus propios estados DM_UPD_*.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.config import Settings
from bot.messages import LIMIT_MESSAGES
from bot.middleware import middleware_check
from database import users as db_users


async def miperfil_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra perfil del usuario por DM (nunca en grupo por privacidad)."""
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
        "",
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

    profile_text = "\n".join(lines)

    # Enviar por DM para no exponer datos personales en el grupo
    try:
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text=profile_text,
        )
        # Confirmación breve en grupo
        if update.effective_chat.type != "private":
            await update.message.reply_text(
                "Te he enviado tu perfil por privado. Mira tus DMs.",
                reply_to_message_id=update.message.message_id,
            )
    except Exception:
        # Si no puede enviar DM (usuario no ha iniciado chat con el bot)
        await update.message.reply_text(
            "No puedo enviarte un mensaje privado. Escríbeme primero al DM y luego repite /miperfil.",
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

async def actualizarperfil_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """`/actualizarperfil` — redirige al DM (el flujo real está en
    `dm_onboarding.py`).

    Se queda como CommandHandler simple porque el botón apunta a un deep
    link `?start=update_profile` que arranca el ConversationHandler de DM.
    """
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
