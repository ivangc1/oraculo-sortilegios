"""Carta natal védica (Jyotish) con kerykeion v5 sidereal + pyswisseph para nakshatras.

kerykeion v5 soporta sidereal/Lahiri nativamente.
Para nakshatras y dashas: cálculo propio con la posición lunar sidereal.

Import condicional — pyswisseph no compila en Windows dev.
"""

import json
from pathlib import Path

from loguru import logger

from service.calculators.sun_sign import _translate_sign

_HAS_KERYKEION = False
try:
    from kerykeion import AstrologicalSubjectFactory
    _HAS_KERYKEION = True
except ImportError:
    logger.info("kerykeion not available — natal vedica disabled")

# Cargar nakshatras
_NAKSHATRAS: list[dict] | None = None


def _load_nakshatras() -> list[dict]:
    global _NAKSHATRAS
    if _NAKSHATRAS is not None:
        return _NAKSHATRAS
    path = Path(__file__).parent.parent.parent / "data" / "nakshatras.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            _NAKSHATRAS = json.load(f)["nakshatras"]
    else:
        # Generar tabla básica de 27 nakshatras (13°20' cada una)
        _NAKSHATRAS = _generate_nakshatra_table()
    return _NAKSHATRAS


def _generate_nakshatra_table() -> list[dict]:
    """Tabla de 27 nakshatras con datos básicos."""
    names = [
        ("Ashwini", "Ketu"), ("Bharani", "Venus"), ("Krittika", "Sol"),
        ("Rohini", "Luna"), ("Mrigashira", "Marte"), ("Ardra", "Rahu"),
        ("Punarvasu", "Júpiter"), ("Pushya", "Saturno"), ("Ashlesha", "Mercurio"),
        ("Magha", "Ketu"), ("Purva Phalguni", "Venus"), ("Uttara Phalguni", "Sol"),
        ("Hasta", "Luna"), ("Chitra", "Marte"), ("Swati", "Rahu"),
        ("Vishakha", "Júpiter"), ("Anuradha", "Saturno"), ("Jyeshtha", "Mercurio"),
        ("Mula", "Ketu"), ("Purva Ashadha", "Venus"), ("Uttara Ashadha", "Sol"),
        ("Shravana", "Luna"), ("Dhanishta", "Marte"), ("Shatabhisha", "Rahu"),
        ("Purva Bhadrapada", "Júpiter"), ("Uttara Bhadrapada", "Saturno"), ("Revati", "Mercurio"),
    ]
    span = 360.0 / 27  # 13°20'
    table = []
    for i, (name, ruler) in enumerate(names):
        table.append({
            "number": i + 1,
            "name": name,
            "ruler": ruler,
            "start": round(i * span, 4),
            "end": round((i + 1) * span, 4),
        })
    return table


# Dasha order and years (Vimshottari)
_DASHA_SEQUENCE = [
    ("Ketu", 7), ("Venus", 20), ("Sol", 6), ("Luna", 10),
    ("Marte", 7), ("Rahu", 18), ("Júpiter", 16), ("Saturno", 19),
    ("Mercurio", 17),
]
_TOTAL_DASHA_YEARS = sum(y for _, y in _DASHA_SEQUENCE)  # 120


def get_nakshatra(moon_sidereal_pos: float) -> dict:
    """Devuelve nakshatra para una posición lunar sidereal (0-360)."""
    nakshatras = _load_nakshatras()
    pos = moon_sidereal_pos % 360
    for nak in nakshatras:
        if nak["start"] <= pos < nak["end"]:
            return nak
    return nakshatras[-1]  # Revati (ultimo)


def calculate_mahadasha(moon_sidereal_pos: float, birth_year: int) -> dict:
    """Calcula Mahadasha y Antardasha actuales (Vimshottari)."""
    from datetime import datetime, timezone

    nakshatra = get_nakshatra(moon_sidereal_pos)
    ruler = nakshatra["ruler"]

    # Encontrar posición del ruler en la secuencia
    ruler_idx = next(
        (i for i, (name, _) in enumerate(_DASHA_SEQUENCE) if name == ruler), 0
    )

    # Posición dentro del nakshatra (0-1)
    nak_span = nakshatra["end"] - nakshatra["start"]
    pos_in_nak = (moon_sidereal_pos % 360 - nakshatra["start"]) / nak_span

    # Balance of first dasha at birth
    first_dasha_name, first_dasha_years = _DASHA_SEQUENCE[ruler_idx]
    balance_years = first_dasha_years * (1 - pos_in_nak)

    # Calcular qué dasha está activa ahora
    current_year = datetime.now(timezone.utc).year
    elapsed = current_year - birth_year

    # Avanzar por dashas
    remaining = elapsed - balance_years
    current_idx = ruler_idx

    if remaining < 0:
        # Aún en la primera dasha
        return {
            "mahadasha": first_dasha_name,
            "antardasha": first_dasha_name,  # Simplificado
            "nakshatra_ruler": ruler,
        }

    current_idx = (ruler_idx + 1) % len(_DASHA_SEQUENCE)
    while remaining > 0:
        _, years = _DASHA_SEQUENCE[current_idx]
        if remaining <= years:
            break
        remaining -= years
        current_idx = (current_idx + 1) % len(_DASHA_SEQUENCE)

    mahadasha_name = _DASHA_SEQUENCE[current_idx][0]

    # Antardasha simplificado (subdivisión proporcional)
    maha_years = _DASHA_SEQUENCE[current_idx][1]
    fraction = remaining / maha_years if maha_years > 0 else 0
    antar_idx = int(fraction * len(_DASHA_SEQUENCE)) % len(_DASHA_SEQUENCE)
    antardasha_offset = (current_idx + antar_idx) % len(_DASHA_SEQUENCE)
    antardasha_name = _DASHA_SEQUENCE[antardasha_offset][0]

    return {
        "mahadasha": mahadasha_name,
        "antardasha": antardasha_name,
        "nakshatra_ruler": ruler,
    }


def is_available() -> bool:
    return _HAS_KERYKEION


def calculate_natal_vedica(
    name: str,
    year: int, month: int, day: int,
    hour: int | None, minute: int | None,
    lat: float, lon: float,
    tz_str: str,
) -> dict:
    """Calcula carta natal védica (Jyotish, Lahiri ayanamsa)."""
    if not _HAS_KERYKEION:
        raise RuntimeError("kerykeion not installed — cannot calculate vedic natal")

    has_time = hour is not None and minute is not None
    use_hour = hour if has_time else 12
    use_minute = minute if has_time else 0

    try:
        subject = AstrologicalSubjectFactory.from_birth_data(
            name=name,
            year=year, month=month, day=day,
            hour=use_hour, minute=use_minute,
            lat=lat, lng=lon,
            tz_str=tz_str,
            online=False,
            zodiac_type="Sidereal",
            sidereal_mode="LAHIRI",
            houses_system_identifier="W",  # Whole Sign, standard in Vedic
        )
    except Exception as e:
        logger.error(f"kerykeion vedic calculation failed: {e}")
        raise

    # Signos siderales
    sun_sign = _translate_sidereal(subject.sun.sign)
    moon_sign = _translate_sidereal(subject.moon.sign)

    # Nakshatra lunar
    moon_abs_pos = subject.moon.abs_pos
    nakshatra = get_nakshatra(moon_abs_pos)

    # Dashas
    dasha_info = calculate_mahadasha(moon_abs_pos, year)

    # Planetas
    planet_names = [
        "sun", "moon", "mercury", "venus", "mars",
        "jupiter", "saturn",
    ]  # Védica tradicional: 7 planetas + nodos
    planets = {}
    for pname in planet_names:
        planet = getattr(subject, pname, None)
        if planet:
            planets[pname] = {
                "sign": _translate_sidereal(planet.sign),
                "position": round(planet.position, 2),
                "retrograde": getattr(planet, "retrograde", False),
            }

    # Ascendente (solo con hora)
    ascendant = None
    if has_time:
        first = getattr(subject, "first_house", None)
        if first:
            ascendant = _translate_sidereal(first.sign)

    result = {
        "sun": sun_sign,
        "moon": moon_sign,
        "ascendant": ascendant,
        "nakshatra": nakshatra["name"],
        "nakshatra_ruler": nakshatra["ruler"],
        "mahadasha": dasha_info["mahadasha"],
        "antardasha": dasha_info["antardasha"],
        "planets": planets,
        "simplified": not has_time,
        "ayanamsa": "Lahiri",
    }

    return result


def _translate_sidereal(abbr: str) -> str:
    """Traduce abreviatura kerykeion a español."""
    return _translate_sign(abbr)


def build_drawn_data(natal: dict) -> dict:
    """drawn_data para usage_log."""
    return {
        "sun": natal["sun"],
        "moon": natal["moon"],
        "nakshatra": natal["nakshatra"],
        "mahadasha": natal["mahadasha"],
        "antardasha": natal["antardasha"],
    }
