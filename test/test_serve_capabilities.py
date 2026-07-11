"""Tests for dcs_bridge.serve.capabilities — lockstep matching and cache."""

from __future__ import annotations

from dcs_bridge.serve.capabilities import CapabilityState, evaluate

_TARGETS = {"dcs": None, "mist": "4.5.126", "ctld": "2.0", "veaf": "6"}


class TestEvaluate:
    def test_dcs_always_present(self) -> None:
        status = evaluate("dcs", None, None)
        assert status.present is True

    def test_loaded_matching_version_present(self) -> None:
        status = evaluate("mist", "4.5.126", "4.5.126")
        assert status.present is True
        assert status.reason is None

    def test_version_mismatch_absent(self) -> None:
        status = evaluate("ctld", "1.0", "2.0")
        assert status.present is False
        assert "mismatch" in (status.reason or "")
        assert status.version == "1.0"
        assert status.targeted == "2.0"

    def test_not_loaded_absent(self) -> None:
        status = evaluate("veaf", None, "6")
        assert status.present is False
        assert status.reason == "not loaded"

    def test_no_lockstep_present_when_loaded(self) -> None:
        status = evaluate("mist", "9.9.9", None)
        assert status.present is True


class TestCapabilityState:
    def test_empty_before_handshake(self) -> None:
        state = CapabilityState(_TARGETS)
        assert state.frameworks == {}
        assert state.is_present("mist") is False

    def test_update_marks_present_and_absent(self) -> None:
        state = CapabilityState(_TARGETS)
        state.update({"mist": "4.5.126", "ctld": "1.0"})
        assert state.is_present("dcs") is True
        assert state.is_present("mist") is True
        assert state.is_present("ctld") is False  # version mismatch
        assert state.is_present("veaf") is False  # not loaded

    def test_all_four_frameworks_evaluated(self) -> None:
        state = CapabilityState(_TARGETS)
        state.update({})
        assert set(state.frameworks) == {"dcs", "mist", "ctld", "veaf"}

    def test_clear_resets(self) -> None:
        state = CapabilityState(_TARGETS)
        state.update({"mist": "4.5.126"})
        state.clear()
        assert state.frameworks == {}
        assert state.is_present("mist") is False

    def test_update_refreshes_on_reconnect(self) -> None:
        state = CapabilityState(_TARGETS)
        state.update({"ctld": "2.0"})
        assert state.is_present("ctld") is True
        # mission change: CTLD now on a different version
        state.update({"ctld": "1.0"})
        assert state.is_present("ctld") is False
