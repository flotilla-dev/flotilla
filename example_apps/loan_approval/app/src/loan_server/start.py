import asyncio
from flotilla.flotilla_bootstrap import FlotillaBootstrap
from flotilla.config.resolvers.env_secret_resolver import EnvSecretResolver
from flotilla.config.sources.yaml_configuration_source import YamlConfigurationSource
from flotilla.config.sources.local_env_source import LocalEnvSource
from flotilla_fastapi.application import FastApiFlotillaApplication
from flotilla_sql.async_engine_provider import async_engine_provider
from flotilla.container.providers.reflection_provider import ReflectionProvider
from flotilla_langchain.llm.providers import openai_llm_provider
from loan_server.postgres_saver_provider import create_postgres_saver
from pathlib import Path


CONFIG_DIR = Path(__file__).parent


async def build_app():
    print("Start loan application")

    return await FlotillaBootstrap.create(
        cls=FastApiFlotillaApplication,
        config_sources=[YamlConfigurationSource(config_dir=CONFIG_DIR), LocalEnvSource()],
        secret_resolvers=[EnvSecretResolver()],
        providers={
            "$class": ReflectionProvider(),
            "llm.openai": openai_llm_provider,
            "async_engine_provider": async_engine_provider,
            "postgres_saver_provider": create_postgres_saver,
        },
    )


def start_app():
    # bootstrap the app
    app = asyncio.run(build_app())

    # run the embedded app
    app.run()


if __name__ == "__main__":
    start_app()
