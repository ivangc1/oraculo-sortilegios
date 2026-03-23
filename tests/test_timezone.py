"""Tests de timezone: verano/invierno, zonas históricas, conversión UTC."""

from datetime import datetime
from zoneinfo import ZoneInfo

from service.calculators.timezone import (
    get_timezone_for_coords,
    get_utc_datetime,
    local_to_utc,
)


# === Detección de timezone por coordenadas ===

def test_timezone_madrid():
    tz = get_timezone_for_coords(40.4168, -3.7038)
    assert tz == "Europe/Madrid"


def test_timezone_london():
    tz = get_timezone_for_coords(51.5074, -0.1278)
    assert tz == "Europe/London"


def test_timezone_new_york():
    tz = get_timezone_for_coords(40.7128, -74.0060)
    assert tz == "America/New_York"


def test_timezone_tokyo():
    tz = get_timezone_for_coords(35.6762, 139.6503)
    assert tz == "Asia/Tokyo"


def test_timezone_buenos_aires():
    tz = get_timezone_for_coords(-34.6037, -58.3816)
    assert tz == "America/Argentina/Buenos_Aires"


def test_timezone_kolkata():
    tz = get_timezone_for_coords(28.6139, 77.2090)
    assert tz == "Asia/Kolkata"


def test_timezone_ocean_fallback():
    """Coordenadas en medio del océano → UTC fallback."""
    tz = get_timezone_for_coords(0.0, -160.0)
    # Puede devolver una zona o UTC dependiendo de la versión de timezonefinder
    assert tz is not None


# === Conversión hora local → UTC ===

def test_local_to_utc_madrid_winter():
    """Madrid en invierno: UTC+1."""
    utc = local_to_utc(1993, 1, 15, 14, 30, "Europe/Madrid")
    assert utc.hour == 13  # 14:30 CET → 13:30 UTC
    assert utc.minute == 30


def test_local_to_utc_madrid_summer():
    """Madrid en verano: UTC+2 (CEST)."""
    utc = local_to_utc(1993, 7, 15, 14, 30, "Europe/Madrid")
    assert utc.hour == 12  # 14:30 CEST → 12:30 UTC
    assert utc.minute == 30


def test_local_to_utc_new_york_winter():
    """New York en invierno: UTC-5."""
    utc = local_to_utc(2000, 1, 15, 10, 0, "America/New_York")
    assert utc.hour == 15  # 10:00 EST → 15:00 UTC


def test_local_to_utc_new_york_summer():
    """New York en verano: UTC-4 (EDT)."""
    utc = local_to_utc(2000, 7, 15, 10, 0, "America/New_York")
    assert utc.hour == 14  # 10:00 EDT → 14:00 UTC


def test_local_to_utc_india():
    """India: UTC+5:30 (todo el año, sin DST)."""
    utc = local_to_utc(1990, 6, 15, 10, 30, "Asia/Kolkata")
    assert utc.hour == 5
    assert utc.minute == 0  # 10:30 IST → 05:00 UTC


def test_local_to_utc_unknown_tz():
    """Timezone desconocida → fallback UTC."""
    utc = local_to_utc(2000, 1, 1, 12, 0, "Invalid/Zone")
    assert utc.hour == 12  # Sin offset, hora se mantiene


# === get_utc_datetime ===

def test_get_utc_with_time():
    dt = get_utc_datetime("15/06/1993", "14:30", "Europe/Madrid")
    assert dt.year == 1993
    assert dt.month == 6
    assert dt.day == 15
    # Verano Madrid: UTC+2
    assert dt.hour == 12


def test_get_utc_without_time():
    """Sin hora → mediodía como aproximación."""
    dt = get_utc_datetime("15/06/1993", None, "Europe/Madrid")
    # 12:00 CEST → 10:00 UTC
    assert dt.hour == 10


def test_get_utc_without_timezone():
    """Sin timezone → UTC directo."""
    dt = get_utc_datetime("15/06/1993", "14:30", None)
    assert dt.hour == 14


def test_get_utc_iso_format():
    dt = get_utc_datetime("1993-06-15", "14:30", "Europe/Madrid")
    assert dt.year == 1993
    assert dt.month == 6


# === Zonas históricas (limitaciones documentadas) ===

def test_historic_zone_1950():
    """1950s: zonas IANA generalmente correctas."""
    utc = local_to_utc(1950, 3, 15, 12, 0, "Europe/Madrid")
    assert utc.tzinfo == ZoneInfo("UTC")
    assert utc.year == 1950


def test_historic_zone_1920():
    """1920s: zonas IANA disponibles pero menos fiables."""
    utc = local_to_utc(1920, 6, 1, 12, 0, "Europe/London")
    assert utc.year == 1920
    # BST existía desde 1916
    assert utc.hour == 11  # 12:00 BST → 11:00 UTC


def test_historic_zone_1900():
    """1900: fecha mínima del bot. Zona puede tener incertidumbre."""
    # No crashea
    utc = local_to_utc(1900, 1, 1, 12, 0, "Europe/Madrid")
    assert utc.year == 1900
