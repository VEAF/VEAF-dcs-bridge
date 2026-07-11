"""Tests for dcs_bridge.serve.security — roles, tokens, level resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from dcs_bridge.serve.security import (
    Role,
    Token,
    TokenStore,
    build_token_store,
    load_tokens,
    parse_veaf_pilots,
    resolve_role_from_ucid,
    role_allows,
    role_for_level,
    role_for_name,
    tokens_from_records,
)


class TestRole:
    def test_ordering(self) -> None:
        assert Role.OBSERVER < Role.PILOT < Role.OPERATOR < Role.ADMINISTRATOR < Role.SUPERUSER

    def test_role_for_name(self) -> None:
        assert role_for_name("Operator") is Role.OPERATOR

    def test_role_for_name_unknown_raises(self) -> None:
        with pytest.raises(ValueError):
            role_for_name("wizard")

    def test_role_for_level_exact(self) -> None:
        assert role_for_level(10) is Role.OPERATOR

    def test_role_for_level_between(self) -> None:
        assert role_for_level(50) is Role.OPERATOR  # highest <= 50
        assert role_for_level(95) is Role.ADMINISTRATOR
        assert role_for_level(100) is Role.SUPERUSER

    def test_role_for_level_below_floor(self) -> None:
        assert role_for_level(-5) is Role.OBSERVER

    def test_role_allows(self) -> None:
        assert role_allows(Role.OPERATOR, Role.PILOT)
        assert role_allows(Role.OPERATOR, Role.OPERATOR)
        assert not role_allows(Role.PILOT, Role.OPERATOR)


class TestTokenStore:
    def test_resolve_valid(self) -> None:
        store = TokenStore([Token(token="abc", role=Role.OPERATOR)])
        tok = store.resolve("abc", now=1000.0)
        assert tok is not None and tok.role is Role.OPERATOR

    def test_resolve_unknown_is_none(self) -> None:
        store = TokenStore([Token(token="abc", role=Role.OPERATOR)])
        assert store.resolve("nope", now=1000.0) is None

    def test_resolve_none_is_none(self) -> None:
        store = TokenStore([Token(token="abc", role=Role.OPERATOR)])
        assert store.resolve(None, now=1000.0) is None

    def test_expired_token_is_none(self) -> None:
        store = TokenStore([Token(token="abc", role=Role.OPERATOR, expiry=500.0)])
        assert store.resolve("abc", now=500.0) is None
        assert store.resolve("abc", now=499.0) is not None

    def test_build_store_includes_legacy_superuser(self) -> None:
        store = build_token_store(legacy_api_key="legacy-key")
        tok = store.resolve("legacy-key", now=1.0)
        assert tok is not None and tok.role is Role.SUPERUSER

    def test_build_store_empty_without_legacy(self) -> None:
        store = build_token_store()
        assert store.resolve("anything", now=1.0) is None


class TestTokenRecords:
    def test_tokens_from_records(self) -> None:
        toks = tokens_from_records([{"token": "t1", "role": "pilot", "label": "bob"}])
        assert toks[0].role is Role.PILOT
        assert toks[0].label == "bob"

    def test_records_skip_incomplete(self) -> None:
        assert tokens_from_records([{"token": "t1"}, {"role": "pilot"}]) == []

    def test_load_tokens_absent_file(self, tmp_path: Path) -> None:
        assert load_tokens(tmp_path / "nope.yaml") == []

    def test_load_tokens_from_yaml(self, tmp_path: Path) -> None:
        p = tmp_path / "dcs-tokens.yaml"
        p.write_text("- token: t1\n  role: administrator\n  label: admin\n", encoding="utf-8")
        toks = load_tokens(p)
        assert len(toks) == 1
        assert toks[0].role is Role.ADMINISTRATOR


class TestVeafPilots:
    def test_parse_various_separators(self) -> None:
        text = "# comment\naaa=10\nbbb, 90\nccc 1\n-- lua comment\nbad-line\n"
        pilots = parse_veaf_pilots(text)
        assert pilots == {"aaa": 10, "bbb": 90, "ccc": 1}

    def test_resolve_role_from_ucid(self) -> None:
        pilots = {"aaa": 10, "bbb": 90}
        assert resolve_role_from_ucid("aaa", pilots) is Role.OPERATOR
        assert resolve_role_from_ucid("bbb", pilots) is Role.ADMINISTRATOR

    def test_resolve_unknown_ucid_defaults_observer(self) -> None:
        assert resolve_role_from_ucid("zzz", {}) is Role.OBSERVER
