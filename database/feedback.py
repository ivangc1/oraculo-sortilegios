"""Operaciones de feedback en SQLite."""

from datetime import datetime, timezone

from database.connection import Database


async def save_feedback(usage_id: int, user_id: int, positive: bool) -> None:
    db = await Database.get()
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "INSERT INTO feedback (user_id, usage_id, positive, timestamp) VALUES (?, ?, ?, ?)",
        (user_id, usage_id, positive, now),
    )
    await db.commit()


async def get_feedback(usage_id: int) -> dict | None:
    db = await Database.get()
    cursor = await db.execute(
        "SELECT * FROM feedback WHERE usage_id = ?", (usage_id,)
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return dict(row)


async def get_feedback_stats() -> dict:
    """Estadísticas de feedback para /stats."""
    db = await Database.get()
    cursor = await db.execute(
        """SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE positive = TRUE) as positive,
            COUNT(*) FILTER (WHERE positive = FALSE) as negative
        FROM feedback"""
    )
    row = await cursor.fetchone()
    return {"total": row[0], "positive": row[1], "negative": row[2]}
