"""Tests del módulo telethon_client: filtros, helpers, validaciones."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from service.telethon_client import (
    AdminLogEntry,
    FILTER_MAP,
    VALID_FILTERS,
    _get_user_display,
)


# === FILTER_MAP y VALID_FILTERS ===

def test_valid_filters_sorted():
    """VALID_FILTERS está ordenado alfabéticamente."""
    assert VALID_FILTERS == sorted(VALID_FILTERS)


def test_valid_filters_matches_filter_map():
    """VALID_FILTERS contiene exactamente las keys de FILTER_MAP."""
    assert set(VALID_FILTERS) == set(FILTER_MAP.keys())


def test_filter_map_values_are_bool_dicts():
    """Todos los valores de FILTER_MAP son dicts con valores bool."""
    for key, value in FILTER_MAP.items():
        assert isinstance(value, dict), f"FILTER_MAP[{key}] no es dict"
        for k, v in value.items():
            assert isinstance(v, bool), f"FILTER_MAP[{key}][{k}] no es bool"


def test_common_filters_present():
    """Los filtros más comunes están presentes."""
    expected = {"pin", "ban", "delete", "edit", "kick", "invite"}
    assert expected.issubset(set(VALID_FILTERS))


# === AdminLogEntry ===

def test_admin_log_entry_creation():
    """AdminLogEntry se crea correctamente."""
    entry = AdminLogEntry(
        date=datetime(2025, 1, 15, 14, 30),
        admin_name="TestAdmin",
        action="Fijo mensaje",
        target='"Hola mundo"',
    )
    assert entry.admin_name == "TestAdmin"
    assert entry.action == "Fijo mensaje"
    assert entry.target == '"Hola mundo"'
    assert entry.date.year == 2025


# === _get_user_display ===

def test_get_user_display_full_name():
    """Nombre completo: first + last."""
    user = MagicMock()
    user.first_name = "Juan"
    user.last_name = "García"
    assert _get_user_display(user) == "Juan García"


def test_get_user_display_first_only():
    """Solo first_name."""
    user = MagicMock()
    user.first_name = "María"
    user.last_name = None
    assert _get_user_display(user) == "María"


def test_get_user_display_none():
    """User None devuelve Desconocido."""
    assert _get_user_display(None) == "Desconocido"


def test_get_user_display_no_names():
    """Sin nombres devuelve User#ID."""
    user = MagicMock()
    user.first_name = ""
    user.last_name = ""
    user.id = 12345
    assert _get_user_display(user) == "User#12345"


# === TelethonClient sin conexión ===

def test_client_not_connected_by_default():
    """El cliente no está conectado al crearse."""
    from service.telethon_client import TelethonClient
    client = TelethonClient(api_id=123, api_hash="abc", bot_token="tok")
    assert not client.is_connected


@pytest.mark.asyncio
async def test_get_admin_log_raises_when_disconnected():
    """get_admin_log lanza ConnectionError si no está conectado."""
    from service.telethon_client import TelethonClient
    client = TelethonClient(api_id=123, api_hash="abc", bot_token="tok")
    with pytest.raises(ConnectionError):
        await client.get_admin_log(chat_id=-1001234567890)


@pytest.mark.asyncio
async def test_get_admin_log_raises_on_invalid_filter():
    """get_admin_log lanza ValueError con filtro inválido."""
    from service.telethon_client import TelethonClient
    client = TelethonClient(api_id=123, api_hash="abc", bot_token="tok")
    # Simular conexión
    client._client = MagicMock()
    client._client.is_connected = MagicMock(return_value=True)
    with pytest.raises(ValueError, match="Filtro invalido"):
        await client.get_admin_log(chat_id=-1001234567890, filter_type="inventado")
