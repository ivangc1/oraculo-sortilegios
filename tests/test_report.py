"""Tests del sistema de reportes: mensajes y helpers.

(El cooldown de reportes se eliminó al abrir el bot sin restricciones.)
"""

from unittest.mock import MagicMock

from bot.messages import LIMIT_MESSAGES
from bot.handlers.report import _user_display


# === Mensajes ===

def test_report_messages_exist():
    """Todas las claves report_* existen en LIMIT_MESSAGES."""
    expected = [
        "report_sent",
        "report_no_target",
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
        "exception", "traceback", "stack", "debug",
        "null", "http", "status",
    ]
    report_keys = [k for k in LIMIT_MESSAGES if k.startswith("report_")]
    for key in report_keys:
        msg = LIMIT_MESSAGES[key].lower()
        for word in technical_words:
            assert word not in msg, (
                f"LIMIT_MESSAGES['{key}'] contiene '{word}'"
            )


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
