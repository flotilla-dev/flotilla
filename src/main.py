"""
Main entry point for the Orchestration Agent System
"""
import sys
import json
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

from config.settings import Settings
from config.config_loader import ConfigLoader
from config.config_factory import ConfigFactory
from config.config_models import OrchestrationConfig
from agents.orchestration_agent import OrchestrationAgent
from utils.logger import setup_logging, get_logger


console = Console()
logger = get_logger(__name__)


@click.group()
@click.option('--env', default='DEV', help='Environment to use')
@click.pass_context
def cli(ctx, env):
    """Orchestration Agent CLI - Coordinate data agents, decisioning, and POS operations"""
    ctx.ensure_object(dict)
    settings = ConfigLoader.load(env=env)
    ctx.obj['settings'] = settings
    setup_logging(settings.flotilla.LOG__LEVEL)



@cli.command()
@click.argument('query')
@click.pass_context
def query(ctx, query):
    """Execute a natural language query"""
    settings = ctx.obj['settings']
    
    console.print(Panel.fit(
        f"[bold cyan]Query:[/bold cyan] {query}",
        border_style="cyan"
    ))
    
    try:
        # Initialize orchestration agent
        orchestration_config = ConfigFactory.create_orchestration_config(settings=settings)
        agent = OrchestrationAgent(orchestration_config)
        
        # Execute query
        with console.status("[bold green]Executing query..."):
            result = agent.execute(query)
        
        console.print(f"Result: {result}")
        # Display results
        '''
        if result['success']:
            console.print(Panel(
                result['result'],
                title="[bold green]Result[/bold green]",
                border_style="green"
            ))
        else:
            console.print(Panel(
                f"[red]Error:[/red] {result.get('error', 'Unknown error')}",
                title="[bold red]Error[/bold red]",
                border_style="red"
            ))
        '''
        # Cleanup
        agent.cleanup()
        
    except Exception as e:
        console.print(f"\n[red]✗[/red] Query failed: {e}", style="bold red")
        logger.exception("Query execution failed")
        sys.exit(1)



@cli.command()
@click.pass_context
def test(ctx):
    """Test the orchestration system components"""
    settings = ctx.obj['settings']
    
    console.print(Panel.fit(
        "[bold cyan]Testing Orchestration System[/bold cyan]",
        border_style="cyan"
    ))
    
    try:

        # Initialize orchestration agent
        orchestration_config = ConfigFactory.create_orchestration_config(settings=settings)
        agent = OrchestrationAgent(orchestration_config)
        console.print(f"[green]✓[/green] Orchestration agent initialized\n")
        
        # Test tools
        console.print("Testing Tool Registry...")
        tool_names = agent.tool_registry.get_tool_names()
        if (len(tool_names)) > 0:
            console.print(f"Tools loaded: {', '.join(tool_names)} ")
        else:
            console.print("Warning:  No tools loaded")

        # Test Agents
        console.print("Testing Agent Registry...")
        agent_names = agent.business_registry.list_agent_names()
        if (len(agent_names)) > 0:
            console.print(f"Agents loaded: {', '.join(agent_names)}")
        else:
            console.print("Warning: No agents loaded")
        
        console.print("\n[green]✓[/green] All components tested")
        
        # Cleanup
        agent.cleanup()
        
    except Exception as e:
        console.print(f"\n[red]✗[/red] Test failed: {e}", style="bold red")
        logger.exception("System test failed")
        sys.exit(1)


@cli.command()
@click.pass_context
def info(ctx):
    """Display system information"""
    settings = ctx.obj['settings']
    
    console.print(Panel.fit(
        "[bold cyan]Orchestration Agent System Information[/bold cyan]",
        border_style="cyan"
    ))
    
    table = Table(show_header=False, box=None)
    table.add_column("Property", style="cyan")
    table.add_column("Value")
    
    
    # Check if config files exist
    
    console.print(table)
    




@cli.command()
@click.pass_context
def interactive(ctx):
    """Start interactive mode"""
    settings = ctx.obj['settings']
    
    console.print(Panel.fit(
        "[bold cyan]Interactive Mode[/bold cyan]\nType 'exit' or 'quit' to end session",
        border_style="cyan"
    ))
    
    try:       
        #console.print(f"\n[dim]Client: {config.client.client_name}[/dim]")
        console.print(f"[dim]Initializing agent...[/dim]\n")
        
        # Initialize orchestration agent
        orchestration_config = ConfigFactory.create_orchestration_config(settings=settings)
        agent = OrchestrationAgent(orchestration_config)

        console.print("[green]✓[/green] Ready for queries\n")
        
        # Interactive loop
        while True:
            try:
                query = console.input("[bold cyan]Query >[/bold cyan] ")
                
                if query.lower() in ['exit', 'quit', 'q']:
                    console.print("\n[dim]Goodbye![/dim]")
                    break
                
                if not query.strip():
                    continue
                
                # Execute query
                with console.status("[bold green]Processing..."):
                    result = agent.execute(query)
                
                # Display result
                if result['success']:
                    console.print(f"\n[green]{result['result']}[/green]\n")
                else:
                    console.print(f"\n[red]Error: {result.get('error')}[/red]\n")
                    
            except KeyboardInterrupt:
                console.print("\n\n[dim]Interrupted. Goodbye![/dim]")
                break
            except Exception as e:
                console.print(f"\n[red]Error: {e}[/red]\n")
        
        # Cleanup
        agent.cleanup()
        
    except Exception as e:
        console.print(f"\n[red]✗[/red] Failed to start interactive mode: {e}", style="bold red")
        logger.exception("Interactive mode failed")
        sys.exit(1)


if __name__ == '__main__':
    cli(obj={})