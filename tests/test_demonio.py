"""Tests del módulo demonio: integridad de datos y búsqueda."""

from pathlib import Path

import pytest

from bot.handlers import demonio as demonio_mod
from bot.handlers.demonio import (
    _find_demon,
    _format_demon,
    _get_random_demon,
    _normalize,
    _load_data,
    _parse_args,
)
from service.prompts.demonio import get_sub_prompt as demon_sub_prompt


# Cargar datos antes de los tests
_load_data()
GOETIA = demonio_mod._GOETIA
SHEM = demonio_mod._SHEM


VALID_RANKS = {
    "Rey", "Duque", "Príncipe", "Marqués",
    "Conde", "Presidente", "Caballero",
}

VALID_CHOIRS = {
    "Serafines", "Querubines", "Tronos", "Dominaciones",
    "Virtudes", "Potestades", "Principados", "Arcángeles", "Ángeles",
}


# === Integridad de datos ===

def test_goetia_count():
    """Exactamente 72 demonios."""
    assert len(GOETIA) == 72


def test_goetia_numbers_sequential():
    """Numeración 1-72 sin huecos ni duplicados."""
    nums = [d["number"] for d in GOETIA]
    assert nums == list(range(1, 73))


def test_goetia_required_fields():
    """Todos los campos obligatorios presentes."""
    required = [
        "number", "name", "name_variants", "rank", "legions",
        "powers", "appearance", "description", "corresponding_angel",
    ]
    for d in GOETIA:
        for field in required:
            assert field in d, f"Demonio {d.get('number')} falta campo '{field}'"
            assert d[field] is not None, f"Demonio {d['number']} tiene '{field}' en None"


def test_goetia_ranks_valid():
    """Todos los rangos son válidos."""
    for d in GOETIA:
        assert d["rank"] in VALID_RANKS, (
            f"Demonio {d['number']} ({d['name']}) tiene rango inválido: {d['rank']}"
        )


def test_goetia_legions_positive():
    """Todas las legiones son enteros positivos."""
    for d in GOETIA:
        assert isinstance(d["legions"], int)
        assert d["legions"] > 0, f"Demonio {d['number']} tiene {d['legions']} legiones"


def test_goetia_name_variants_include_main_name():
    """El nombre principal está en las variantes."""
    for d in GOETIA:
        assert d["name"] in d["name_variants"], (
            f"Demonio {d['number']} ({d['name']}) no tiene su propio nombre en variants"
        )


def test_goetia_corresponding_angel_valid_range():
    """Cada demonio apunta a un ángel válido (1-72)."""
    for d in GOETIA:
        angel_num = d["corresponding_angel"]
        assert 1 <= angel_num <= 72, (
            f"Demonio {d['number']} apunta a ángel inválido: {angel_num}"
        )


def test_goetia_shem_bidirectional():
    """Pareo bidireccional: si demonio N → ángel M, entonces ángel M → demonio N."""
    for d in GOETIA:
        angel_num = d["corresponding_angel"]
        angel = SHEM[angel_num - 1]
        assert angel["corresponding_demon"] == d["number"], (
            f"Demonio {d['number']} → ángel {angel_num}, "
            f"pero ángel {angel_num} → demonio {angel['corresponding_demon']}"
        )


def test_goetia_names_unique():
    """Ningún demonio tiene el mismo nombre que otro."""
    names = [d["name"] for d in GOETIA]
    assert len(names) == len(set(names)), "Hay nombres de demonio duplicados"


# === Normalización ===

def test_normalize_removes_accents():
    assert _normalize("Baél") == "bael"
    assert _normalize("Príncipe") == "principe"


def test_normalize_lowercase():
    assert _normalize("BAEL") == "bael"
    assert _normalize("Bael") == "bael"


def test_normalize_strip():
    assert _normalize("  bael  ") == "bael"


# === Búsqueda ===

def test_find_demon_by_name():
    """Búsqueda por nombre tolerante a case."""
    assert _find_demon("Bael")["number"] == 1
    assert _find_demon("BAEL")["number"] == 1
    assert _find_demon("bael")["number"] == 1


def test_find_demon_by_name_with_accents():
    """Búsqueda tolerante a acentos."""
    # "Baél" (acento errado) debe matchear "Bael"
    assert _find_demon("Baél")["number"] == 1


def test_find_demon_by_variant():
    """Búsqueda por variante de nombre."""
    # Bael tiene variante "Baal"
    result = _find_demon("Baal")
    assert result is not None
    assert result["number"] == 1


def test_find_demon_by_number():
    """Búsqueda por número."""
    assert _find_demon("1")["name"] == "Bael"
    assert _find_demon("72")["number"] == 72
    assert _find_demon("32")["name"] == "Asmoday"


def test_find_demon_not_found():
    """Demonio inexistente devuelve None."""
    assert _find_demon("inexistente_xyz") is None
    assert _find_demon("73") is None  # Fuera de rango
    assert _find_demon("0") is None
    assert _find_demon("") is None


# === Aleatorio + anti-repetición ===

def test_random_returns_valid_demon():
    demon = _get_random_demon(user_id=99999)
    assert demon is not None
    assert "number" in demon
    assert 1 <= demon["number"] <= 72


def test_anti_repetition_same_user():
    """Aleatorio no repite el último para el mismo usuario."""
    # Hacer varias tiradas y verificar que hubo variación
    user_id = 88888
    # Reset
    demonio_mod._LAST_DEMON.pop(user_id, None)

    first = _get_random_demon(user_id)
    # La siguiente tirada no debe ser la misma
    for _ in range(10):
        next_demon = _get_random_demon(user_id)
        assert next_demon["number"] != first["number"] or len(set(
            [_get_random_demon(user_id)["number"] for _ in range(5)]
        )) > 1


# === Formato ===

def test_format_demon_contains_name():
    demon = GOETIA[0]  # Bael
    text = _format_demon(demon)
    assert "Bael" in text
    assert "Rey" in text


def test_format_demon_contains_angel_reference():
    """La ficha incluye referencia al ángel correspondiente."""
    demon = GOETIA[0]
    text = _format_demon(demon)
    assert "Vehuiah" in text  # Ángel 1
    assert "/angel 1" in text


def test_format_demon_has_markers():
    """Usa marcadores [[T]] y [[C]] de format_response."""
    demon = GOETIA[0]
    text = _format_demon(demon)
    assert "[[T]]" in text
    assert "[[C]]" in text


# === Parseo de args ===

def test_parse_args_empty():
    """Sin args → random, sin pregunta."""
    demon, q = _parse_args([], user_id=10001)
    assert demon is not None
    assert q is None


def test_parse_args_aleatorio():
    """['aleatorio'] → random, sin pregunta."""
    demon, q = _parse_args(["aleatorio"], user_id=10002)
    assert demon is not None
    assert q is None


def test_parse_args_aleatorio_with_question():
    """['aleatorio', '¿pregunta?'] → random + pregunta."""
    demon, q = _parse_args(["aleatorio", "¿cómo", "va?"], user_id=10003)
    assert demon is not None
    assert q == "¿cómo va?"


def test_parse_args_by_name():
    """['bael'] → Bael, sin pregunta."""
    demon, q = _parse_args(["bael"], user_id=10004)
    assert demon["number"] == 1
    assert q is None


def test_parse_args_by_name_with_question():
    """['bael', '¿pregunta?'] → Bael + pregunta."""
    demon, q = _parse_args(["bael", "¿me", "conviene?"], user_id=10005)
    assert demon["number"] == 1
    assert q == "¿me conviene?"


def test_parse_args_by_number():
    """['1'] → Bael por número."""
    demon, q = _parse_args(["1"], user_id=10006)
    assert demon["number"] == 1
    assert q is None


def test_parse_args_by_number_with_question():
    """['1', '¿pregunta?'] → Bael por número + pregunta."""
    demon, q = _parse_args(["32", "¿me", "ayudará?"], user_id=10007)
    assert demon["number"] == 32
    assert q == "¿me ayudará?"


def test_parse_args_only_question():
    """['palabra', 'que', 'no', 'es', 'demonio'] → random + toda la cadena como pregunta."""
    demon, q = _parse_args(["¿qué", "me", "depara", "hoy?"], user_id=10008)
    assert demon is not None
    assert q == "¿qué me depara hoy?"


# === Sub-prompt ===

def test_sub_prompt_without_demon():
    """Sub-prompt base sin demonio."""
    prompt = demon_sub_prompt(None)
    assert "Goetia" in prompt
    assert "DEMONIO CONSULTADO" not in prompt


def test_sub_prompt_with_demon_includes_name():
    """Sub-prompt con demonio incluye nombre y atributos."""
    demon = GOETIA[0]  # Bael
    prompt = demon_sub_prompt(demon)
    assert "Bael" in prompt
    assert "DEMONIO CONSULTADO" in prompt
    assert "Rey" in prompt
    assert "66" in prompt  # Legiones


def test_sub_prompt_with_demon_has_base_instructions():
    """Sub-prompt con demonio incluye las instrucciones base."""
    demon = GOETIA[0]
    prompt = demon_sub_prompt(demon)
    assert "Ars Goetia" in prompt or "Goetia" in prompt
    assert "NUNCA" in prompt  # Instrucciones
    assert "CÓMO RESPONDER" in prompt
