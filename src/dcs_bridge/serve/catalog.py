"""Capability-filtered action catalogue + discovery (ADR-0005).

The catalogue is the **union** of every verb at least one backend can perform,
filtered to what the running mission actually supports. The long tail of valid
parameter values (DCS unit types, later VEAF keyphrases) is held here as
**queryable data**, not as tools: a client uses :func:`search_catalog` /
:func:`describe` to discover valid ``kind`` / keyphrase values without loading
the whole tail (ADR-0005 *Granularity*).
"""

from __future__ import annotations

from pydantic import BaseModel

from dcs_bridge.serve.actions import DEFAULT_PREFERENCE, Action, ParamSpec, all_actions, get_action
from dcs_bridge.serve.capabilities import CapabilityState


class CatalogValue(BaseModel):
    """A single value in a long-tail value catalogue.

    Attributes:
        value: The value passed to the action (e.g. ``"Hummer"``).
        label: A human-readable label (e.g. ``"HMMWV"``).
        tags: Free-form tags used for searching / grouping.
    """

    value: str
    label: str
    tags: list[str] = []


# Long-tail value catalogues referenced by ParamSpec.catalog. A representative
# sample for now; full generation from the DCS datamine / VMCT is a later build
# step (ADR-0005 open question *Catalogue-generation pipeline*).
VALUE_CATALOGUES: dict[str, list[CatalogValue]] = {
    "dcs_unit_types": [
        CatalogValue(value="Hummer", label="HMMWV (unarmed)", tags=["vehicle", "ground", "usa"]),
        CatalogValue(value="M-2 Bradley", label="M2A2 Bradley IFV", tags=["vehicle", "ground", "usa", "ifv"]),
        CatalogValue(value="M1A2", label="M1A2 Abrams MBT", tags=["vehicle", "ground", "usa", "tank"]),
        CatalogValue(value="T-72B", label="T-72B MBT", tags=["vehicle", "ground", "russia", "tank"]),
        CatalogValue(value="BTR-80", label="BTR-80 APC", tags=["vehicle", "ground", "russia", "apc"]),
        CatalogValue(value="Ural-375", label="Ural-375 truck", tags=["vehicle", "ground", "russia", "truck"]),
        CatalogValue(value="2S6 Tunguska", label="2S6 Tunguska SAM/AAA", tags=["vehicle", "ground", "russia", "sam"]),
        CatalogValue(value="Soldier M4", label="Infantry with M4", tags=["vehicle", "ground", "usa", "infantry"]),
    ],
    # VMCT default shortcut keyphrases (a representative sample; per-mission
    # custom aliases are out of scope — ADR-0005 open question). Values are the
    # marker keyphrase bases understood by veafCommands.execute.
    "veaf_shortcuts": [
        CatalogValue(value="-farp", label="Deploy a FARP", tags=["veaf", "structure", "farp"]),
        CatalogValue(value="-fob", label="Deploy a FOB", tags=["veaf", "structure", "fob"]),
        CatalogValue(value="-convoy", label="Spawn a ground convoy", tags=["veaf", "spawn", "ground", "convoy"]),
        CatalogValue(value="-cas", label="Spawn a CAS target group", tags=["veaf", "spawn", "ground", "cas"]),
        CatalogValue(value="-armor", label="Spawn an armored group", tags=["veaf", "spawn", "ground", "armor"]),
        CatalogValue(value="-infantry", label="Spawn an infantry group", tags=["veaf", "spawn", "ground", "infantry"]),
        CatalogValue(value="-sam", label="Spawn a SAM site", tags=["veaf", "spawn", "ground", "sam"]),
        CatalogValue(value="-tanker", label="Spawn a tanker track", tags=["veaf", "spawn", "air", "tanker"]),
        CatalogValue(value="-awacs", label="Spawn an AWACS orbit", tags=["veaf", "spawn", "air", "awacs"]),
        CatalogValue(value="-jtac", label="Spawn a JTAC", tags=["veaf", "spawn", "ground", "jtac"]),
        CatalogValue(value="-smoke", label="Drop VEAF smoke", tags=["veaf", "marker", "smoke"]),
        CatalogValue(value="-flare", label="Fire a signal flare", tags=["veaf", "marker", "flare"]),
    ],
}


class ActionInfo(BaseModel):
    """Catalogue view of an action, filtered by detected capabilities."""

    name: str
    summary: str
    scope: str
    min_role: str
    backends: list[str]
    available_backends: list[str]
    params: list[ParamSpec]


class ValueMatch(BaseModel):
    """A long-tail value that matched a search query."""

    catalog: str
    value: str
    label: str


class SearchResult(BaseModel):
    """Result of :func:`search_catalog`."""

    actions: list[ActionInfo]
    values: list[ValueMatch]


def available_backends(action: Action, caps: CapabilityState) -> list[str]:
    """Return the action's backends present in the mission, in preference order.

    Args:
        action: The action to inspect.
        caps: The detected capability set.

    Returns:
        Backend keys that are both declared and currently present.
    """
    order = action.preference or DEFAULT_PREFERENCE
    ordered = list(order) + [b for b in action.backends if b not in order]
    return [b for b in ordered if b in action.backends and caps.is_present(b)]


def _action_info(action: Action, caps: CapabilityState) -> ActionInfo:
    """Build the catalogue view of an action."""
    return ActionInfo(
        name=action.name,
        summary=action.summary,
        scope=action.scope,
        min_role=action.min_role,
        backends=sorted(action.backends),
        available_backends=available_backends(action, caps),
        params=list(action.params),
    )


def build_catalog(caps: CapabilityState) -> list[ActionInfo]:
    """Return the catalogue filtered by detected capabilities.

    An action is included when at least one of its backends is present. When no
    handshake has happened yet the capability set is empty, so nothing is
    available and the catalogue is empty.

    Args:
        caps: The detected capability set.

    Returns:
        The available actions, sorted by name.
    """
    infos = [_action_info(a, caps) for a in all_actions()]
    return [info for info in infos if info.available_backends]


def describe(name: str, caps: CapabilityState) -> dict[str, object] | None:
    """Describe one action, resolving its long-tail parameter values.

    Args:
        name: The action name.
        caps: The detected capability set (for the available-backends view).

    Returns:
        A dict with the action info plus a ``values`` map (param name → the value
        catalogue behind it), or ``None`` if the action is unknown.
    """
    action = get_action(name)
    if action is None:
        return None
    values: dict[str, list[CatalogValue]] = {}
    for param in action.params:
        if param.catalog and param.catalog in VALUE_CATALOGUES:
            values[param.name] = VALUE_CATALOGUES[param.catalog]
    info = _action_info(action, caps)
    return {"action": info.model_dump(), "values": {k: [v.model_dump() for v in vs] for k, vs in values.items()}}


def _action_matches(action: Action, query: str) -> bool:
    """Return True if an action matches a lowercase query."""
    if query in action.name.lower() or query in action.summary.lower():
        return True
    return any(query in p.name.lower() or query in p.description.lower() for p in action.params)


def search_catalog(query: str, caps: CapabilityState) -> SearchResult:
    """Search actions and long-tail values for a query string.

    Args:
        query: Case-insensitive substring. An empty query matches nothing.
        caps: The detected capability set (available actions only).

    Returns:
        Matching available actions and matching long-tail values.
    """
    q = query.strip().lower()
    if not q:
        return SearchResult(actions=[], values=[])

    infos = [info for info in build_catalog(caps) if _action_matches(get_action(info.name), q)]  # type: ignore[arg-type]

    values: list[ValueMatch] = []
    for catalog_name, entries in VALUE_CATALOGUES.items():
        for entry in entries:
            haystack = " ".join([entry.value, entry.label, *entry.tags]).lower()
            if q in haystack:
                values.append(ValueMatch(catalog=catalog_name, value=entry.value, label=entry.label))

    return SearchResult(actions=infos, values=values)
