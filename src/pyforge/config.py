"""Configuration management for PyForge."""

import os
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG = {
    "provider": "ollama",  # Options: ollama, openrouter
    "model": {
        "name": "qwen3.5:latest",
        "host": "http://localhost:11434",
        "timeout": 120,
        "temperature": 0.7,
        "top_p": 0.9,
    },
    "openrouter": {
        "api_key": "",  # Set via OPENROUTER_API_KEY env var or config
        "base_url": "https://openrouter.ai/api/v1",
    },
    "output": {
        "format": "rich",
        "color_scheme": "default",
        "show_line_numbers": True,
    },
    "generation": {
        "include_type_hints": True,
        "include_docstrings": True,
        "include_examples": True,
        "max_tokens": 4096,
    },
    "debug": {
        "auto_apply": False,
        "backup_original": True,
        "explain_before_fix": True,
    },
    "review": {
        "check_pep8": True,
        "check_security": True,
        "check_performance": True,
        "check_style": True,
    },
}


def get_config_dir() -> Path:
    """Get the configuration directory path."""
    config_dir = Path.home() / ".pyforge"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_path() -> Path:
    """Get the configuration file path."""
    return get_config_dir() / "config.yaml"


def load_config() -> dict[str, Any]:
    """Load configuration from file or create default if not exists."""
    config_path = get_config_path()
    
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                user_config = yaml.safe_load(f)
            # Merge with defaults
            config = DEFAULT_CONFIG.copy()
            if user_config:
                _deep_update(config, user_config)
            return config
        except Exception as e:
            print(f"Warning: Failed to load config: {e}. Using defaults.")
            return DEFAULT_CONFIG.copy()
    else:
        # Create default config file
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()


def save_config(config: dict[str, Any]) -> None:
    """Save configuration to file."""
    config_path = get_config_path()
    try:
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    except Exception as e:
        print(f"Warning: Failed to save config: {e}")


def _deep_update(base: dict, update: dict) -> None:
    """Recursively update nested dictionaries."""
    for key, value in update.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_update(base[key], value)
        else:
            base[key] = value


def get_config_value(key_path: str, default: Any = None) -> Any:
    """Get a configuration value by dot-separated key path."""
    config = load_config()
    keys = key_path.split(".")
    value = config
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    return value