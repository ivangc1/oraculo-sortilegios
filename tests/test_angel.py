"""Tests del módulo angel: integridad de datos y búsqueda."""

from bot.handlers import angel as angel_mod
from bot.handlers.angel import (
    _find_angel,
    _format_angel,
    _get_random_angel,
    _normalize,
    _load_data,
)


_load_data()
SHEM = angel_mod._SHEM
GOETIA = angel_mod._GOETIA


VALID_CHOIRS = {
    "Serafines", "Querubines", "Tronos", "Dominaciones",
    "Virtudes", "Potestades", "Principados", "Arcángeles", "Ángeles",
}


# === Integridad de datos ===

def test_shem_count():
    """Exactamente 72 ángeles."""
    assert len(SHEM) == 72


def test_shem_numbers_sequential():
    """Numeración 1-72 sin huecos ni duplicados."""
    nums = [a["number"] for a in SHEM]
    assert nums == list(range(1, 73))


def test_shem_required_fields():
    """Todos los campos obligatorios presentes."""
    required = [
        "number", "name", "name_hebrew", "name_variants",
        "choir", "attribute", "psalm", "day_regency",
        "hour_regency", "virtue", "description", "corresponding_demon",
    ]
    for a in SHEM:
        for field in required:
            assert field in a, f"Ángel {a.get('number')} falta campo '{field}'"
            assert a[field] is not None, f"Ángel {a['number']} tiene '{field}' en None"


def test_shem_choirs_valid():
    """Todos los coros son válidos."""
    for a in SHEM:
        assert a["choir"] in VALID_CHOIRS, (
            f"Ángel {a['number']} ({a['name']}) tiene coro inválido: {a['choir']}"
        )


def test_shem_name_variants_include_main_name():
    """El nombre principal está en las variantes."""
    for a in SHEM:
        assert a["name"] in a["name_variants"], (
            f"Ángel {a['number']} ({a['name']}) no tiene su propio nombre en variants"
        )


def test_shem_corresponding_demon_valid_range():
    """Cada ángel apunta a un demonio válido (1-72)."""
    for a in SHEM:
        demon_num = a["corresponding_demon"]
        assert 1 <= demon_num <= 72, (
            f"Ángel {a['number']} apunta a demonio inválido: {demon_num}"
        )


def test_shem_goetia_bidirectional():
    """Pareo bidireccional: si ángel N → demonio M, entonces demonio M → ángel N."""
    for a in SHEM:
        demon_num = a["corresponding_demon"]
        demon = GOETIA[demon_num - 1]
        assert demon["corresponding_angel"] == a["number"], (
            f"Ángel {a['number']} → demonio {demon_num}, "
            f"pero demonio {demon_num} → ángel {demon['corresponding_angel']}"
        )


# === Normalización ===

def test_normalize_angel_basic():
    assert _normalize("Vehuiah") == "vehuiah"
    assert _normalize("  VEHUIAH  ") == "vehuiah"


# === Búsqueda ===

def test_find_angel_by_name():
    """Búsqueda por nombre tolerante a case."""
    assert _find_angel("Vehuiah")["number"] == 1
    assert _find_angel("VEHUIAH")["number"] == 1
    assert _find_angel("vehuiah")["number"] == 1


def test_find_angel_by_number():
    """Búsqueda por número."""
    assert _find_angel("1")["name"] == "Vehuiah"
    assert _find_angel("72")["number"] == 72
    assert _find_angel("2")["name"] == "Jeliel"


def test_find_angel_not_found():
    """Ángel inexistente devuelve None."""
    assert _find_angel("inexistente_xyz") is None
    assert _find_angel("73") is None
    assert _find_angel("0") is None
    assert _find_angel("") is None


# === Aleatorio + anti-repetición ===

def test_random_returns_valid_angel():
    angel = _get_random_angel(user_id=99998)
    assert angel is not None
    assert "number" in angel
    assert 1 <= angel["number"] <= 72


def test_anti_repetition_angel_same_user():
    """Aleatorio no repite el último para el mismo usuario."""
    user_id = 88887
    angel_mod._LAST_ANGEL.pop(user_id, None)

    first = _get_random_angel(user_id)
    second = _get_random_angel(user_id)
    # El segundo debe ser distinto al primero
    assert second["number"] != first["number"]


# === Formato ===

def test_format_angel_contains_name():
    angel = SHEM[0]  # Vehuiah
    text = _format_angel(angel)
    assert "Vehuiah" in text
    assert "Serafines" in text


def test_format_angel_contains_demon_reference():
    """La ficha incluye referencia al demonio correspondiente."""
    angel = SHEM[0]
    text = _format_angel(angel)
    assert "Bael" in text  # Demonio 1
    assert "/demonio 1" in text


def test_format_angel_has_markers():
    """Usa marcadores [[T]] y [[C]] de format_response."""
    angel = SHEM[0]
    text = _format_angel(angel)
    assert "[[T]]" in text
    assert "[[C]]" in text
