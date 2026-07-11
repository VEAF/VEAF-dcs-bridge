"""Tests for dcs_bridge.serve.api — FastAPI routes, auth, WebSocket."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from dcs_bridge.common.models import Coalition, FullRefresh, Response, Unit, UnitPositionDcs, UnitPositionGeo
from dcs_bridge.serve.api import create_app
from dcs_bridge.serve.config import ServeConfig
from dcs_bridge.serve.core import CommandBus, DcsConnection, EventBroadcaster, Snapshot

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_API_KEY = "test-key-1234"


def _make_config(**overrides: Any) -> ServeConfig:
    return ServeConfig(api_key=_API_KEY, **overrides)


def _make_unit(name: str = "u1", coalition: Coalition = Coalition.BLUE) -> Unit:
    return Unit(
        name=name,
        position_dcs=UnitPositionDcs(x=1.0, y=2.0, z=3.0),
        position_geo=UnitPositionGeo(lat=43.0, lon=1.5),
        altitude_agl=100.0,
        category="airplane",
        type="F-16C",
        coalition=coalition,
    )


@pytest.fixture()
def snapshot() -> Snapshot:
    return Snapshot()


@pytest.fixture()
def bus() -> CommandBus:
    return CommandBus()


@pytest.fixture()
def conn() -> DcsConnection:
    c = DcsConnection()
    c._writer = MagicMock()  # mark as connected
    return c


@pytest.fixture()
def broadcaster() -> EventBroadcaster:
    return EventBroadcaster()


@pytest.fixture()
def cfg() -> ServeConfig:
    return _make_config(default_timeout=2.0, stale_threshold=30.0)


@pytest.fixture()
def app(snapshot: Snapshot, bus: CommandBus, conn: DcsConnection, broadcaster: EventBroadcaster, cfg: ServeConfig):  # type: ignore[no-untyped-def]
    return create_app(snapshot=snapshot, bus=bus, conn=conn, broadcaster=broadcaster, config=cfg)


@pytest.fixture()
async def client(app) -> AsyncClient:  # type: ignore[no-untyped-def]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class TestAuth:
    async def test_missing_key_returns_401(self, client: AsyncClient) -> None:
        r = await client.get("/api/units")
        assert r.status_code == 401

    async def test_wrong_key_returns_401(self, client: AsyncClient) -> None:
        r = await client.get("/api/units", headers={"X-API-Key": "wrong"})
        assert r.status_code == 401

    async def test_correct_key_passes(self, client: AsyncClient, snapshot: Snapshot) -> None:
        snapshot.apply_full_refresh(FullRefresh(units=[]))
        r = await client.get("/api/units", headers={"X-API-Key": _API_KEY})
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/units
# ---------------------------------------------------------------------------


class TestGetUnits:
    async def test_503_when_not_ready(self, client: AsyncClient) -> None:
        r = await client.get("/api/units", headers={"X-API-Key": _API_KEY})
        assert r.status_code == 503
        assert r.json() == {"ready": False}

    async def test_200_with_units(self, client: AsyncClient, snapshot: Snapshot) -> None:
        u = _make_unit("alpha")
        snapshot.apply_full_refresh(FullRefresh(units=[u]))
        r = await client.get("/api/units", headers={"X-API-Key": _API_KEY})
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["name"] == "alpha"

    async def test_503_when_stale(self, client: AsyncClient, snapshot: Snapshot) -> None:
        snapshot.apply_full_refresh(FullRefresh(units=[]))
        cfg_stale = _make_config(stale_threshold=0.0, default_timeout=2.0)
        app_stale = create_app(
            snapshot=snapshot,
            bus=CommandBus(),
            conn=DcsConnection(),
            broadcaster=EventBroadcaster(),
            config=cfg_stale,
        )
        async with AsyncClient(transport=ASGITransport(app=app_stale), base_url="http://test") as c:
            r = await c.get("/api/units", headers={"X-API-Key": _API_KEY})
        assert r.status_code == 503
        assert r.json()["stale"] is True


# ---------------------------------------------------------------------------
# POST /api/exec
# ---------------------------------------------------------------------------


class TestExecLua:
    async def test_503_when_disconnected(self, client: AsyncClient, conn: DcsConnection) -> None:
        conn.set_writer(None)
        r = await client.post("/api/exec", headers={"X-API-Key": _API_KEY}, json={"code": "return 1"})
        assert r.status_code == 503

    async def test_200_on_success(
        self,
        client: AsyncClient,
        bus: CommandBus,
        conn: DcsConnection,
    ) -> None:
        async def _fake_send(data: str) -> None:
            msg = json.loads(data)
            bus.resolve(msg["id"], result="42", error=None)

        conn.send = _fake_send  # type: ignore[method-assign]
        r = await client.post("/api/exec", headers={"X-API-Key": _API_KEY}, json={"code": "return 42"})
        assert r.status_code == 200
        assert r.json()["result"] == "42"

    async def test_504_on_timeout(
        self,
        client: AsyncClient,
        conn: DcsConnection,
    ) -> None:
        async def _slow_send(data: str) -> None:
            pass  # never resolve → bus will time out

        conn.send = _slow_send  # type: ignore[method-assign]
        r = await client.post(
            "/api/exec",
            headers={"X-API-Key": _API_KEY},
            json={"code": "return 1", "timeout": 0.05},
        )
        assert r.status_code == 504

    async def test_error_from_dcs_returns_200_with_error_field(
        self,
        client: AsyncClient,
        bus: CommandBus,
        conn: DcsConnection,
    ) -> None:
        async def _fake_send(data: str) -> None:
            msg = json.loads(data)
            bus.resolve(msg["id"], result=None, error="DCS script error")

        conn.send = _fake_send  # type: ignore[method-assign]
        r = await client.post("/api/exec", headers={"X-API-Key": _API_KEY}, json={"code": "bad()"})
        assert r.status_code == 200
        assert r.json()["error"] == "DCS script error"

    async def test_default_timeout_from_config_is_used(
        self,
        client: AsyncClient,
        bus: CommandBus,
        conn: DcsConnection,
        cfg: ServeConfig,
    ) -> None:
        """When no per-request timeout is given, cfg.default_timeout must be used."""
        captured: list[float] = []
        original_wait = bus.wait

        async def _spy_wait(cmd_id: str, *, timeout: float) -> Response:
            captured.append(timeout)
            return await original_wait(cmd_id, timeout=timeout)

        bus.wait = _spy_wait  # type: ignore[method-assign]

        async def _fake_send(data: str) -> None:
            msg = json.loads(data)
            bus.resolve(msg["id"], result="ok", error=None)

        conn.send = _fake_send  # type: ignore[method-assign]
        await client.post("/api/exec", headers={"X-API-Key": _API_KEY}, json={"code": "return 1"})
        assert captured == [cfg.default_timeout]

    async def test_send_failure_unregisters_cmd_id(
        self,
        client: AsyncClient,
        bus: CommandBus,
        conn: DcsConnection,
    ) -> None:
        """If send raises RuntimeError, the cmd_id must not remain in the bus."""
        async def _failing_send(data: str) -> None:
            raise RuntimeError("connection lost")

        conn.send = _failing_send  # type: ignore[method-assign]
        r = await client.post("/api/exec", headers={"X-API-Key": _API_KEY}, json={"code": "return 1"})
        assert r.status_code == 503
        assert not bus._pending  # no stale entry left


# ---------------------------------------------------------------------------
# POST /api/spawn
# ---------------------------------------------------------------------------


class TestSpawnUnit:
    async def test_200_on_success(
        self,
        client: AsyncClient,
        bus: CommandBus,
        conn: DcsConnection,
    ) -> None:
        async def _fake_send(data: str) -> None:
            msg = json.loads(data)
            bus.resolve(msg["id"], result="spawned", error=None)

        conn.send = _fake_send  # type: ignore[method-assign]
        r = await client.post(
            "/api/spawn",
            headers={"X-API-Key": _API_KEY},
            json={"group_def": {"name": "TestGroup"}},
        )
        assert r.status_code == 200
        assert r.json()["result"] == "spawned"


# ---------------------------------------------------------------------------
# POST /api/action
# ---------------------------------------------------------------------------


class TestRunAction:
    async def test_spawn_routes_to_exec_and_returns_200(
        self,
        client: AsyncClient,
        bus: CommandBus,
        conn: DcsConnection,
    ) -> None:
        captured: list[str] = []

        async def _fake_send(data: str) -> None:
            msg = json.loads(data)
            captured.append(msg["payload"]["code"])
            bus.resolve(msg["id"], result="alpha", error=None)

        conn.send = _fake_send  # type: ignore[method-assign]
        r = await client.post(
            "/api/action",
            headers={"X-API-Key": _API_KEY},
            json={
                "name": "spawn",
                "args": {"type": "Hummer", "kind": "vehicle", "coalition": "blue", "position": {"lat": 43.0, "lon": 1.5}},
            },
        )
        assert r.status_code == 200
        assert r.json()["result"] == "alpha"
        assert "coalition.addGroup(" in captured[0]

    async def test_unknown_action_returns_404(self, client: AsyncClient) -> None:
        r = await client.post(
            "/api/action",
            headers={"X-API-Key": _API_KEY},
            json={"name": "frobnicate", "args": {}},
        )
        assert r.status_code == 404

    async def test_invalid_args_returns_400(self, client: AsyncClient) -> None:
        r = await client.post(
            "/api/action",
            headers={"X-API-Key": _API_KEY},
            json={"name": "spawn", "args": {"kind": "vehicle"}},  # missing type + position
        )
        assert r.status_code == 400

    async def test_forced_unavailable_backend_returns_400(self, client: AsyncClient) -> None:
        r = await client.post(
            "/api/action",
            headers={"X-API-Key": _API_KEY},
            json={
                "name": "spawn",
                "backend": "mist",
                "args": {"type": "Hummer", "position": {"lat": 1.0, "lon": 2.0}},
            },
        )
        assert r.status_code == 400

    async def test_requires_auth(self, client: AsyncClient) -> None:
        r = await client.post("/api/action", json={"name": "spawn", "args": {}})
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# WebSocket /ws/stream
# ---------------------------------------------------------------------------


class TestWsStream:
    async def test_close_on_bad_key(self, app) -> None:  # type: ignore[no-untyped-def]
        from starlette.testclient import TestClient

        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/stream?api_key=badkey"):
                pass

    async def test_receives_snapshot_on_connect(
        self,
        app,  # type: ignore[no-untyped-def]
        snapshot: Snapshot,
    ) -> None:
        from starlette.testclient import TestClient

        snapshot.apply_full_refresh(FullRefresh(units=[_make_unit("bravo")]))
        client = TestClient(app)
        with client.websocket_connect(f"/ws/stream?api_key={_API_KEY}") as ws:
            data = json.loads(ws.receive_text())
            assert data["type"] == "full_refresh"
            assert data["units"][0]["name"] == "bravo"

    async def test_receives_broadcast_event(
        self,
        app,  # type: ignore[no-untyped-def]
        snapshot: Snapshot,
        broadcaster: EventBroadcaster,
    ) -> None:
        from starlette.testclient import TestClient

        snapshot.apply_full_refresh(FullRefresh(units=[]))
        client = TestClient(app)
        with client.websocket_connect(f"/ws/stream?api_key={_API_KEY}") as ws:
            ws.receive_text()  # consume initial snapshot
            broadcaster.broadcast({"type": "event", "name": "unit_destroyed", "data": {"unit": "x"}})
            data = json.loads(ws.receive_text())
            assert data["type"] == "event"
            assert data["name"] == "unit_destroyed"
