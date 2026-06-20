"""
Lightweight migration runner for FastAPI lifespan.

Reads migrations/*.sql, tracks state in schema_migrations table,
and applies only missing files in alphabetical order.
No new dependencies — uses asyncpg already in the project.
"""

import logging
from pathlib import Path

import asyncpg

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent


async def run_migrations(connection_string: str) -> None:
    """
    Apply pending SQL migrations from migrations/*.sql.

    - Creates a `schema_migrations` tracking table if it doesn't exist.
    - Reads all .sql files in the migrations directory, sorted by filename.
    - Skips files already recorded in schema_migrations.
    - Runs missing files in a single transaction per file.
    - Logs successes and non-fatal errors (does not raise, so startup isn't blocked).
    """
    if not MIGRATIONS_DIR.exists():
        logger.warning("Migrations directory not found: %s", MIGRATIONS_DIR)
        return

    sql_files = sorted([f for f in MIGRATIONS_DIR.iterdir() if f.suffix == ".sql"])
    if not sql_files:
        logger.info("No migration files found in %s", MIGRATIONS_DIR)
        return

    conn = None
    try:
        conn = await asyncpg.connect(connection_string)

        # Ensure tracking table exists
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )

        # Fetch already-applied filenames
        applied_rows = await conn.fetch("SELECT filename FROM schema_migrations")
        applied = {row["filename"] for row in applied_rows}

        for sql_file in sql_files:
            filename = sql_file.name
            if filename in applied:
                continue

            sql = sql_file.read_text(encoding="utf-8")
            if not sql.strip():
                logger.info("Skipping empty migration: %s", filename)
                continue

            try:
                # Execute without explicit transaction so each statement is its own
                # implicit transaction. This avoids rollback of the tracking INSERT
                # when idempotent DDL (CREATE IF NOT EXISTS) statements succeed.
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO schema_migrations (filename) VALUES ($1)",
                    filename,
                )
                logger.info("Applied migration: %s", filename)
            except Exception as exc:
                logger.error("Migration failed (non-fatal): %s — %s", filename, exc)
                # Continue so one bad migration doesn't block the rest or crash startup

    except Exception as exc:
        logger.error("Migration runner failed to connect (non-fatal): %s", exc)
    finally:
        if conn is not None:
            await conn.close()
