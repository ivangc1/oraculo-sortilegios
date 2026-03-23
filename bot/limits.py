"""Límites de uso diario y cooldown."""

import time

from bot.config import Settings
from database import usage as db_usage

# Cooldown por usuario: {user_id: timestamp último uso}
_last_use: dict[int, float] = {}

# Modos que consumen del pool de adivinación
_DIVINATION_MODES = {"tarot", "runas", "iching", "geomancia"}


async def check_limits(user_id: int, mode: str, settings: Settings) -> str | None:
    """Verifica límites. Devuelve clave de LIMIT_MESSAGES si se excede, None si OK."""
    # Cooldown
    now = time.time()
    last = _last_use.get(user_id, 0)
    if (now - last) < settings.COOLDOWN_SECONDS:
        return "cooldown"

    # Límite por modo
    if mode in _DIVINATION_MODES:
        count = await db_usage.get_daily_usage_count(user_id)
        if count >= settings.DAILY_DIVINATION_POOL:
            return "daily_limit"
    elif mode == "numerologia":
        count = await db_usage.get_daily_usage_count(user_id, mode="numerologia")
        if count >= settings.DAILY_NUMEROLOGIA_LIMIT:
            return "daily_limit"
    elif mode == "natal":
        count = await db_usage.get_daily_usage_count(user_id, mode="natal")
        if count >= settings.DAILY_NATAL_LIMIT:
            return "daily_limit"
    elif mode == "oraculo":
        count = await db_usage.get_daily_usage_count(user_id, mode="oraculo")
        if count >= settings.DAILY_ORACULO_LIMIT:
            return "daily_limit"

    return None


def record_cooldown(user_id: int) -> None:
    """Registra timestamp para cooldown."""
    _last_use[user_id] = time.time()
