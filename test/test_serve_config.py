"""Tests for dcs_bridge.serve.config — config loading and API key generation."""

from __future__ import annotations

from pathlib import Path

import yaml

from dcs_bridge.serve.config import ServeConfig, load_config


class TestLoadConfig:
    def test_defaults_when_no_file(self, tmp_path: Path) -> None:
        cfg = load_config(tmp_path / "missing.yaml")
        assert cfg.tcp_port == 7777
        assert cfg.http_port == 8080
        assert cfg.default_timeout == 10.0

    def test_api_key_generated_when_absent(self, tmp_path: Path) -> None:
        cfg = load_config(tmp_path / "cfg.yaml")
        assert len(cfg.api_key) > 0

    def test_api_key_persisted_on_first_run(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.yaml"
        cfg = load_config(p)
        assert p.exists()
        data = yaml.safe_load(p.read_text())
        assert data["api_key"] == cfg.api_key

    def test_existing_api_key_preserved(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.yaml"
        p.write_text(yaml.dump({"api_key": "my-secret-key"}))
        cfg = load_config(p)
        assert cfg.api_key == "my-secret-key"

    def test_overrides_applied(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.yaml"
        p.write_text(yaml.dump({"api_key": "k", "tcp_port": 9999, "default_timeout": 5.0}))
        cfg = load_config(p)
        assert cfg.tcp_port == 9999
        assert cfg.default_timeout == 5.0

    def test_two_loads_same_key(self, tmp_path: Path) -> None:
        p = tmp_path / "cfg.yaml"
        key1 = load_config(p).api_key
        key2 = load_config(p).api_key
        assert key1 == key2


class TestServeConfig:
    def test_stale_threshold_default(self) -> None:
        cfg = ServeConfig(api_key="k")
        assert cfg.stale_threshold == 15.0
