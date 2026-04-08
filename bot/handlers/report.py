"""Handler de /reportar — reportar usuarios/mensajes a los admins.

Dos modos:
- Reply a mensaje + /reportar [motivo]
- /reportar @usuario [motivo]

Notificación por DM a todos los admins. Confirmación breve en grupo.
Intenta borrar el /reportar para proteger anonimato del reportante.
"""

import time
from datetime import datetime, timezone

from loguru import logger
from telegram import Update
from telegram.error import BadRequest, Forbidden
from telegram.ext import ContextTypes

from bot.config import Settings
from bot.messages import LIMIT_MESSAGES
from bot.middleware import middleware_check
from bot.typing import get_thread_id

# Cooldown in-memory: user_id → timestamp último reporte
_report_cooldown: dict[int, float] = {}


def _check_cooldown(user_id: int, cooldown_seconds: int) -> bool:
    """True si el usuario puede reportar, False si en cooldown."""
    now = time.time()
    last = _report_cooldown.get(user_id, 0)
    return (now - last) >= cooldown_seconds


def _record_cooldown(user_id: int) -> None:
    _report_cooldown[user_id] = time.time()


def _user_display(user) -> str:
    """Nombre legible de un usuario Telegram."""
    if not user:
        return "Desconocido"
    name = user.full_name or user.first_name or ""
    username = f" (@{user.username})" if user.username else ""
    return f"{name}{username} [ID: {user.id}]"


async def reportar_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para /reportar — reportar usuario o mensaje a los admins."""
    settings: Settings = context.bot_data["settings"]
    if not await middleware_check(update, context, settings):
        return

    user = update.effective_user
    user_id = user.id
    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    msg = update.message

    # Cooldown
    if not _check_cooldown(user_id, settings.REPORT_COOLDOWN_SECONDS):
        await msg.reply_text(
            LIMIT_MESSAGES["report_cooldown"],
            reply_to_message_id=msg.message_id,
        )
        return

    # Determinar target: reply o @username en args
    reported_user = None
    reported_message = None
    reason_parts = list(context.args) if context.args else []

    if msg.reply_to_message:
        # Modo reply: el target es el autor del mensaje respondido
        reported_user = msg.reply_to_message.from_user
        reported_message = msg.reply_to_message
        reason = " ".join(reason_parts) if reason_parts else "(sin motivo)"
    elif reason_parts and reason_parts[0].startswith("@"):
        # Modo @username: /reportar @usuario motivo
        target_username = reason_parts[0].lstrip("@")
        reason = " ".join(reason_parts[1:]) if len(reason_parts) > 1 else "(sin motivo)"
        # No podemos resolver @username a user object sin reply, solo guardar el username
        reported_user = None  # Sin objeto user, solo tenemos el username
    else:
        await msg.reply_text(
            LIMIT_MESSAGES["report_no_target"],
            reply_to_message_id=msg.message_id,
        )
        return

    # Validaciones
    if reported_user:
        if reported_user.id == user_id:
            await msg.reply_text(
                LIMIT_MESSAGES["report_self"],
                reply_to_message_id=msg.message_id,
            )
            return
        if reported_user.id in settings.report_admin_ids:
            await msg.reply_text(
                LIMIT_MESSAGES["report_admin"],
                reply_to_message_id=msg.message_id,
            )
            return

    # Construir mensaje de reporte para admins
    now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    lines = [
        "🚨 REPORTE",
        "",
        f"De: {_user_display(user)}",
    ]

    if reported_user:
        lines.append(f"Contra: {_user_display(reported_user)}")
    elif reason_parts and reason_parts[0].startswith("@"):
        lines.append(f"Contra: @{reason_parts[0].lstrip('@')}")

    lines.append(f"Motivo: {reason}")
    lines.append(f"Fecha: {now}")

    if reported_message:
        # Texto del mensaje reportado
        msg_text = reported_message.text or reported_message.caption or "(multimedia sin texto)"
        if len(msg_text) > 200:
            msg_text = msg_text[:200] + "..."
        lines.append(f"Mensaje: {msg_text}")

        # Link al mensaje si es posible
        if reported_message.link:
            lines.append(f"Link: {reported_message.link}")

    report_text = "\n".join(lines)

    # Enviar DM a cada admin
    _record_cooldown(user_id)
    sent_count = 0
    for admin_id in settings.report_admin_ids:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=report_text,
            )
            sent_count += 1
        except (Forbidden, BadRequest) as e:
            logger.warning(f"No se pudo enviar reporte a admin {admin_id}: {e}")
        except Exception as e:
            logger.error(f"Error enviando reporte a admin {admin_id}: {e}")

    if sent_count == 0:
        await msg.reply_text(
            LIMIT_MESSAGES["report_error"],
            reply_to_message_id=msg.message_id,
        )
        return

    # Confirmación breve en grupo
    await msg.reply_text(
        LIMIT_MESSAGES["report_sent"],
        reply_to_message_id=msg.message_id,
    )

    # Intentar borrar el /reportar para proteger anonimato
    try:
        await msg.delete()
    except (Forbidden, BadRequest):
        pass  # Sin permiso de borrar, no pasa nada

    logger.info(
        f"Reporte: {user.id} → {reported_user.id if reported_user else 'username'} "
        f"| motivo: {reason[:50]}"
    )
