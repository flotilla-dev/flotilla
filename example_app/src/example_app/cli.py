"""
Example Application Main Entry Point
Demonstrates how to use the Flotilla framework from an external app.
"""

from __future__ import annotations

import asyncio
import sys
import uuid
import traceback
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from flotilla.config.resolvers.env_secret_resolver import EnvSecretResolver
from flotilla.config.sources.yaml_configuration_source import YamlConfigurationSource
from flotilla.config.sources.local_env_source import LocalEnvSource
from flotilla.utils.logger import get_logger
from flotilla.flotilla_bootstrap import FlotillaBootstrap
from flotilla.flotilla_application import FlotillaApplication
from flotilla.runtime.flotilla_runtime import FlotillaRuntime
from flotilla.thread.thread_service import ThreadService
from flotilla.runtime.runtime_request import RuntimeRequest
from flotilla.runtime.runtime_response import RuntimeResponse
from flotilla.runtime.content_part import ContentPart, TextPart, ContentPartType

from flotilla_langchain.llm.providers import openai_llm_provider
from flotilla.container.constants import REFLECTION_PROVIDER_KEY
from flotilla.container.providers.reflection_provider import ReflectionProvider
from app_agents.weather_agent_provider import weather_agent_provider

console = Console()
logger = get_logger(__name__)


# ------------------------------------------------------------
# Async helpers
# ------------------------------------------------------------
async def _run_query_async(
    runtime,
    *,
    query: str,
    thread_id: Optional[str] = RuntimeResponse,
):
    """
    Execute a single query against the runtime using the new public API.
    """

    # IMPORTANT: runtime.run() is async -> must await
    request: RuntimeRequest = RuntimeRequest(
        thread_id=thread_id, user_id="u1", content=[TextPart(id="query", text=query)]
    )
    return await runtime.run(request)


async def _interactive_loop_async(app: FlotillaApplication) -> None:
    """
    Single asyncio loop for the whole interactive session.
    """
    runtime = app.runtime
    thread_id = await app.thread_service.create_thread()

    console.print("[green]✓ Ready for queries[/green]")
    console.print(f"[dim]thread_id: {thread_id}[/dim]\n")

    while True:
        # rich Console.input is sync; that's OK inside an async function for a CLI
        user_query = console.input("[bold cyan]Query > [/bold cyan] ").strip()

        if user_query.lower() in ("exit", "quit"):
            console.print("\n[dim]Goodbye![/dim]")
            return

        if not user_query:
            continue

        try:
            with console.status("[bold green]Processing…[/bold green]"):
                response: RuntimeResponse = await _run_query_async(
                    runtime,
                    query=user_query,
                    thread_id=thread_id,
                )

            # RuntimeeResponse shape: List[ContentPart]
            # Keep this simple for now; print output if present.
            if response.content is not None:

                for part in response.content:
                    if part.type == ContentPartType.TEXT:
                        console.print(f"\n[bold green] ContentPart: {part.text}")
                    else:
                        console.print(f"\n[bold green] ContentPart: {part}")

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            console.print(f"[dim]{traceback.format_exc()}[/dim]")


# ------------------------------------------------------------
# CLI SETUP
# ------------------------------------------------------------
@click.group()
@click.option("--env", default="DEV", help="Environment to use (e.g., DEV, UAT, PROD)")
@click.pass_context
def cli(ctx, env: str):
    """Example App: Run queries through the Flotilla orchestration framework."""
    ctx.ensure_object(dict)

    # Load .env into environment
    # load_dotenv()

    # example_app/config directory
    base_dir = Path(__file__).resolve().parent
    config_dir = base_dir / "app_config"

    console.print(f"[green]Loading configuration from:[/green] {config_dir}")

    sources = [
        LocalEnvSource(),
        YamlConfigurationSource(config_dir=str(config_dir), env=env),
    ]
    secrets = [EnvSecretResolver()]

    providers = {
        "llm.openai": openai_llm_provider,
        REFLECTION_PROVIDER_KEY: ReflectionProvider(),
        "weather_agent_provider": weather_agent_provider,
    }

    app: FlotillaApplication = FlotillaBootstrap.run(
        FlotillaApplication, config_sources=sources, secret_resolvers=secrets, providers=providers
    )

    # Save app in ctx for commands
    ctx.obj["app"] = app


# ------------------------------------------------------------
# QUERY COMMAND
# ------------------------------------------------------------
@cli.command()
@click.argument("query")
@click.pass_context
def query(ctx, query: str):
    """Execute a natural language query through the runtime."""
    console.print(Panel.fit(f"[bold cyan]Query:[/bold cyan] {query}", border_style="cyan"))

    app: FlotillaApplication = ctx.obj["app"]
    runtime = app.runtime

    try:
        with console.status("[bold green]Executing query...[/bold green]"):
            result = asyncio.run(_run_query_async(runtime, query=query))

        if getattr(result, "output", None) is not None:
            console.print(f"\n[bold green]Output:[/bold green] {result.output}")
        else:
            console.print(f"\n[bold green]Result:[/bold green] {result}")

    except Exception as e:
        console.print(f"\n[red]✗ Query failed:[/red] {e}", style="bold red")
        logger.exception("Query execution failed")
        sys.exit(1)
    finally:
        app.shutdown()


# ------------------------------------------------------------
# TEST COMMAND
# ------------------------------------------------------------
@cli.command()
@click.pass_context
def test(ctx):
    """Runs simple framework sanity checks."""
    console.print(Panel.fit("[bold cyan]Testing System Components[/bold cyan]", border_style="cyan"))

    app: FlotillaApplication = ctx.obj["app"]

    try:
        runtime = app.runtime
        console.print("[green]✓[/green] Runtime initialized")

        # Keep this minimal because runtime internals may differ across implementations
        console.print(f"[green]✓[/green] Runtime type: {type(runtime).__name__}")

        # Optional: run a very simple query to prove end-to-end execution
        with console.status("[bold green]Executing smoke query...[/bold green]"):
            result = asyncio.run(_run_query_async(runtime, query="What is the weather in Chicago?"))

        console.print("[green]✓[/green] Smoke query executed")
        if getattr(result, "output", None) is not None:
            console.print(f"[dim]output: {result.output}[/dim]")

        console.print("\n[green]✓ All components tested successfully[/green]\n")

    except Exception as e:
        console.print(f"\n[red]✗ Test failed: {e}[/red]")
        logger.exception("System test failed")
        sys.exit(1)
    finally:
        app.shutdown()


# ------------------------------------------------------------
# INTERACTIVE MODE
# ------------------------------------------------------------
@cli.command()
@click.pass_context
def interactive(ctx):
    """Start an interactive REPL for issuing queries."""
    console.print(
        Panel.fit(
            "[bold cyan]Interactive Mode[/bold cyan]\nType 'exit' to quit.",
            border_style="cyan",
        )
    )

    app: FlotillaApplication = ctx.obj["app"]

    try:
        asyncio.run(_interactive_loop_async(app))
    except Exception as e:
        console.print(f"\n[red]✗ Failed to start interactive mode:[/red] {e}")
        logger.exception("Interactive mode failed")
        sys.exit(1)
    finally:
        app.shutdown()


# ------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------
if __name__ == "__main__":
    cli(obj={})
