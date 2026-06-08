"""Tests for dcs_bridge.client.config."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from dcs_bridge.client.config import ClientConfig, load_config


def test_load_config_defaults_when_file_absent(tmp_path: Path) -> None:
    cfg = load_config(tmp_path / "missing.yaml")
    assert cfg == ClientConfig()


def test_load_config_reads_values(tmp_path: Path) -> None:
    p = tmp_path / "dcs-client.yaml"
    p.write_text(yaml.dump({"host": "10.0.0.1", "port": 9090, "api_key": "secret"}))
    cfg = load_config(p)
    assert cfg.host == "10.0.0.1"
    assert cfg.port == 9090
    assert cfg.api_key == "secret"


def test_load_config_defaults_on_invalid_yaml(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text(":::invalid yaml:::")
    cfg = load_config(p)
    assert cfg == ClientConfig()


def test_load_config_defaults_on_non_mapping(tmp_path: Path) -> None:
    p = tmp_path / "list.yaml"
    p.write_text("- a\n- b\n")
    cfg = load_config(p)
    assert cfg == ClientConfig()
