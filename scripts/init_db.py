"""Create the database (if missing) and apply every sql/*.sql migration in order.

Usage:  py scripts/init_db.py

Connects with the DATABASE_URL from .env. If the target database does not exist,
it is created by connecting to the default 'postgres' database first.
"""

import asyncio
import sys
from pathlib import Path
from urllib.parse import urlsplit

import asyncpg

# Allow running as `py scripts/init_db.py` from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def _asyncpg_dsn(database_url: str) -> str:
    """Convert the SQLAlchemy URL (postgresql+asyncpg://...) to a plain asyncpg DSN."""
    return database_url.replace("postgresql+asyncpg://", "postgresql://")


async def _ensure_database(dsn: str) -> None:
    parts = urlsplit(dsn)
    db_name = parts.path.lstrip("/")
    admin_dsn = dsn.replace(f"/{db_name}", "/postgres")

    conn = await asyncpg.connect(admin_dsn)
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db_name)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{db_name}"')
            print(f"Created database '{db_name}'.")
        else:
            print(f"Database '{db_name}' already exists.")
    finally:
        await conn.close()


async def _apply_migrations(dsn: str) -> None:
    conn = await asyncpg.connect(dsn)
    try:
        for sql_file in sorted(SQL_DIR.glob("*.sql")):
            print(f"Applying {sql_file.name} ...")
            await conn.execute(sql_file.read_text(encoding="utf-8"))
    finally:
        await conn.close()


async def main() -> None:
    dsn = _asyncpg_dsn(get_settings().database_url)
    await _ensure_database(dsn)
    await _apply_migrations(dsn)
    print("Done. Schema is up to date.")


if __name__ == "__main__":
    asyncio.run(main())
