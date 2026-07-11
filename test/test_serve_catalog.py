"""Tests for dcs_bridge.serve.catalog — capability-filtered catalogue + search."""

from __future__ import annotations

import pytest

from dcs_bridge.serve.capabilities import CapabilityState
from dcs_bridge.serve.catalog import build_catalog, describe, search_catalog


@pytest.fixture()
def caps_dcs() -> CapabilityState:
    state = CapabilityState({"dcs": None, "mist": "4.5.126", "ctld": "2.0", "veaf": "6"})
    state.update({})  # DCS present, nothing else
    return state


class TestBuildCatalog:
    def test_empty_before_handshake(self) -> None:
        # No update() called → nothing present → empty catalogue.
        assert build_catalog(CapabilityState()) == []

    def test_includes_dcs_actions(self, caps_dcs: CapabilityState) -> None:
        names = {info.name for info in build_catalog(caps_dcs)}
        assert {"spawn", "smoke", "remove"} <= names

    def test_available_backends_populated(self, caps_dcs: CapabilityState) -> None:
        spawn = next(i for i in build_catalog(caps_dcs) if i.name == "spawn")
        assert spawn.available_backends == ["dcs"]

    def test_sorted_by_name(self, caps_dcs: CapabilityState) -> None:
        names = [info.name for info in build_catalog(caps_dcs)]
        assert names == sorted(names)


class TestDescribe:
    def test_unknown_returns_none(self, caps_dcs: CapabilityState) -> None:
        assert describe("nope", caps_dcs) is None

    def test_resolves_long_tail_values(self, caps_dcs: CapabilityState) -> None:
        result = describe("spawn", caps_dcs)
        assert result is not None
        assert result["action"]["name"] == "spawn"
        # 'type' param is backed by the dcs_unit_types catalogue.
        assert "type" in result["values"]
        assert any(v["value"] == "Hummer" for v in result["values"]["type"])

    def test_action_without_catalog_has_no_values(self, caps_dcs: CapabilityState) -> None:
        result = describe("remove", caps_dcs)
        assert result is not None
        assert result["values"] == {}


class TestSearch:
    def test_empty_query_matches_nothing(self, caps_dcs: CapabilityState) -> None:
        result = search_catalog("", caps_dcs)
        assert result.actions == []
        assert result.values == []

    def test_matches_action_by_name(self, caps_dcs: CapabilityState) -> None:
        result = search_catalog("smoke", caps_dcs)
        assert any(a.name == "smoke" for a in result.actions)

    def test_matches_long_tail_value(self, caps_dcs: CapabilityState) -> None:
        result = search_catalog("abrams", caps_dcs)
        assert any(v.value == "M1A2" for v in result.values)

    def test_matches_value_by_tag(self, caps_dcs: CapabilityState) -> None:
        result = search_catalog("tank", caps_dcs)
        values = {v.value for v in result.values}
        assert {"M1A2", "T-72B"} <= values

    def test_search_actions_filtered_by_capabilities(self) -> None:
        # No capabilities → no available actions, even if a value matches.
        result = search_catalog("spawn", CapabilityState())
        assert result.actions == []
