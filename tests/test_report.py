"""Tests del sistema de reportes: mensajes, cooldown, helpers."""

import time
from unittest.mock import MagicMock

from bot.messages import LIMIT_MESSAGES
from bot.handlers.report import (
    _check_cooldown,
    _record_cooldown,
    _report_cooldown,
    _user_display,
)


# === Mensajes ===

def test_report_messages_exist():
    """Todas las claves report_* existen en LIMIT_MESSAGES."""
    expected = [
        "report_sent",
        "report_no_target",
        "report_cooldown",
        "report_self",
        "report_admin",
        "report_error",
    ]
    for key in expected:
        assert key in LIMIT_MESSAGES, f"Falta clave: {key}"
        assert LIMIT_MESSAGES[key], f"Mensaje vacío: {key}"


def test_report_messages_no_technical():
    """Los mensajes de reporte no contienen jerga técnica."""
    technical_words = [
        "error", "exception", "traceback", "stack", "debug",
        "null", "none", "api", "http", "status", "code",
    ]
    report_keys = [k for k in LIMIT_MESSAGES if k.startswith("report_")]
    for key in report_keys:
        msg = LIMIT_MESSAGES[key].lower()
        for word in technical_words:
            assert word not in msg, (
                f"LIMIT_MESSAGES['{key}'] contiene '{word}'"
            )


# === Cooldown ===

def test_cooldown_allows_first_report():
    """Primer reporte siempre permitido."""
    user_id = 999999
    _report_cooldown.pop(user_id, None)
    assert _check_cooldown(user_id, 300) is True


def test_cooldown_blocks_rapid_report():
    """Segundo reporte dentro del cooldown bloqueado."""
    user_id = 888888
    _record_cooldown(user_id)
    assert _check_cooldown(user_id, 300) is False


def test_cooldown_allows_after_expiry():
    """Reporte permitido después del cooldown."""
    user_id = 777777
    _report_cooldown[user_id] = time.time() - 301
    assert _check_cooldown(user_id, 300) is True


# === User display ===

def test_user_display_full():
    """Nombre completo con username."""
    user = MagicMock()
    user.full_name = "Juan García"
    user.first_name = "Juan"
    user.username = "juanito"
    user.id = 12345
    assert "Juan García" in _user_display(user)
    assert "@juanito" in _user_display(user)
    assert "12345" in _user_display(user)


def test_user_display_no_username():
    """Sin username."""
    user = MagicMock()
    user.full_name = "María"
    user.first_name = "María"
    user.username = None
    user.id = 67890
    result = _user_display(user)
    assert "María" in result
    assert "@" not in result


def test_user_display_none():
    """User None devuelve Desconocido."""
    assert _user_display(None) == "Desconocido"
