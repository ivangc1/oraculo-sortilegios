"""Timezone: timezonefinder + zoneinfo. Hora local → UTC.

Limitaciones documentadas:
- Pre-1970: zonas horarias históricas dependen de IANA database. Generalmente buena
  pero no perfecta universalmente.
- Pre-1900 (fecha mínima bot): mayor incertidumbre.
- El bot no puede garantizar precisión al minuto para fechas muy antiguas.
"""

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from loguru import logger
from timezonefinder import TimezoneFinder

from service.calculators.dates import parse_birth_date

_tf = TimezoneFinder()


def get_timezone_for_coords(lat: float, lon: float) -> str:
    """Devuelve timezone IANA para coordenadas. Fallback a UTC."""
    tz_str = _tf.timezone_at(lat=lat, lng=lon)
    if tz_str is None:
        logger.warning(f"No timezone found for ({lat}, {lon}), using UTC")
        return "UTC"
    return tz_str


def local_to_utc(
    year: int, month: int, day: int,
    hour: int, minute: int,
    timezone_str: str,
) -> datetime:
    """Convierte fecha/hora local a UTC."""
    try:
        tz = ZoneInfo(timezone_str)
    except (ZoneInfoNotFoundError, KeyError):
        logger.warning(f"Unknown timezone: {timezone_str}, using UTC")
        tz = ZoneInfo("UTC")

    local_dt = datetime(year, month, day, hour, minute, tzinfo=tz)
    return local_dt.astimezone(ZoneInfo("UTC"))


def get_utc_datetime(
    birth_date: str,
    birth_time: str | None,
    timezone_str: str | None,
) -> datetime:
    """Construye datetime UTC desde datos de nacimiento.

    Sin hora: usa mediodía local como aproximación.
    Sin timezone: usa UTC directamente.
    """
    day, month, year = parse_birth_date(birth_date)

    if birth_time:
        time_parts = birth_time.split(":")
        hour, minute = int(time_parts[0]), int(time_parts[1])
    else:
        hour, minute = 12, 0  # Mediodía como aproximación sin hora

    tz_str = timezone_str or "UTC"
    return local_to_utc(year, month, day, hour, minute, tz_str)
