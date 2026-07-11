"""Tests for dcs_bridge.serve.actions — registry and DCS spawn adapter."""

from __future__ import annotations

from typing import Any

import pytest

from dcs_bridge.serve.actions import (
    ActionError,
    all_actions,
    build_action_lua,
    build_remove_dcs,
    build_smoke_dcs,
    build_spawn_ctld,
    build_spawn_dcs,
    build_spawn_mist,
    get_action,
    select_backend,
)
from dcs_bridge.serve.capabilities import CapabilityState

_TARGETS = {"dcs": None, "mist": "4.5.126", "ctld": "2.0", "veaf": "6"}


def _caps(**announced: str) -> CapabilityState:
    """Build a capability state with the announced frameworks present (DCS always)."""
    state = CapabilityState(_TARGETS)
    state.update(announced)
    return state


def _spawn_args(**overrides: Any) -> dict[str, Any]:
    args: dict[str, Any] = {
        "type": "Hummer",
        "kind": "vehicle",
        "coalition": "blue",
        "position": {"lat": 43.0, "lon": 1.5},
    }
    args.update(overrides)
    return args


class TestRegistry:
    def test_spawn_is_registered(self) -> None:
        action = get_action("spawn")
        assert action is not None
        assert {"dcs", "mist", "ctld"} <= set(action.backends)

    def test_unknown_action_is_none(self) -> None:
        assert get_action("does-not-exist") is None

    def test_build_action_lua_unknown_raises_keyerror(self) -> None:
        with pytest.raises(KeyError):
            build_action_lua("nope", {}, _caps())


class TestBackendSelection:
    def test_vehicle_prefers_dcs_when_alone(self) -> None:
        action = get_action("spawn")
        assert action is not None
        assert select_backend(action, _caps(), _spawn_args()) == "dcs"

    def test_vehicle_prefers_mist_over_dcs_when_present(self) -> None:
        action = get_action("spawn")
        assert action is not None
        assert select_backend(action, _caps(mist="4.5.126"), _spawn_args(kind="vehicle")) == "mist"

    def test_farp_prefers_ctld_when_present(self) -> None:
        action = get_action("spawn")
        assert action is not None
        assert select_backend(action, _caps(ctld="2.0"), _spawn_args(kind="farp")) == "ctld"

    def test_farp_falls_back_to_dcs_without_ctld(self) -> None:
        action = get_action("spawn")
        assert action is not None
        assert select_backend(action, _caps(), _spawn_args(kind="farp")) == "dcs"

    def test_ctld_not_chosen_for_vehicle(self) -> None:
        action = get_action("spawn")
        assert action is not None
        # ctld present but only handles structures → vehicle routes to dcs.
        assert select_backend(action, _caps(ctld="2.0"), _spawn_args(kind="vehicle")) == "dcs"

    def test_forced_backend_ok(self) -> None:
        action = get_action("spawn")
        assert action is not None
        assert select_backend(action, _caps(), _spawn_args(), forced="mist") == "mist"

    def test_forced_undeclared_backend_raises(self) -> None:
        action = get_action("spawn")
        assert action is not None
        with pytest.raises(ActionError):
            select_backend(action, _caps(), _spawn_args(), forced="veaf")

    def test_forced_backend_skips_kind_and_presence_checks(self) -> None:
        action = get_action("spawn")
        assert action is not None
        # ctld normally only handles structures and here is not even present,
        # but forcing it (debug/repro) bypasses both checks.
        assert select_backend(action, CapabilityState(_TARGETS), _spawn_args(kind="vehicle"), forced="ctld") == "ctld"

    def test_no_present_backend_raises(self) -> None:
        action = get_action("spawn")
        assert action is not None
        with pytest.raises(ActionError):
            select_backend(action, CapabilityState(_TARGETS), _spawn_args())  # nothing present


class TestSpawnDcs:
    def test_emits_add_group(self) -> None:
        lua = build_spawn_dcs(_spawn_args())
        assert "coalition.addGroup(" in lua

    def test_maps_vehicle_to_ground_category(self) -> None:
        lua = build_spawn_dcs(_spawn_args(kind="vehicle"))
        assert "Group.Category.GROUND" in lua

    def test_maps_ship_category(self) -> None:
        lua = build_spawn_dcs(_spawn_args(kind="ship"))
        assert "Group.Category.SHIP" in lua

    def test_blue_maps_to_usa(self) -> None:
        lua = build_spawn_dcs(_spawn_args(coalition="blue"))
        assert "country.id.USA" in lua

    def test_red_maps_to_russia(self) -> None:
        lua = build_spawn_dcs(_spawn_args(coalition="red"))
        assert "country.id.RUSSIA" in lua

    def test_coalition_accepts_int(self) -> None:
        lua = build_spawn_dcs(_spawn_args(coalition=1))
        assert "country.id.RUSSIA" in lua

    def test_type_name_present(self) -> None:
        lua = build_spawn_dcs(_spawn_args(type="M-2 Bradley"))
        assert '"M-2 Bradley"' in lua

    def test_latlon_uses_coord_lltolo(self) -> None:
        lua = build_spawn_dcs(_spawn_args(position={"lat": 43.0, "lon": 1.5}))
        assert "coord.LLtoLO(43.0, 1.5)" in lua

    def test_xz_position_literal(self) -> None:
        lua = build_spawn_dcs(_spawn_args(position={"x": 10.0, "z": 20.0}))
        assert "coord.LLtoLO" not in lua
        assert "x = 10.0" in lua and "z = 20.0" in lua

    def test_country_override(self) -> None:
        lua = build_spawn_dcs(_spawn_args(country="country.id.FRANCE"))
        assert "country.id.FRANCE" in lua

    def test_returns_group_name(self) -> None:
        lua = build_spawn_dcs(_spawn_args(name="alpha"))
        assert "getName()" in lua
        assert '"alpha"' in lua

    def test_missing_type_raises(self) -> None:
        args = _spawn_args()
        del args["type"]
        with pytest.raises(ActionError):
            build_spawn_dcs(args)

    def test_missing_position_raises(self) -> None:
        args = _spawn_args()
        del args["position"]
        with pytest.raises(ActionError):
            build_spawn_dcs(args)

    def test_unsupported_kind_raises(self) -> None:
        with pytest.raises(ActionError):
            build_spawn_dcs(_spawn_args(kind="submarine"))

    def test_invalid_coalition_raises(self) -> None:
        with pytest.raises(ActionError):
            build_spawn_dcs(_spawn_args(coalition="purple"))

    def test_bad_position_raises(self) -> None:
        with pytest.raises(ActionError):
            build_spawn_dcs(_spawn_args(position={"foo": 1}))

    def test_string_type_is_escaped(self) -> None:
        # A malicious type name must be escaped inside a Lua string, not spliced raw:
        # every double quote in the payload is backslash-escaped, so it cannot
        # close the Lua string literal and break out into code.
        lua = build_spawn_dcs(_spawn_args(type='x") os.execute("rm'))
        assert '\\"' in lua
        assert '"x") os.execute("rm"' not in lua  # no un-escaped break-out

    def test_ground_task_for_vehicle(self) -> None:
        lua = build_spawn_dcs(_spawn_args(kind="vehicle"))
        assert '"Ground Nothing"' in lua

    def test_non_ground_task_not_ground_nothing(self) -> None:
        lua = build_spawn_dcs(_spawn_args(kind="plane"))
        assert "Ground Nothing" not in lua
        assert '"Nothing"' in lua

    def test_non_numeric_position_raises_actionerror(self) -> None:
        with pytest.raises(ActionError):
            build_spawn_dcs(_spawn_args(position={"lat": "north", "lon": 1.5}))

    def test_non_numeric_heading_raises_actionerror(self) -> None:
        with pytest.raises(ActionError):
            build_spawn_dcs(_spawn_args(heading="sideways"))

    def test_build_via_registry(self) -> None:
        lua = build_action_lua("spawn", _spawn_args(), _caps())
        assert "coalition.addGroup(" in lua


class TestSpawnStructuresDcs:
    def test_farp_emits_static_object(self) -> None:
        lua = build_spawn_dcs(_spawn_args(kind="farp"))
        assert "coalition.addStaticObject(" in lua
        assert '"FARP"' in lua
        assert "addGroup" not in lua

    def test_fob_emits_static_object(self) -> None:
        lua = build_spawn_dcs(_spawn_args(kind="fob"))
        assert "coalition.addStaticObject(" in lua


class TestSpawnMist:
    def test_emits_dyn_add(self) -> None:
        lua = build_spawn_mist(_spawn_args())
        assert "mist.dynAdd(" in lua

    def test_blue_maps_to_usa_country_name(self) -> None:
        lua = build_spawn_mist(_spawn_args(coalition="blue"))
        assert '"USA"' in lua

    def test_red_maps_to_russia_country_name(self) -> None:
        lua = build_spawn_mist(_spawn_args(coalition="red"))
        assert '"Russia"' in lua

    def test_rejects_structure_kind(self) -> None:
        with pytest.raises(ActionError):
            build_spawn_mist(_spawn_args(kind="farp"))


class TestSpawnCtld:
    def test_farp_emits_scene(self) -> None:
        lua = build_spawn_ctld(_spawn_args(kind="farp"))
        assert "CTLDSceneManager:playSceneAtPos(" in lua
        assert '"FARP"' in lua

    def test_fob_uses_distinct_scene(self) -> None:
        lua = build_spawn_ctld(_spawn_args(kind="fob"))
        assert '"FOB"' in lua

    def test_rejects_unit_kind(self) -> None:
        with pytest.raises(ActionError):
            build_spawn_ctld(_spawn_args(kind="vehicle"))

    def test_requires_position(self) -> None:
        with pytest.raises(ActionError):
            build_spawn_ctld({"kind": "farp"})


class TestSmokeDcs:
    def test_emits_smoke_call(self) -> None:
        lua = build_smoke_dcs({"position": {"lat": 43.0, "lon": 1.5}, "color": "red"})
        assert "trigger.action.smoke(" in lua
        assert "trigger.smokeColor.Red" in lua

    def test_default_color_green(self) -> None:
        lua = build_smoke_dcs({"position": {"x": 1.0, "z": 2.0}})
        assert "trigger.smokeColor.Green" in lua

    def test_unknown_color_raises(self) -> None:
        with pytest.raises(ActionError):
            build_smoke_dcs({"position": {"lat": 1.0, "lon": 2.0}, "color": "chartreuse"})

    def test_missing_position_raises(self) -> None:
        with pytest.raises(ActionError):
            build_smoke_dcs({"color": "red"})


class TestRemoveDcs:
    def test_emits_destroy(self) -> None:
        lua = build_remove_dcs({"name": "Reaper-1"})
        assert "Group.getByName(" in lua
        assert '"Reaper-1"' in lua
        assert "destroy()" in lua

    def test_missing_name_raises(self) -> None:
        with pytest.raises(ActionError):
            build_remove_dcs({})

    def test_name_is_escaped(self) -> None:
        lua = build_remove_dcs({"name": 'a"b'})
        assert '\\"' in lua


class TestActionMetadata:
    def test_all_actions_sorted(self) -> None:
        names = [a.name for a in all_actions()]
        assert names == sorted(names)
        assert {"spawn", "smoke", "remove"} <= set(names)

    def test_spawn_has_param_schema(self) -> None:
        action = get_action("spawn")
        assert action is not None
        pnames = {p.name for p in action.params}
        assert {"type", "position", "kind", "coalition"} <= pnames

    def test_multi_backend_action_is_portable(self) -> None:
        action = get_action("spawn")
        assert action is not None
        assert action.scope == "portable"  # dcs + mist + ctld

    def test_single_backend_action_is_specific(self) -> None:
        action = get_action("smoke")
        assert action is not None
        assert action.scope == "specific"  # dcs only
