"""Handler de /ayuda: contenido definido con todos los comandos."""

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import Settings
from bot.middleware import middleware_check


_HELP_TEXT = """🔮 Modos disponibles:

🃏 /tarot — Consulta las cartas del Tarot
   Una carta (Sí/No) · Tres cartas · Cruz Celta

ᚱ /runa — Consulta las runas del Elder Futhark
   Runa de Odín · Tres Nornas · Cruz Rúnica

☯ /iching — Consulta el I Ching
   Hexagrama con líneas mutables

⊕ /geomancia — Consulta las figuras geománticas
   Una figura · Escudo completo

🔢 /numerologia — Tu mapa numerológico
   Informe completo · Compatibilidad

🪐 /natal — Carta natal tropical
🕉 /vedica — Carta natal védica (Jyotish)
🔮 /oraculo — Pregunta libre al oráculo

📖 /bibliomancia — Fragmento de texto sagrado
   Biblia · Corán · Gita · Evangelio de Tomás

🛡 /admins — Guardianes de la taberna

🆕 /consulta — Registrarte para empezar
📋 /miperfil · ✏️ /actualizarperfil · 🗑 /borrarme
❌ /cancelar — Cancelar operación en curso
❓ /ayuda — Este mensaje

Tienes 5 tiradas diarias + 3 consultas al oráculo."""


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para /ayuda."""
    settings: Settings = context.bot_data["settings"]
    if not await middleware_check(update, context, settings):
        return

    await update.message.reply_text(
        _HELP_TEXT,
        reply_to_message_id=update.message.message_id,
    )
