"""Tests del system prompt: estático, sin f-strings, ≥1024 tokens."""

from service.prompts.master import get_master_prompt


def test_system_prompt_is_static():
    """El prompt debe ser idéntico en cada llamada para que el caché funcione."""
    prompt1 = get_master_prompt()
    prompt2 = get_master_prompt()
    assert prompt1 == prompt2


def test_system_prompt_no_fstrings():
    """No debe contener f-strings residuales ni variables."""
    prompt = get_master_prompt()
    # Buscar llaves sueltas que indiquen f-string residual
    # {{ es escape literal y es OK
    for i, char in enumerate(prompt):
        if char == "{":
            # Verificar que no es {{ (escape)
            if i + 1 < len(prompt) and prompt[i + 1] == "{":
                continue
            # Verificar que no es cierre }}
            assert False, f"Posible f-string residual en posición {i}: ...{prompt[max(0,i-10):i+10]}..."


def test_system_prompt_min_tokens():
    """Debe tener ≥1024 tokens para que el caching se active."""
    prompt = get_master_prompt()
    # Estimación conservadora: ~4 chars = 1 token
    estimated_tokens = len(prompt) / 4
    assert estimated_tokens >= 1024, (
        f"System prompt demasiado corto: ~{estimated_tokens:.0f} tokens estimados "
        f"(necesita ≥1024). Longitud: {len(prompt)} chars"
    )


def test_system_prompt_contains_key_instructions():
    """Verifica que contiene instrucciones clave."""
    prompt = get_master_prompt()
    assert "[[T]]" in prompt, "Falta instrucción de marcador [[T]]"
    assert "[[C]]" in prompt, "Falta instrucción de marcador [[C]]"
    assert "Pezuñento" in prompt, "Falta nombre del personaje"
    assert "Hierofante" in prompt, "Falta nomenclatura Hierofante"
    assert "Bastos" in prompt, "Falta nomenclatura Bastos"
    assert "Wilhelm" in prompt, "Falta marco I Ching Wilhelm"
