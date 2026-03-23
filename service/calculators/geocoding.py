"""Geocoding con Nominatim: caché SQLite + asyncio.Lock + rate limit.

user_agent obligatorio, 1.1s entre requests (Nominatim policy).
Ciudades homónimas: devuelve la primera coincidencia con display_name completo
para que el usuario confirme o sea más específico.
"""

import asyncio
from functools import partial

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable, GeocoderServiceError
from loguru import logger

from database.geocache import cache_city, get_cached_city
from service.calculators.timezone import get_timezone_for_coords

_nominatim_lock = asyncio.Lock()
_geolocator = Nominatim(user_agent="oraculo-sortilegios/1.0", timeout=10)


class GeocodingResult:
    """Resultado de geocoding."""
    def __init__(self, city_name: str, lat: float, lon: float, timezone_str: str):
        self.city_name = city_name
        self.lat = lat
        self.lon = lon
        self.timezone = timezone_str


async def geocode_city(city_input: str) -> GeocodingResult | None:
    """Geocodifica una ciudad. Caché SQLite, rate limit con lock.

    Returns:
        GeocodingResult o None si no encontrada o servicio caído.

    Raises:
        Exception si Nominatim está completamente caído.
    """
    normalized = city_input.strip().lower()
    if not normalized:
        return None

    # 1. Buscar en caché
    cached = await get_cached_city(normalized)
    if cached:
        return GeocodingResult(
            city_name=cached["city_name"],
            lat=cached["lat"],
            lon=cached["lon"],
            timezone_str=cached["timezone"],
        )

    # 2. Consultar Nominatim con lock (1 request a la vez)
    async with _nominatim_lock:
        # Rate limit: 1.1s entre requests
        await asyncio.sleep(1.1)

        try:
            loop = asyncio.get_event_loop()
            location = await loop.run_in_executor(
                None,
                partial(_geolocator.geocode, city_input, exactly_one=True, language="es"),
            )
        except (GeocoderTimedOut, GeocoderUnavailable, GeocoderServiceError) as e:
            logger.warning(f"Nominatim error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected geocoding error: {e}")
            raise

    if location is None:
        return None

    # 3. Obtener timezone
    tz_str = get_timezone_for_coords(location.latitude, location.longitude)

    # 4. Guardar en caché
    result = GeocodingResult(
        city_name=location.address,
        lat=location.latitude,
        lon=location.longitude,
        timezone_str=tz_str,
    )
    await cache_city(
        city_query=normalized,
        city_name=result.city_name,
        lat=result.lat,
        lon=result.lon,
        timezone_str=result.timezone,
    )

    return result
