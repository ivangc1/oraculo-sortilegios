"""Teclados inline y mapeo de callback data (<=64 bytes cada uno)."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Mapeo callback_data -> (mode, variant)
CALLBACKS = {
    # Tarot (9 variantes + smart)
    "t:1": ("tarot", "1_carta"),
    "t:3": ("tarot", "3_cartas"),
    "t:cc": ("tarot", "cruz_celta"),
    "t:hr": ("tarot", "herradura"),
    "t:rl": ("tarot", "relacion"),
    "t:es": ("tarot", "estrella"),
    "t:cs": ("tarot", "cruz_simple"),
    "t:sn": ("tarot", "si_no"),
    "t:dd": ("tarot", "tirada_dia"),
    "t:sm": ("tarot", "smart"),
    # Runas (5 variantes)
    "r:1": ("runas", "odin"),
    "r:3": ("runas", "nornas"),
    "r:cr": ("runas", "cruz"),
    "r:5": ("runas", "cinco"),
    "r:7": ("runas", "siete"),
    # Otros
    "ic": ("iching", "hexagrama"),
    "g:1": ("geomancia", "1_figura"),
    "g:e": ("geomancia", "escudo"),
    "n:i": ("numerologia", "informe"),
    "n:c": ("numerologia", "compatibilidad"),
    "nt": ("natal", "tropical"),
    "nv": ("natal", "vedica"),
    "or": ("oraculo", "libre"),
    "q:y": ("question", "yes"),
    "q:n": ("question", "no"),
    # Bibliomancia
    "bl:bi": ("bibliomancia", "biblia"),
    "bl:co": ("bibliomancia", "coran"),
    "bl:gi": ("bibliomancia", "gita"),
    "bl:ev": ("bibliomancia", "evangelio"),
    # Admins (back)
    "a:bk": ("admins", "back"),
}

# Callbacks de admins se generan dinamicamente: "a:0" a "a:19"
for i in range(20):
    CALLBACKS[f"a:{i}"] = ("admins", str(i))


def parse_callback(data: str) -> tuple[str, str] | None:
    """Parsea callback_data -> (mode, variant) o None si no reconocido."""
    if data.startswith("fb:"):
        return ("feedback", data)
    return CALLBACKS.get(data)


def tarot_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🃏 Una carta", callback_data="t:1"),
            InlineKeyboardButton("🃏 Tres cartas", callback_data="t:3"),
        ],
        [
            InlineKeyboardButton("🃏 Cruz Celta", callback_data="t:cc"),
            InlineKeyboardButton("🃏 Sí/No", callback_data="t:sn"),
        ],
        [
            InlineKeyboardButton("🃏 Herradura", callback_data="t:hr"),
            InlineKeyboardButton("🃏 Relación", callback_data="t:rl"),
        ],
        [
            InlineKeyboardButton("🃏 Estrella", callback_data="t:es"),
            InlineKeyboardButton("🃏 Cruz Simple", callback_data="t:cs"),
        ],
        [InlineKeyboardButton("☀️ Tirada del día", callback_data="t:dd")],
        [InlineKeyboardButton("🎯 El Pezuñento elige", callback_data="t:sm")],
    ])


def runas_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("ᚱ Runa de Odín", callback_data="r:1"),
            InlineKeyboardButton("ᚱ Tres Nornas", callback_data="r:3"),
        ],
        [
            InlineKeyboardButton("ᚱ Cruz Rúnica", callback_data="r:cr"),
            InlineKeyboardButton("ᚱ Cinco Runas", callback_data="r:5"),
        ],
        [InlineKeyboardButton("ᚱ Siete Runas", callback_data="r:7")],
    ])


def iching_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("☯ Hexagrama", callback_data="ic")],
    ])


def geomancia_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⊕ Una figura", callback_data="g:1"),
            InlineKeyboardButton("⊕ Escudo completo", callback_data="g:e"),
        ],
    ])


def numerologia_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔢 Informe", callback_data="n:i"),
            InlineKeyboardButton("🔢 Compatibilidad", callback_data="n:c"),
        ],
    ])


def natal_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🪐 Tropical", callback_data="nt"),
            InlineKeyboardButton("🕉 Védica", callback_data="nv"),
        ],
    ])


def question_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Sí", callback_data="q:y"),
            InlineKeyboardButton("No", callback_data="q:n"),
        ],
    ])


def bibliomancia_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📖 Biblia", callback_data="bl:bi"),
            InlineKeyboardButton("📖 Corán", callback_data="bl:co"),
        ],
        [
            InlineKeyboardButton("📖 Gita", callback_data="bl:gi"),
            InlineKeyboardButton("📖 Evangelio de Tomás", callback_data="bl:ev"),
        ],
    ])


def feedback_keyboard(usage_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👍", callback_data=f"fb:p:{usage_id}"),
            InlineKeyboardButton("👎", callback_data=f"fb:n:{usage_id}"),
        ],
    ])
