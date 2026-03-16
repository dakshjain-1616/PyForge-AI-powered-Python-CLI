"""Debug command for analyzing and fixing Python code."""

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.markdown import Markdown

from pyforge.llm import LLMProvider, LLMProviderError

console = Console()


SYSTEM_PROMPT = """You are an expert Python debugger using a high-capability reasoning model. Analyze the provided code and/or traceback with deep reasoning to:

1. Identify the root cause of the issue with precise technical analysis
2. Explain the problem clearly, including the underlying mechanism causing the bug
3. Provide a fixed version of the code that addresses the root cause, not just symptoms
4. Explain what was changed, why it fixes the issue, and how it prevents recurrence

Follow these guidelines:
- Perform deep root cause analysis (trace through execution flow, identify assumptions)
- Consider edge cases, race conditions, and type safety issues
- Provide the complete fixed code with comprehensive error handling
- Include detailed comments explaining key changes and reasoning
- Follow Python 3.10+ best practices (type hints, modern syntax, proper exception handling)
- Ensure the fix is robust and handles all edge cases
- Consider performance implications of the fix

Format your response as:

## Root Cause Analysis
[Deep technical analysis of the problem, including:
- What exactly is failing
- Why it's failing (underlying mechanism)
- What assumptions were violated
- How the error propagates]

## Solution Strategy
[Explanation of the fix approach:
- Why this approach was chosen
- Alternative approaches considered
- Trade-offs made]

## Fixed Code
```python
[Complete fixed code with comprehensive error handling and comments]
```

## Changes Made
- [Detailed list of specific changes with rationale]
- [Include type safety improvements]
- [Include error handling additions]
- [Include edge case handling]"""


@click.command(name="debug")
@click.argument("file", type=click.Path(exists=True, dir_okay=False), required=True)
@click.option(
    "--traceback",
    "-t",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to a file containing the traceback/error message.",
)
@click.option(
    "--apply",
    "-a",
    is_flag=True,
    help="Apply the suggested fix automatically.",
)
@click.option(
    "--backup/--no-backup",
    default=True,
    help="Create a backup of the original file before applying fix.",
)
@click.pass_context
def debug_command(
    ctx: click.Context,
    file: str,
    traceback: str | None,
    apply: bool,
    backup: bool,
) -> None:
    """Debug Python code and suggest fixes.

    FILE is the Python script to analyze.

    Examples:
        pyforge debug myscript.py
        pyforge debug myscript.py --traceback error.txt
        pyforge debug myscript.py --apply --backup
    """
    from pyforge.cli import get_client as get_cli_client

    client: LLMProvider = get_cli_client(ctx)

    file_path = Path(file)
    try:
        source_code = file_path.read_text(encoding="utf-8")
    except Exception as e:
        console.print(f"[bold red]Error reading file:[/bold red] {e}")
        sys.exit(1)

    traceback_text = None
    if traceback:
        try:
            traceback_text = Path(traceback).read_text(encoding="utf-8")
        except Exception as e:
            console.print(f"[bold red]Error reading traceback:[/bold red] {e}")
            sys.exit(1)

    prompt = _build_debug_prompt(source_code, file_path.name, traceback_text)

    try:
        console.print("[dim]Analyzing code...[/dim]\n")

        response = client.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            stream=False,
        )

        console.print(Markdown(response))
        console.print()

        fixed_code = _extract_fixed_code(response)

        if fixed_code and fixed_code != source_code.strip():
            if apply:
                _apply_fix(file_path, fixed_code, backup)
            else:
                console.print("[dim]Use --apply to automatically apply the fix.[/dim]")
        elif fixed_code == source_code.strip():
            console.print("[green]No changes needed - code appears to be correct.[/green]")
        else:
            console.print("[yellow]Could not extract fixed code from response.[/yellow]")

    except LLMProviderError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


def _build_debug_prompt(source_code: str, filename: str, traceback: str | None) -> str:
    parts = []

    parts.append(f"File: {filename}")
    parts.append("\nSource code:")
    parts.append("```python")
    parts.append(source_code)
    parts.append("```")

    if traceback:
        parts.append("\nTraceback/Error:")
        parts.append("```")
        parts.append(traceback)
        parts.append("```")

    parts.append("\nPlease analyze this code, identify any issues, and provide a fix.")

    return "\n".join(parts)


def _extract_fixed_code(response: str) -> str | None:
    patterns = [
        r"## Fixed Code\s*```python\s*(.*?)\s*```",
        r"## Fixed Code\s*```\s*(.*?)\s*```",
        r"```python\s*(.*?)\s*```",
        r"```\s*(.*?)\s*```",
    ]

    for pattern in patterns:
        match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return None


def _apply_fix(file_path: Path, fixed_code: str, backup: bool) -> None:
    if backup:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = file_path.parent / f"{file_path.stem}_{timestamp}{file_path.suffix}.bak"
        shutil.copy2(file_path, backup_path)
        console.print(f"[dim]Backup created: {backup_path}[/dim]")

    file_path.write_text(fixed_code, encoding="utf-8")
    console.print(f"[bold green]Fix applied to {file_path}[/bold green]")
