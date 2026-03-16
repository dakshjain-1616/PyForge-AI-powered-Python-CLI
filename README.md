# PyForge

AI-powered Python CLI tool for code generation, debugging, review, and chat.

> This project was built autonomously by **[NEO - Your Fully Autonomous AI Agent](https://heyneo.so)**

Supports two LLM backends:
- **Ollama** (local, free) — runs models on your machine, no data leaves your system
- **OpenRouter** (cloud) — access frontier models via API key

---

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Commands](#commands)
  - [generate](#generate)
  - [debug](#debug)
  - [review](#review)
  - [chat](#chat)
- [Providers](#providers)
  - [Ollama (local)](#ollama-local)
  - [OpenRouter (cloud)](#openrouter-cloud)
- [Configuration](#configuration)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

---

## Installation

```bash
git clone https://github.com/pyforge/pyforge
cd pyforge
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -e .
```

> **Note:** You must run `source venv/bin/activate` in every new terminal before using `pyforge`. Alternatively, install with `pipx install .` (requires `pipx`) to make `pyforge` available system-wide without activating a venv each time.

Then set up a provider (see [Providers](#providers) below).

---

## Quick Start

```bash
# Generate a Python function
pyforge generate "Create a function that validates an email address"

# Debug a broken script
pyforge debug script.py

# Debug with an error log
pyforge debug script.py --traceback error.log --apply

# Review code for security issues
pyforge review mymodule.py --focus security

# Interactive AI chat
pyforge chat
```

---

## Commands

### generate

Generate Python code from a natural language description.

```
pyforge generate PROMPT [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-o, --output FILE` | Save output to a file instead of printing to terminal |
| `-c, --context FILE` | Include a file as context (repeatable) |
| `-t, --temperature FLOAT` | Sampling temperature 0.0–1.0 (default: 0.7) |

**Examples:**

```bash
# Print generated code to terminal
pyforge generate "Create a binary search function with type hints"

# Save to file
pyforge generate "Build a FastAPI CRUD app for a todo list" -o todo_api.py

# Provide existing code as context
pyforge generate "Add input validation to this function" -c utils.py

# Multiple context files
pyforge generate "Write unit tests for these functions" -c models.py -c db.py -o test_models.py

# More deterministic output
pyforge generate "Implement quicksort" -t 0.2
```

**Sample output:**

```
╭─────────────────────────── Generated Code ────────────────────────────────╮
│   1 │ import re                                                            │
│   2 │ from typing import Optional                                          │
│   3 │                                                                      │
│   4 │ def validate_email(email: str) -> bool:                              │
│   5 │     """Validate an email address format.                             │
│   6 │                                                                      │
│   7 │     Args:                                                            │
│   8 │         email: The email string to validate.                         │
│   9 │                                                                      │
│  10 │     Returns:                                                         │
│  11 │         True if the format is valid, False otherwise.                │
│  12 │                                                                      │
│  13 │     Examples:                                                        │
│  14 │         >>> validate_email("user@example.com")                       │
│  15 │         True                                                         │
│  16 │         >>> validate_email("not-an-email")                           │
│  17 │         False                                                        │
│  18 │     """                                                              │
│  19 │     pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$' │
│  20 │     return bool(re.match(pattern, email.strip()))                    │
╰────────────────────────────────────────────────────────────────────────────╯
```

---

### debug

Analyze a Python file for bugs, explain root causes, and optionally apply the fix.

```
pyforge debug FILE [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-t, --traceback FILE` | Error log or traceback to include in the analysis |
| `-a, --apply` | Automatically write the fix back to the file |
| `--backup / --no-backup` | Create a `.bak` before overwriting (default: on) |

**Examples:**

```bash
# Analyze and print diagnosis
pyforge debug broken_script.py

# Provide an error log for more accurate analysis
pyforge debug app.py --traceback error.log

# Apply the fix automatically (creates backup first)
pyforge debug app.py --apply

# Apply fix, skip backup
pyforge debug app.py --apply --no-backup
```

**Typical workflow:**

```bash
# 1. Run script, capture error
python app.py 2> error.log

# 2. Let PyForge diagnose and fix
pyforge debug app.py --traceback error.log --apply
```

**Sample output:**

```
## Root Cause Analysis
The `divide` function does not guard against division by zero. When `b=0`
is passed, Python raises ZeroDivisionError at runtime.

## Fixed Code
def divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("Divisor cannot be zero")
    return a / b

## Changes Made
- Added a zero-check guard before the division operation
- Raises ValueError with a descriptive message rather than crashing

✓ Fix applied to broken_script.py
  Backup: broken_script_20240315_142301.py.bak
```

---

### review

Evaluate code for quality, security, and style issues.

```
pyforge review FILE [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-f, --focus AREA` | One of: `pep8`, `security`, `performance`, `style`, `all` (default: `all`) |
| `-o, --output FILE` | Save the review report as a Markdown file |

**Examples:**

```bash
# Full review (all categories)
pyforge review mymodule.py

# Security-focused review
pyforge review api_handlers.py --focus security

# Performance-focused review
pyforge review data_processor.py --focus performance

# Save report to file
pyforge review mymodule.py -o review_report.md
```

**Sample output:**

```
╭──────────────────────── Code Review: mymodule.py ─────────────────────────╮
│                                                                             │
│  ## Executive Summary                                                       │
│  Overall quality score: 6/10                                                │
│                                                                             │
│  ### Security — HIGH                                                        │
│  Line 14: os.system(user_input) — command injection risk                    │
│  Fix: Use subprocess.run([...], check=True) with validated arguments        │
│                                                                             │
│  ### PEP8 — LOW                                                             │
│  Line 3: Missing blank line after imports                                   │
│  Line 22: Line length 107 exceeds 100 characters                            │
│                                                                             │
│  ## Priority Action Items                                                   │
│  1. Replace os.system with subprocess (Critical security fix)               │
│  2. Add type hints to all public functions                                  │
│  3. Write docstrings for exported functions                                 │
╰─────────────────────────────────────────────────────────────────────────────╯
```

---

### chat

Start an interactive REPL-style conversation with the AI.

```
pyforge chat [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--history / --no-history` | Save/restore input history across sessions (default: on) |

**In-session commands:**

| Input | Action |
|-------|--------|
| `exit` / `quit` / `q` | End the session |
| `clear` | Reset conversation context |

**Examples:**

```bash
# Start a chat session
pyforge chat

# Without persistent history
pyforge chat --no-history
```

**Sample session:**

```
╭──────────────────────────── PyForge Chat ─────────────────────────────────╮
│ Welcome to PyForge Chat!                                                    │
│                                                                             │
│ Provider: ollama   Model: qwen3.5:latest                                    │
│ Type exit or quit to exit, clear to clear history.                          │
╰─────────────────────────────────────────────────────────────────────────────╯

You: What's the difference between a list and a tuple in Python?
Assistant: Lists are mutable (you can change them after creation), tuples are immutable.

  - Use lists for collections that may change: shopping_cart = ['apple', 'banana']
  - Use tuples for fixed data: coordinates = (51.5, -0.1)
  - Tuples are slightly faster and can be used as dict keys

You: exit
Goodbye!
```

---

## Providers

### Ollama (local)

Runs models entirely on your machine. No data leaves your system.

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start the service
ollama serve

# Pull a model (choose based on your hardware)
ollama pull qwen3.5:latest          # default, good balance
ollama pull qwen2.5-coder:7b        # ~4 GB, fast on most machines
ollama pull qwen2.5-coder:14b       # ~8 GB, better quality
ollama pull qwen2.5-coder:32b       # ~18 GB, best quality

# List downloaded models
ollama list
```

PyForge uses `qwen3.5:latest` by default. To use a different model:

```bash
pyforge --model qwen2.5-coder:14b generate "Write a web scraper"
```

Or set it permanently in `~/.pyforge/config.yaml`.

### OpenRouter (cloud)

Access hosted models (GPT-4, Claude, Gemini, etc.) via the OpenRouter API.

```bash
# 1. Get an API key at https://openrouter.ai
# 2. Set the environment variable
export OPENROUTER_API_KEY=sk-or-...

# Use OpenRouter with a specific model
pyforge --provider openrouter --model qwen/qwen-2.5-coder-32b-instruct generate "Write a parser"

# Or set as default in config
```

To make OpenRouter the default, update `~/.pyforge/config.yaml`:

```yaml
provider: openrouter
model:
  name: qwen/qwen-2.5-coder-32b-instruct
openrouter:
  api_key: sk-or-...  # or leave blank and use env var
```

---

## Configuration

Config is stored at `~/.pyforge/config.yaml` and created automatically on first run.

```yaml
# LLM provider: ollama (local) or openrouter (cloud)
provider: ollama

model:
  name: qwen3.5:latest          # model name
  host: http://localhost:11434  # Ollama host (ignored for openrouter)
  timeout: 120                  # request timeout in seconds
  temperature: 0.7              # creativity (0.0 = deterministic, 1.0 = creative)
  top_p: 0.9                    # nucleus sampling

openrouter:
  api_key: ""                    # or set OPENROUTER_API_KEY env var
  base_url: https://openrouter.ai/api/v1

workspace:
  dir: ~/pyforge-workspace      # all outputs auto-saved here
  auto_save: true               # set false to disable auto-saving

generation:
  max_tokens: 4096              # max output length

debug:
  backup_original: true         # create .bak before applying fixes

review:
  check_pep8: true
  check_security: true
  check_performance: true
  check_style: true
```

### Per-command overrides

Any config value can be overridden on the command line:

```bash
# Use a different model for one command
pyforge --model qwen2.5-coder:14b review app.py

# Use a different provider
pyforge --provider openrouter generate "Write a REST API"

# Point to a remote Ollama instance
pyforge --host http://192.168.1.10:11434 chat

# Use a custom config file
pyforge --config /path/to/my-config.yaml debug script.py
```

---

## Development

### Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest tests/ -v
```

Tests use mocked LLM providers so they run without Ollama or an API key.

### Code Style

```bash
black src/ tests/
flake8 src/ tests/
mypy src/
```

---

## Troubleshooting

### "Cannot connect to Ollama service"

```bash
# Check if Ollama is running
ollama list

# Start it if not
ollama serve
```

### "model not found" or "pull model manifest: file does not exist"

```bash
# Pull the model first
ollama pull qwen3.5:latest

# Or switch to a model you already have
ollama list
pyforge --model <model-name-from-list> generate "..."
```

### "OpenRouter API key not found"

```bash
export OPENROUTER_API_KEY=sk-or-...
```

Or add it to `~/.pyforge/config.yaml` under `openrouter.api_key`.

### Slow first response

Normal — Ollama loads the model into memory on the first request. Subsequent requests in the same session are faster.

### Output looks garbled (missing colors/boxes)

Use a terminal that supports Unicode and ANSI colors (most modern terminals do). If piping output to a file, use `--output` flags instead of shell redirection to get plain text.

---

## License

MIT License
> This project was built autonomously by **[NEO - Your Fully Autonomous AI Agent](https://heyneo.so)**