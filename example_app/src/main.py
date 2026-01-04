"""
Example Application Main Entry Point
Demonstrates how to use the Flotilla framework from an external app.
"""

import sys
import json
from pathlib import Path
import uuid

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from dotenv import load_dotenv

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

from flotilla.orchestration_engine import OrchestrationEngine

from flotilla.utils.logger import setup_logging, get_logger
from flotilla.config.sources.yaml_configuration_source import YamlConfigurationSource
from flotilla.config.resolvers.env_secret_resolver import EnvSecretResolver
from flotilla.flotilla_application import FlotillaApplication


from flotilla.llm.llm_builders import openai_llm_builder
from flotilla.core.builders.checkpoint_builders import memory_checkpointer_buidler
from flotilla.selectors.builders.agent_selector_builders import keyword_agent_selector_builder
from flotilla.agents.wiring.agent_contributor_group import AgentContributorGroup
from flotilla.tools.wiring.tool_contributor_group import ToolsContributorGroup
from flotilla.core.wiring.checkpoint_contributor import CheckpointContributor
from flotilla.selectors.wiring.keyword_agent_contributor import KeywordAgentSelectorContributor
from flotilla.core.wiring.orchestration_engine_contributor import OrchestrationEngineContributor



from app_agents.weather_agent_builder import weather_agent_buidler
from app_tools. weather_tools_builder import weather_tools_builder



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
    # load .env file into environment
    load_dotenv()

    # example_app/config directory
    base_dir = Path(__file__).resolve().parent
    config_dir = base_dir / "app_config"

    console.print(f"[green]Loading configuration from:[/green] {config_dir}")

    #settings = ConfigLoader.load(env=env, config_dir=str(config_dir))
    #ctx.obj["settings"] = settings

    # Initialize logging using example app or framework settings
    #setup_logging(settings.flotilla.LOG__LEVEL)


    # create the Flotilla Application with yaml config source
    sources = [YamlConfigurationSource(config_dir=str(config_dir), env=env)]
    secrets = [EnvSecretResolver()]

    app = FlotillaApplication(sources=sources, secrets=secrets)

    # register the wiring logic and application builders
    # TODO this needs to be moved to an application builder group
    app.register_builder("agents.weather_agent", weather_agent_buidler)
    app.register_builder("tools.weather_tools", weather_tools_builder)
    app.register_builder("llm.openai", openai_llm_builder)
    app.register_builder("checkpointer.memory", memory_checkpointer_buidler)
    app.register_builder("agent_selector.keyword", keyword_agent_selector_builder)

    app.register_contributor(ToolsContributorGroup())
    app.register_contributor(AgentContributorGroup())
    app.register_contributor(CheckpointContributor())
    app.register_contributor(KeywordAgentSelectorContributor())
    app.register_contributor(OrchestrationEngineContributor())

    app.start()

    # save the app in the ctx
    ctx.obj["app"] = app




# ------------------------------------------------------------
# QUERY COMMAND
# ------------------------------------------------------------
@cli.command()
@click.argument("query")
@click.pass_context
def query(ctx, query):
    """Execute a natural language query through the orchestration agent."""

    console.print(Panel.fit(
        f"[bold cyan]Query:[/bold cyan] {query}",
        border_style="cyan"
    ))

    try:
        app:FlotillaApplication = ctx.obj["app"]
        engine = app.orchestration_engine()

        with console.status("[bold green]Executing query...[/bold green]"):
            result = engine.execute(query)

        console.print(f"\n[bold green]Result:[/bold green] {result}")
        app.shutdown()

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

    console.print(Panel.fit(
        "[bold cyan]Testing System Components[/bold cyan]",
        border_style="cyan"
    ))

    try:
        app:FlotillaApplication = ctx.obj["app"]
        engine = app.orchestration_engine()

        console.print("[green]✓[/green] Orchestration agent initialized")

        console.print("Testing Tool Registry…")
        tool_names = engine.tool_registry.get_tool_names()
        if tool_names:
            console.print(f"Tools loaded: {', '.join(tool_names)}")
        else:
            console.print("[yellow]Warning: No tools loaded[/yellow]")

        console.print("Testing Agent Registry…")
        agent_names = engine.agent_registry.list_agent_names()
        if agent_names:
            console.print(f"Agents loaded: {', '.join(agent_names)}")
        else:
            console.print("[yellow]Warning: No agents loaded[/yellow]")

        console.print("\n[green]✓ All components tested successfully[/green]\n")
        app.shutdown()

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
    console.print(Panel.fit(
        "[bold cyan]Interactive Mode[/bold cyan]\nType 'exit' to quit.",
        border_style="cyan"
    ))

    try:
        app:FlotillaApplication = ctx.obj["app"]
        engine = app.orchestration_engine()

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
                    thread_id = uuid.uuid4()
                    context = {"configurable": {"thread_id": thread_id}}
                    result = engine.execute(query, context)

                console.print(f"\n[bold green]{result.message}[/bold green]\n")

            except Exception as e:
                stack = e.format_exc()
                console.print(f"[red]Error:[/red] {e}", stack)

        app.shutdown()

    except Exception as e:
        console.print(f"\n[red]✗ Failed to start interactive mode:[/red] {e}")
        logger.exception("Interactive mode failed")
        sys.exit(1)


# ------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------
if __name__ == "__main__":
    cli(obj={})
