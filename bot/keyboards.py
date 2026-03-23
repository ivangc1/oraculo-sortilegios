"""Teclados inline y mapeo de callback data (≤64 bytes cada uno)."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Mapeo callback_data → (mode, variant)
CALLBACKS = {
    "t:1": ("tarot", "1_carta"),
    "t:3": ("tarot", "3_cartas"),
    "t:cc": ("tarot", "cruz_celta"),
    "r:1": ("runas", "odin"),
    "r:3": ("runas", "nornas"),
    "r:cr": ("runas", "cruz"),
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

# Callbacks de admins se generan dinámicamente: "a:0" a "a:19"
for i in range(20):
    CALLBACKS[f"a:{i}"] = ("admins", str(i))


def parse_callback(data: str) -> tuple[str, str] | None:
    """Parsea callback_data → (mode, variant) o None si no reconocido."""
    # Feedback: "fb:p:123" o "fb:n:123"
    if data.startswith("fb:"):
        return ("feedback", data)
    return CALLBACKS.get(data)


def tarot_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🃏 Una carta", callback_data="t:1"),
            InlineKeyboardButton("🃏 Tres cartas", callback_data="t:3"),
        ],
        [InlineKeyboardButton("🃏 Cruz Celta", callback_data="t:cc")],
    ])


def runas_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("ᚱ Runa de Odín", callback_data="r:1"),
            InlineKeyboardButton("ᚱ Tres Nornas", callback_data="r:3"),
        ],
        [InlineKeyboardButton("ᚱ Cruz Rúnica", callback_data="r:cr")],
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
