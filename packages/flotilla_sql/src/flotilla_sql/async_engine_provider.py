from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from flotilla.utils.logger import get_logger

logger = get_logger(__name__)


def async_engine_provider(
    dsn: str,
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_timeout: int = 30,
    pool_recycle: int = 1800,
    echo: bool = False,
) -> AsyncEngine:
    """
    Custom FlotillaContainer provider function that can be used to create an AsyncEngine for injection to
    components that need to query the database

    Expect `dsn` to be a SQLAlchemy async URL such as `postgresql+asyncpg://...`.
    Keep this separate from any psycopg/libpq DSN used by sync PostgreSQL clients.
    """
    logger.info(
        "Create SQLAlchemy async engine pool_size=%d max_overflow=%d pool_timeout=%d pool_recycle=%d echo=%s",
        pool_size,
        max_overflow,
        pool_timeout,
        pool_recycle,
        echo,
    )
    return create_async_engine(
        url=dsn,
        echo=echo,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
    )
