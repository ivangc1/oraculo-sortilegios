"""Handler de /consulta en grupo.

`consulta_command` decide entre:
  - DM → rechaza (dm_only_group).
  - Chat no autorizado → silencio.
  - Usuario registrado → lista de comandos.
  - Usuario no registrado → invitación a /start onboarding por DM.

El registro real ocurre en bot/handlers/dm_onboarding.py. Antes existía aquí
una máquina de estados (alias → fecha → hora → ciudad) pero `consulta_command`
nunca devuelve un estado distinto de END, así que el flujo era inalcanzable.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, ContextTypes

from bot.config import Settings
from bot.messages import LIMIT_MESSAGES
from database import users as db_users


async def consulta_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/consulta — muestra estado del usuario o lo redirige al onboarding por DM."""
    settings: Settings = context.bot_data["settings"]

    chat = update.effective_chat
    if chat.type == "private":
        await update.message.reply_text(LIMIT_MESSAGES["dm_only_group"])
        return

    if chat.id != settings.ALLOWED_CHAT_ID:
        return

    user_id = update.effective_user.id
    user = await db_users.get_user(user_id)

    if user and user["onboarding_complete"]:
        await update.message.reply_text(
            f"{user['alias']}, elige tu veneno.\n\n"
            "🃏 /tirartarot · ᚱ /runa · ☯ /iching · ⊕ /geomancia\n"
            "🔮 /oraculo · 📖 /bibliomancia · /ayudaoraculo para ver todo.",
            reply_to_message_id=update.message.message_id,
        )
        return

    bot_username = context.bot_data["bot_username"]
    await update.message.reply_text(
        "Puedes usar las tiradas directamente sin registrarte.\n\n"
        "🃏 /tirartarot · ᚱ /runa · ☯ /iching · ⊕ /geomancia\n"
        "🔮 /oraculo · 📖 /bibliomancia\n\n"
        "Si te registras, las lecturas se personalizan con tu perfil astral.\n"
        "Para /natal, /vedica y /numerologia sí necesitas registro.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "📝 Registrarme (opcional)",
                url=f"https://t.me/{bot_username}?start=onboarding",
            )],
        ]),
        reply_to_message_id=update.message.message_id,
    )


def build_onboarding_handler() -> CommandHandler:
    """Registra /consulta como comando simple. No hay máquina de estados."""
    return CommandHandler("consulta", consulta_command)
