"""Tests de signo solar: fechas límite, aproximación vs efemérides."""

from service.calculators.sun_sign import (
    _sun_sign_approximate,
    get_sun_sign,
    ZODIAC_SIGNS,
)


# === Tabla aproximada (siempre disponible, incluso sin kerykeion) ===

def test_approximate_aries():
    assert _sun_sign_approximate(3, 25) == "Aries"
    assert _sun_sign_approximate(4, 15) == "Aries"


def test_approximate_tauro():
    assert _sun_sign_approximate(4, 22) == "Tauro"
    assert _sun_sign_approximate(5, 15) == "Tauro"


def test_approximate_geminis():
    assert _sun_sign_approximate(6, 1) == "Géminis"


def test_approximate_cancer():
    assert _sun_sign_approximate(7, 1) == "Cáncer"


def test_approximate_leo():
    assert _sun_sign_approximate(8, 1) == "Leo"


def test_approximate_virgo():
    assert _sun_sign_approximate(9, 1) == "Virgo"


def test_approximate_libra():
    assert _sun_sign_approximate(10, 1) == "Libra"


def test_approximate_escorpio():
    assert _sun_sign_approximate(11, 1) == "Escorpio"


def test_approximate_sagitario():
    assert _sun_sign_approximate(12, 1) == "Sagitario"


def test_approximate_capricornio():
    assert _sun_sign_approximate(1, 5) == "Capricornio"
    assert _sun_sign_approximate(12, 25) == "Capricornio"


def test_approximate_acuario():
    assert _sun_sign_approximate(1, 25) == "Acuario"
    assert _sun_sign_approximate(2, 10) == "Acuario"


def test_approximate_piscis():
    assert _sun_sign_approximate(2, 22) == "Piscis"
    assert _sun_sign_approximate(3, 15) == "Piscis"


# === Fechas límite: días de transición entre signos ===

def test_boundary_aries_tauro():
    """Alrededor del 20 de abril."""
    # 19 abril = Aries (claro)
    assert _sun_sign_approximate(4, 19) == "Aries"
    # 21 abril = Tauro (claro)
    assert _sun_sign_approximate(4, 21) == "Tauro"


def test_boundary_geminis_cancer():
    """Alrededor del 21 de junio."""
    assert _sun_sign_approximate(6, 20) == "Géminis"
    assert _sun_sign_approximate(6, 22) == "Cáncer"


def test_boundary_leo_virgo():
    """Alrededor del 23 de agosto."""
    assert _sun_sign_approximate(8, 22) == "Leo"
    assert _sun_sign_approximate(8, 24) == "Virgo"


def test_boundary_libra_escorpio():
    """Alrededor del 23 de octubre."""
    assert _sun_sign_approximate(10, 22) == "Libra"
    assert _sun_sign_approximate(10, 24) == "Escorpio"


# === get_sun_sign (usa efemérides si disponible, sino aproximado) ===

def test_get_sun_sign_returns_valid():
    """Siempre devuelve un signo válido."""
    sign = get_sun_sign(1993, 6, 15)
    assert sign in ZODIAC_SIGNS


def test_get_sun_sign_gemini_clear():
    """15 junio = Géminis (claro, lejos de bordes)."""
    sign = get_sun_sign(1993, 6, 15)
    assert sign == "Géminis"


def test_get_sun_sign_capricornio_clear():
    """25 diciembre = Capricornio (claro)."""
    sign = get_sun_sign(1990, 12, 25)
    assert sign == "Capricornio"


def test_get_sun_sign_all_months():
    """Un día claro de cada mes devuelve un signo válido."""
    for month in range(1, 13):
        sign = get_sun_sign(2000, month, 10)
        assert sign in ZODIAC_SIGNS, f"Mes {month} devolvió signo inválido: {sign}"


def test_zodiac_has_12_signs():
    assert len(ZODIAC_SIGNS) == 12
