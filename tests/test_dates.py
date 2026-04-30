"""Tests del helper común `service.calculators.dates.parse_birth_date`."""

import pytest

from service.calculators.dates import parse_birth_date


# === Formato DD/MM/AAAA (formato del onboarding) ===

def test_parse_dd_mm_yyyy():
    assert parse_birth_date("15/06/1993") == (15, 6, 1993)


def test_parse_dd_mm_yyyy_zero_padded():
    """Día/mes con cero a la izquierda."""
    assert parse_birth_date("01/01/2000") == (1, 1, 2000)
    assert parse_birth_date("09/03/1985") == (9, 3, 1985)


def test_parse_dd_mm_yyyy_master_day():
    """Día 11 (maestro numerológico) — preserva el entero correcto."""
    assert parse_birth_date("11/03/1985") == (11, 3, 1985)


def test_parse_dd_mm_yyyy_max_day():
    """Día 31 — el helper no valida rangos, solo parsea."""
    assert parse_birth_date("31/12/1999") == (31, 12, 1999)


# === Formato AAAA-MM-DD (ISO) ===

def test_parse_iso():
    assert parse_birth_date("1993-06-15") == (15, 6, 1993)


def test_parse_iso_zero_padded():
    assert parse_birth_date("2000-01-01") == (1, 1, 2000)


def test_iso_and_dmy_equivalentes():
    """Misma fecha en ambos formatos da el mismo resultado."""
    assert parse_birth_date("15/06/1993") == parse_birth_date("1993-06-15")


# === Errores de formato ===

def test_format_no_separator():
    with pytest.raises(ValueError, match="Formato de fecha no reconocido"):
        parse_birth_date("19930615")


def test_format_unknown_separator():
    with pytest.raises(ValueError, match="Formato de fecha no reconocido"):
        parse_birth_date("15.06.1993")


def test_empty_string():
    with pytest.raises(ValueError, match="Formato de fecha no reconocido"):
        parse_birth_date("")


# === Datos no numéricos en el path correcto del separador ===

def test_dmy_with_invalid_chars():
    """Si el separador es `/` pero los componentes no son enteros, ValueError de int()."""
    with pytest.raises(ValueError):
        parse_birth_date("ab/cd/efgh")


def test_iso_with_invalid_chars():
    with pytest.raises(ValueError):
        parse_birth_date("ab-cd-ef")
