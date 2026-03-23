"""Alertas DM al admin con throttle."""

import time

from loguru import logger
from telegram import Bot

_alert_timestamps: dict[str, float] = {}

# Configurado en main.py
_admin_user_id: int = 0


def set_admin_user_id(user_id: int) -> None:
    global _admin_user_id
    _admin_user_id = user_id


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
        logger.error(f"Failed to send alert: {alert_type}")
