"""Tests for dcs_bridge.serve.actions — registry and DCS spawn adapter."""

from __future__ import annotations

from typing import Any

import pytest

from dcs_bridge.serve.actions import (
    ActionError,
    build_action_lua,
    build_spawn_dcs,
    get_action,
    select_backend,
)


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
        assert "dcs" in action.backends

    def test_unknown_action_is_none(self) -> None:
        assert get_action("does-not-exist") is None

    def test_select_backend_uses_preference(self) -> None:
        action = get_action("spawn")
        assert action is not None
        assert select_backend(action) == "dcs"

    def test_select_backend_forced_ok(self) -> None:
        action = get_action("spawn")
        assert action is not None
        assert select_backend(action, "dcs") == "dcs"

    def test_select_backend_forced_unavailable_raises(self) -> None:
        action = get_action("spawn")
        assert action is not None
        with pytest.raises(ActionError):
            select_backend(action, "mist")

    def test_build_action_lua_unknown_raises_keyerror(self) -> None:
        with pytest.raises(KeyError):
            build_action_lua("nope", {})


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
        lua = build_action_lua("spawn", _spawn_args())
        assert "coalition.addGroup(" in lua
