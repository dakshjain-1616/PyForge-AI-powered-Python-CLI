"""Modular LLM Provider interface for PyForge.

This module provides an abstraction layer over different LLM backends,
supporting both Ollama and OpenRouter providers.
"""

import os
import sys
from abc import ABC, abstractmethod
from typing import Any, Iterator

from rich.console import Console

console = Console()


class LLMProviderError(Exception):
    """Custom exception for LLM provider errors."""
    pass


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(
        self,
        model: str,
        temperature: float = 0.7,
        top_p: float = 0.9,
        timeout: int = 120,
        **kwargs: Any,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.timeout = timeout
        self.extra_params = kwargs

    @abstractmethod
    def check_connection(self) -> bool:
        pass

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        stream: bool = False,
    ) -> str | Iterator[str]:
        pass


class OllamaProvider(LLMProvider):
    """Provider implementation for Ollama (local models)."""

    def __init__(
        self,
        model: str | None = None,
        host: str | None = None,
        **kwargs: Any,
    ) -> None:
        try:
            import ollama
        except ImportError:
            raise LLMProviderError(
                "Ollama SDK not installed. Install with: pip install ollama"
            )

        from pyforge.config import get_config_value

        model = model or get_config_value("model.name", "qwen2.5-coder:7b")
        host = host or get_config_value("model.host", "http://localhost:11434")

        super().__init__(model=model, **kwargs)

        self.host = host

        try:
            self.client = ollama.Client(host=self.host)
        except Exception as e:
            raise LLMProviderError(f"Failed to initialize Ollama client: {e}")

    def check_connection(self) -> bool:
        try:
            self.client.list()
            return True
        except Exception:
            return False

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        stream: bool = False,
    ) -> str | Iterator[str]:
        if not self.check_connection():
            raise LLMProviderError(
                "Cannot connect to Ollama service. "
                "Please ensure Ollama is running (ollama serve)"
            )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            if stream:
                return self._stream_response(messages)
            else:
                response = self.client.chat(
                    model=self.model,
                    messages=messages,
                    options={
                        "temperature": self.temperature,
                        "top_p": self.top_p,
                    },
                )
                return response["message"]["content"]
        except Exception as e:
            raise LLMProviderError(f"Generation failed: {e}")

    def _stream_response(self, messages: list[dict]) -> Iterator[str]:
        try:
            stream = self.client.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                },
                stream=True,
            )
            for chunk in stream:
                content = chunk.get("message", {}).get("content", "")
                if content:
                    yield content
        except Exception as e:
            raise LLMProviderError(f"Streaming failed: {e}")


class OpenRouterProvider(LLMProvider):
    """Provider implementation for OpenRouter (cloud models via OpenAI-compatible API)."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str = "https://openrouter.ai/api/v1",
        **kwargs: Any,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError:
            raise LLMProviderError(
                "OpenAI SDK not installed. Install with: pip install openai"
            )

        from pyforge.config import get_config_value

        model = model or get_config_value("model.name", "qwen/qwen-2.5-coder-32b-instruct")
        api_key = api_key or os.environ.get("OPENROUTER_API_KEY")

        if not api_key:
            raise LLMProviderError(
                "OpenRouter API key not found. Set OPENROUTER_API_KEY environment variable "
                "or provide it in the config."
            )

        super().__init__(model=model, **kwargs)

        self.base_url = base_url
        self.api_key = api_key

        try:
            self.client = OpenAI(
                base_url=base_url,
                api_key=api_key,
            )
        except Exception as e:
            raise LLMProviderError(f"Failed to initialize OpenRouter client: {e}")

    def check_connection(self) -> bool:
        try:
            self.client.models.list()
            return True
        except Exception:
            return False

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        stream: bool = False,
    ) -> str | Iterator[str]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            if stream:
                return self._stream_response(messages)
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    top_p=self.top_p,
                    timeout=self.timeout,
                    max_tokens=self.extra_params.get("max_tokens", 4096),
                )
                return response.choices[0].message.content
        except Exception as e:
            raise LLMProviderError(f"Generation failed: {e}")

    def _stream_response(self, messages: list[dict]) -> Iterator[str]:
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                top_p=self.top_p,
                timeout=self.timeout,
                max_tokens=self.extra_params.get("max_tokens", 4096),
                stream=True,
            )
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as e:
            raise LLMProviderError(f"Streaming failed: {e}")


def create_provider(
    provider_type: str | None = None,
    model: str | None = None,
    **kwargs: Any,
) -> LLMProvider:
    """Factory function to create the appropriate LLM provider."""
    from pyforge.config import get_config_value

    provider_type = provider_type or get_config_value("provider", "ollama")

    if provider_type == "ollama":
        return OllamaProvider(model=model, **kwargs)
    elif provider_type == "openrouter":
        return OpenRouterProvider(model=model, **kwargs)
    else:
        raise LLMProviderError(f"Unknown provider type: {provider_type}")


def get_client(ctx: Any = None) -> LLMProvider:
    """Get a configured LLM provider instance."""
    if ctx is not None and hasattr(ctx, 'obj') and ctx.obj and ctx.obj.get('client'):
        return ctx.obj['client']
    return create_provider()


def handle_llm_error(error: LLMProviderError) -> None:
    """Handle LLM provider errors with user-friendly messages."""
    console.print(f"[bold red]Error:[/bold red] {error}")
    console.print("\n[dim]Troubleshooting tips:[/dim]")
    console.print("  • Check your configuration: [cyan]~/.pyforge/config.yaml[/cyan]")
    console.print("  • Verify provider settings (ollama/openrouter)")
    console.print("  • For Ollama: ensure service is running: [cyan]ollama serve[/cyan]")
    console.print("  • For OpenRouter: check OPENROUTER_API_KEY is set")
    sys.exit(1)
