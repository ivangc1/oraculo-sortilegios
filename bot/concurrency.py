"""Bloqueo de peticiones concurrentes por usuario + cola API."""

import asyncio
from contextlib import asynccontextmanager

# Usuarios con petición en curso
_active_requests: set[int] = set()

# Semáforo para limitar llamadas concurrentes a Anthropic
_api_semaphore: asyncio.Semaphore | None = None


def init_semaphore(max_concurrent: int = 3) -> None:
    global _api_semaphore
    _api_semaphore = asyncio.Semaphore(max_concurrent)


def get_semaphore() -> asyncio.Semaphore:
    if _api_semaphore is None:
        raise RuntimeError("Semáforo no inicializado. Llama init_semaphore() primero.")
    return _api_semaphore


def is_user_busy(user_id: int) -> bool:
    return user_id in _active_requests


def mark_user_busy(user_id: int) -> None:
    _active_requests.add(user_id)


def release_user(user_id: int) -> None:
    _active_requests.discard(user_id)


@asynccontextmanager
async def user_busy(user_id: int):
    """Contextmanager async que marca al usuario ocupado y libera al salir.

    Garantiza el release incluso ante excepciones, sin necesidad de try/finally
    repetido en cada handler. El caller debe verificar antes con is_user_busy()
    si quiere mostrar un mensaje específico al usuario; este contextmanager no
    hace esa verificación.
    """
    mark_user_busy(user_id)
    try:
        yield
    finally:
        release_user(user_id)
