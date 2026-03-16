"""Chat command for interactive REPL-style conversation with the model."""

import sys
from pathlib import Path

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from pyforge.llm import LLMProvider, LLMProviderError
from pyforge.config import get_config_dir

console = Console()

style = Style.from_dict({
    "prompt": "#00aa00 bold",
    "": "#ffffff",
})


SYSTEM_PROMPT = """You are an expert Python programming assistant. Help the user with:
- Writing and explaining Python code
- Debugging and troubleshooting
- Best practices and design patterns
- Code review and optimization
- Answering Python-related questions

Guidelines:
- Provide clear, concise explanations
- Include code examples when helpful
- Follow Python 3.10+ best practices
- Be friendly and professional
- If unsure, say so honestly"""


@click.command(name="chat")
@click.option(
    "--history/--no-history",
    default=True,
    help="Enable command history (default: enabled).",
)
@click.pass_context
def chat_command(ctx: click.Context, history: bool) -> None:
    """Start an interactive chat session with the AI.

    This opens a REPL-style interface where you can have a conversation
    with the AI model. Type 'exit' or 'quit' to exit.

    Examples:
        pyforge chat
        pyforge chat --no-history
    """
    from pyforge.cli import get_client as get_cli_client

    client: LLMProvider = get_cli_client(ctx)

    try:
        if not client.check_connection():
            console.print("[bold red]Error:[/bold red] Cannot connect to LLM service.")
            console.print("[dim]Please check your provider configuration in ~/.pyforge/config.yaml[/dim]")
            sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)

    if history:
        history_path = get_config_dir() / "chat_history"
        session = PromptSession(history=FileHistory(str(history_path)))
    else:
        session = PromptSession()

    provider_name = ctx.obj["config"].get("provider", "ollama")
    model_name = ctx.obj["config"]["model"]["name"]
    console.print(Panel(
        f"[bold green]Welcome to PyForge Chat![/bold green]\n\n"
        f"Provider: [cyan]{provider_name}[/cyan]\n"
        f"Model: [cyan]{model_name}[/cyan]\n"
        f"Type [yellow]exit[/yellow] or [yellow]quit[/yellow] to exit, "
        f"[yellow]clear[/yellow] to clear history.",
        title="PyForge Chat",
        border_style="green",
    ))
    console.print()

    chat_history: list[dict] = []

    while True:
        try:
            user_input = session.prompt(
                [("class:prompt", "You: ")],
                style=style,
            ).strip()

            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                console.print("[dim]Goodbye![/dim]")
                break

            if user_input.lower() == "clear":
                chat_history.clear()
                console.print("[dim]Chat history cleared.[/dim]")
                continue

            chat_history.append({"role": "user", "content": user_input})

            with console.status("[bold green]Thinking...[/bold green]"):
                try:
                    response = client.generate(
                        prompt=user_input,
                        system_prompt=SYSTEM_PROMPT,
                        stream=False,
                    )
                except LLMProviderError as e:
                    console.print(f"[bold red]Error:[/bold red] {e}")
                    continue

            console.print("[bold cyan]Assistant:[/bold cyan]")
            console.print(Markdown(response))
            console.print()

            chat_history.append({"role": "assistant", "content": response})

            if len(chat_history) > 20:
                chat_history = chat_history[-20:]

        except KeyboardInterrupt:
            console.print("\n[dim]Use 'exit' or 'quit' to exit.[/dim]")
            continue
        except (EOFError, ValueError):
            console.print("\n[dim]Goodbye![/dim]")
            break
