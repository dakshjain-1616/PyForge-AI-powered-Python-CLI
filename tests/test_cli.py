"""Test suite for PyForge CLI commands.

This module provides comprehensive test coverage for all CLI commands
using mocked LLM providers to ensure fast, reliable testing without
dependencies on external services.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

# Ensure src is in path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pyforge.llm import LLMProviderError


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a Click CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_provider() -> MagicMock:
    """Provide a mocked LLM provider."""
    mock = MagicMock()
    mock.check_connection.return_value = True
    mock.temperature = 0.7
    mock.top_p = 0.9
    return mock


def invoke_with_mock(cli_runner, mock_provider, args, input=None):
    """Helper to invoke CLI with mocked provider in context."""
    # Patch get_client at the source before importing cli
    # This ensures all imports of get_client get the mock
    with patch("pyforge.cli.get_client", return_value=mock_provider):
        from pyforge.cli import cli
        
        if input:
            result = cli_runner.invoke(cli, args, input=input)
        else:
            result = cli_runner.invoke(cli, args)
    return result


class TestGenerateCommand:
    """Test cases for the 'generate' command."""

    def test_generate_success(self, cli_runner: CliRunner, mock_provider: MagicMock) -> None:
        """Test successful code generation with mocked provider."""
        mock_provider.generate.return_value = '''
def hello_world():
    """Print hello world."""
    print("Hello, World!")
'''
        
        result = invoke_with_mock(cli_runner, mock_provider, ["generate", "Create a hello world function"])
        
        assert result.exit_code == 0
        mock_provider.generate.assert_called_once()

    def test_generate_with_output_file(self, cli_runner: CliRunner, mock_provider: MagicMock, tmp_path: Path) -> None:
        """Test code generation with output file redirection."""
        output_file = tmp_path / "generated.py"
        mock_provider.generate.return_value = "def test(): pass"
        
        result = invoke_with_mock(cli_runner, mock_provider, ["generate", "Create a test function", "-o", str(output_file)])
        
        assert result.exit_code == 0
        assert output_file.exists()


class TestDebugCommand:
    """Test cases for the 'debug' command."""

    def test_debug_success(self, cli_runner: CliRunner, mock_provider: MagicMock, tmp_path: Path) -> None:
        """Test successful debugging with mocked provider."""
        buggy_file = tmp_path / "buggy.py"
        buggy_file.write_text("def divide(a, b): return a / b")
        
        mock_provider.generate.return_value = '''
## Root Cause Analysis
The function lacks zero-division protection.

## Fixed Code
```/usr/bin/python3
def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
```
'''
        
        result = invoke_with_mock(cli_runner, mock_provider, ["debug", str(buggy_file)])
        
        assert result.exit_code == 0
        mock_provider.generate.assert_called_once()

    def test_debug_apply_fix(self, cli_runner: CliRunner, mock_provider: MagicMock, tmp_path: Path) -> None:
        """Test applying debug fix automatically."""
        buggy_file = tmp_path / "buggy.py"
        buggy_file.write_text("def bad(): pass")
        
        mock_provider.generate.return_value = '''
## Fixed Code
```/usr/bin/python3
def good():
    """Good function."""
    pass
```
'''
        
        result = invoke_with_mock(cli_runner, mock_provider, ["debug", str(buggy_file), "--apply"])
        
        assert result.exit_code == 0
        assert "Fix applied" in result.output


class TestReviewCommand:
    """Test cases for the 'review' command."""

    def test_review_success(self, cli_runner: CliRunner, mock_provider: MagicMock, tmp_path: Path) -> None:
        """Test successful code review with mocked provider."""
        code_file = tmp_path / "code.py"
        code_file.write_text("def hello(): print('hello')")
        
        mock_provider.generate.return_value = '''
## Executive Summary
Overall quality score: 7/10

### PEP8 Compliance
- Missing docstring
'''
        
        result = invoke_with_mock(cli_runner, mock_provider, ["review", str(code_file)])
        
        assert result.exit_code == 0
        mock_provider.generate.assert_called_once()

    def test_review_with_focus(self, cli_runner: CliRunner, mock_provider: MagicMock, tmp_path: Path) -> None:
        """Test code review with specific focus area."""
        code_file = tmp_path / "code.py"
        code_file.write_text("import os\nos.system('ls')")
        
        mock_provider.generate.return_value = "## Security Review\nNo issues found."
        
        result = invoke_with_mock(cli_runner, mock_provider, ["review", str(code_file), "--focus", "security"])
        
        assert result.exit_code == 0
        # Verify focus was included in prompt
        call_args = mock_provider.generate.call_args
        assert "Focus area: SECURITY" in call_args[1]["prompt"]


class TestChatCommand:
    """Test cases for the 'chat' command."""

    def test_chat_connection_check(self, cli_runner: CliRunner, mock_provider: MagicMock) -> None:
        """Test chat command connection check."""
        mock_provider.check_connection.return_value = True
        
        result = invoke_with_mock(cli_runner, mock_provider, ["chat", "--no-history"], input="exit\n")
        
        assert result.exit_code == 0
        mock_provider.check_connection.assert_called_once()

    def test_chat_connection_failure(self, cli_runner: CliRunner, mock_provider: MagicMock) -> None:
        """Test chat command handles connection failure."""
        mock_provider.check_connection.return_value = False
        
        result = invoke_with_mock(cli_runner, mock_provider, ["chat", "--no-history"])
        
        assert result.exit_code == 1
        assert "Cannot connect" in result.output or "Error" in result.output

    def test_chat_response_generation(self, cli_runner: CliRunner, mock_provider: MagicMock) -> None:
        """Test chat command generates and displays response."""
        mock_provider.check_connection.return_value = True
        mock_provider.generate.return_value = "Hello! How can I help you today?"

        inputs = iter(["What is Python?", "exit"])

        with patch("prompt_toolkit.PromptSession.prompt", side_effect=lambda *a, **kw: next(inputs)):
            result = invoke_with_mock(
                cli_runner, mock_provider,
                ["chat", "--no-history"],
            )

        assert result.exit_code == 0
        assert "Hello! How can I help you today?" in result.output


class TestLLMProviderErrorHandling:
    """Test cases for LLM provider error handling."""

    def test_ollama_provider_unreachable(self, cli_runner: CliRunner) -> None:
        """Smoke test: Verify LLMProviderError handling when Ollama is unreachable."""
        mock_provider = MagicMock()
        mock_provider.generate.side_effect = LLMProviderError(
            "Cannot connect to Ollama service. Please ensure Ollama is running (ollama serve)"
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def test(): pass")
            temp_file = f.name

        try:
            result = invoke_with_mock(cli_runner, mock_provider, ["review", temp_file])
            assert result.exit_code == 1
            assert "Error" in result.output or "Cannot connect" in result.output
        finally:
            Path(temp_file).unlink(missing_ok=True)

    def test_openrouter_provider_unreachable(self, cli_runner: CliRunner) -> None:
        """Smoke test: Verify LLMProviderError handling when OpenRouter is unreachable."""
        mock_provider = MagicMock()
        mock_provider.generate.side_effect = LLMProviderError(
            "Generation failed: Connection error"
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def test(): pass")
            temp_file = f.name

        try:
            result = invoke_with_mock(
                cli_runner, mock_provider,
                ["--provider", "openrouter", "review", temp_file]
            )
            assert result.exit_code == 1
            assert "Error" in result.output
        finally:
            Path(temp_file).unlink(missing_ok=True)

    def test_provider_error_exit_code(self, cli_runner: CliRunner) -> None:
        """Test that provider errors result in exit code 1."""
        mock_provider = MagicMock()
        mock_provider.generate.side_effect = LLMProviderError("Test error")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def test(): pass")
            temp_file = f.name

        try:
            result = invoke_with_mock(cli_runner, mock_provider, ["debug", temp_file])
            assert result.exit_code == 1
        finally:
            Path(temp_file).unlink(missing_ok=True)
