"""Stub de límites — el bot NO tiene topes de uso ni cooldown.

Decisión consciente: ni cooldown, ni cuota diaria, ni tope mensual de gasto,
ni rate limit de onboarding, ni cap de longitud de pregunta. Cualquier
protección contra abuso se hace en Telegram (admins del grupo) o reintroduciendo
límites aquí; las funciones se mantienen como no-op para que los handlers
existentes que las llaman sigan funcionando.

Lo único activo a nivel técnico (en otros sitios):
- QUEUE_TIMEOUT en bot/config.py (45 s) para no bloquear el chat.
- MAX_CONCURRENT_API (semáforo asyncio) para no saturar la API.
- request_in_progress por usuario en bot/concurrency.py (un usuario no puede
  lanzar dos lecturas en paralelo).
"""

from bot.config import Settings


async def check_limits(user_id: int, mode: str, settings: Settings) -> str | None:
    """Sin límites: siempre OK."""
    return None


def record_cooldown(user_id: int) -> None:
    """Sin cooldown: no-op."""
    return None
