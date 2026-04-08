"""Handler de /ayudaoraculo: contenido definido con todos los comandos."""

from telegram import Update
from telegram.ext import ContextTypes

import html

from bot.config import Settings
from bot.formatting import wrap_blockquote
from bot.middleware import middleware_check


_HELP_TEXT = """🔮 Modos disponibles:

🃏 /tirartarot — Consulta las cartas del Tarot
   Mazos: Rider-Waite · Marsella
   Una carta · Tres cartas · Cruz Celta · Sí/No
   Herradura (7) · Relación (6) · Estrella (7) · Cruz Simple (5)
   Tirada del día · 🎯 El Pezuñento elige
   Atajo: /tirartarot <tu pregunta>

ᚱ /runa — Consulta las runas del Elder Futhark
   Runa de Odín · Tres Nornas · Cruz Rúnica
   Cinco Runas · Siete Runas

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
   Biblia · Corán · Gita · Evangelio de Tomás · Liber AL

🆕 /consulta — Registrarte para empezar
📋 /miperfil · ✏️ /actualizarperfil · 🗑 /borrarme
🚨 /reportar — Reportar usuario o mensaje a los guardianes
❌ /cancelaroraculo — Cancelar operación en curso
❓ /ayudaoraculo — Este mensaje

Tira lo que quieras, cuando quieras. El oráculo no cierra."""


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para /ayudaoraculo."""
    settings: Settings = context.bot_data["settings"]
    if not await middleware_check(update, context, settings):
        return

    text = wrap_blockquote(html.escape(_HELP_TEXT)) if settings.USE_BLOCKQUOTE else _HELP_TEXT
    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_to_message_id=update.message.message_id,
    )
