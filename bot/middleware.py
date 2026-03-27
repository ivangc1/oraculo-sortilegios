"""Middleware completo: edits, DM, chat_id, topics, membresía caché, username, migration."""

import time

from loguru import logger
from telegram import Update
from telegram.error import BadRequest, Forbidden
from telegram.ext import ContextTypes

from bot.config import Settings
from database import users as db_users

# Caché de membresía: {user_id: timestamp}
_membership_cache: dict[int, float] = {}
_MEMBERSHIP_TTL = 3600  # 1 hora


async def middleware_check(update: Update, context: ContextTypes.DEFAULT_TYPE, settings: Settings) -> bool:
    """Verifica todas las precondiciones. Devuelve True si el mensaje puede procesarse.

    Orden:
    1. Ignorar ediciones
    2. Ignorar no-texto (fotos, stickers, forwards, audio)
    3. Bloquear DMs (salvo /start que responde in-character)
    4. Verificar chat_id
    5. Topics (si ALLOWED_THREAD_ID configurado)
    6. Verificar membresía (caché 1h)
    7. Actualizar username si cambió
    """
    # Sin mensaje efectivo → ignorar
    if update.effective_message is None:
        return False

    message = update.effective_message

    # 1. Ignorar ediciones
    if update.edited_message is not None:
        return False

    # 2. Ignorar no-texto (fotos, stickers, forwards, audio, etc.)
    if message.text is None:
        return False

    user = update.effective_user
    if user is None:
        return False
    # Permitir admins anónimos (id=1087968824, is_bot=True)
    if user.is_bot and user.id != 1087968824:
        return False

    chat = update.effective_chat

    # 3. DMs — solo permitir /start (deep links) y /cancelaroraculo
    # Los flujos de datos personales (onboarding, update_profile, set_fullname)
    # se manejan via ConversationHandler en DM. Todo lo demas se bloquea.
    if chat.type == "private":
        if message.text:
            cmd = message.text.split()[0].split("@")[0]
            # Comandos permitidos en DM
            if cmd in ("/start", "/startoraculo", "/cancelaroraculo"):
                return True
        # Todo lo demas en DM → rechazo (tiradas, etc.)
        try:
            await message.reply_text(
                "Solo funciono en La Taberna de los Sortilegios. No hago consultas privadas.",
                reply_to_message_id=message.message_id,
            )
        except (Forbidden, BadRequest):
            pass
        return False

    # 4. Verificar chat_id
    if chat.id != settings.ALLOWED_CHAT_ID:
        return False

    # 5. Topics — si el grupo es forum y hay hilo configurado, solo aceptar ese hilo
    if getattr(chat, "is_forum", False) and settings.ALLOWED_THREAD_ID is not None:
        if message.message_thread_id != settings.ALLOWED_THREAD_ID:
            return False

    # 6. Membresía (caché 1h) — admins anónimos siempre pasan
    if user.id != 1087968824 and not await _check_membership(user.id, chat.id, context, settings):
        return False

    # 7. Actualizar username si cambió
    await _update_username_if_changed(user.id, user.username)

    return True


async def _check_membership(
    user_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE, settings: Settings
) -> bool:
    """Verifica que el usuario es miembro del grupo. Caché 1h."""
    now = time.time()
    cached_at = _membership_cache.get(user_id)
    if cached_at and (now - cached_at) < _MEMBERSHIP_TTL:
        return True

    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status in ("member", "administrator", "creator"):
            _membership_cache[user_id] = now
            return True
        return False
    except (BadRequest, Forbidden):
        return False


async def _update_username_if_changed(user_id: int, current_username: str | None) -> None:
    """Actualiza username en DB si cambió."""
    user_data = await db_users.get_user(user_id)
    if user_data is None:
        return
    if user_data["telegram_username"] != current_username:
        await db_users.update_username(user_id, current_username)
        logger.info(f"Username actualizado para user {user_id}")


def cleanup_membership_cache() -> int:
    """Limpia entradas expiradas. Devuelve número de limpiadas."""
    now = time.time()
    expired = [
        uid for uid, ts in _membership_cache.items()
        if (now - ts) >= _MEMBERSHIP_TTL
    ]
    for uid in expired:
        del _membership_cache[uid]
    return len(expired)


async def handle_migration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para migración grupo → supergrupo. Alerta máxima prioridad."""
    if update.message is None:
        return
    old_id = update.message.migrate_from_chat_id
    new_id = update.effective_chat.id
    logger.critical(f"Group migrated! Old: {old_id} → New: {new_id}")
    # Importar aquí para evitar circular
    from bot.alerts import send_alert
    await send_alert(
        context.bot,
        "migration",
        f"🚨 El grupo migró de ID.\n"
        f"Viejo: {old_id}\nNuevo: {new_id}\n"
        f"Actualizar ALLOWED_CHAT_ID en .env y reiniciar.",
        throttle_seconds=0,  # Sin throttle para migraciones
    )
