"""Configuration management for Cascade CLI."""

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_CONFIG = {
    "provider": "openai",
    "model": "gpt-4o",
    "api_key": "",
    "api_base": "",
    "max_tokens": 4096,
    "temperature": 0.7,
    "system_prompt": (
        "You are Cascade, a helpful AI coding assistant. "
        "You can read files, propose code changes, and suggest terminal commands. "
        "When proposing file edits, output the FULL file content inside a code block "
        "with the file path as the language specifier, like: ```python path/to/file.py. "
        "When suggesting commands, wrap them in ```bash blocks. Always be concise."
    ),
    "auto_confirm": False,
    "max_context_files": 20,
    "streaming": True,
    "profile": "default",
    "profiles": {},
}

# Pre-built profiles for common providers
PRESET_PROFILES = {
    "openai": {"provider": "openai", "model": "gpt-4o", "api_base": ""},
    "openai-cheap": {"provider": "openai", "model": "gpt-4o-mini", "api_base": ""},
    "anthropic": {"provider": "anthropic", "model": "claude-3-5-sonnet-20241022", "api_base": ""},
    "ollama": {"provider": "ollama", "model": "llama3.1", "api_base": "http://localhost:11434/v1"},
    "groq": {"provider": "groq", "model": "llama-3.1-70b-versatile", "api_base": ""},
}

CONFIG_DIR = Path.home() / ".config" / "cascade-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict[str, Any]:
    """Load configuration from file, profiles, and environment."""
    config = DEFAULT_CONFIG.copy()

    # Load from file
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                file_config = json.load(f)
                config.update(file_config)
        except (json.JSONDecodeError, IOError):
            pass

    # Apply active profile if set
    active_profile = config.get("profile", "default")
    profiles = config.get("profiles", {})
    if active_profile in profiles:
        config.update(profiles[active_profile])
    elif active_profile in PRESET_PROFILES:
        config.update(PRESET_PROFILES[active_profile])

    # Override with environment variables
    env_map = {
        "CASCADE_PROVIDER": "provider",
        "CASCADE_MODEL": "model",
        "CASCADE_API_KEY": "api_key",
        "CASCADE_API_BASE": "api_base",
        "CASCADE_MAX_TOKENS": "max_tokens",
        "CASCADE_TEMPERATURE": "temperature",
        "CASCADE_AUTO_CONFIRM": "auto_confirm",
    }

    for env_var, key in env_map.items():
        value = os.environ.get(env_var)
        if value is not None:
            if key in ("max_tokens",):
                config[key] = int(value)
            elif key in ("temperature",):
                config[key] = float(value)
            elif key in ("auto_confirm",):
                config[key] = value.lower() in ("true", "1", "yes")
            else:
                config[key] = value

    return config


def save_config(config: dict[str, Any]) -> None:
    """Save configuration to file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def list_profiles(config: dict[str, Any]) -> dict[str, Any]:
    """Return all available profiles."""
    profiles = dict(PRESET_PROFILES)
    profiles.update(config.get("profiles", {}))
    return profiles


def switch_profile(config: dict[str, Any], profile_name: str) -> bool:
    """Switch to a profile and save."""
    profiles = list_profiles(config)
    if profile_name not in profiles:
        return False
    config["profile"] = profile_name
    save_config(config)
    return True


def ensure_config() -> dict[str, Any]:
    """Ensure config exists and return it."""
    config = load_config()
    if not config.get("api_key"):
        print("No API key configured. Set CASCADE_API_KEY or run `cascade --setup`.")
    return config
