"""Alertas DM al admin con throttle."""

import time

from loguru import logger
from telegram import Bot

_alert_timestamps: dict[str, float] = {}

# Configurado en main.py
_admin_user_id: int = 0
_fallback_chat_id: int = 0
_fallback_thread_id: int | None = None


def set_admin_user_id(user_id: int) -> None:
    global _admin_user_id
    _admin_user_id = user_id


def set_fallback_chat_id(chat_id: int, thread_id: int | None = None) -> None:
    global _fallback_chat_id, _fallback_thread_id
    _fallback_chat_id = chat_id
    _fallback_thread_id = thread_id


async def send_alert(
    bot: Bot,
    alert_type: str,
    message: str,
    throttle_seconds: int = 300,
) -> None:
    """Envía alerta DM al admin. Throttle por tipo de alerta."""
    if _admin_user_id == 0:
        return

    now = time.time()
    last = _alert_timestamps.get(alert_type, 0)
    if throttle_seconds > 0 and (now - last) < throttle_seconds:
        return

    _alert_timestamps[alert_type] = now
    try:
        await bot.send_message(_admin_user_id, message)
    except Exception:
        # DM falló (el admin no ha iniciado /start con el bot).
        # Intentar enviar al grupo si hay chat_id configurado.
        try:
            if _fallback_chat_id:
                await bot.send_message(_fallback_chat_id, message,
                                       message_thread_id=_fallback_thread_id)
        except Exception:
            logger.error(f"Failed to send alert: {alert_type}")
