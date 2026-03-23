"""Tests básicos de handlers: start, help, admin checks, mensajes."""

from bot.handlers.help import _HELP_TEXT
from bot.handlers.start import _INTRO_GROUP, _INTRO_DM, _INTRO_GROUP_REGISTERED
from bot.messages import LIMIT_MESSAGES


# === /startoraculo texts ===

def test_start_group_text():
    assert "Pezuñento" in _INTRO_GROUP
    assert "/consulta" in _INTRO_GROUP


def test_start_dm_text():
    assert "Taberna" in _INTRO_DM
    assert "privadas" in _INTRO_DM.lower() or "grupo" in _INTRO_DM.lower()


def test_start_registered_has_alias():
    text = _INTRO_GROUP_REGISTERED.format(alias="TestUser")
    assert "TestUser" in text


# === /ayudaoraculo content ===

def test_help_has_all_commands():
    """Verifica que /ayudaoraculo incluye todos los comandos."""
    commands = [
        "/consulta", "/tarot", "/runa", "/iching", "/geomancia", "/numerologia",
        "/natal", "/vedica", "/oraculo", "/bibliomancia", "/admins",
        "/miperfil", "/actualizarperfil", "/borrarme", "/cancelaroraculo", "/ayudaoraculo",
    ]
    for cmd in commands:
        assert cmd in _HELP_TEXT, f"Falta {cmd} en /ayudaoraculo"


def test_help_has_limits():
    assert "5 tiradas" in _HELP_TEXT
    assert "3 consultas" in _HELP_TEXT


def test_help_has_bibliomancia_books():
    assert "Biblia" in _HELP_TEXT
    assert "Corán" in _HELP_TEXT
    assert "Gita" in _HELP_TEXT
    assert "Evangelio de Tomás" in _HELP_TEXT


# === Mensajes in-character ===

def test_limit_messages_all_keys():
    """Todos los mensajes esperados existen."""
    expected_keys = [
        "daily_limit", "cooldown", "empty_response", "queue_timeout",
        "request_in_progress", "truncated", "not_registered", "off_topic",
        "admin_only", "nominatim_down", "dm_only_group", "api_error",
        "rate_limit", "already_registered", "onboarding_timeout",
        "cancelled", "invalid_date", "invalid_time", "unknown_guardian",
    ]
    for key in expected_keys:
        assert key in LIMIT_MESSAGES, f"Falta mensaje: {key}"
        assert len(LIMIT_MESSAGES[key]) > 0


def test_limit_messages_no_technical():
    """Mensajes no contienen lenguaje técnico."""
    technical_words = ["error", "exception", "traceback", "stack", "null", "undefined",
                       "ValueError", "TypeError", "IndexError"]
    for key, msg in LIMIT_MESSAGES.items():
        for word in technical_words:
            assert word.lower() not in msg.lower(), (
                f"Mensaje '{key}' contiene término técnico '{word}': {msg}"
            )


def test_limit_messages_tono_baphomet():
    """Mensajes tienen tono directo, no servil."""
    servile_phrases = ["disculpa", "lo siento", "perdón", "lamentablemente"]
    for key, msg in LIMIT_MESSAGES.items():
        for phrase in servile_phrases:
            assert phrase.lower() not in msg.lower(), (
                f"Mensaje '{key}' tiene tono servil '{phrase}': {msg}"
            )
