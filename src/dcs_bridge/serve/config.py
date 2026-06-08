"""Configuration loading and persistence for dcs-serve."""

from __future__ import annotations

import logging
import secrets
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = Path("dcs-serve.yaml")


class ServeConfig(BaseModel):
    """Runtime configuration for dcs-serve.

    Loaded from dcs-serve.yaml on startup. An API key is generated and
    persisted automatically if absent.
    """

    tcp_host: str = "127.0.0.1"
    tcp_port: int = 7777
    http_host: str = "0.0.0.0"
    http_port: int = 8080
    api_key: str = Field(default="")
    default_timeout: float = 10.0
    stale_threshold: float = 15.0


def load_config(path: Path = _DEFAULT_CONFIG_PATH) -> ServeConfig:
    """Load config from YAML file, generating an API key if absent.

    Args:
        path: Path to the YAML config file. Created if it does not exist.

    Returns:
        A fully populated ServeConfig with a valid api_key.
    """
    if path.exists():
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            logger.warning("Failed to parse config YAML at %s: %s; using defaults.", path, exc)
            raw = {}
        if not isinstance(raw, dict):
            logger.warning("Config YAML at %s must be a mapping, got %s; using defaults.", path, type(raw).__name__)
            raw = {}
        cfg = ServeConfig(**raw)
    else:
        cfg = ServeConfig()

    if not cfg.api_key:
        cfg = cfg.model_copy(update={"api_key": secrets.token_urlsafe(32)})
        _persist_config(cfg, path)
        logger.info("Generated new API key — saved to %s", path)

    return cfg


def _persist_config(cfg: ServeConfig, path: Path) -> None:
    """Write config to YAML file.

    Args:
        cfg: Config to write.
        path: Destination file path.
    """
    path.write_text(yaml.dump(cfg.model_dump(), default_flow_style=False), encoding="utf-8")
