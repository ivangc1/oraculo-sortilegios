"""Tests del system prompt: estatico, sin f-strings, >=1024 tokens."""

from service.prompts.master import get_master_prompt


def test_system_prompt_is_static():
    """El prompt debe ser identico en cada llamada para que el cache funcione."""
    prompt1 = get_master_prompt()
    prompt2 = get_master_prompt()
    assert prompt1 == prompt2


def test_system_prompt_no_fstrings():
    """No debe contener f-strings residuales ni variables."""
    prompt = get_master_prompt()
    for i, char in enumerate(prompt):
        if char == "{":
            if i + 1 < len(prompt) and prompt[i + 1] == "{":
                continue
            assert False, f"Posible f-string residual en posicion {i}: ...{prompt[max(0,i-10):i+10]}..."


def test_system_prompt_min_tokens_estimated():
    """Estimacion conservadora: ~4 chars = 1 token. Debe ser >=1024.

    El conteo exacto requiere la API de Anthropic (count_tokens) y por tanto
    una API key + red — no aporta sobre la estimación local que tiene margen
    holgado (el prompt actual ronda los 3600 tokens estimados, ~3.5x el mínimo).
    """
    prompt = get_master_prompt()
    estimated_tokens = len(prompt) / 4
    assert estimated_tokens >= 1024, (
        f"System prompt demasiado corto: ~{estimated_tokens:.0f} tokens estimados "
        f"(necesita >=1024). Longitud: {len(prompt)} chars"
    )


def test_system_prompt_contains_key_instructions():
    """Verifica que contiene instrucciones clave."""
    prompt = get_master_prompt()
    assert "[[T]]" in prompt, "Falta instruccion de marcador [[T]]"
    assert "[[C]]" in prompt, "Falta instruccion de marcador [[C]]"
    assert "Pezuñento" in prompt, "Falta nombre del personaje"
    assert "Hierofante" in prompt, "Falta nomenclatura Hierofante"
    assert "Bastos" in prompt, "Falta nomenclatura Bastos"
    assert "Wilhelm" in prompt, "Falta marco I Ching Wilhelm"
