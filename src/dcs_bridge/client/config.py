"""Configuration loading for dcs-client."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from pydantic import BaseModel

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = Path("dcs-client.yaml")


class ClientConfig(BaseModel):
    """Runtime configuration for dcs-client.

    Loaded from dcs-client.yaml on startup.
    """

    host: str = "127.0.0.1"
    port: int = 8080
    api_key: str = ""


def load_config(path: Path = _DEFAULT_CONFIG_PATH) -> ClientConfig:
    """Load client config from YAML file.

    Args:
        path: Path to the YAML config file.

    Returns:
        A ClientConfig populated from the file, or defaults if the file is absent/invalid.
    """
    if not path.exists():
        return ClientConfig()

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        logger.warning("Failed to parse config YAML at %s: %s; using defaults.", path, exc)
        return ClientConfig()

    if not isinstance(raw, dict):
        logger.warning("Config YAML at %s must be a mapping; using defaults.", path)
        return ClientConfig()

    return ClientConfig(**raw)
