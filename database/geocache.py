"""Caché de geocoding en SQLite."""

from datetime import datetime, timezone

from database.connection import Database


async def get_cached_city(city_query: str) -> dict | None:
    db = await Database.get()
    cursor = await db.execute(
        "SELECT * FROM geocache WHERE city_query = ?", (city_query.lower().strip(),)
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return dict(row)


async def cache_city(
    city_query: str,
    city_name: str,
    lat: float,
    lon: float,
    timezone_str: str,
) -> None:
    db = await Database.get()
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """INSERT OR REPLACE INTO geocache (city_query, city_name, lat, lon, timezone, cached_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (city_query.lower().strip(), city_name, lat, lon, timezone_str, now),
    )
    await db.commit()
