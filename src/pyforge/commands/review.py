"""Review command for evaluating Python code quality."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from pyforge.llm import LLMProvider, LLMProviderError

console = Console()


SYSTEM_PROMPT = """You are an expert Python code reviewer using a high-capability reasoning model. Perform a comprehensive, deep code review leveraging advanced reasoning capabilities:

1. **PEP8 Compliance**: Rigorous check of formatting, naming conventions (snake_case, PascalCase), line length (79/100 chars), import organization (stdlib, third-party, local), whitespace, indentation
2. **Security**: Deep security analysis including injection vulnerabilities (SQL, command, XPath), XSS, CSRF, unsafe eval/exec, hardcoded secrets/tokens, path traversal, deserialization risks, cryptographic issues, authentication/authorization flaws
3. **Performance**: Algorithmic complexity analysis (Big O), unnecessary computations, memory leaks, inefficient data structures, I/O bottlenecks, caching opportunities, lazy evaluation, generator usage, vectorization opportunities
4. **Code Style**: Readability, maintainability, documentation quality, type hint completeness (Python 3.10+ features), docstring standards (Google/NumPy style), comments quality, function/class design (SRP, cohesion)
5. **Best Practices**: Error handling (specific exceptions, custom exceptions), testing considerations (testability, edge cases), design patterns (appropriate usage), Pythonic idioms, async/await usage, context managers, immutability, functional programming opportunities
6. **Type Safety**: Comprehensive type hint analysis, use of generics, TypeVars, Protocols, overloads, Optional/Union usage, cast safety
7. **Architecture**: Module organization, dependency management, coupling/cohesion, API design, abstraction levels

For each issue found, provide:
- Severity: Critical/High/Medium/Low/Info
- Category: PEP8/Security/Performance/Style/BestPractice/TypeSafety/Architecture
- Line number(s) (if applicable)
- Detailed description of the issue with reasoning
- Specific, actionable fix with code example
- Reference to relevant PEP, Python docs, or security best practice (if applicable)

Format your response in Markdown with:
- Executive Summary (overall quality score and key findings)
- Detailed Findings by Category
- Priority Action Items
- Positive Highlights (what's done well)
- Summary Table of all issues"""


@click.command(name="review")
@click.argument("file", type=click.Path(exists=True, dir_okay=False), required=True)
@click.option(
    "--focus",
    "-f",
    type=click.Choice(["pep8", "security", "performance", "style", "all"]),
    default="all",
    help="Focus area for the review (default: all).",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file for the review report.",
)
@click.pass_context
def review_command(
    ctx: click.Context,
    file: str,
    focus: str,
    output: str | None,
) -> None:
    """Review Python code for quality, security, and style issues.

    FILE is the Python script to review.

    Examples:
        pyforge review myscript.py
        pyforge review myscript.py --focus security
        pyforge review myscript.py -o review_report.md
    """
    from pyforge.cli import get_client as get_cli_client
    from pyforge.config import get_workspace_dir
    from datetime import datetime

    client: LLMProvider = get_cli_client(ctx)
    cfg = ctx.obj["config"]

    file_path = Path(file)
    try:
        source_code = file_path.read_text(encoding="utf-8")
    except Exception as e:
        console.print(f"[bold red]Error reading file:[/bold red] {e}")
        sys.exit(1)

    prompt = _build_review_prompt(source_code, file_path.name, focus)

    try:
        with console.status(f"[bold green]Reviewing {file_path.name}...[/bold green]"):
            response = client.generate(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
                stream=False,
            )

        # Always display in terminal
        console.print(Panel(
            Markdown(response),
            title=f"Code Review: {file_path.name}",
            border_style="blue",
            padding=(1, 2),
        ))

        # Save to explicit output path if given
        if output:
            output_path = Path(output)
            output_path.write_text(response, encoding="utf-8")
            console.print(f"[bold green]Review saved to:[/bold green] {output_path.absolute()}")

        # Auto-save to workspace
        elif cfg.get("workspace", {}).get("auto_save", True):
            workspace = get_workspace_dir(cfg)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            stem = file_path.stem
            focus_tag = f"_{focus}" if focus != "all" else ""
            save_path = workspace / "reviews" / f"{timestamp}_{stem}{focus_tag}_review.md"
            save_path.write_text(response, encoding="utf-8")
            console.print(f"[dim]Auto-saved to: {save_path}[/dim]")

    except LLMProviderError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


def _build_review_prompt(source_code: str, filename: str, focus: str) -> str:
    parts = []

    parts.append(f"Please review the following Python file: {filename}")

    if focus != "all":
        parts.append(f"\nFocus area: {focus.upper()}")

    parts.append("\nSource code:")
    parts.append("```python")
    parts.append(source_code)
    parts.append("```")

    parts.append("\nPlease provide a comprehensive code review.")

    return "\n".join(parts)
