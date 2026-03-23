"""Operaciones de usuario en SQLite."""

from datetime import datetime, timezone

from database.connection import Database


async def get_user(user_id: int) -> dict | None:
    db = await Database.get()
    cursor = await db.execute(
        "SELECT * FROM users WHERE telegram_user_id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return dict(row)


async def create_user(
    user_id: int,
    username: str | None,
    alias: str,
    birth_date: str,
    birth_time: str | None = None,
    birth_city: str | None = None,
    birth_lat: float | None = None,
    birth_lon: float | None = None,
    birth_timezone: str | None = None,
    sun_sign: str | None = None,
    moon_sign: str | None = None,
    ascendant: str | None = None,
    lunar_nakshatra: str | None = None,
    life_path: int | None = None,
) -> None:
    db = await Database.get()
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """INSERT INTO users (
            telegram_user_id, telegram_username, alias, birth_date,
            birth_time, birth_city, birth_lat, birth_lon, birth_timezone,
            sun_sign, moon_sign, ascendant, lunar_nakshatra, life_path,
            registered_at, last_activity, onboarding_complete
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE)""",
        (
            user_id, username, alias, birth_date,
            birth_time, birth_city, birth_lat, birth_lon, birth_timezone,
            sun_sign, moon_sign, ascendant, lunar_nakshatra, life_path,
            now, now,
        ),
    )
    await db.commit()


async def update_username(user_id: int, username: str | None) -> None:
    db = await Database.get()
    await db.execute(
        "UPDATE users SET telegram_username = ? WHERE telegram_user_id = ?",
        (username, user_id),
    )
    await db.commit()


async def update_last_activity(user_id: int) -> None:
    db = await Database.get()
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "UPDATE users SET last_activity = ? WHERE telegram_user_id = ?",
        (now, user_id),
    )
    await db.commit()


async def update_full_birth_name(user_id: int, name: str) -> None:
    db = await Database.get()
    await db.execute(
        "UPDATE users SET full_birth_name = ? WHERE telegram_user_id = ?",
        (name, user_id),
    )
    await db.commit()


async def update_profile(user_id: int, **fields) -> None:
    """Actualiza campos arbitrarios del perfil."""
    if not fields:
        return
    db = await Database.get()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [user_id]
    await db.execute(
        f"UPDATE users SET {set_clause} WHERE telegram_user_id = ?",
        values,
    )
    await db.commit()


async def delete_user(user_id: int) -> None:
    db = await Database.get()
    await db.execute(
        "DELETE FROM users WHERE telegram_user_id = ?", (user_id,)
    )
    await db.commit()


async def save_partial_onboarding(user_id: int, username: str | None, alias: str, birth_date: str) -> None:
    """Guarda perfil parcial (sin onboarding_complete) para retomar tras restart."""
    db = await Database.get()
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """INSERT OR REPLACE INTO users (
            telegram_user_id, telegram_username, alias, birth_date,
            registered_at, onboarding_complete
        ) VALUES (?, ?, ?, ?, ?, FALSE)""",
        (user_id, username, alias, birth_date, now),
    )
    await db.commit()


async def get_incomplete_onboarding(user_id: int) -> dict | None:
    """Devuelve perfil si existe con onboarding_complete=FALSE."""
    db = await Database.get()
    cursor = await db.execute(
        "SELECT * FROM users WHERE telegram_user_id = ? AND onboarding_complete = FALSE",
        (user_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return dict(row)


async def complete_onboarding(user_id: int) -> None:
    db = await Database.get()
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "UPDATE users SET onboarding_complete = TRUE, last_activity = ? WHERE telegram_user_id = ?",
        (now, user_id),
    )
    await db.commit()
