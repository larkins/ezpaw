"""Load configuration from config.yaml and .env files."""
import os
import re
from pathlib import Path

from dotenv import load_dotenv
import yaml

BASE_DIR = Path(__file__).parent.parent
CONFIG_PATH = BASE_DIR / "config.yaml"
ENV_PATH = BASE_DIR / ".env"

load_dotenv(ENV_PATH)


def _expand_env_vars(value):
    """Expand environment variables in a string value.

    Supports $VAR, ${VAR}, and ~ (already handled by Path).
    """
    if isinstance(value, str):
        return os.path.expandvars(value)
    elif isinstance(value, dict):
        return {k: _expand_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_expand_env_vars(v) for v in value]
    return value


def load_config():
    """Load configuration from config.yaml."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            raw = yaml.safe_load(f)
            return _expand_env_vars(raw)
    else:
        raise FileNotFoundError(
            f"config.yaml not found at {CONFIG_PATH}. "
            "Copy config.yaml.example to config.yaml and edit it."
        )


def get_database_config():
    """Get database configuration.

    Non-sensitive settings come from config.yaml.
    Password comes from .env (never hardcoded or in config.yaml).
    """
    config = load_config()
    db_config = config.get("database", {})

    # Password MUST come from .env — never put it in config.yaml
    db_config["password"] = os.getenv("DB_PASSWORD", "")

    return db_config


def get_app_config():
    """Get app configuration."""
    config = load_config()
    return config.get("app", {})


def get_gpaw_config():
    """Get GPAW configuration."""
    config = load_config()
    return config.get("gpaw", {})


def get_ezpaw_config():
    """Get ezpaw-specific configuration."""
    config = load_config()
    return config.get("ezpaw", {})


_config = None


def get_config():
    """Get cached configuration."""
    global _config
    if _config is None:
        _config = load_config()
    return _config
