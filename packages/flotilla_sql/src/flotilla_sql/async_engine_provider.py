from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def create_async_engine(
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
    """
    return create_async_engine(
        dsn=dsn,
        echo=echo,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        future=True,
    )
