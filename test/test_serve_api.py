"""Tests for dcs_bridge.serve.api — FastAPI endpoints, auth, WebSocket."""

from __future__ import annotations

import json
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from dcs_bridge.common.models import Coalition, FullRefresh, Unit, UnitPositionDcs, UnitPositionGeo
from dcs_bridge.serve.api import create_app
from dcs_bridge.serve.core import CommandBus, Snapshot

API_KEY = "test-secret-key"


def make_unit(name: str = "u1") -> Unit:
    return Unit(
        name=name,
        position_dcs=UnitPositionDcs(x=0.0, y=0.0, z=0.0),
        position_geo=UnitPositionGeo(lat=0.0, lon=0.0),
        altitude_agl=0.0,
        category="vehicle",
        type="T-80",
        coalition=Coalition.RED,
    )


@pytest.fixture
def snapshot() -> Snapshot:
    return Snapshot()


@pytest.fixture
def bus() -> CommandBus:
    return CommandBus()


@pytest.fixture
async def client(snapshot: Snapshot, bus: CommandBus) -> AsyncGenerator[AsyncClient, None]:
    app = create_app(snapshot=snapshot, bus=bus, api_key=API_KEY)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class TestAuth:
    async def test_missing_key_returns_401(self, client: AsyncClient) -> None:
        resp = await client.get("/api/units")
        assert resp.status_code == 401

    async def test_wrong_key_returns_401(self, client: AsyncClient) -> None:
        resp = await client.get("/api/units", headers={"X-API-Key": "wrong"})
        assert resp.status_code == 401

    async def test_correct_key_passes(self, client: AsyncClient, snapshot: Snapshot) -> None:
        snapshot.apply_full_refresh(FullRefresh(units=[]))
        resp = await client.get("/api/units", headers={"X-API-Key": API_KEY})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/units
# ---------------------------------------------------------------------------

class TestGetUnits:
    async def test_503_when_not_ready(self, client: AsyncClient) -> None:
        resp = await client.get("/api/units", headers={"X-API-Key": API_KEY})
        assert resp.status_code == 503
        assert resp.json()["detail"]["ready"] is False

    async def test_returns_units(self, client: AsyncClient, snapshot: Snapshot) -> None:
        snapshot.apply_full_refresh(FullRefresh(units=[make_unit("alpha")]))
        resp = await client.get("/api/units", headers={"X-API-Key": API_KEY})
        assert resp.status_code == 200
        data = resp.json()
        assert data["units"][0]["name"] == "alpha"
        assert data["stale"] is False

    async def test_stale_flag(self, client: AsyncClient, snapshot: Snapshot) -> None:
        snapshot.apply_full_refresh(FullRefresh(units=[]))
        snapshot.backdate_for_test(60.0)
        resp = await client.get("/api/units", headers={"X-API-Key": API_KEY})
        assert resp.status_code == 200
        assert resp.json()["stale"] is True


# ---------------------------------------------------------------------------
# POST /api/exec
# ---------------------------------------------------------------------------

class TestPostExec:
    async def test_exec_returns_result(
        self, client: AsyncClient, snapshot: Snapshot, bus: CommandBus
    ) -> None:
        snapshot.apply_full_refresh(FullRefresh(units=[]))

        async def fake_send(cmd_id: str, payload: dict, timeout: float) -> None:  # type: ignore[type-arg]
            bus.register(cmd_id)
            bus.resolve(cmd_id, result="42", error=None)

        with patch("dcs_bridge.serve.api.send_command", new=AsyncMock(side_effect=fake_send)):
            resp = await client.post(
                "/api/exec",
                json={"code": "return 42"},
                headers={"X-API-Key": API_KEY},
            )
        assert resp.status_code == 200
        assert resp.json()["result"] == "42"
        assert resp.json()["success"] is True

    async def test_exec_lua_error_returns_200(
        self, client: AsyncClient, snapshot: Snapshot, bus: CommandBus
    ) -> None:
        snapshot.apply_full_refresh(FullRefresh(units=[]))

        async def fake_send(cmd_id: str, payload: dict, timeout: float) -> None:  # type: ignore[type-arg]
            bus.register(cmd_id)
            bus.resolve(cmd_id, result=None, error="runtime error")

        with patch("dcs_bridge.serve.api.send_command", new=AsyncMock(side_effect=fake_send)):
            resp = await client.post(
                "/api/exec",
                json={"code": "error('boom')"},
                headers={"X-API-Key": API_KEY},
            )
        assert resp.status_code == 200
        assert resp.json()["success"] is False
        assert "runtime error" in resp.json()["error"]

    async def test_exec_timeout_returns_504(
        self, client: AsyncClient, snapshot: Snapshot, bus: CommandBus
    ) -> None:
        snapshot.apply_full_refresh(FullRefresh(units=[]))

        async def fake_send(cmd_id: str, payload: dict, timeout: float) -> None:  # type: ignore[type-arg]
            bus.register(cmd_id)
            raise TimeoutError("timeout")

        with patch("dcs_bridge.serve.api.send_command", new=AsyncMock(side_effect=fake_send)):
            resp = await client.post(
                "/api/exec",
                json={"code": "return 1"},
                headers={"X-API-Key": API_KEY},
            )
        assert resp.status_code == 504

    async def test_exec_dcs_unavailable_returns_503(
        self, client: AsyncClient
    ) -> None:
        resp = await client.post(
            "/api/exec",
            json={"code": "return 1"},
            headers={"X-API-Key": API_KEY},
        )
        assert resp.status_code == 503

    async def test_custom_timeout_respected(
        self, client: AsyncClient, snapshot: Snapshot, bus: CommandBus
    ) -> None:
        snapshot.apply_full_refresh(FullRefresh(units=[]))
        received_timeout: list[float] = []

        async def fake_send(cmd_id: str, payload: dict, timeout: float) -> None:  # type: ignore[type-arg]
            received_timeout.append(timeout)
            bus.register(cmd_id)
            bus.resolve(cmd_id, result="ok", error=None)

        with patch("dcs_bridge.serve.api.send_command", new=AsyncMock(side_effect=fake_send)):
            await client.post(
                "/api/exec",
                json={"code": "return 1", "timeout": 99},
                headers={"X-API-Key": API_KEY},
            )
        assert received_timeout[0] == 99

    async def test_negative_timeout_clamped_to_minimum(
        self, client: AsyncClient, snapshot: Snapshot, bus: CommandBus
    ) -> None:
        snapshot.apply_full_refresh(FullRefresh(units=[]))
        received_timeout: list[float] = []

        async def fake_send(cmd_id: str, payload: dict, timeout: float) -> None:  # type: ignore[type-arg]
            received_timeout.append(timeout)
            bus.register(cmd_id)
            bus.resolve(cmd_id, result="ok", error=None)

        with patch("dcs_bridge.serve.api.send_command", new=AsyncMock(side_effect=fake_send)):
            await client.post(
                "/api/exec",
                json={"code": "return 1", "timeout": -5},
                headers={"X-API-Key": API_KEY},
            )
        assert received_timeout[0] >= 0.1


# ---------------------------------------------------------------------------
# POST /api/spawn
# ---------------------------------------------------------------------------


class TestPostSpawn:
    async def test_spawn_success(
        self, client: AsyncClient, snapshot: Snapshot, bus: CommandBus
    ) -> None:
        snapshot.apply_full_refresh(FullRefresh(units=[]))

        async def fake_send(cmd_id: str, payload: dict, timeout: float) -> None:  # type: ignore[type-arg]
            bus.register(cmd_id)
            bus.resolve(cmd_id, result="spawned", error=None)

        with patch("dcs_bridge.serve.api.send_command", new=AsyncMock(side_effect=fake_send)):
            resp = await client.post(
                "/api/spawn",
                json={"group": {"name": "test-group"}},
                headers={"X-API-Key": API_KEY},
            )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert resp.json()["result"] == "spawned"

    async def test_spawn_dcs_unavailable_returns_503(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/spawn",
            json={"group": {"name": "test-group"}},
            headers={"X-API-Key": API_KEY},
        )
        assert resp.status_code == 503

    async def test_spawn_timeout_returns_504(
        self, client: AsyncClient, snapshot: Snapshot, bus: CommandBus
    ) -> None:
        snapshot.apply_full_refresh(FullRefresh(units=[]))

        async def fake_send(cmd_id: str, payload: dict, timeout: float) -> None:  # type: ignore[type-arg]
            bus.register(cmd_id)
            raise TimeoutError("timeout")

        with patch("dcs_bridge.serve.api.send_command", new=AsyncMock(side_effect=fake_send)):
            resp = await client.post(
                "/api/spawn",
                json={"group": {"name": "test-group"}},
                headers={"X-API-Key": API_KEY},
            )
        assert resp.status_code == 504


# ---------------------------------------------------------------------------
# GET /api/mission
# ---------------------------------------------------------------------------

class TestGetMission:
    async def test_503_when_not_ready(self, client: AsyncClient) -> None:
        resp = await client.get("/api/mission", headers={"X-API-Key": API_KEY})
        assert resp.status_code == 503

    async def test_returns_mission_info(
        self, client: AsyncClient, snapshot: Snapshot, bus: CommandBus
    ) -> None:
        snapshot.apply_full_refresh(FullRefresh(units=[]))

        async def fake_send(cmd_id: str, payload: dict, timeout: float) -> None:  # type: ignore[type-arg]
            bus.register(cmd_id)
            bus.resolve(cmd_id, result=json.dumps({"theatre": "Caucasus", "name": "test"}), error=None)

        with patch("dcs_bridge.serve.api.send_command", new=AsyncMock(side_effect=fake_send)):
            resp = await client.get("/api/mission", headers={"X-API-Key": API_KEY})
        assert resp.status_code == 200
        assert resp.json()["theatre"] == "Caucasus"
