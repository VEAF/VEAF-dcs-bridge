"""Shared Pydantic models for the DCS bridge protocol."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class CommandAction(StrEnum):
    """Actions that dcs-serve can request the Lua bridge to execute."""

    EXEC = "exec"
    SPAWN = "spawn"


class EventName(StrEnum):
    """Names of spontaneous events sent by the Lua bridge."""

    UNIT_POSITION = "unit_position"
    UNIT_DESTROYED = "unit_destroyed"
    UNIT_SPAWNED = "unit_spawned"


class UnitPositionDcs(BaseModel):
    """Unit position in native DCS coordinates.

    DCS uses a flat-earth projection where x/z are the horizontal plane
    and y is absolute altitude.
    """

    x: float
    y: float
    z: float


class UnitPositionGeo(BaseModel):
    """Unit position in geographic coordinates.

    Computed by the Lua bridge via coord.LOtoLL() — guaranteed accurate
    for all DCS theaters without any Python-side projection logic.
    """

    lat: float
    lon: float


class Unit(BaseModel):
    """A DCS unit as exposed by the API."""

    name: str
    position_dcs: UnitPositionDcs
    position_geo: UnitPositionGeo
    altitude_agl: float
    category: str
    type: str
    coalition: int


class Command(BaseModel):
    """A command sent from dcs-serve to the Lua bridge over TCP."""

    id: str
    action: CommandAction
    payload: dict[str, Any]


class Response(BaseModel):
    """A response from the Lua bridge to a Command, correlated by id."""

    id: str
    result: str | None
    error: str | None


class DcsEvent(BaseModel):
    """A spontaneous event pushed by the Lua bridge to dcs-serve."""

    name: EventName
    data: dict[str, Any]


class FullRefresh(BaseModel):
    """Complete unit state snapshot sent by the Lua bridge every N seconds."""

    units: list[Unit]
