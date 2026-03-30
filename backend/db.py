import asyncpg
from config import settings
import logging

logger = logging.getLogger(__name__)

pool: asyncpg.Pool | None = None


async def init_pool() -> None:
    global pool
    # Supabase requires SSL; asyncpg handles it via the DSN or ssl param
    dsn = settings.database_url
    pool = await asyncpg.create_pool(
        dsn=dsn,
        min_size=2,
        max_size=10,
        command_timeout=30,
        ssl="require",
        statement_cache_size=0,  # required for Supabase PgBouncer compatibility
    )
    logger.info("Database pool initialized")


async def close_pool() -> None:
    global pool
    if pool:
        await pool.close()
        logger.info("Database pool closed")


async def get_pool() -> asyncpg.Pool:
    assert pool is not None, "Database pool not initialized"
    return pool
