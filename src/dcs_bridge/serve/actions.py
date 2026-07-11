"""Action registry and backend adapters (ADR-0005).

An :class:`Action` is an abstract verb (e.g. ``spawn``) with one or more backend
adapters. Each adapter is a small ``(args) -> Lua snippet`` function built on the
:mod:`dcs_bridge.serve.lua` serialiser. This module ships the tracer-bullet
slice: the ``spawn`` verb with a single DCS-native backend that emits
``coalition.addGroup(...)`` — no MIST dependency (LOT-018 ticket 01).

Capability filtering, extra backends, and security gating are added by later
tickets; here the registry hard-codes DCS availability.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from dcs_bridge.serve.lua import LuaRaw, to_lua

# Backend adapter signature: build a Lua snippet from validated action args.
BackendBuilder = Callable[[dict[str, Any]], str]


class ActionError(ValueError):
    """Raised when an action cannot be built from the supplied arguments."""


@dataclass(frozen=True)
class Action:
    """An abstract verb with one backend adapter per available framework.

    Attributes:
        name: The verb name (e.g. ``spawn``).
        backends: Mapping of backend key (``dcs``/``mist``/``ctld``/``veaf``) to
            its Lua-snippet builder.
        preference: Backend keys in decreasing order of preference; the first one
            present is chosen when the caller does not force a backend.
    """

    name: str
    backends: dict[str, BackendBuilder]
    preference: tuple[str, ...]


# ---------------------------------------------------------------------------
# spawn — DCS-native backend
# ---------------------------------------------------------------------------

# kind → (Group.Category, default task) for coalition.addGroup.
_KIND_TO_CATEGORY: dict[str, str] = {
    "vehicle": "Group.Category.GROUND",
    "ship": "Group.Category.SHIP",
    "plane": "Group.Category.AIRPLANE",
    "helicopter": "Group.Category.HELICOPTER",
}

# coalition → default Lua country expression (overridable via args["country"]).
_COALITION_TO_COUNTRY: dict[str, str] = {
    "neutral": "country.id.USA",
    "red": "country.id.RUSSIA",
    "blue": "country.id.USA",
}

_COALITION_ALIASES: dict[int, str] = {0: "neutral", 1: "red", 2: "blue"}


def _resolve_coalition(raw: Any) -> str:
    """Normalise a coalition argument to ``"red"``/``"blue"``/``"neutral"``.

    Args:
        raw: A coalition name (str) or DCS coalition id (0/1/2).

    Returns:
        The canonical coalition name.

    Raises:
        ActionError: If the value is not a recognised coalition.
    """
    if isinstance(raw, bool):  # bool is an int subclass — reject explicitly
        raise ActionError(f"invalid coalition: {raw!r}")
    if isinstance(raw, int):
        name = _COALITION_ALIASES.get(raw)
        if name is None:
            raise ActionError(f"invalid coalition id: {raw}")
        return name
    if isinstance(raw, str):
        name = raw.strip().lower()
        if name in _COALITION_TO_COUNTRY:
            return name
    raise ActionError(f"invalid coalition: {raw!r}")


def _position_expr(position: Any) -> str:
    """Return a Lua expression yielding a point with ``.x``/``.z`` fields.

    Accepts a geographic position ``{"lat":.., "lon":..}`` (converted in-mission
    via ``coord.LLtoLO``) or native DCS coordinates ``{"x":.., "z":..}``.

    Args:
        position: The position mapping.

    Returns:
        A Lua expression (string) evaluating to a point table.

    Raises:
        ActionError: If the mapping has neither lat/lon nor x/z.
    """
    if not isinstance(position, dict):
        raise ActionError("position must be a mapping with lat/lon or x/z")
    if "lat" in position and "lon" in position:
        return f"coord.LLtoLO({to_lua(float(position['lat']))}, {to_lua(float(position['lon']))})"
    if "x" in position and "z" in position:
        return to_lua({"x": float(position["x"]), "z": float(position["z"])})
    raise ActionError("position requires either lat/lon or x/z")


def build_spawn_dcs(args: dict[str, Any]) -> str:
    """Build a DCS-native ``coalition.addGroup`` snippet for a ``spawn`` action.

    Args:
        args: Action arguments. Required: ``type`` (DCS type name) and
            ``position`` (lat/lon or x/z). Optional: ``kind`` (default
            ``"vehicle"``), ``coalition`` (default ``"blue"``), ``country`` (Lua
            country expression overriding the coalition default), ``name`` (group
            and unit base name), ``heading`` (radians, default ``0``), ``skill``
            (default ``"Average"``).

    Returns:
        A Lua snippet that spawns the group and returns the new group name.

    Raises:
        ActionError: If required arguments are missing or invalid.
    """
    type_name = args.get("type")
    if not isinstance(type_name, str) or not type_name:
        raise ActionError("spawn requires a non-empty 'type'")

    if "position" not in args:
        raise ActionError("spawn requires a 'position'")

    kind = str(args.get("kind", "vehicle")).lower()
    category = _KIND_TO_CATEGORY.get(kind)
    if category is None:
        raise ActionError(f"unsupported kind: {kind!r} (expected one of {sorted(_KIND_TO_CATEGORY)})")

    coalition = _resolve_coalition(args.get("coalition", "blue"))
    country_expr = str(args.get("country") or _COALITION_TO_COUNTRY[coalition])
    name = str(args.get("name") or f"dcs-bridge-{type_name}")
    heading = float(args.get("heading", 0.0))
    skill = str(args.get("skill", "Average"))

    pos_expr = _position_expr(args["position"])
    px, pz = LuaRaw("__pos.x"), LuaRaw("__pos.z")

    unit = {
        "type": type_name,
        "name": f"{name}-1",
        "x": px,
        "y": pz,
        "heading": heading,
        "skill": skill,
    }
    group_data = {
        "name": name,
        "task": "Ground Nothing",
        "x": px,
        "y": pz,
        "route": {"points": [{"x": px, "y": pz, "type": "Turning Point", "action": "Off Road", "speed": 0}]},
        "units": [unit],
    }

    return (
        f"local __pos = {pos_expr}\n"
        f"local __g = coalition.addGroup({country_expr}, {category}, {to_lua(group_data)})\n"
        f"return __g and __g:getName() or {to_lua(name)}"
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, Action] = {
    "spawn": Action(name="spawn", backends={"dcs": build_spawn_dcs}, preference=("dcs",)),
}


def get_action(name: str) -> Action | None:
    """Return the registered action by name, or ``None`` if unknown.

    Args:
        name: The verb name.

    Returns:
        The :class:`Action`, or ``None``.
    """
    return _REGISTRY.get(name)


def select_backend(action: Action, forced: str | None = None) -> str:
    """Pick the backend for an action.

    Args:
        action: The action whose backend is selected.
        forced: A backend key the caller wants to force (debug/repro), or ``None``
            to use the action's preference order.

    Returns:
        The chosen backend key.

    Raises:
        ActionError: If ``forced`` is not one of the action's backends, or no
            preferred backend is available.
    """
    if forced is not None:
        if forced not in action.backends:
            raise ActionError(f"backend {forced!r} not available for action {action.name!r}")
        return forced
    for backend in action.preference:
        if backend in action.backends:
            return backend
    raise ActionError(f"no backend available for action {action.name!r}")


def build_action_lua(name: str, args: dict[str, Any], *, backend: str | None = None) -> str:
    """Resolve an action and build its Lua snippet.

    Args:
        name: The verb name.
        args: Action arguments.
        backend: Optional forced backend key.

    Returns:
        The Lua snippet to execute in DCS.

    Raises:
        KeyError: If the action name is unknown.
        ActionError: If backend selection or snippet building fails.
    """
    action = get_action(name)
    if action is None:
        raise KeyError(name)
    chosen = select_backend(action, backend)
    return action.backends[chosen](args)
