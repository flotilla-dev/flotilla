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
from flotilla.core.agent_input import AgentInput
from flotilla.core.execution_config import ExecutionConfig
from flotilla.flotilla_application import FlotillaApplication
from flotilla.utils.logger import get_logger

# Framework + app builders
from flotilla.llm.llm_builders import openai_llm_builder
from flotilla.core.factories.checkpoint_builders import memory_checkpointer_buidler
from flotilla.selectors.builders.agent_selector_builders import (
    keyword_agent_selector_builder,
)
from flotilla.core.factories.single_agent_runtime_factory import (
    create_single_factory_runtime,
)

from app_agents.weather_agent_builder import weather_agent_buidler
from app_tools.weather_tools_builder import weather_tools_builder


console = Console()
logger = get_logger(__name__)


# ------------------------------------------------------------
# Async helpers
# ------------------------------------------------------------
async def _run_query_async(
    runtime,
    *,
    query: str,
    thread_id: Optional[str] = None,
):
    """
    Execute a single query against the runtime using the new public API.
    """
    agent_input = AgentInput(query=query, thread_id=thread_id)
    exec_config = ExecutionConfig(thread_id=thread_id)

    # IMPORTANT: runtime.run() is async -> must await
    return await runtime.run(agent_input=agent_input, execution_config=exec_config)


async def _interactive_loop_async(app: FlotillaApplication) -> None:
    """
    Single asyncio loop for the whole interactive session.
    """
    runtime = app.runtime
    thread_id = str(uuid.uuid4())

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
                result = await _run_query_async(
                    runtime,
                    query=user_query,
                    thread_id=thread_id,
                )

            # RuntimeResult shape: status/output/agent_name/checkpoint/metadata
            # Keep this simple for now; print output if present.
            if getattr(result, "output", None) is not None:
                console.print(f"\n[bold green]Output:[/bold green] {result.output}\n")
            else:
                console.print(f"\n[bold green]Result:[/bold green] {result}\n")

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
    load_dotenv()

    # example_app/config directory
    base_dir = Path(__file__).resolve().parent
    config_dir = base_dir / "app_config"

    console.print(f"[green]Loading configuration from:[/green] {config_dir}")

    sources = [
        LocalEnvSource(),
        YamlConfigurationSource(config_dir=str(config_dir), env=env),
    ]
    secrets = [EnvSecretResolver()]

    app = FlotillaApplication(sources=sources, secrets=secrets)

    # Register builders/factories (wiring logic)
    # TODO: move to an application builder group
    app.register_factory("agents.weather_agent", weather_agent_buidler)
    app.register_factory("tools.weather_tools", weather_tools_builder)
    app.register_factory("llm.openai", openai_llm_builder)
    app.register_factory("checkpointer.memory", memory_checkpointer_buidler)
    app.register_factory("agent_selector.keyword", keyword_agent_selector_builder)
    app.register_factory("runtime.single_agent", create_single_factory_runtime)

    app.start()

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
    console.print(
        Panel.fit(f"[bold cyan]Query:[/bold cyan] {query}", border_style="cyan")
    )

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
    console.print(
        Panel.fit(
            "[bold cyan]Testing System Components[/bold cyan]", border_style="cyan"
        )
    )

    app: FlotillaApplication = ctx.obj["app"]

    try:
        runtime = app.runtime
        console.print("[green]✓[/green] Runtime initialized")

        # Keep this minimal because runtime internals may differ across implementations
        console.print(f"[green]✓[/green] Runtime type: {type(runtime).__name__}")

        # Optional: run a very simple query to prove end-to-end execution
        with console.status("[bold green]Executing smoke query...[/bold green]"):
            result = asyncio.run(
                _run_query_async(runtime, query="What is the weather in Chicago?")
            )

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
