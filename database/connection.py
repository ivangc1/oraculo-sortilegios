"""Singleton de conexión SQLite con WAL, FK, busy_timeout y migraciones."""

import aiosqlite
from loguru import logger

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS users (
    telegram_user_id    INTEGER PRIMARY KEY,
    telegram_username   TEXT,
    alias               TEXT NOT NULL,
    full_birth_name     TEXT,
    birth_date          TEXT NOT NULL,
    birth_time          TEXT,
    birth_city          TEXT,
    birth_lat           REAL,
    birth_lon           REAL,
    birth_timezone      TEXT,
    sun_sign            TEXT,
    moon_sign           TEXT,
    ascendant           TEXT,
    lunar_nakshatra     TEXT,
    life_path           INTEGER,
    registered_at       TEXT NOT NULL,
    last_activity       TEXT,
    onboarding_complete BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS usage_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    mode            TEXT NOT NULL,
    variant         TEXT,
    tokens_input    INTEGER NOT NULL,
    tokens_output   INTEGER NOT NULL,
    cost_usd        REAL NOT NULL,
    cached          BOOLEAN NOT NULL,
    truncated       BOOLEAN NOT NULL DEFAULT FALSE,
    drawn_data      TEXT,
    timestamp       TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(telegram_user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS feedback (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    usage_id    INTEGER NOT NULL UNIQUE,
    positive    BOOLEAN NOT NULL,
    timestamp   TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(telegram_user_id) ON DELETE CASCADE,
    FOREIGN KEY (usage_id) REFERENCES usage_log(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS geocache (
    city_query  TEXT PRIMARY KEY,
    city_name   TEXT NOT NULL,
    lat         REAL NOT NULL,
    lon         REAL NOT NULL,
    timezone    TEXT NOT NULL,
    cached_at   TEXT NOT NULL
);
"""


class Database:
    """Singleton async SQLite. Se inicializa una vez, se cierra al apagar."""

    _instance: aiosqlite.Connection | None = None
    _db_path: str = "bot-taberna.db"

    @classmethod
    async def get(cls) -> aiosqlite.Connection:
        if cls._instance is None:
            cls._instance = await aiosqlite.connect(cls._db_path)
            cls._instance.row_factory = aiosqlite.Row
            await cls._instance.execute("PRAGMA journal_mode=WAL")
            await cls._instance.execute("PRAGMA busy_timeout=5000")
            await cls._instance.execute("PRAGMA foreign_keys=ON")
            await cls._init_tables(cls._instance)
            await cls._apply_migrations(cls._instance)
            logger.info("SQLite inicializado (WAL, FK ON)")
        return cls._instance

    @classmethod
    async def close(cls):
        if cls._instance:
            await cls._instance.close()
            cls._instance = None
            logger.info("SQLite cerrado")

    @classmethod
    async def _init_tables(cls, db: aiosqlite.Connection):
        await db.executescript(_SCHEMA_SQL)
        await db.commit()

    @classmethod
    async def _apply_migrations(cls, db: aiosqlite.Connection):
        """Aplica migraciones pendientes desde database/migrations/."""
        cursor = await db.execute(
            "SELECT MAX(version) FROM schema_version"
        )
        row = await cursor.fetchone()
        current_version = row[0] if row[0] is not None else 0

        import os
        migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
        if not os.path.isdir(migrations_dir):
            return

        migration_files = sorted(
            f for f in os.listdir(migrations_dir)
            if f.endswith(".sql") and f.split("_")[0].isdigit()
        )

        for filename in migration_files:
            version = int(filename.split("_")[0])
            if version <= current_version:
                continue

            filepath = os.path.join(migrations_dir, filename)
            with open(filepath, encoding="utf-8") as f:
                sql = f.read()

            await db.executescript(sql)
            await db.execute(
                "INSERT INTO schema_version (version) VALUES (?)", (version,)
            )
            await db.commit()
            logger.info(f"Migración aplicada: {filename}")
