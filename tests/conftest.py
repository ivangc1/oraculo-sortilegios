"""Fixtures compartidas para tests."""

import pytest

from service.models import InterpretationResponse


@pytest.fixture
def mock_anthropic_response():
    """Factory de respuestas mock de Anthropic."""
    def _make(
        text="Respuesta de prueba",
        tokens_input=100,
        tokens_output=50,
        cost_usd=0.001,
        cached=False,
        truncated=False,
        error=None,
    ):
        return InterpretationResponse(
            text=text,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_usd=cost_usd,
            cached=cached,
            truncated=truncated,
            error=error,
        )
    return _make
