"""Generate command for creating Python code from natural language."""

import re
import sys
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from pyforge.llm import LLMProvider, LLMProviderError

console = Console()


SYSTEM_PROMPT = """You are an expert Python developer using a high-capability reasoning model. Generate clean, production-ready Python code with exceptional quality.

Requirements:
1. Use Python 3.10+ syntax and features (match/case, walrus operator, type hinting improvements)
2. Include comprehensive type hints for all functions, variables, and class attributes using modern typing (ParamSpec, TypeVar, Generic)
3. Write detailed docstrings following Google style with Args, Returns, Raises, Examples, and Notes sections
4. Include comprehensive usage examples in docstrings demonstrating real-world scenarios
5. Follow PEP8 style guidelines rigorously (line length, imports, naming conventions)
6. Handle errors gracefully with appropriate exception handling, custom exceptions, and informative error messages
7. Use descriptive variable and function names following Python naming conventions
8. Add module-level docstrings explaining the module's purpose and usage
9. Include __all__ for public API definition
10. Add type stubs where appropriate for complex types
11. Consider performance implications and document complexity where relevant
12. Include unit test examples or doctest where applicable

Output ONLY the Python code without any markdown formatting or explanations."""


@click.command(name="generate")
@click.argument("prompt", required=True)
@click.option(
    "--context",
    "-c",
    type=click.Path(exists=True, dir_okay=False),
    multiple=True,
    help="Context file(s) to include in the prompt.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path. Overrides workspace auto-save location.",
)
@click.option(
    "--temperature",
    "-t",
    type=float,
    default=None,
    help="Temperature for generation (0.0-1.0, overrides config).",
)
@click.pass_context
def generate_command(
    ctx: click.Context,
    prompt: str,
    context: tuple[str, ...],
    output: str | None,
    temperature: float | None,
) -> None:
    """Generate Python code from natural language description.

    PROMPT is a natural language description of the code you want to generate.
    Output is always shown in the terminal and auto-saved to ~/pyforge-workspace/generated/.

    Examples:
        pyforge generate "Create a function to sort a list of dictionaries by a key"
        pyforge generate "Build a CLI tool with click that converts CSV to JSON"
        pyforge generate "Create a FastAPI endpoint for user authentication" -o auth.py
        pyforge generate "Create a decorator that logs function execution time" -c utils.py
    """
    from pyforge.cli import get_client as get_cli_client
    from pyforge.config import get_workspace_dir

    client: LLMProvider = get_cli_client(ctx)
    cfg = ctx.obj["config"]

    full_prompt = _build_prompt(prompt, context)

    if temperature is not None:
        client.temperature = temperature

    try:
        with console.status("[bold green]Generating code...[/bold green]"):
            response = client.generate(
                prompt=full_prompt,
                system_prompt=SYSTEM_PROMPT,
                stream=False,
            )

        code = _extract_code(response)

        # Always display in terminal
        syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title="Generated Code", border_style="green"))

        # Save to explicit output path if given
        if output:
            out = Path(output)
            out.write_text(code, encoding="utf-8")
            console.print(f"[bold green]Saved to:[/bold green] {out.absolute()}")

        # Auto-save to workspace
        elif cfg.get("workspace", {}).get("auto_save", True):
            workspace = get_workspace_dir(cfg)
            filename = _prompt_to_filename(prompt)
            save_path = workspace / "generated" / filename
            save_path.write_text(code, encoding="utf-8")
            console.print(f"[dim]Auto-saved to: {save_path}[/dim]")

    except LLMProviderError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


def _prompt_to_filename(prompt: str) -> str:
    """Turn a prompt string into a safe, readable filename."""
    slug = re.sub(r"[^a-z0-9]+", "_", prompt.lower())[:40].strip("_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_{slug}.py"


def _build_prompt(user_prompt: str, context_files: tuple[str, ...]) -> str:
    parts = []

    if context_files:
        parts.append("Context files:")
        for ctx_file in context_files:
            try:
                content = Path(ctx_file).read_text(encoding="utf-8")
                parts.append(f"\n--- {ctx_file} ---")
                parts.append(content)
                parts.append("--- end ---\n")
            except Exception as e:
                parts.append(f"\n[Error reading {ctx_file}: {e}]\n")

    parts.append("\nGenerate Python code for:")
    parts.append(user_prompt)

    return "\n".join(parts)


def _extract_code(response: str) -> str:
    code = response.strip()

    if code.startswith("```python"):
        code = code[9:]
    elif code.startswith("```"):
        code = code[3:]

    if code.endswith("```"):
        code = code[:-3]

    return code.strip()
