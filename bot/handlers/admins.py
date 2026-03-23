"""Handler de /admins: directorio de guardianes de la taberna (€0 API).

Grid inline 2 columnas → bio individual → [← Volver].
Un solo mensaje que se edita (zero spam).
Mención por user_id (HTML: <a href="tg://user?id=X">).
Datos en admins_private.json (en .gitignore).
Auto-captura user_id como fallback si no tiene ID en el JSON.
"""

import json
from pathlib import Path

from loguru import logger
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from bot.config import Settings
from bot.messages import LIMIT_MESSAGES
from bot.middleware import middleware_check

_ADMINS_DATA: list[dict] | None = None
_ADMINS_BY_KEY: dict[str, dict] | None = None


def _load_admins() -> None:
    global _ADMINS_DATA, _ADMINS_BY_KEY
    if _ADMINS_DATA is not None:
        return

    path = Path(__file__).parent.parent.parent / "data" / "admins_private.json"
    if not path.exists():
        logger.warning("admins_private.json not found, admins command disabled")
        _ADMINS_DATA = []
        _ADMINS_BY_KEY = {}
        return

    with open(path, encoding="utf-8") as f:
        _ADMINS_DATA = json.load(f)

    _ADMINS_BY_KEY = {a["key"]: a for a in _ADMINS_DATA}
    logger.info(f"Admins cargados: {len(_ADMINS_DATA)}")


def _build_grid_keyboard() -> InlineKeyboardMarkup:
    """Grid de 2 columnas con los nombres de los admins."""
    _load_admins()
    buttons = []
    row = []
    for i, admin in enumerate(_ADMINS_DATA):
        row.append(InlineKeyboardButton(
            admin["display_name"],
            callback_data=f"a:{i}",
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


def _build_bio_text(admin: dict) -> str:
    """Construye texto de bio con mención por user_id."""
    name = admin["display_name"]
    user_id = admin.get("telegram_user_id", 0)
    bio = admin.get("bio", "")

    if user_id and user_id != 0:
        mention = f'<a href="tg://user?id={user_id}">{name}</a>'
    else:
        # Sin user_id → solo nombre
        username = admin.get("username", "")
        if username:
            mention = f"@{username} ({name})"
        else:
            mention = name

    return f"🛡 {mention}\n\n{bio}"


def _back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("← Volver", callback_data="a:bk")],
    ])


async def admins_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para /admins — grid o búsqueda directa."""
    settings: Settings = context.bot_data["settings"]
    if not await middleware_check(update, context, settings):
        return

    _load_admins()

    # Comprobar argumento directo: /admins @void o /admins void
    text = (update.message.text or "").strip()
    parts = text.split(maxsplit=1)
    if len(parts) > 1:
        search = parts[1].strip().lstrip("@").lower()
        admin = _find_admin(search)
        if admin:
            bio_text = _build_bio_text(admin)
            await update.message.reply_text(
                bio_text,
                parse_mode="HTML",
                reply_markup=_back_keyboard(),
                reply_to_message_id=update.message.message_id,
            )
        else:
            await update.message.reply_text(
                LIMIT_MESSAGES["unknown_guardian"],
                reply_to_message_id=update.message.message_id,
            )
        return

    # Sin argumento → grid
    if not _ADMINS_DATA:
        await update.message.reply_text(
            "No hay guardianes registrados.",
            reply_to_message_id=update.message.message_id,
        )
        return

    await update.message.reply_text(
        "🛡 Guardianes de La Taberna de los Sortilegios",
        reply_markup=_build_grid_keyboard(),
        reply_to_message_id=update.message.message_id,
    )


async def admins_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, index_or_action: str,
) -> None:
    """Callback desde grid o botón volver."""
    query = update.callback_query
    await query.answer()

    _load_admins()

    if index_or_action == "back":
        # Volver al grid
        try:
            await query.edit_message_text(
                "🛡 Guardianes de La Taberna de los Sortilegios",
                reply_markup=_build_grid_keyboard(),
            )
        except BadRequest:
            pass
        return

    # Mostrar bio del admin por índice
    try:
        idx = int(index_or_action)
    except ValueError:
        return

    if idx < 0 or idx >= len(_ADMINS_DATA):
        return

    admin = _ADMINS_DATA[idx]
    bio_text = _build_bio_text(admin)

    try:
        await query.edit_message_text(
            bio_text,
            parse_mode="HTML",
            reply_markup=_back_keyboard(),
        )
    except BadRequest:
        pass


def _find_admin(search: str) -> dict | None:
    """Busca admin por key o username (case-insensitive)."""
    _load_admins()
    search = search.lower()

    # Buscar por key
    if search in _ADMINS_BY_KEY:
        return _ADMINS_BY_KEY[search]

    # Buscar por username
    for admin in _ADMINS_DATA:
        if admin.get("username", "").lower() == search:
            return admin
        if admin.get("display_name", "").lower() == search:
            return admin

    return None


async def auto_capture_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Auto-captura: si un admin sin user_id escribe en el grupo, captura su ID.

    Se llama desde middleware para todos los mensajes.
    """
    _load_admins()
    if not _ADMINS_DATA:
        return

    user = update.effective_user
    if not user or not user.username:
        return

    username_lower = user.username.lower()
    for admin in _ADMINS_DATA:
        if (admin.get("username", "").lower() == username_lower
                and (not admin.get("telegram_user_id") or admin["telegram_user_id"] == 0)):
            logger.info(
                f"Auto-captured admin user_id: {user.username} → {user.id}. "
                f"Update admins_private.json manually."
            )
            # No modificamos el JSON automáticamente, solo logueamos
            break
