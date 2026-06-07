"""Shared Pydantic models for the DCS bridge protocol."""

from __future__ import annotations

from enum import IntEnum, StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class CommandAction(StrEnum):
    """Actions that dcs-serve can request the Lua bridge to execute."""

    EXEC = "exec"
    SPAWN = "spawn"


class EventName(StrEnum):
    """Names of spontaneous events sent by the Lua bridge."""

    UNIT_POSITION = "unit_position"
    UNIT_DESTROYED = "unit_destroyed"
    UNIT_SPAWNED = "unit_spawned"


class Coalition(IntEnum):
    """DCS coalition identifiers as used in the mission scripting API."""

    NEUTRAL = 0
    RED = 1
    BLUE = 2


class UnitPositionDcs(BaseModel):
    """Unit position in native DCS coordinates.

    DCS uses a flat-earth projection where x/z are the horizontal plane
    and y is absolute altitude.
    """

    model_config = ConfigDict(frozen=True)

    x: float
    y: float
    z: float


class UnitPositionGeo(BaseModel):
    """Unit position in geographic coordinates.

    Computed by the Lua bridge via coord.LOtoLL() — guaranteed accurate
    for all DCS theaters without any Python-side projection logic.
    """

    model_config = ConfigDict(frozen=True)

    lat: float
    lon: float


class Unit(BaseModel):
    """A DCS unit as exposed by the API."""

    model_config = ConfigDict(frozen=True)

    name: str
    position_dcs: UnitPositionDcs
    position_geo: UnitPositionGeo
    altitude_agl: float
    category: str
    type: str
    coalition: Coalition


class Command(BaseModel):
    """A command sent from dcs-serve to the Lua bridge over TCP."""

    model_config = ConfigDict(frozen=True)

    id: str
    action: CommandAction
    payload: dict[str, Any]


class Response(BaseModel):
    """A response from the Lua bridge to a Command, correlated by id.

    Exactly one of result or error must be non-None.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    result: str | None
    error: str | None

    @model_validator(mode="after")
    def exactly_one_of_result_or_error(self) -> Response:
        """Enforce that exactly one of result or error is set."""
        if (self.result is None) == (self.error is None):
            raise ValueError("Exactly one of 'result' or 'error' must be non-None")
        return self


class DcsEvent(BaseModel):
    """A spontaneous event pushed by the Lua bridge to dcs-serve."""

    model_config = ConfigDict(frozen=True)

    name: EventName
    data: dict[str, Any]


class FullRefresh(BaseModel):
    """Complete unit state snapshot sent by the Lua bridge every N seconds."""

    model_config = ConfigDict(frozen=True)

    units: list[Unit]
