"""Tests de callback data: todos ≤64 bytes, cada callback verificado."""

import pytest

from bot.keyboards import CALLBACKS, parse_callback


def test_all_callbacks_under_64_bytes():
    """CADA callback_data debe ser ≤64 bytes (límite Telegram)."""
    for key in CALLBACKS:
        byte_len = len(key.encode("utf-8"))
        assert byte_len <= 64, (
            f"Callback '{key}' excede 64 bytes: {byte_len} bytes"
        )


def test_feedback_callback_under_64_bytes():
    """Feedback con usage_id grande debe seguir bajo 64 bytes."""
    data = "fb:p:9999999999"
    assert len(data.encode("utf-8")) <= 64


# === Verificación individual de cada callback ===

@pytest.mark.parametrize("code,expected", [
    ("t:1", ("tarot", "1_carta")),
    ("t:3", ("tarot", "3_cartas")),
    ("t:cc", ("tarot", "cruz_celta")),
    ("r:1", ("runas", "odin")),
    ("r:3", ("runas", "nornas")),
    ("r:cr", ("runas", "cruz")),
    ("ic", ("iching", "hexagrama")),
    ("g:1", ("geomancia", "1_figura")),
    ("g:e", ("geomancia", "escudo")),
    ("n:i", ("numerologia", "informe")),
    ("n:c", ("numerologia", "compatibilidad")),
    ("nt", ("natal", "tropical")),
    ("nv", ("natal", "vedica")),
    ("or", ("oraculo", "libre")),
    ("q:y", ("question", "yes")),
    ("q:n", ("question", "no")),
    ("bl:bi", ("bibliomancia", "biblia")),
    ("bl:co", ("bibliomancia", "coran")),
    ("bl:gi", ("bibliomancia", "gita")),
    ("bl:ev", ("bibliomancia", "evangelio")),
    ("a:bk", ("admins", "back")),
])
def test_parse_each_callback(code, expected):
    """Cada callback se parsea al (mode, variant) correcto."""
    assert parse_callback(code) == expected


@pytest.mark.parametrize("idx", range(20))
def test_admin_callbacks(idx):
    """Los 20 callbacks de admin (a:0 a a:19) existen y son ≤64 bytes."""
    key = f"a:{idx}"
    assert key in CALLBACKS
    assert len(key.encode("utf-8")) <= 64
    mode, variant = CALLBACKS[key]
    assert mode == "admins"
    assert variant == str(idx)


def test_parse_feedback_callback():
    result = parse_callback("fb:p:123")
    assert result == ("feedback", "fb:p:123")

    result = parse_callback("fb:n:456")
    assert result == ("feedback", "fb:n:456")


def test_parse_unknown_callback():
    assert parse_callback("xyz") is None
    assert parse_callback("") is None
    assert parse_callback("unknown:data") is None


def test_total_callback_count():
    """Verifica que tenemos el número esperado de callbacks.
    21 base + 20 admins = 41 + los que se generan dinámicamente.
    """
    # Al menos los 21 hardcoded + 20 admin slots
    assert len(CALLBACKS) >= 41


def test_no_duplicate_callback_values():
    """Dos callbacks diferentes no mapean al mismo (mode, variant),
    excepto admin callbacks que son genéricos."""
    seen = {}
    for key, val in CALLBACKS.items():
        if val[0] == "admins" and val[1].isdigit():
            continue  # Admin indices are expected to be unique but generic
        if val in seen:
            assert False, f"Duplicado: {key} y {seen[val]} mapean a {val}"
        seen[val] = key
