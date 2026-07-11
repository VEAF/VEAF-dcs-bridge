"""Action registry and backend adapters (ADR-0005).

An :class:`Action` is an abstract, parameterised verb (e.g. ``spawn``) with one or
more backend adapters. Each adapter is a small ``(args) -> Lua snippet`` function
built on the :mod:`dcs_bridge.serve.lua` serialiser. An action also declares an
argument schema (:class:`ParamSpec`), a minimum role (placeholder until ticket 06)
and a supported-backends preference order.

The "what" (a DCS type, a smoke colour, later a VEAF keyphrase) is a **parameter**,
not a dedicated tool — the long tail lives as queryable data (see
:mod:`dcs_bridge.serve.catalog`), following ADR-0005 *Granularity*.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from dcs_bridge.serve.capabilities import CapabilityState
from dcs_bridge.serve.lua import LuaRaw, to_lua

# Backend adapter signature: build a Lua snippet from validated action args.
BackendBuilder = Callable[[dict[str, Any]], str]

# Global default backend preference — higher-level frameworks first (more
# integrated result), overridable per action (ADR-0005 *Backend preference*).
DEFAULT_PREFERENCE: tuple[str, ...] = ("veaf", "ctld", "mist", "dcs")


class ActionError(ValueError):
    """Raised when an action cannot be built from the supplied arguments."""


class ParamSpec(BaseModel):
    """Declaration of a single action parameter (for catalogue / discovery).

    Attributes:
        name: Parameter name.
        type: Coarse type hint (``string``/``number``/``position``/``enum``/
            ``coalition``).
        required: Whether the parameter must be supplied.
        description: Human-readable purpose.
        choices: Small inline enumeration of valid values, when short.
        catalog: Name of a value catalogue (see :mod:`dcs_bridge.serve.catalog`)
            holding the long tail of valid values, when too large to inline.
    """

    name: str
    type: str
    required: bool
    description: str
    choices: list[str] | None = None
    catalog: str | None = None


@dataclass(frozen=True)
class Action:
    """A parameterised verb with one backend adapter per supported framework.

    Attributes:
        name: The verb name (e.g. ``spawn``).
        summary: One-line description shown in the catalogue.
        params: The argument schema.
        backends: Mapping of backend key (``dcs``/``mist``/``ctld``/``veaf``) to
            its Lua-snippet builder.
        preference: Backend keys in decreasing order of preference; empty means
            use :data:`DEFAULT_PREFERENCE`. The first present backend is chosen
            when the caller does not force one.
        params: The argument schema.
        min_role: Minimum role required to run the action (enforced in ticket 06).
        backend_kinds: Optional per-backend restriction of the ``kind`` values a
            backend can handle (e.g. CTLD only does ``farp``/``fob``). A backend
            absent from this map handles every kind.
    """

    name: str
    summary: str
    backends: dict[str, BackendBuilder]
    preference: tuple[str, ...] = ()
    params: tuple[ParamSpec, ...] = field(default_factory=tuple)
    min_role: str = "operator"
    backend_kinds: dict[str, frozenset[str]] = field(default_factory=dict)

    @property
    def scope(self) -> str:
        """``"portable"`` when several backends can perform it, else ``"specific"``."""
        return "portable" if len(self.backends) > 1 else "specific"

    def ordered_preference(self) -> tuple[str, ...]:
        """Return the effective preference order (explicit, else global default)."""
        return self.preference or DEFAULT_PREFERENCE


# ---------------------------------------------------------------------------
# spawn — DCS-native backend
# ---------------------------------------------------------------------------

# kind → (Group.Category, default group task) for coalition.addGroup.
# The task must match the category — DCS rejects a "Ground Nothing" task on an
# air/naval group.
_KIND_TO_SPEC: dict[str, tuple[str, str]] = {
    "vehicle": ("Group.Category.GROUND", "Ground Nothing"),
    "ship": ("Group.Category.SHIP", "Nothing"),
    "plane": ("Group.Category.AIRPLANE", "Nothing"),
    "helicopter": ("Group.Category.HELICOPTER", "Nothing"),
}

# Structure kinds are spawned as static objects (DCS) or scenes (CTLD), not as
# unit groups. All spawn kinds understood by the verb:
_STRUCTURE_KINDS: frozenset[str] = frozenset({"farp", "fob"})

# structure kind → (DCS static category, type). DCS has no distinct FOB static
# type, so a FOB spawns as a FARP heliport; the kinds stay distinct at the API
# level (and map to different CTLD scenes below).
_STRUCTURE_STATIC_TYPES: dict[str, tuple[str, str]] = {
    "farp": ("Heliport", "FARP"),
    "fob": ("Heliport", "FARP"),
}

# structure kind → CTLD scene name (a mission-defined scene played by the CTLD
# scene manager).
_STRUCTURE_CTLD_SCENES: dict[str, str] = {
    "farp": "FARP",
    "fob": "FOB",
}
_UNIT_KINDS: frozenset[str] = frozenset(_KIND_TO_SPEC)
_SPAWN_KINDS: frozenset[str] = _UNIT_KINDS | _STRUCTURE_KINDS

# coalition → MIST country name (mist.dynAdd takes a country name string).
_COALITION_TO_MIST_COUNTRY: dict[str, str] = {
    "neutral": "USA",
    "red": "Russia",
    "blue": "USA",
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


def _as_float(value: Any, label: str) -> float:
    """Coerce a value to float, raising :class:`ActionError` on failure.

    Args:
        value: The value to coerce.
        label: Field name used in the error message.

    Returns:
        The value as a float.

    Raises:
        ActionError: If ``value`` cannot be interpreted as a number.
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ActionError(f"{label} must be numeric, got {value!r}") from None


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
        lat, lon = _as_float(position["lat"], "position.lat"), _as_float(position["lon"], "position.lon")
        return f"coord.LLtoLO({to_lua(lat)}, {to_lua(lon)})"
    if "x" in position and "z" in position:
        return to_lua({"x": _as_float(position["x"], "position.x"), "z": _as_float(position["z"], "position.z")})
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
    coalition = _resolve_coalition(args.get("coalition", "blue"))
    country_expr = str(args.get("country") or _COALITION_TO_COUNTRY[coalition])
    name = str(args.get("name") or f"dcs-bridge-{type_name}")
    heading = _as_float(args.get("heading", 0.0), "heading")
    pos_expr = _position_expr(args["position"])
    px, pz = LuaRaw("__pos.x"), LuaRaw("__pos.z")

    if kind in _STRUCTURE_KINDS:
        static_category, static_type = _STRUCTURE_STATIC_TYPES[kind]
        static_data = {
            "heading": heading,
            "name": name,
            "category": static_category,
            "type": static_type,
            "x": px,
            "y": pz,
            "dead": False,
        }
        return (
            f"local __pos = {pos_expr}\n"
            f"local __s = coalition.addStaticObject({country_expr}, {to_lua(static_data)})\n"
            f"return __s and __s:getName() or {to_lua(name)}"
        )

    spec = _KIND_TO_SPEC.get(kind)
    if spec is None:
        raise ActionError(f"unsupported kind: {kind!r} (expected one of {sorted(_SPAWN_KINDS)})")
    category, task = spec
    skill = str(args.get("skill", "Average"))

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
        "task": task,
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


def build_spawn_mist(args: dict[str, Any]) -> str:
    """Build a MIST ``mist.dynAdd`` snippet for a ``spawn`` action (unit kinds only).

    Args:
        args: Same schema as :func:`build_spawn_dcs`; ``kind`` must be a unit kind
            (``vehicle``/``ship``/``plane``/``helicopter``).

    Returns:
        A Lua snippet spawning the group via MIST and returning its name.

    Raises:
        ActionError: If arguments are missing/invalid or ``kind`` is a structure.
    """
    type_name = args.get("type")
    if not isinstance(type_name, str) or not type_name:
        raise ActionError("spawn requires a non-empty 'type'")
    if "position" not in args:
        raise ActionError("spawn requires a 'position'")

    kind = str(args.get("kind", "vehicle")).lower()
    if kind not in _UNIT_KINDS:
        raise ActionError(f"mist backend does not support kind {kind!r} (expected one of {sorted(_UNIT_KINDS)})")

    coalition = _resolve_coalition(args.get("coalition", "blue"))
    country = str(args.get("country") or _COALITION_TO_MIST_COUNTRY[coalition])
    name = str(args.get("name") or f"dcs-bridge-{type_name}")
    heading = _as_float(args.get("heading", 0.0), "heading")
    skill = str(args.get("skill", "Average"))

    pos_expr = _position_expr(args["position"])
    px, pz = LuaRaw("__pos.x"), LuaRaw("__pos.z")

    group_data = {
        "country": country,
        "category": kind,
        "name": name,
        "units": [{"type": type_name, "name": f"{name}-1", "x": px, "y": pz, "heading": heading, "skill": skill}],
    }
    return (
        f"local __pos = {pos_expr}\n"
        f"local __g = mist.dynAdd({to_lua(group_data)})\n"
        f"return __g and __g.name or {to_lua(name)}"
    )


def build_spawn_ctld(args: dict[str, Any]) -> str:
    """Build a CTLD v2 snippet for a ``spawn`` action (structure kinds only).

    Deploys a FARP/FOB via the CTLD scene manager (ADR-0005 *Execution*). Exact
    CTLD v2 signatures are pinned by the targeted version and validated in-mission.

    Args:
        args: ``kind`` must be ``farp``/``fob``; requires ``position``. Optional
            ``name`` (scene/site label).

    Returns:
        A Lua snippet playing the CTLD scene and returning the site name.

    Raises:
        ActionError: If ``kind`` is not a structure or ``position`` is missing.
    """
    if "position" not in args:
        raise ActionError("spawn requires a 'position'")
    kind = str(args.get("kind", "")).lower()
    if kind not in _STRUCTURE_KINDS:
        raise ActionError(f"ctld backend only spawns structures {sorted(_STRUCTURE_KINDS)}, not {kind!r}")

    name = str(args.get("name") or f"dcs-bridge-{kind}")
    scene = _STRUCTURE_CTLD_SCENES[kind]
    pos_expr = _position_expr(args["position"])
    return (
        f"local __pos = {pos_expr}\n"
        f"CTLDSceneManager:playSceneAtPos({to_lua(scene)}, __pos, {to_lua(name)})\n"
        f"return {to_lua(name)}"
    )


# ---------------------------------------------------------------------------
# smoke — DCS-native backend
# ---------------------------------------------------------------------------

_SMOKE_COLORS: dict[str, str] = {
    "green": "trigger.smokeColor.Green",
    "red": "trigger.smokeColor.Red",
    "white": "trigger.smokeColor.White",
    "orange": "trigger.smokeColor.Orange",
    "blue": "trigger.smokeColor.Blue",
}


def build_smoke_dcs(args: dict[str, Any]) -> str:
    """Build a DCS-native ``trigger.action.smoke`` snippet for a ``smoke`` action.

    Args:
        args: Action arguments. Required: ``position`` (lat/lon or x/z). Optional:
            ``color`` (default ``"green"``).

    Returns:
        A Lua snippet dropping the smoke and returning ``"smoke"``.

    Raises:
        ActionError: If ``position`` is missing/invalid or ``color`` is unknown.
    """
    if "position" not in args:
        raise ActionError("smoke requires a 'position'")
    color = str(args.get("color", "green")).lower()
    color_expr = _SMOKE_COLORS.get(color)
    if color_expr is None:
        raise ActionError(f"unknown smoke color: {color!r} (expected one of {sorted(_SMOKE_COLORS)})")

    pos_expr = _position_expr(args["position"])
    return (
        f"local __pos = {pos_expr}\n"
        f"local __p = {{x = __pos.x, y = land.getHeight({{x = __pos.x, y = __pos.z}}), z = __pos.z}}\n"
        f"trigger.action.smoke(__p, {color_expr})\n"
        f'return "smoke"'
    )


# ---------------------------------------------------------------------------
# remove — DCS-native backend
# ---------------------------------------------------------------------------


def build_remove_dcs(args: dict[str, Any]) -> str:
    """Build a DCS-native snippet removing a group by name for a ``remove`` action.

    Args:
        args: Action arguments. Required: ``name`` (group name to destroy).

    Returns:
        A Lua snippet destroying the group and returning ``"removed"`` (or
        ``"not found"`` if the group does not exist).

    Raises:
        ActionError: If ``name`` is missing or empty.
    """
    name = args.get("name")
    if not isinstance(name, str) or not name:
        raise ActionError("remove requires a non-empty 'name'")
    return (
        f"local __g = Group.getByName({to_lua(name)})\n"
        f'if __g then __g:destroy(); return "removed" else return "not found" end'
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, Action] = {
    "spawn": Action(
        name="spawn",
        summary="Spawn a unit or group at a position.",
        params=(
            ParamSpec(
                name="type", type="string", required=True, description="DCS type name.", catalog="dcs_unit_types"
            ),
            ParamSpec(name="position", type="position", required=True, description="Location as lat/lon or x/z."),
            ParamSpec(
                name="kind",
                type="enum",
                required=False,
                description="Unit category or structure.",
                choices=["vehicle", "ship", "plane", "helicopter", "farp", "fob"],
            ),
            ParamSpec(
                name="coalition",
                type="coalition",
                required=False,
                description="Owning coalition.",
                choices=["red", "blue", "neutral"],
            ),
        ),
        backends={"dcs": build_spawn_dcs, "mist": build_spawn_mist, "ctld": build_spawn_ctld},
        # Global preference (VMCT > CTLD > MIST > DCS); MIST does units, CTLD does
        # structures, DCS does both — so a FARP prefers CTLD then DCS, a vehicle
        # prefers MIST then DCS.
        backend_kinds={"mist": _UNIT_KINDS, "ctld": _STRUCTURE_KINDS},
        min_role="operator",
    ),
    "smoke": Action(
        name="smoke",
        summary="Drop a coloured smoke marker at a position.",
        params=(
            ParamSpec(name="position", type="position", required=True, description="Location as lat/lon or x/z."),
            ParamSpec(
                name="color",
                type="enum",
                required=False,
                description="Smoke colour.",
                choices=["green", "red", "white", "orange", "blue"],
            ),
        ),
        backends={"dcs": build_smoke_dcs},
        preference=("dcs",),
        min_role="pilot",
    ),
    "remove": Action(
        name="remove",
        summary="Remove (destroy) a group by name.",
        params=(ParamSpec(name="name", type="string", required=True, description="Group name to remove."),),
        backends={"dcs": build_remove_dcs},
        preference=("dcs",),
        min_role="operator",
    ),
}


def all_actions() -> list[Action]:
    """Return all registered actions, sorted by name.

    Returns:
        The list of :class:`Action` in the registry.
    """
    return [_REGISTRY[name] for name in sorted(_REGISTRY)]


def get_action(name: str) -> Action | None:
    """Return the registered action by name, or ``None`` if unknown.

    Args:
        name: The verb name.

    Returns:
        The :class:`Action`, or ``None``.
    """
    return _REGISTRY.get(name)


def select_backend(
    action: Action,
    caps: CapabilityState,
    args: dict[str, Any] | None = None,
    forced: str | None = None,
) -> str:
    """Pick the backend for an action, honouring capabilities and preference.

    Without ``forced``, the first backend that is declared, **present** (per
    ``caps``) and able to handle the requested ``kind`` (per
    :attr:`Action.backend_kinds`) in preference order is chosen. ``forced`` skips
    the presence/kind checks (debug/repro) but must still be a declared backend.

    Args:
        action: The action whose backend is selected.
        caps: The detected capability set.
        args: The action arguments (used to read ``kind``).
        forced: A backend key the caller wants to force, or ``None``.

    Returns:
        The chosen backend key.

    Raises:
        ActionError: If ``forced`` is not declared, or no present backend can
            handle the request.
    """
    if forced is not None:
        if forced not in action.backends:
            raise ActionError(f"backend {forced!r} not available for action {action.name!r}")
        return forced

    kind = str((args or {}).get("kind", "")).lower()
    for backend in action.ordered_preference():
        if backend not in action.backends or not caps.is_present(backend):
            continue
        allowed = action.backend_kinds.get(backend)
        if allowed is not None and kind not in allowed:
            continue
        return backend
    raise ActionError(f"no available backend for action {action.name!r}")


def build_action_lua(
    name: str,
    args: dict[str, Any],
    caps: CapabilityState,
    *,
    backend: str | None = None,
) -> str:
    """Resolve an action and build its Lua snippet.

    Args:
        name: The verb name.
        args: Action arguments.
        caps: The detected capability set (drives backend selection).
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
    chosen = select_backend(action, caps, args, backend)
    return action.backends[chosen](args)
