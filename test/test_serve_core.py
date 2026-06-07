"""Tests for dcs_bridge.serve.core — TCP handler, snapshot, correlation."""

from __future__ import annotations

import asyncio
import json

import pytest

from dcs_bridge.common.models import Coalition, FullRefresh, Unit, UnitPositionDcs, UnitPositionGeo
from dcs_bridge.serve.core import CommandBus, Snapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_unit(name: str = "u1", coalition: Coalition = Coalition.RED) -> Unit:
    return Unit(
        name=name,
        position_dcs=UnitPositionDcs(x=0.0, y=0.0, z=0.0),
        position_geo=UnitPositionGeo(lat=0.0, lon=0.0),
        altitude_agl=0.0,
        category="vehicle",
        type="T-80",
        coalition=coalition,
    )


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------

class TestSnapshot:
    def test_initially_not_ready(self) -> None:
        snap = Snapshot()
        assert not snap.ready

    def test_ready_after_first_refresh(self) -> None:
        snap = Snapshot()
        snap.apply_full_refresh(FullRefresh(units=[]))
        assert snap.ready

    def test_units_replaced_on_full_refresh(self) -> None:
        snap = Snapshot()
        snap.apply_full_refresh(FullRefresh(units=[make_unit("a"), make_unit("b")]))
        snap.apply_full_refresh(FullRefresh(units=[make_unit("c")]))
        assert len(snap.units) == 1
        assert snap.units[0].name == "c"

    def test_not_stale_right_after_refresh(self) -> None:
        snap = Snapshot()
        snap.apply_full_refresh(FullRefresh(units=[]))
        assert not snap.stale(threshold=5.0)

    def test_stale_after_threshold(self) -> None:
        snap = Snapshot()
        snap.apply_full_refresh(FullRefresh(units=[]))
        # manually backdate last_updated
        import time
        snap._last_updated -= 10.0  # type: ignore[attr-defined]
        assert snap.stale(threshold=5.0)

    def test_last_updated_is_set(self) -> None:
        snap = Snapshot()
        assert snap.last_updated is None
        snap.apply_full_refresh(FullRefresh(units=[]))
        assert snap.last_updated is not None


# ---------------------------------------------------------------------------
# CommandBus
# ---------------------------------------------------------------------------

class TestCommandBus:
    async def test_send_and_receive_response(self) -> None:
        bus = CommandBus()
        cmd_id = "test-123"
        bus.register(cmd_id)

        # simulate DCS responding
        async def respond() -> None:
            await asyncio.sleep(0.01)
            bus.resolve(cmd_id, result="42", error=None)

        asyncio.create_task(respond())
        response = await bus.wait(cmd_id, timeout=1.0)
        assert response.result == "42"
        assert response.error is None

    async def test_timeout_raises(self) -> None:
        bus = CommandBus()
        cmd_id = "timeout-test"
        bus.register(cmd_id)
        with pytest.raises(TimeoutError):
            await bus.wait(cmd_id, timeout=0.05)

    async def test_error_response(self) -> None:
        bus = CommandBus()
        cmd_id = "err-456"
        bus.register(cmd_id)

        async def respond() -> None:
            await asyncio.sleep(0.01)
            bus.resolve(cmd_id, result=None, error="runtime error")

        asyncio.create_task(respond())
        response = await bus.wait(cmd_id, timeout=1.0)
        assert response.error == "runtime error"
        assert response.result is None

    async def test_resolve_unknown_id_is_ignored(self) -> None:
        bus = CommandBus()
        bus.resolve("ghost-id", result="x", error=None)  # must not raise


# ---------------------------------------------------------------------------
# TcpHandler (integration test with fake DCS server)
# ---------------------------------------------------------------------------

class TestTcpHandler:
    async def test_full_refresh_updates_snapshot(self) -> None:
        from dcs_bridge.serve.core import TcpHandler

        snapshot = Snapshot()
        bus = CommandBus()
        handler = TcpHandler(snapshot=snapshot, bus=bus)

        full_refresh = json.dumps({
            "type": "full_refresh",
            "units": [{
                "name": "u1",
                "position_dcs": {"x": 1.0, "y": 2.0, "z": 3.0},
                "position_geo": {"lat": 41.0, "lon": 42.0},
                "altitude_agl": 100.0,
                "category": "vehicle",
                "type": "T-80",
                "coalition": 1,
            }],
        }) + "\n"

        handler.feed(full_refresh)
        assert snapshot.ready
        assert len(snapshot.units) == 1
        assert snapshot.units[0].name == "u1"

    async def test_response_resolves_command(self) -> None:
        from dcs_bridge.serve.core import TcpHandler

        snapshot = Snapshot()
        bus = CommandBus()
        handler = TcpHandler(snapshot=snapshot, bus=bus)

        cmd_id = "abc"
        bus.register(cmd_id)

        response_line = json.dumps({"id": cmd_id, "result": "99", "error": None}) + "\n"
        handler.feed(response_line)

        response = await bus.wait(cmd_id, timeout=0.1)
        assert response.result == "99"

    async def test_malformed_json_is_ignored(self) -> None:
        from dcs_bridge.serve.core import TcpHandler

        snapshot = Snapshot()
        bus = CommandBus()
        handler = TcpHandler(snapshot=snapshot, bus=bus)

        handler.feed("not json\n")
        assert not snapshot.ready  # no crash, snapshot unchanged
