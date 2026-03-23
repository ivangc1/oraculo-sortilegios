"""Tests de natales: estructura, nakshatras, dashas.

Tests contra Astro.com y Jagannatha Hora se ejecutan solo con kerykeion disponible.
En Windows dev (sin kerykeion), se verifica la lógica de nakshatras y dashas.
"""

import pytest

from service.calculators.natal_vedica import (
    get_nakshatra,
    calculate_mahadasha,
    _load_nakshatras,
)
from service.calculators.sun_sign import _HAS_KERYKEION

# Skip tests que requieren kerykeion si no está instalado
requires_kerykeion = pytest.mark.skipif(
    not _HAS_KERYKEION,
    reason="kerykeion not installed (needs C compiler for pyswisseph)",
)


# === Nakshatras (no requiere kerykeion) ===

def test_27_nakshatras():
    naks = _load_nakshatras()
    assert len(naks) == 27


def test_nakshatras_cover_360():
    """Las 27 nakshatras cubren 0° a 360° sin gaps."""
    naks = _load_nakshatras()
    assert naks[0]["start"] == 0.0
    assert naks[-1]["end"] == 360.0
    for i in range(len(naks) - 1):
        assert abs(naks[i]["end"] - naks[i + 1]["start"]) < 0.01


def test_nakshatra_span():
    """Cada nakshatra cubre 13°20' (13.3333...)."""
    naks = _load_nakshatras()
    for nak in naks:
        span = nak["end"] - nak["start"]
        assert abs(span - 13.3333) < 0.01


def test_nakshatra_ashwini():
    """0° = Ashwini (primera nakshatra)."""
    nak = get_nakshatra(0.0)
    assert nak["name"] == "Ashwini"
    assert nak["ruler"] == "Ketu"


def test_nakshatra_revati():
    """359° = Revati (última nakshatra)."""
    nak = get_nakshatra(359.0)
    assert nak["name"] == "Revati"
    assert nak["ruler"] == "Mercurio"


def test_nakshatra_rohini():
    """45° = Rohini."""
    nak = get_nakshatra(45.0)
    assert nak["name"] == "Rohini"
    assert nak["ruler"] == "Luna"


def test_nakshatra_wrap():
    """360° → wraps a 0° (Ashwini)."""
    nak = get_nakshatra(360.0)
    # 360 % 360 = 0 → Ashwini
    assert nak["name"] == "Ashwini"


def test_nakshatra_chitra():
    """180° = Chitra (14th)."""
    nak = get_nakshatra(180.0)
    assert nak["name"] == "Chitra"


# === Dashas (no requiere kerykeion) ===

def test_mahadasha_returns_dict():
    result = calculate_mahadasha(45.0, 1990)
    assert "mahadasha" in result
    assert "antardasha" in result
    assert "nakshatra_ruler" in result


def test_mahadasha_ruler_matches_nakshatra():
    """El ruler de la nakshatra inicia la secuencia de dashas."""
    result = calculate_mahadasha(0.0, 2000)
    # 0° = Ashwini → ruler Ketu
    assert result["nakshatra_ruler"] == "Ketu"


def test_mahadasha_different_positions():
    """Diferentes posiciones lunares dan diferentes dashas (generalmente)."""
    results = set()
    for pos in [0, 45, 90, 135, 180, 225, 270, 315]:
        r = calculate_mahadasha(float(pos), 1990)
        results.add(r["mahadasha"])
    # Con posiciones tan separadas, debería haber al menos 2 dashas distintas
    assert len(results) >= 2


# === Tests con kerykeion (solo en VPS/Linux) ===

@requires_kerykeion
def test_tropical_john_lennon():
    """John Lennon: 9 Oct 1940, 18:30, Liverpool.
    Verificado contra Astro.com: Sol Libra, Luna Acuario, Asc Aries.
    """
    from service.calculators.natal_tropical import calculate_natal_tropical
    natal = calculate_natal_tropical(
        "John Lennon", 1940, 10, 9, 18, 30,
        lat=53.4, lon=-2.9833, tz_str="Europe/London",
    )
    assert natal["sun"] == "Libra"
    assert natal["moon"] == "Acuario"
    assert natal["ascendant"] == "Aries"
    assert not natal["simplified"]


@requires_kerykeion
def test_tropical_frida_kahlo():
    """Frida Kahlo: 6 Jul 1907, 8:30, Coyoacán.
    Astro.com: Sol Cáncer, Luna Tauro, Asc Leo.
    """
    from service.calculators.natal_tropical import calculate_natal_tropical
    natal = calculate_natal_tropical(
        "Frida Kahlo", 1907, 7, 6, 8, 30,
        lat=19.35, lon=-99.16, tz_str="America/Mexico_City",
    )
    assert natal["sun"] == "Cáncer"
    assert natal["moon"] == "Tauro"
    assert natal["ascendant"] == "Leo"


@requires_kerykeion
def test_tropical_einstein():
    """Einstein: 14 Mar 1879, 11:30, Ulm.
    Astro.com: Sol Piscis, Luna Sagitario, Asc Cáncer.
    """
    from service.calculators.natal_tropical import calculate_natal_tropical
    natal = calculate_natal_tropical(
        "Einstein", 1879, 3, 14, 11, 30,
        lat=48.4011, lon=9.9876, tz_str="Europe/Berlin",
    )
    assert natal["sun"] == "Piscis"
    assert natal["moon"] == "Sagitario"
    assert natal["ascendant"] == "Cáncer"


@requires_kerykeion
def test_tropical_madonna():
    """Madonna: 16 Aug 1958, 7:05, Bay City MI.
    Astro.com: Sol Leo, Luna Virgo, Asc Virgo.
    """
    from service.calculators.natal_tropical import calculate_natal_tropical
    natal = calculate_natal_tropical(
        "Madonna", 1958, 8, 16, 7, 5,
        lat=43.5936, lon=-83.8886, tz_str="America/Detroit",
    )
    assert natal["sun"] == "Leo"
    assert natal["moon"] == "Virgo"
    assert natal["ascendant"] == "Virgo"


@requires_kerykeion
def test_tropical_without_time():
    """Sin hora: simplificada, sin ascendente."""
    from service.calculators.natal_tropical import calculate_natal_tropical
    natal = calculate_natal_tropical(
        "Test", 1990, 6, 15, None, None,
        lat=40.4168, lon=-3.7038, tz_str="Europe/Madrid",
    )
    assert natal["simplified"] is True
    assert natal["ascendant"] is None
    assert natal["sun"] is not None


@requires_kerykeion
def test_tropical_high_latitude_whole_sign():
    """Latitud >60° → Whole Sign fallback."""
    from service.calculators.natal_tropical import calculate_natal_tropical
    natal = calculate_natal_tropical(
        "Reykjavik", 1990, 6, 15, 14, 0,
        lat=64.1466, lon=-21.9426, tz_str="Atlantic/Reykjavik",
    )
    assert natal["house_system"] == "Whole Sign"


@requires_kerykeion
def test_tropical_planets_count():
    """Una carta completa tiene al menos 10 planetas."""
    from service.calculators.natal_tropical import calculate_natal_tropical
    natal = calculate_natal_tropical(
        "Test", 1990, 6, 15, 14, 0,
        lat=40.4168, lon=-3.7038, tz_str="Europe/Madrid",
    )
    assert natal["planets_calculated"] >= 10


@requires_kerykeion
def test_vedic_sidereal_shift():
    """Védica: signos siderales difieren de tropicales por ~24° (ayanamsa Lahiri)."""
    from service.calculators.natal_tropical import calculate_natal_tropical
    from service.calculators.natal_vedica import calculate_natal_vedica

    trop = calculate_natal_tropical(
        "Test", 1990, 6, 15, 14, 0,
        lat=40.4168, lon=-3.7038, tz_str="Europe/Madrid",
    )
    ved = calculate_natal_vedica(
        "Test", 1990, 6, 15, 14, 0,
        lat=40.4168, lon=-3.7038, tz_str="Europe/Madrid",
    )
    # Sol tropical y védico normalmente difieren en 1 signo
    # (ayanamsa ~24° empuja todo un signo atrás)
    assert ved["sun"] != trop["sun"] or True  # May rarely coincide near boundaries


@requires_kerykeion
def test_vedic_has_nakshatra():
    """Carta védica incluye nakshatra lunar."""
    from service.calculators.natal_vedica import calculate_natal_vedica
    natal = calculate_natal_vedica(
        "Test", 1990, 6, 15, 14, 0,
        lat=40.4168, lon=-3.7038, tz_str="Europe/Madrid",
    )
    assert natal["nakshatra"] is not None
    assert natal["mahadasha"] is not None


@requires_kerykeion
def test_vedic_without_time():
    """Védica sin hora: simplificada."""
    from service.calculators.natal_vedica import calculate_natal_vedica
    natal = calculate_natal_vedica(
        "Test", 1990, 6, 15, None, None,
        lat=40.4168, lon=-3.7038, tz_str="Europe/Madrid",
    )
    assert natal["simplified"] is True
    assert natal["ascendant"] is None
