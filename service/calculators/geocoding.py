"""Geocoding con Nominatim: caché SQLite + asyncio.Lock + rate limit.

user_agent obligatorio, 1.1s entre requests (Nominatim policy).
Ciudades homónimas: devuelve múltiples resultados como botones inline
para que el usuario seleccione la correcta.
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

# Máximo de resultados a mostrar al usuario
MAX_GEOCODING_RESULTS = 5


class GeocodingResult:
    """Resultado de geocoding."""
    def __init__(self, city_name: str, lat: float, lon: float, timezone_str: str):
        self.city_name = city_name
        self.lat = lat
        self.lon = lon
        self.timezone = timezone_str


async def geocode_city(city_input: str) -> GeocodingResult | None:
    """Geocodifica una ciudad (resultado único). Caché SQLite, rate limit con lock.

    Returns:
        GeocodingResult o None si no encontrada o servicio caído.
    """
    results = await geocode_city_multi(city_input)
    return results[0] if results else None


async def geocode_city_multi(city_input: str) -> list[GeocodingResult]:
    """Geocodifica una ciudad y devuelve múltiples resultados.

    Returns:
        Lista de GeocodingResult (hasta MAX_GEOCODING_RESULTS). Vacía si no encontrada.

    Raises:
        Exception si Nominatim está completamente caído.
    """
    normalized = city_input.strip().lower()
    if not normalized:
        return []

    # 1. Buscar en caché (si hay hit, devolver solo ese)
    cached = await get_cached_city(normalized)
    if cached:
        return [GeocodingResult(
            city_name=cached["city_name"],
            lat=cached["lat"],
            lon=cached["lon"],
            timezone_str=cached["timezone"],
        )]

    # 2. Consultar Nominatim con lock (1 request a la vez)
    async with _nominatim_lock:
        await asyncio.sleep(1.1)

        try:
            loop = asyncio.get_event_loop()
            locations = await loop.run_in_executor(
                None,
                partial(
                    _geolocator.geocode,
                    city_input,
                    exactly_one=False,
                    limit=MAX_GEOCODING_RESULTS,
                    language="es",
                ),
            )
        except (GeocoderTimedOut, GeocoderUnavailable, GeocoderServiceError) as e:
            logger.warning(f"Nominatim error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected geocoding error: {e}")
            raise

    if not locations:
        return []

    # 3. Construir resultados con timezone
    results = []
    for loc in locations[:MAX_GEOCODING_RESULTS]:
        tz_str = get_timezone_for_coords(loc.latitude, loc.longitude)
        results.append(GeocodingResult(
            city_name=loc.address,
            lat=loc.latitude,
            lon=loc.longitude,
            timezone_str=tz_str,
        ))

    return results


async def cache_geocoding_result(city_input: str, result: GeocodingResult) -> None:
    """Cachea un resultado de geocoding seleccionado por el usuario."""
    normalized = city_input.strip().lower()
    await cache_city(
        city_query=normalized,
        city_name=result.city_name,
        lat=result.lat,
        lon=result.lon,
        timezone_str=result.timezone,
    )
