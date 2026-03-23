"""Handler de /startoraculo: presentación in-character El Pezuñento.

- En grupo: si registrado → "Usa /consulta". Si no → "Preséntate con /consulta".
- En DM: "Solo funciono en La Taberna."
"""

from telegram import Update
from telegram.ext import ContextTypes

from database import users as db_users


_INTRO_GROUP = """🔮 Soy El Pezuñento, el oráculo de La Taberna de los Sortilegios.

Leo las cartas, las runas, los hexagramas y lo que haga falta. No endulzo las lecturas y no hago recados. Si preguntas en serio, te respondo en serio.

Usa /consulta para presentarte y empezar. Si ya nos conocemos, escribe /tarot, /runa, /iching o lo que te apetezca."""

_INTRO_GROUP_REGISTERED = """🔮 Ya nos conocemos, {alias}.

Usa /tarot, /runa, /iching, /geomancia, /numerologia, /natal, /vedica, /oraculo, /bibliomancia o /ayudaoraculo para ver todo lo que puedo hacer."""

_INTRO_DM = """🔮 Soy El Pezuñento, el oráculo de La Taberna de los Sortilegios.

Solo funciono en el grupo. No hago consultas privadas. Búscame en La Taberna."""


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para /startoraculo — DM o grupo."""
    chat = update.effective_chat

    if chat.type == "private":
        await update.message.reply_text(_INTRO_DM)
        return

    # En grupo
    user_id = update.effective_user.id
    user = await db_users.get_user(user_id)

    if user and user["onboarding_complete"]:
        text = _INTRO_GROUP_REGISTERED.format(alias=user["alias"])
    else:
        text = _INTRO_GROUP

    await update.message.reply_text(
        text,
        reply_to_message_id=update.message.message_id,
    )
