"""Main CLI entry point for PyForge."""

import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from pyforge.config import load_config
from pyforge.llm import create_provider, LLMProviderError, handle_llm_error
from pyforge.commands.generate import generate_command
from pyforge.commands.debug import debug_command
from pyforge.commands.review import review_command
from pyforge.commands.chat import chat_command

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="pyforge")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to custom configuration file.",
)
@click.option(
    "--model",
    "-m",
    help="Model name to use (overrides config).",
)
@click.option(
    "--provider",
    "-p",
    type=click.Choice(["ollama", "openrouter"]),
    help="LLM provider to use (overrides config).",
)
@click.option(
    "--host",
    "-h",
    help="Ollama host URL (overrides config, Ollama only).",
)
@click.pass_context
def cli(
    ctx: click.Context,
    config: str | None,
    model: str | None,
    provider: str | None,
    host: str | None,
) -> None:
    """PyForge - AI-powered Python CLI tool for code generation, debugging, review, and chat.
    
    Supports multiple LLM backends: Ollama (local) and OpenRouter (cloud).
    
    Examples:
        pyforge generate "Create a function to sort a list of dicts by key"
        pyforge debug myscript.py --traceback traceback.txt
        pyforge review mycode.py
        pyforge chat
        
        # Using OpenRouter
        pyforge --provider openrouter --model qwen/qwen-2.5-coder-32b-instruct generate "Hello"
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Load configuration
    cfg = load_config()
    
    # Apply CLI overrides
    if model:
        cfg["model"]["name"] = model
    if provider:
        cfg["provider"] = provider
    if host:
        cfg["model"]["host"] = host
    
    # Store in context
    ctx.obj["config"] = cfg
    ctx.obj["client"] = None  # Lazy initialization


def get_client(ctx: click.Context) -> Any:
    """Get or create LLM client from context.
    
    Args:
        ctx: Click context object.
        
    Returns:
        Configured LLM provider instance.
    """
    if ctx.obj["client"] is None:
        cfg = ctx.obj["config"]
        try:
            provider_type = cfg.get("provider", "ollama")
            
            # Build kwargs based on provider type
            kwargs = {
                "temperature": cfg["model"].get("temperature", 0.7),
                "top_p": cfg["model"].get("top_p", 0.9),
                "timeout": cfg["model"].get("timeout", 120),
            }
            
            if provider_type == "ollama":
                kwargs["host"] = cfg["model"].get("host", "http://localhost:11434")
            elif provider_type == "openrouter":
                kwargs["api_key"] = cfg["openrouter"].get("api_key", "")
                kwargs["base_url"] = cfg["openrouter"].get(
                    "base_url", "https://openrouter.ai/api/v1"
                )
            
            ctx.obj["client"] = create_provider(
                provider_type=provider_type,
                model=cfg["model"]["name"],
                **kwargs,
            )
        except LLMProviderError as e:
            handle_llm_error(e)
    return ctx.obj["client"]


# Register commands
cli.add_command(generate_command)
cli.add_command(debug_command)
cli.add_command(review_command)
cli.add_command(chat_command)


def main() -> None:
    """Main entry point."""
    try:
        cli()
    except LLMProviderError as e:
        handle_llm_error(e)
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
