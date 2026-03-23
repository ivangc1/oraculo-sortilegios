"""Tests de numerología pitagórica: cálculos + normalización Unicode."""

from service.calculators.numerologia import (
    compatibility,
    expression_number,
    full_report,
    life_path,
    normalize_name,
    personal_month,
    personal_year,
    personality_number,
    soul_number,
)


# === Normalización Unicode ===

def test_normalize_plain():
    assert normalize_name("Juan") == "juan"


def test_normalize_accents():
    """á→a, é→e, etc."""
    assert normalize_name("María José") == "mariajose"


def test_normalize_ene():
    """ñ→n."""
    assert normalize_name("Muñoz") == "munoz"


def test_normalize_full_spanish():
    """Nombre español completo con todos los diacríticos."""
    assert normalize_name("José María Núñez García") == "josemarianunezgarcia"


def test_normalize_strips_non_alpha():
    """Quita espacios, guiones, apóstrofos, números."""
    assert normalize_name("Ana-María O'Brien 3rd") == "anamariaobrienrd"


def test_normalize_dieresis():
    """ü→u."""
    assert normalize_name("Müller") == "muller"


def test_normalize_cedilla():
    """ç→c."""
    assert normalize_name("François") == "francois"


def test_normalize_empty():
    assert normalize_name("") == ""


def test_normalize_only_symbols():
    assert normalize_name("123 !@#") == ""


# === Camino de vida ===

def test_life_path_basic():
    """15/06/1993 → 1+5=6, 0+6=6, 1+9+9+3=22→22(maestro), 6+6+22=34→7."""
    # Método: reducir por separado, sumar, reducir
    # Día: 15 → 1+5 = 6
    # Mes: 06 → 0+6 = 6
    # Año: 1993 → 1+9+9+3 = 22 (maestro, no reducir)
    # Total: 6+6+22 = 34 → 3+4 = 7
    assert life_path("15/06/1993") == 7


def test_life_path_master_11():
    """29/02/1980 → 2+9=11(maestro), 0+2=2, 1+9+8+0=18→9, 11+2+9=22(maestro)."""
    assert life_path("29/02/1980") == 22


def test_life_path_iso_format():
    """Formato AAAA-MM-DD también funciona."""
    assert life_path("1993-06-15") == life_path("15/06/1993")


def test_life_path_single_digit():
    """01/01/2000 → 1, 1, 2 → 4."""
    assert life_path("01/01/2000") == 4


def test_life_path_known_value():
    """25/12/1990 → 2+5=7, 1+2=3, 1+9+9+0=19→10→1, 7+3+1=11(maestro)."""
    assert life_path("25/12/1990") == 11


# === Números del nombre ===

def test_expression_number():
    """Verificar cálculo manual para 'Juan'.
    j=1, u=3, a=1, n=5 → total=10 → 1+0=1.
    """
    assert expression_number("Juan") == 1


def test_soul_number():
    """Solo vocales de 'Juan': u=3, a=1 → 4."""
    assert soul_number("Juan") == 4


def test_personality_number():
    """Solo consonantes de 'Juan': j=1, n=5 → 6."""
    assert personality_number("Juan") == 6


def test_expression_with_accents():
    """'María' normalizado = 'maria': m=4, a=1, r=9, i=9, a=1 → 24 → 6."""
    assert expression_number("María") == 6


def test_soul_with_ene():
    """Vocales de 'Muñoz' normalizado 'munoz': u=3, o=6 → 9."""
    assert soul_number("Muñoz") == 9


# === Año y mes personal ===

def test_personal_year():
    """15/06 + 2026 → día(1+5)=6, mes(0+6)=6, año(2+0+2+6)=10 → 6+6+10=22 (maestro)."""
    assert personal_year("15/06/1993", current_year=2026) == 22


def test_personal_month():
    """Año personal 22 + mes 3 = 25 → 7."""
    assert personal_month("15/06/1993", current_year=2026, current_month=3) == 7


# === Informe completo ===

def test_full_report_without_name():
    report = full_report("15/06/1993")
    assert "life_path" in report
    assert "personal_year" in report
    assert "expression" not in report  # Sin nombre


def test_full_report_with_name():
    report = full_report("15/06/1993", full_name="Juan García López")
    assert "life_path" in report
    assert "expression" in report
    assert "soul" in report
    assert "personality" in report


# === Compatibilidad ===

def test_compatibility():
    compat = compatibility("15/06/1993", "25/12/1990")
    assert compat["life_path_1"] == 7
    assert compat["life_path_2"] == 11


def test_compatibility_same():
    compat = compatibility("15/06/1993", "15/06/1993")
    assert compat["life_path_1"] == compat["life_path_2"]
