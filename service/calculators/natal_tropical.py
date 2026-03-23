"""Carta natal tropical con kerykeion v5.

Placidus por defecto. Fallback a Whole Sign si |lat| > 60°.
Sin hora → carta simplificada (sin ascendente ni casas).

Requiere kerykeion (no disponible en Windows dev sin C compiler).
Import condicional para que tests locales funcionen con mocks.
"""

from loguru import logger

from service.calculators.sun_sign import _translate_sign

_HAS_KERYKEION = False
try:
    from kerykeion import AstrologicalSubjectFactory, AspectsFactory
    _HAS_KERYKEION = True
except ImportError:
    logger.info("kerykeion not available — natal tropical disabled")


def is_available() -> bool:
    return _HAS_KERYKEION


def calculate_natal_tropical(
    name: str,
    year: int, month: int, day: int,
    hour: int | None, minute: int | None,
    lat: float, lon: float,
    tz_str: str,
) -> dict:
    """Calcula carta natal tropical completa.

    Returns dict con: sun, moon, ascendant, planets, houses, aspects,
    house_system, simplified (bool).
    """
    if not _HAS_KERYKEION:
        raise RuntimeError("kerykeion not installed — cannot calculate tropical natal")

    has_time = hour is not None and minute is not None
    use_hour = hour if has_time else 12
    use_minute = minute if has_time else 0

    # Determinar sistema de casas
    house_system = "P"  # Placidus
    if abs(lat) > 60:
        house_system = "W"  # Whole Sign fallback
        logger.info(f"Latitude {lat}° > 60°, using Whole Sign instead of Placidus")

    try:
        subject = AstrologicalSubjectFactory.from_birth_data(
            name=name,
            year=year, month=month, day=day,
            hour=use_hour, minute=use_minute,
            lat=lat, lng=lon,
            tz_str=tz_str,
            online=False,
            houses_system_identifier=house_system,
        )
    except Exception as e:
        logger.error(f"kerykeion calculation failed: {e}")
        raise

    # Extraer planetas
    planet_names = [
        "sun", "moon", "mercury", "venus", "mars",
        "jupiter", "saturn", "uranus", "neptune", "pluto",
    ]
    planets = {}
    for pname in planet_names:
        planet = getattr(subject, pname, None)
        if planet:
            planets[pname] = {
                "sign": _translate_sign(planet.sign),
                "position": round(planet.position, 2),
                "house": _format_house(planet.house) if has_time else None,
                "retrograde": getattr(planet, "retrograde", False),
            }

    # Casas (solo con hora)
    houses = {}
    if has_time:
        for i in range(1, 13):
            house_attr = f"{'first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth'.split()[i-1]}_house"
            house_obj = getattr(subject, house_attr, None)
            if house_obj:
                houses[str(i)] = {
                    "sign": _translate_sign(house_obj.sign),
                    "position": round(house_obj.position, 2),
                }

    # Ascendente (solo con hora)
    ascendant = None
    if has_time:
        first = getattr(subject, "first_house", None)
        if first:
            ascendant = _translate_sign(first.sign)

    # Aspectos
    aspects = []
    try:
        aspects_result = AspectsFactory.single_chart_aspects(subject)
        for a in aspects_result.aspects:
            aspects.append({
                "p1": a.p1_name,
                "aspect": a.aspect,
                "p2": a.p2_name,
                "orbit": round(a.orbit, 2),
            })
    except Exception as e:
        logger.warning(f"Aspects calculation failed: {e}")

    result = {
        "sun": _translate_sign(subject.sun.sign),
        "moon": _translate_sign(subject.moon.sign),
        "ascendant": ascendant,
        "planets": planets,
        "houses": houses,
        "aspects": aspects,
        "house_system": "Whole Sign" if house_system == "W" else "Placidus",
        "simplified": not has_time,
        "planets_calculated": len(planets),
        "aspects_found": len(aspects),
    }

    return result


def _format_house(house_str: str) -> str:
    """Convierte 'Sixth_House' → 'Casa 6'."""
    ordinals = {
        "First": "1", "Second": "2", "Third": "3", "Fourth": "4",
        "Fifth": "5", "Sixth": "6", "Seventh": "7", "Eighth": "8",
        "Ninth": "9", "Tenth": "10", "Eleventh": "11", "Twelfth": "12",
    }
    if house_str and "_" in house_str:
        word = house_str.split("_")[0]
        num = ordinals.get(word, word)
        return f"Casa {num}"
    return house_str or ""


def build_drawn_data(natal: dict) -> dict:
    """drawn_data para usage_log."""
    return {
        "sun": natal["sun"],
        "moon": natal["moon"],
        "asc": natal["ascendant"],
        "planets_calculated": natal["planets_calculated"],
        "aspects_found": natal["aspects_found"],
    }
