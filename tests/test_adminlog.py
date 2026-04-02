"""Tests del comando /adminlog: mensajes, filtros, integración."""

from bot.messages import LIMIT_MESSAGES
from service.telethon_client import VALID_FILTERS


# === Mensajes adminlog en LIMIT_MESSAGES ===

def test_adminlog_messages_exist():
    """Todas las claves adminlog_* existen en LIMIT_MESSAGES."""
    expected = [
        "adminlog_no_results",
        "adminlog_not_configured",
        "adminlog_no_permission",
        "adminlog_invalid_filter",
        "adminlog_error",
    ]
    for key in expected:
        assert key in LIMIT_MESSAGES, f"Falta clave: {key}"
        assert LIMIT_MESSAGES[key], f"Mensaje vacío: {key}"


def test_adminlog_messages_no_technical():
    """Los mensajes adminlog no contienen jerga técnica."""
    technical_words = [
        "error", "exception", "traceback", "stack", "debug",
        "null", "none", "api", "http", "status", "code",
    ]
    adminlog_keys = [k for k in LIMIT_MESSAGES if k.startswith("adminlog_")]
    for key in adminlog_keys:
        msg = LIMIT_MESSAGES[key].lower()
        for word in technical_words:
            assert word not in msg, (
                f"LIMIT_MESSAGES['{key}'] contiene '{word}': {msg}"
            )


def test_adminlog_invalid_filter_has_placeholder():
    """El mensaje de filtro inválido tiene placeholder {filters}."""
    msg = LIMIT_MESSAGES["adminlog_invalid_filter"]
    assert "{filters}" in msg


def test_adminlog_invalid_filter_formats_correctly():
    """El placeholder {filters} se puede formatear con VALID_FILTERS."""
    msg = LIMIT_MESSAGES["adminlog_invalid_filter"]
    formatted = msg.format(filters=", ".join(VALID_FILTERS))
    assert "pin" in formatted
    assert "ban" in formatted
    assert "{filters}" not in formatted


# === VALID_FILTERS integración ===

def test_valid_filters_non_empty():
    """VALID_FILTERS no está vacío."""
    assert len(VALID_FILTERS) > 0


def test_valid_filters_all_lowercase():
    """Todos los filtros son lowercase."""
    for f in VALID_FILTERS:
        assert f == f.lower(), f"Filtro no lowercase: {f}"
