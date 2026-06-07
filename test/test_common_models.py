"""Tests for dcs_bridge.common.models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from dcs_bridge.common.models import (
    Command,
    CommandAction,
    DcsEvent,
    EventName,
    FullRefresh,
    Response,
    Unit,
    UnitPositionDcs,
    UnitPositionGeo,
)


class TestUnitPositionDcs:
    def test_valid(self) -> None:
        pos = UnitPositionDcs(x=100.0, y=50.0, z=200.0)
        assert pos.x == 100.0
        assert pos.y == 50.0
        assert pos.z == 200.0

    def test_requires_all_fields(self) -> None:
        with pytest.raises(ValidationError):
            UnitPositionDcs(x=1.0, y=2.0)  # type: ignore[call-arg]


class TestUnitPositionGeo:
    def test_valid(self) -> None:
        pos = UnitPositionGeo(lat=41.123, lon=41.456)
        assert pos.lat == 41.123
        assert pos.lon == 41.456


class TestUnit:
    def test_full_unit(self) -> None:
        unit = Unit(
            name="unit-1",
            position_dcs=UnitPositionDcs(x=100.0, y=50.0, z=200.0),
            position_geo=UnitPositionGeo(lat=41.0, lon=42.0),
            altitude_agl=100.0,
            category="vehicle",
            type="T-80",
            coalition=2,
        )
        assert unit.name == "unit-1"
        assert unit.coalition == 2

    def test_name_required(self) -> None:
        with pytest.raises(ValidationError):
            Unit(  # type: ignore[call-arg]
                position_dcs=UnitPositionDcs(x=0.0, y=0.0, z=0.0),
                position_geo=UnitPositionGeo(lat=0.0, lon=0.0),
                altitude_agl=0.0,
                category="vehicle",
                type="T-80",
                coalition=1,
            )


class TestCommand:
    def test_exec_command(self) -> None:
        cmd = Command(id="abc123", action=CommandAction.EXEC, payload={"code": "return 1"})
        assert cmd.id == "abc123"
        assert cmd.action == CommandAction.EXEC
        assert cmd.payload["code"] == "return 1"

    def test_spawn_command(self) -> None:
        cmd = Command(id="xyz", action=CommandAction.SPAWN, payload={"group": {}})
        assert cmd.action == CommandAction.SPAWN

    def test_invalid_action(self) -> None:
        with pytest.raises(ValidationError):
            Command(id="x", action="invalid", payload={})  # type: ignore[arg-type]


class TestResponse:
    def test_success_response(self) -> None:
        resp = Response(id="abc123", result="42", error=None)
        assert resp.id == "abc123"
        assert resp.result == "42"
        assert resp.error is None

    def test_error_response(self) -> None:
        resp = Response(id="abc123", result=None, error="runtime error")
        assert resp.error == "runtime error"
        assert resp.result is None

    def test_id_required(self) -> None:
        with pytest.raises(ValidationError):
            Response(result="x", error=None)  # type: ignore[call-arg]


class TestDcsEvent:
    def test_unit_position_event(self) -> None:
        event = DcsEvent(name=EventName.UNIT_POSITION, data={"unit": "abc"})
        assert event.name == EventName.UNIT_POSITION
        assert event.data["unit"] == "abc"

    def test_unknown_event_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DcsEvent(name="unknown_event", data={})  # type: ignore[arg-type]


class TestFullRefresh:
    def test_empty_refresh(self) -> None:
        refresh = FullRefresh(units=[])
        assert refresh.units == []

    def test_with_units(self) -> None:
        unit = Unit(
            name="u1",
            position_dcs=UnitPositionDcs(x=0.0, y=0.0, z=0.0),
            position_geo=UnitPositionGeo(lat=0.0, lon=0.0),
            altitude_agl=0.0,
            category="plane",
            type="F-16C",
            coalition=1,
        )
        refresh = FullRefresh(units=[unit])
        assert len(refresh.units) == 1
        assert refresh.units[0].name == "u1"
