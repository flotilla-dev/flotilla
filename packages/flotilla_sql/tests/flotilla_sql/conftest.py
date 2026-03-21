import pytest
from testcontainers.postgres import PostgresContainer
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from importlib.resources import files


# --- Container (session scoped) ---
@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:15") as pg:
        yield pg


# --- DSN conversion ---
@pytest.fixture(scope="session")
def async_dsn(postgres_container):
    return postgres_container.get_connection_url().replace("postgresql+psycopg2", "postgresql+asyncpg")


# --- Engine ---
@pytest.fixture
async def engine(async_dsn):
    engine = create_async_engine(async_dsn)

    # Load schema
    schema_path = files("flotilla_sql.thread.schema").joinpath("thread_entry_store.sql")
    ddl = schema_path.read_text()

    async with engine.begin() as conn:
        # 🔥 Drop all tables (reverse dependency order)
        await conn.exec_driver_sql("DROP TABLE IF EXISTS content_part CASCADE")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS thread_entry CASCADE")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS thread CASCADE")

    async with engine.begin() as conn:
        for stmt in ddl.split(";"):  # ✅ split into single statements
            stmt = stmt.strip()
            if stmt:
                await conn.exec_driver_sql(stmt)

    yield engine

    await engine.dispose()
