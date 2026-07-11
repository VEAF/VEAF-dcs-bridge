"""Tests for dcs_bridge.serve.api — FastAPI routes, auth, WebSocket."""

from __future__ import annotations

import json
import time
from typing import Any
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from dcs_bridge.common.models import Coalition, FullRefresh, Response, Unit, UnitPositionDcs, UnitPositionGeo
from dcs_bridge.serve.api import create_app
from dcs_bridge.serve.capabilities import CapabilityState
from dcs_bridge.serve.config import ServeConfig
from dcs_bridge.serve.core import CommandBus, DcsConnection, EventBroadcaster, Snapshot
from dcs_bridge.serve.security import Role, Token, TokenStore

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_API_KEY = "test-key-1234"


def _auth(token: str) -> dict[str, str]:
    """Build an Authorization: Bearer header for the given token."""
    return {"Authorization": f"Bearer {token}"}


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
def capabilities() -> CapabilityState:
    return CapabilityState({"dcs": None, "mist": "4.5.126", "ctld": "2.0", "veaf": "6"})


@pytest.fixture()
def app(  # type: ignore[no-untyped-def]
    snapshot: Snapshot,
    bus: CommandBus,
    conn: DcsConnection,
    broadcaster: EventBroadcaster,
    cfg: ServeConfig,
    capabilities: CapabilityState,
):
    return create_app(
        snapshot=snapshot, bus=bus, conn=conn, broadcaster=broadcaster, config=cfg, capabilities=capabilities
    )


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
        r = await client.get("/api/units", headers=_auth("wrong"))
        assert r.status_code == 401

    async def test_correct_key_passes(self, client: AsyncClient, snapshot: Snapshot) -> None:
        snapshot.apply_full_refresh(FullRefresh(units=[]))
        r = await client.get("/api/units", headers=_auth(_API_KEY))
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/units
# ---------------------------------------------------------------------------


class TestGetUnits:
    async def test_503_when_not_ready(self, client: AsyncClient) -> None:
        r = await client.get("/api/units", headers=_auth(_API_KEY))
        assert r.status_code == 503
        assert r.json() == {"ready": False}

    async def test_200_with_units(self, client: AsyncClient, snapshot: Snapshot) -> None:
        u = _make_unit("alpha")
        snapshot.apply_full_refresh(FullRefresh(units=[u]))
        r = await client.get("/api/units", headers=_auth(_API_KEY))
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
            r = await c.get("/api/units", headers=_auth(_API_KEY))
        assert r.status_code == 503
        assert r.json()["stale"] is True


# ---------------------------------------------------------------------------
# POST /api/exec
# ---------------------------------------------------------------------------


class TestExecLua:
    async def test_503_when_disconnected(self, client: AsyncClient, conn: DcsConnection) -> None:
        conn.set_writer(None)
        r = await client.post("/api/exec", headers=_auth(_API_KEY), json={"code": "return 1"})
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
        r = await client.post("/api/exec", headers=_auth(_API_KEY), json={"code": "return 42"})
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
            headers=_auth(_API_KEY),
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
        r = await client.post("/api/exec", headers=_auth(_API_KEY), json={"code": "bad()"})
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
        await client.post("/api/exec", headers=_auth(_API_KEY), json={"code": "return 1"})
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
        r = await client.post("/api/exec", headers=_auth(_API_KEY), json={"code": "return 1"})
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
            headers=_auth(_API_KEY),
            json={"group_def": {"name": "TestGroup"}},
        )
        assert r.status_code == 200
        assert r.json()["result"] == "spawned"


# ---------------------------------------------------------------------------
# GET /api/capabilities
# ---------------------------------------------------------------------------


class TestCatalog:
    async def test_catalog_requires_auth(self, client: AsyncClient) -> None:
        assert (await client.get("/api/catalog")).status_code == 401

    async def test_catalog_empty_before_handshake(self, client: AsyncClient) -> None:
        r = await client.get("/api/catalog", headers=_auth(_API_KEY))
        assert r.status_code == 200
        assert r.json()["actions"] == []

    async def test_catalog_lists_dcs_actions(self, client: AsyncClient, capabilities: CapabilityState) -> None:
        capabilities.update({})  # DCS present
        r = await client.get("/api/catalog", headers=_auth(_API_KEY))
        assert r.status_code == 200
        names = {a["name"] for a in r.json()["actions"]}
        assert {"spawn", "smoke", "remove"} <= names

    async def test_describe_action(self, client: AsyncClient, capabilities: CapabilityState) -> None:
        capabilities.update({})
        r = await client.get("/api/catalog/spawn", headers=_auth(_API_KEY))
        assert r.status_code == 200
        body = r.json()
        assert body["action"]["name"] == "spawn"
        assert any(v["value"] == "Hummer" for v in body["values"]["type"])

    async def test_describe_unknown_404(self, client: AsyncClient) -> None:
        r = await client.get("/api/catalog/frobnicate", headers=_auth(_API_KEY))
        assert r.status_code == 404

    async def test_search(self, client: AsyncClient, capabilities: CapabilityState) -> None:
        capabilities.update({})
        r = await client.get("/api/catalog/search", params={"q": "tank"}, headers=_auth(_API_KEY))
        assert r.status_code == 200
        values = {v["value"] for v in r.json()["values"]}
        assert "M1A2" in values


class TestGetCapabilities:
    async def test_requires_auth(self, client: AsyncClient) -> None:
        r = await client.get("/api/capabilities")
        assert r.status_code == 401

    async def test_empty_before_handshake(self, client: AsyncClient) -> None:
        r = await client.get("/api/capabilities", headers=_auth(_API_KEY))
        assert r.status_code == 200
        body = r.json()
        assert body["connected"] is True  # conn fixture is marked connected
        assert body["frameworks"] == {}

    async def test_reflects_handshake(self, client: AsyncClient, capabilities: CapabilityState) -> None:
        capabilities.update({"mist": "4.5.126", "ctld": "1.0"})
        r = await client.get("/api/capabilities", headers=_auth(_API_KEY))
        assert r.status_code == 200
        fw = r.json()["frameworks"]
        assert fw["dcs"]["present"] is True
        assert fw["mist"]["present"] is True
        assert fw["ctld"]["present"] is False
        assert "mismatch" in fw["ctld"]["reason"]
        assert fw["veaf"]["present"] is False


# ---------------------------------------------------------------------------
# POST /api/action
# ---------------------------------------------------------------------------


class TestRunAction:
    async def test_spawn_routes_to_exec_and_returns_200(
        self,
        client: AsyncClient,
        bus: CommandBus,
        conn: DcsConnection,
        capabilities: CapabilityState,
    ) -> None:
        capabilities.update({})  # DCS present
        captured: list[str] = []

        async def _fake_send(data: str) -> None:
            msg = json.loads(data)
            captured.append(msg["payload"]["code"])
            bus.resolve(msg["id"], result="alpha", error=None)

        conn.send = _fake_send  # type: ignore[method-assign]
        r = await client.post(
            "/api/action",
            headers=_auth(_API_KEY),
            json={
                "name": "spawn",
                "args": {
                    "type": "Hummer",
                    "kind": "vehicle",
                    "coalition": "blue",
                    "position": {"lat": 43.0, "lon": 1.5},
                },
            },
        )
        assert r.status_code == 200
        assert r.json()["result"] == "alpha"
        assert "coalition.addGroup(" in captured[0]

    async def test_farp_routes_to_ctld_when_present(
        self,
        client: AsyncClient,
        bus: CommandBus,
        conn: DcsConnection,
        capabilities: CapabilityState,
    ) -> None:
        capabilities.update({"ctld": "2.0"})  # DCS + CTLD present
        captured: list[str] = []

        async def _fake_send(data: str) -> None:
            msg = json.loads(data)
            captured.append(msg["payload"]["code"])
            bus.resolve(msg["id"], result="fob", error=None)

        conn.send = _fake_send  # type: ignore[method-assign]
        r = await client.post(
            "/api/action",
            headers=_auth(_API_KEY),
            json={"name": "spawn", "args": {"type": "FARP", "kind": "farp", "position": {"lat": 1.0, "lon": 2.0}}},
        )
        assert r.status_code == 200
        assert "CTLDSceneManager:playSceneAtPos(" in captured[0]

    async def test_no_available_backend_returns_400(self, client: AsyncClient) -> None:
        # No handshake → nothing present → no backend can run the action.
        r = await client.post(
            "/api/action",
            headers=_auth(_API_KEY),
            json={"name": "spawn", "args": {"type": "Hummer", "position": {"lat": 1.0, "lon": 2.0}}},
        )
        assert r.status_code == 400

    async def test_unknown_action_returns_404(self, client: AsyncClient) -> None:
        r = await client.post(
            "/api/action",
            headers=_auth(_API_KEY),
            json={"name": "frobnicate", "args": {}},
        )
        assert r.status_code == 404

    async def test_invalid_args_returns_400(self, client: AsyncClient, capabilities: CapabilityState) -> None:
        capabilities.update({})
        r = await client.post(
            "/api/action",
            headers=_auth(_API_KEY),
            json={"name": "spawn", "args": {"kind": "vehicle"}},  # missing type + position
        )
        assert r.status_code == 400

    async def test_forced_undeclared_backend_returns_400(
        self, client: AsyncClient, capabilities: CapabilityState
    ) -> None:
        capabilities.update({})
        r = await client.post(
            "/api/action",
            headers=_auth(_API_KEY),
            json={
                "name": "spawn",
                "backend": "bogus",  # not a declared backend of spawn
                "args": {"type": "Hummer", "position": {"lat": 1.0, "lon": 2.0}},
            },
        )
        assert r.status_code == 400

    async def test_requires_auth(self, client: AsyncClient) -> None:
        r = await client.post("/api/action", json={"name": "spawn", "args": {}})
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Role-based enforcement (ADR-0005 / ticket 06)
# ---------------------------------------------------------------------------

_ROLE_TOKENS = TokenStore(
    [
        Token(token="obs", role=Role.OBSERVER),
        Token(token="pil", role=Role.PILOT),
        Token(token="ops", role=Role.OPERATOR),
        Token(token="root", role=Role.SUPERUSER),
    ]
)


@pytest.fixture()
def role_client_factory(  # type: ignore[no-untyped-def]
    snapshot: Snapshot,
    bus: CommandBus,
    conn: DcsConnection,
    broadcaster: EventBroadcaster,
    cfg: ServeConfig,
    capabilities: CapabilityState,
):
    capabilities.update({})  # DCS present so actions are available

    async def _fake_send(data: str) -> None:
        msg = json.loads(data)
        bus.resolve(msg["id"], result="ok", error=None)

    conn.send = _fake_send  # type: ignore[method-assign]
    app = create_app(
        snapshot=snapshot,
        bus=bus,
        conn=conn,
        broadcaster=broadcaster,
        config=cfg,
        capabilities=capabilities,
        tokens=_ROLE_TOKENS,
    )
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class TestRoleEnforcement:
    async def test_invalid_token_401(self, role_client_factory: AsyncClient) -> None:
        async with role_client_factory as c:
            r = await c.get("/api/units", headers=_auth("bogus"))
        assert r.status_code == 401

    async def test_observer_can_read(self, role_client_factory: AsyncClient, snapshot: Snapshot) -> None:
        snapshot.apply_full_refresh(FullRefresh(units=[]))
        async with role_client_factory as c:
            r = await c.get("/api/units", headers=_auth("obs"))
        assert r.status_code == 200

    async def test_observer_cannot_exec(self, role_client_factory: AsyncClient) -> None:
        async with role_client_factory as c:
            r = await c.post("/api/exec", headers=_auth("obs"), json={"code": "return 1"})
        assert r.status_code == 403

    async def test_superuser_can_exec(self, role_client_factory: AsyncClient) -> None:
        async with role_client_factory as c:
            r = await c.post("/api/exec", headers=_auth("root"), json={"code": "return 1"})
        assert r.status_code == 200

    async def test_observer_cannot_run_operator_action(self, role_client_factory: AsyncClient) -> None:
        async with role_client_factory as c:
            r = await c.post(
                "/api/action",
                headers=_auth("obs"),
                json={"name": "spawn", "args": {"type": "Hummer", "position": {"lat": 1.0, "lon": 2.0}}},
            )
        assert r.status_code == 403

    async def test_pilot_can_run_smoke_but_not_spawn(self, role_client_factory: AsyncClient) -> None:
        async with role_client_factory as c:
            smoke = await c.post(
                "/api/action",
                headers=_auth("pil"),
                json={"name": "smoke", "args": {"position": {"lat": 1.0, "lon": 2.0}}},
            )
            spawn = await c.post(
                "/api/action",
                headers=_auth("pil"),
                json={"name": "spawn", "args": {"type": "Hummer", "position": {"lat": 1.0, "lon": 2.0}}},
            )
        assert smoke.status_code == 200  # smoke min_role = pilot
        assert spawn.status_code == 403  # spawn min_role = operator

    async def test_operator_can_spawn(self, role_client_factory: AsyncClient) -> None:
        async with role_client_factory as c:
            r = await c.post(
                "/api/action",
                headers=_auth("ops"),
                json={"name": "spawn", "args": {"type": "Hummer", "position": {"lat": 1.0, "lon": 2.0}}},
            )
        assert r.status_code == 200

    async def test_unknown_action_still_404_for_authorised(self, role_client_factory: AsyncClient) -> None:
        async with role_client_factory as c:
            r = await c.post("/api/action", headers=_auth("root"), json={"name": "nope", "args": {}})
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# WebSocket /ws/stream
# ---------------------------------------------------------------------------


class TestWsTicket:
    async def test_issue_requires_auth(self, client: AsyncClient) -> None:
        r = await client.post("/api/ws-ticket")
        assert r.status_code == 401

    async def test_issue_returns_ticket(self, client: AsyncClient) -> None:
        r = await client.post("/api/ws-ticket", headers=_auth(_API_KEY))
        assert r.status_code == 200
        body = r.json()
        assert body["ticket"]
        assert body["expires_in"] > 0


def _issue_ticket(app) -> str:  # type: ignore[no-untyped-def]
    """Issue a valid WS ticket on the app's ticket store (superuser token)."""
    return app.state.tickets.issue(Token(token="x", role=Role.SUPERUSER), now=time.time()).ticket


class TestWsStream:
    async def test_close_on_bad_ticket(self, app) -> None:  # type: ignore[no-untyped-def]
        from starlette.testclient import TestClient

        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/stream?ticket=badticket"):
                pass

    async def test_close_without_ticket(self, app) -> None:  # type: ignore[no-untyped-def]
        from starlette.testclient import TestClient

        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/stream"):
                pass

    async def test_ticket_is_single_use(self, app, snapshot: Snapshot) -> None:  # type: ignore[no-untyped-def]
        from starlette.testclient import TestClient

        snapshot.apply_full_refresh(FullRefresh(units=[]))
        ticket = _issue_ticket(app)
        client = TestClient(app)
        with client.websocket_connect(f"/ws/stream?ticket={ticket}") as ws:
            ws.receive_text()
        # The same ticket must not open a second socket.
        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws/stream?ticket={ticket}"):
                pass

    async def test_receives_snapshot_on_connect(
        self,
        app,  # type: ignore[no-untyped-def]
        snapshot: Snapshot,
    ) -> None:
        from starlette.testclient import TestClient

        snapshot.apply_full_refresh(FullRefresh(units=[_make_unit("bravo")]))
        client = TestClient(app)
        with client.websocket_connect(f"/ws/stream?ticket={_issue_ticket(app)}") as ws:
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
        with client.websocket_connect(f"/ws/stream?ticket={_issue_ticket(app)}") as ws:
            ws.receive_text()  # consume initial snapshot
            broadcaster.broadcast({"type": "event", "name": "unit_destroyed", "data": {"unit": "x"}})
            data = json.loads(ws.receive_text())
            assert data["type"] == "event"
            assert data["name"] == "unit_destroyed"
