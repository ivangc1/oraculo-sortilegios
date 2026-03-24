"""Operaciones de tracking de uso en SQLite."""

import json
from datetime import datetime, timezone

from database.connection import Database


async def record_usage(
    user_id: int,
    mode: str,
    variant: str | None,
    tokens_input: int,
    tokens_output: int,
    cost_usd: float,
    cached: bool,
    truncated: bool = False,
    drawn_data: dict | None = None,
) -> int:
    """Registra uso + actualiza last_activity en transacción atómica. Devuelve usage_id."""
    db = await Database.get()
    now = datetime.now(timezone.utc).isoformat()
    drawn_json = json.dumps(drawn_data, ensure_ascii=False) if drawn_data else None

    async with db.execute("BEGIN"):
        # Verificar si el usuario existe. Si no, saltar FK desactivando temporalmente.
        cursor_check = await db.execute(
            "SELECT 1 FROM users WHERE telegram_user_id = ?", (user_id,)
        )
        user_exists = await cursor_check.fetchone() is not None
        if not user_exists:
            await db.execute("PRAGMA foreign_keys = OFF")
        cursor = await db.execute(
            """INSERT INTO usage_log (
                user_id, mode, variant, tokens_input, tokens_output,
                cost_usd, cached, truncated, drawn_data, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id, mode, variant, tokens_input, tokens_output,
                cost_usd, cached, truncated, drawn_json, now,
            ),
        )
        usage_id = cursor.lastrowid
        if user_exists:
            await db.execute(
                "UPDATE users SET last_activity = ? WHERE telegram_user_id = ?",
                (now, user_id),
            )
        await db.commit()
        if not user_exists:
            await db.execute("PRAGMA foreign_keys = ON")

    return usage_id


async def get_usage(usage_id: int) -> dict | None:
    db = await Database.get()
    cursor = await db.execute(
        "SELECT * FROM usage_log WHERE id = ?", (usage_id,)
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return dict(row)


async def get_daily_usage_count(user_id: int, mode: str | None = None) -> int:
    """Cuenta usos del día (UTC). Si mode=None, cuenta todos los modos de adivinación."""
    db = await Database.get()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if mode is None:
        # Pool de adivinación: tarot + runas + iching + geomancia
        cursor = await db.execute(
            """SELECT COUNT(*) FROM usage_log
               WHERE user_id = ? AND timestamp >= ? AND mode IN ('tarot', 'runas', 'iching', 'geomancia')""",
            (user_id, today),
        )
    else:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM usage_log WHERE user_id = ? AND timestamp >= ? AND mode = ?",
            (user_id, today, mode),
        )
    row = await cursor.fetchone()
    return row[0]


async def get_daily_cost() -> float:
    """Coste total del día actual."""
    db = await Database.get()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cursor = await db.execute(
        "SELECT COALESCE(SUM(cost_usd), 0) FROM usage_log WHERE timestamp >= ?",
        (today,),
    )
    row = await cursor.fetchone()
    return row[0]


async def get_monthly_cost() -> float:
    """Coste total del mes actual."""
    db = await Database.get()
    month_start = datetime.now(timezone.utc).strftime("%Y-%m-01")
    cursor = await db.execute(
        "SELECT COALESCE(SUM(cost_usd), 0) FROM usage_log WHERE timestamp >= ?",
        (month_start,),
    )
    row = await cursor.fetchone()
    return row[0]


async def get_stats_summary() -> dict:
    """Resumen para /stats. Top 5 usuarios, totales, etc."""
    db = await Database.get()

    # Total usos y coste
    cursor = await db.execute(
        "SELECT COUNT(*), COALESCE(SUM(cost_usd), 0), COALESCE(SUM(tokens_input), 0), COALESCE(SUM(tokens_output), 0) FROM usage_log"
    )
    row = await cursor.fetchone()
    total_uses, total_cost, total_input, total_output = row

    # Top 5 usuarios
    cursor = await db.execute(
        """SELECT u.alias, COUNT(*) as uses, SUM(ul.cost_usd) as cost
           FROM usage_log ul JOIN users u ON ul.user_id = u.telegram_user_id
           GROUP BY ul.user_id ORDER BY uses DESC LIMIT 5"""
    )
    top_users = [dict(r) for r in await cursor.fetchall()]

    # Usos por modo
    cursor = await db.execute(
        "SELECT mode, COUNT(*) as uses FROM usage_log GROUP BY mode ORDER BY uses DESC"
    )
    by_mode = [dict(r) for r in await cursor.fetchall()]

    # Cache hit rate
    cursor = await db.execute(
        "SELECT COUNT(*) FILTER (WHERE cached = TRUE), COUNT(*) FROM usage_log"
    )
    row = await cursor.fetchone()
    cache_hits, cache_total = row
    cache_rate = (cache_hits / cache_total * 100) if cache_total > 0 else 0

    # Truncados
    cursor = await db.execute(
        "SELECT COUNT(*) FROM usage_log WHERE truncated = TRUE"
    )
    truncated_count = (await cursor.fetchone())[0]

    return {
        "total_uses": total_uses,
        "total_cost": total_cost,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "top_users": top_users,
        "by_mode": by_mode,
        "cache_rate": cache_rate,
        "truncated_count": truncated_count,
    }
