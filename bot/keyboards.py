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
    # Tarot sub-menus
    "tm:r": ("tarot_menu", "rapidas"),
    "tm:c": ("tarot_menu", "completas"),
    "tm:e": ("tarot_menu", "especiales"),
    "tm:bk": ("tarot_menu", "back"),
    # Tarot deck selection
    "td:rws": ("tarot_deck", "rws"),
    "td:mar": ("tarot_deck", "marsella"),
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
    "bl:la": ("bibliomancia", "liber"),
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


def tarot_deck_keyboard() -> InlineKeyboardMarkup:
    """Selección de mazo de tarot."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎴 Rider-Waite", callback_data="td:rws"),
            InlineKeyboardButton("🏰 Marsella", callback_data="td:mar"),
        ],
    ])


def tarot_keyboard() -> InlineKeyboardMarkup:
    """Menu principal de tarot — 3 categorias."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚡ Rápidas", callback_data="tm:r"),
            InlineKeyboardButton("🔮 Completas", callback_data="tm:c"),
        ],
        [InlineKeyboardButton("✨ Especiales", callback_data="tm:e")],
    ])


def tarot_rapidas_keyboard() -> InlineKeyboardMarkup:
    """Sub-menu: tiradas rapidas (1-3 cartas)."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🃏 Una carta", callback_data="t:1"),
            InlineKeyboardButton("🃏 Sí/No", callback_data="t:sn"),
        ],
        [InlineKeyboardButton("☀️ Tirada del día", callback_data="t:dd")],
        [InlineKeyboardButton("← Volver", callback_data="tm:bk")],
    ])


def tarot_completas_keyboard() -> InlineKeyboardMarkup:
    """Sub-menu: tiradas completas (3-10 cartas)."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🃏 Tres cartas", callback_data="t:3"),
            InlineKeyboardButton("🃏 Cruz Simple", callback_data="t:cs"),
        ],
        [
            InlineKeyboardButton("🃏 Herradura", callback_data="t:hr"),
            InlineKeyboardButton("🃏 Cruz Celta", callback_data="t:cc"),
        ],
        [InlineKeyboardButton("← Volver", callback_data="tm:bk")],
    ])


def tarot_especiales_keyboard() -> InlineKeyboardMarkup:
    """Sub-menu: tiradas especiales."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🃏 Relación", callback_data="t:rl"),
            InlineKeyboardButton("🃏 Estrella", callback_data="t:es"),
        ],
        [InlineKeyboardButton("🎯 El Pezuñento elige", callback_data="t:sm")],
        [InlineKeyboardButton("← Volver", callback_data="tm:bk")],
    ])


def runas_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("ᚱ Odín (1)", callback_data="r:1"),
            InlineKeyboardButton("ᚱ Nornas (3)", callback_data="r:3"),
        ],
        [
            InlineKeyboardButton("ᚱ Cruz (5)", callback_data="r:cr"),
            InlineKeyboardButton("ᚱ Cinco (5)", callback_data="r:5"),
        ],
        [InlineKeyboardButton("ᚱ Siete (7)", callback_data="r:7")],
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
        [
            InlineKeyboardButton("📖 Liber AL vel Legis", callback_data="bl:la"),
        ],
    ])


def feedback_keyboard(usage_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👍", callback_data=f"fb:p:{usage_id}"),
            InlineKeyboardButton("👎", callback_data=f"fb:n:{usage_id}"),
        ],
    ])
