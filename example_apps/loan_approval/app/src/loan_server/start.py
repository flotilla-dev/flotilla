import asyncio
import logging
import sys
from pathlib import Path

from flotilla.flotilla_bootstrap import FlotillaBootstrap
from flotilla.config.resolvers.env_secret_resolver import EnvSecretResolver
from flotilla.config.sources.yaml_configuration_source import YamlConfigurationSource
from flotilla.config.sources.local_env_source import LocalEnvSource
from flotilla_fastapi.application import FastApiFlotillaApplication
from flotilla_sql.async_engine_provider import async_engine_provider
from flotilla_langchain.llm.providers import openai_llm_provider
from loan_server.postgres_saver_provider import create_postgres_saver
from flotilla.utils.logger import get_logger

CONFIG_DIR = Path(__file__).parent
logger = get_logger(__name__)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
    )


async def build_app():
    logger.info("Start loan application")

    return await FlotillaBootstrap.create(
        cls=FastApiFlotillaApplication,
        config_sources=[YamlConfigurationSource(path=CONFIG_DIR / "flotilla.yml"), LocalEnvSource()],
        secret_resolvers=[EnvSecretResolver()],
        providers={
            "llm.openai": openai_llm_provider,
            "async_engine_provider": async_engine_provider,
            "postgres_saver_provider": create_postgres_saver,
        },
    )


def start_app():
    configure_logging()

    # bootstrap the app
    app = asyncio.run(build_app())

    # run the embedded app
    app.run(log_level="info")


if __name__ == "__main__":
    start_app()
