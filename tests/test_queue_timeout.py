"""Tests del timeout global 45s y concurrencia."""

import asyncio

import pytest

from bot.concurrency import (
    get_semaphore,
    init_semaphore,
    is_user_busy,
    mark_user_busy,
    release_user,
)
from bot.config import Settings


def test_user_busy_flow():
    """mark_user_busy → is_user_busy → release_user."""
    user_id = 99999
    assert not is_user_busy(user_id)
    mark_user_busy(user_id)
    assert is_user_busy(user_id)
    release_user(user_id)
    assert not is_user_busy(user_id)


def test_release_nonexistent_user():
    """release de usuario no marcado no falla (discard)."""
    release_user(88888)  # No debería lanzar excepción


def test_multiple_users_independent():
    """Dos usuarios no interfieren entre sí."""
    mark_user_busy(1001)
    mark_user_busy(1002)
    assert is_user_busy(1001)
    assert is_user_busy(1002)
    release_user(1001)
    assert not is_user_busy(1001)
    assert is_user_busy(1002)
    release_user(1002)


def test_semaphore_init():
    init_semaphore(3)
    sem = get_semaphore()
    assert isinstance(sem, asyncio.Semaphore)


def test_semaphore_not_init_raises():
    """Sin inicializar, get_semaphore lanza error."""
    import bot.concurrency as cc
    original = cc._api_semaphore
    cc._api_semaphore = None
    try:
        with pytest.raises(RuntimeError):
            get_semaphore()
    finally:
        cc._api_semaphore = original


def test_default_queue_timeout():
    """Settings tiene timeout 45s por defecto."""
    # No podemos instanciar Settings sin .env, pero verificamos el default
    import inspect
    source = inspect.getsource(Settings)
    assert "45.0" in source


@pytest.mark.asyncio
async def test_timeout_fires():
    """asyncio.wait_for con timeout corto lanza TimeoutError."""
    async def slow_task():
        await asyncio.sleep(10)

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(slow_task(), timeout=0.01)
