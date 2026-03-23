"""Signo solar con efemérides (no tabla fija).

Usa kerykeion si disponible, fallback a tabla aproximada.
Para fecha sin hora, usa mediodía como aproximación.
"""

from datetime import datetime
from loguru import logger

# Signos del zodíaco en orden (0-11)
ZODIAC_SIGNS = [
    "Aries", "Tauro", "Géminis", "Cáncer", "Leo", "Virgo",
    "Libra", "Escorpio", "Sagitario", "Capricornio", "Acuario", "Piscis",
]

# Intentar usar kerykeion para cálculo preciso con efemérides
_HAS_KERYKEION = False
try:
    from kerykeion import AstrologicalSubjectFactory
    _HAS_KERYKEION = True
except ImportError:
    logger.info("kerykeion not available, using approximate sun sign table")


def get_sun_sign(
    year: int, month: int, day: int,
    hour: int = 12, minute: int = 0,
    lat: float = 40.4168, lon: float = -3.7038,
    tz_str: str = "Europe/Madrid",
) -> str:
    """Calcula signo solar. Con efemérides si kerykeion disponible, sino aproximado.

    Para fechas límite (19-22 de cada mes), el cálculo con efemérides
    es crucial: la tabla fija puede errar por 1-2 días.
    """
    if _HAS_KERYKEION:
        return _sun_sign_ephemeris(year, month, day, hour, minute, lat, lon, tz_str)
    return _sun_sign_approximate(month, day)


def _sun_sign_ephemeris(
    year: int, month: int, day: int,
    hour: int, minute: int,
    lat: float, lon: float, tz_str: str,
) -> str:
    """Cálculo preciso con efemérides vía kerykeion."""
    try:
        subject = AstrologicalSubjectFactory.from_birth_data(
            name="_sun_sign_calc",
            year=year, month=month, day=day,
            hour=hour, minute=minute,
            lat=lat, lng=lon,
            tz_str=tz_str,
            online=False,
        )
        # subject.sun.sign devuelve abreviatura inglesa: "Ari", "Tau", etc.
        sign_abbr = subject.sun.sign
        return _translate_sign(sign_abbr)
    except Exception as e:
        logger.warning(f"Ephemeris sun sign failed: {e}, using approximate")
        return _sun_sign_approximate(month, day)


def _sun_sign_approximate(month: int, day: int) -> str:
    """Tabla aproximada. Solo como fallback si efemérides no disponibles."""
    # Fechas aproximadas de ingreso solar (pueden variar ±1 día)
    boundaries = [
        (1, 20, "Acuario"), (2, 19, "Piscis"), (3, 21, "Aries"),
        (4, 20, "Tauro"), (5, 21, "Géminis"), (6, 21, "Cáncer"),
        (7, 23, "Leo"), (8, 23, "Virgo"), (9, 23, "Libra"),
        (10, 23, "Escorpio"), (11, 22, "Sagitario"), (12, 22, "Capricornio"),
    ]

    for b_month, b_day, sign in boundaries:
        if month == b_month and day >= b_day:
            return sign
        if month == b_month and day < b_day:
            # Signo anterior
            idx = boundaries.index((b_month, b_day, sign))
            prev = boundaries[idx - 1]
            return prev[2]

    return "Capricornio"  # Enero 1-19


def _translate_sign(abbr: str) -> str:
    """Traduce abreviatura kerykeion al español."""
    translations = {
        "Ari": "Aries", "Tau": "Tauro", "Gem": "Géminis",
        "Can": "Cáncer", "Leo": "Leo", "Vir": "Virgo",
        "Lib": "Libra", "Sco": "Escorpio", "Sag": "Sagitario",
        "Cap": "Capricornio", "Aqu": "Acuario", "Pis": "Piscis",
    }
    return translations.get(abbr, abbr)
