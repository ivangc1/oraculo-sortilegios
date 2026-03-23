"""Tests de truncamiento y respuesta vacía."""

from service.models import InterpretationResponse
from bot.messages import LIMIT_MESSAGES


def test_truncated_response():
    """Respuesta truncada tiene truncated=True y stop_reason max_tokens."""
    resp = InterpretationResponse(
        text="Texto parcial",
        tokens_input=100,
        tokens_output=400,
        truncated=True,
        error=None,
    )
    assert resp.truncated is True


def test_truncated_message_appended():
    """El mensaje de truncamiento se puede añadir al texto."""
    text = "Interpretación parcial"
    text += LIMIT_MESSAGES["truncated"]
    assert "oráculo ha dicho" in text.lower()


def test_empty_response_error():
    resp = InterpretationResponse(error="empty_response")
    assert resp.error == "empty_response"
    assert resp.text == ""


def test_empty_response_message():
    """El mensaje de respuesta vacía es in-character."""
    msg = LIMIT_MESSAGES["empty_response"]
    assert len(msg) > 0
    assert "cartas" in msg.lower() or "momento" in msg.lower()


def test_timeout_error():
    resp = InterpretationResponse(error="timeout")
    assert resp.error == "timeout"


def test_rate_limit_error():
    resp = InterpretationResponse(error="rate_limit")
    assert resp.error == "rate_limit"


def test_api_format_error():
    resp = InterpretationResponse(error="api_format_error")
    assert resp.error == "api_format_error"


def test_all_error_types_have_messages():
    """Todos los tipos de error tienen mensaje amigable."""
    error_to_key = {
        "timeout": "queue_timeout",
        "rate_limit": "rate_limit",
        "empty_response": "empty_response",
        "api_error": "api_error",
    }
    for error_type, msg_key in error_to_key.items():
        assert msg_key in LIMIT_MESSAGES, f"Falta mensaje para error: {error_type}"
        assert len(LIMIT_MESSAGES[msg_key]) > 0
