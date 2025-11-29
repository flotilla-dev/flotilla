"""
Example Application Main Entry Point
Demonstrates how to use the Flotilla framework from an external app.
"""

import sys
import json
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# ------------------------------------------------------------
# Add framework `/src` directory to sys.path
# ------------------------------------------------------------
current_file = Path(__file__).resolve()

# example_app/src/ → parent = example_app/
example_app_root = current_file.parent.parent

# project root = parent of example_app
project_root = example_app_root.parent

# framework src directory
framework_src = project_root / "src"

sys.path.insert(0, str(framework_src))

# ------------------------------------------------------------
# Now imports from framework work correctly
# ------------------------------------------------------------
from config.settings import Settings
from config.config_loader import ConfigLoader
from config.config_factory import ConfigFactory
from agents.orchestration_agent import OrchestrationAgent
from utils.logger import setup_logging, get_logger


console = Console()
logger = get_logger(__name__)


# ------------------------------------------------------------
# CLI SETUP
# ------------------------------------------------------------
@click.group()
@click.option('--env', default='DEV', help='Environment to use (e.g., DEV, UAT, PROD)')
@click.pass_context
def cli(ctx, env):
    """Example App: Run queries through the Flotilla orchestration framework."""

    ctx.ensure_object(dict)

    # example_app/config directory
    base_dir = Path(__file__).resolve().parent
    config_dir = base_dir / "config"

    console.print(f"[green]Loading configuration from:[/green] {config_dir}")

    settings = ConfigLoader.load(env=env, config_dir=str(config_dir))
    ctx.obj["settings"] = settings

    # Initialize logging using example app or framework settings
    setup_logging(settings.flotilla.LOG__LEVEL)


# ------------------------------------------------------------
# QUERY COMMAND
# ------------------------------------------------------------
@cli.command()
@click.argument("query")
@click.pass_context
def query(ctx, query):
    """Execute a natural language query through the orchestration agent."""
    settings = ctx.obj["settings"]

    console.print(Panel.fit(
        f"[bold cyan]Query:[/bold cyan] {query}",
        border_style="cyan"
    ))

    try:
        orchestration_config = ConfigFactory.create_orchestration_config(settings=settings)
        agent = OrchestrationAgent(orchestration_config)

        with console.status("[bold green]Executing query...[/bold green]"):
            result = agent.execute(query)

        console.print(f"\n[bold green]Result:[/bold green] {result}")
        agent.cleanup()

    except Exception as e:
        console.print(f"\n[red]✗ Query failed:[/red] {e}", style="bold red")
        logger.exception("Query execution failed")
        sys.exit(1)


# ------------------------------------------------------------
# TEST COMMAND
# ------------------------------------------------------------
@cli.command()
@click.pass_context
def test(ctx):
    """Runs simple framework sanity checks."""
    settings = ctx.obj["settings"]

    console.print(Panel.fit(
        "[bold cyan]Testing System Components[/bold cyan]",
        border_style="cyan"
    ))

    try:
        orchestration_config = ConfigFactory.create_orchestration_config(settings=settings)
        agent = OrchestrationAgent(orchestration_config)

        console.print("[green]✓[/green] Orchestration agent initialized")

        console.print("Testing Tool Registry…")
        tool_names = agent.tool_registry.get_tool_names()
        if tool_names:
            console.print(f"Tools loaded: {', '.join(tool_names)}")
        else:
            console.print("[yellow]Warning: No tools loaded[/yellow]")

        console.print("Testing Agent Registry…")
        agent_names = agent.business_registry.list_agent_names()
        if agent_names:
            console.print(f"Agents loaded: {', '.join(agent_names)}")
        else:
            console.print("[yellow]Warning: No agents loaded[/yellow]")

        console.print("\n[green]✓ All components tested successfully[/green]\n")
        agent.cleanup()

    except Exception as e:
        console.print(f"\n[red]✗ Test failed: {e}[/red]")
        logger.exception("System test failed")
        sys.exit(1)


# ------------------------------------------------------------
# INTERACTIVE MODE
# ------------------------------------------------------------
@cli.command()
@click.pass_context
def interactive(ctx):
    """Start an interactive REPL for issuing queries."""
    settings = ctx.obj["settings"]

    console.print(Panel.fit(
        "[bold cyan]Interactive Mode[/bold cyan]\nType 'exit' to quit.",
        border_style="cyan"
    ))

    try:
        orchestration_config = ConfigFactory.create_orchestration_config(settings=settings)
        agent = OrchestrationAgent(orchestration_config)

        console.print("[green]✓ Ready for queries[/green]\n")

        while True:
            query = console.input("[bold cyan]Query > [/bold cyan] ").strip()
            if query.lower() in ("exit", "quit"):
                console.print("\n[dim]Goodbye![/dim]")
                break

            if not query:
                continue

            try:
                with console.status("[bold green]Processing…[/bold green]"):
                    result = agent.execute(query)

                console.print(f"\n[bold green]{result}[/bold green]\n")

            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")

        agent.cleanup()

    except Exception as e:
        console.print(f"\n[red]✗ Failed to start interactive mode:[/red] {e}")
        logger.exception("Interactive mode failed")
        sys.exit(1)


# ------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------
if __name__ == "__main__":
    cli(obj={})
