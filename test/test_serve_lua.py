"""Tests for dcs_bridge.serve.lua — the Python-to-Lua serialiser."""

from __future__ import annotations

import pytest

from dcs_bridge.serve.lua import LuaRaw, escape_string, to_lua


class TestScalars:
    def test_none_is_nil(self) -> None:
        assert to_lua(None) == "nil"

    def test_bool(self) -> None:
        assert to_lua(True) == "true"
        assert to_lua(False) == "false"

    def test_int(self) -> None:
        assert to_lua(42) == "42"
        assert to_lua(-7) == "-7"

    def test_float(self) -> None:
        assert to_lua(1.5) == "1.5"

    def test_bool_not_treated_as_int(self) -> None:
        # bool is an int subclass; it must serialise as a Lua boolean.
        assert to_lua(True) == "true"


class TestStrings:
    def test_plain_string(self) -> None:
        assert to_lua("Hummer") == '"Hummer"'

    def test_escapes_double_quote(self) -> None:
        assert escape_string('a"b') == '"a\\"b"'

    def test_escapes_backslash(self) -> None:
        assert escape_string("a\\b") == '"a\\\\b"'

    def test_escapes_newline_and_tab(self) -> None:
        assert escape_string("a\nb\tc") == '"a\\nb\\tc"'

    def test_escapes_control_char(self) -> None:
        assert escape_string("\x07") == '"\\7"'


class TestCollections:
    def test_list_is_array_table(self) -> None:
        assert to_lua([1, 2, 3]) == "{1, 2, 3}"

    def test_tuple_is_array_table(self) -> None:
        assert to_lua((1, "x")) == '{1, "x"}'

    def test_empty_list(self) -> None:
        assert to_lua([]) == "{}"

    def test_dict_identifier_key(self) -> None:
        assert to_lua({"x": 1}) == "{x = 1}"

    def test_dict_non_identifier_key_is_bracketed(self) -> None:
        assert to_lua({"1bad": 2}) == '{["1bad"] = 2}'

    def test_dict_reserved_word_key_is_bracketed(self) -> None:
        assert to_lua({"end": 1}) == '{["end"] = 1}'

    def test_nested_table(self) -> None:
        result = to_lua({"units": [{"type": "Hummer"}]})
        assert result == '{units = {{type = "Hummer"}}}'

    def test_non_string_key_raises(self) -> None:
        with pytest.raises(TypeError):
            to_lua({1: "x"})


class TestLuaRaw:
    def test_raw_emitted_verbatim(self) -> None:
        assert to_lua(LuaRaw("country.id.USA")) == "country.id.USA"

    def test_raw_inside_table(self) -> None:
        assert to_lua({"x": LuaRaw("__pos.x")}) == "{x = __pos.x}"

    def test_raw_equality(self) -> None:
        assert LuaRaw("a") == LuaRaw("a")
        assert LuaRaw("a") != LuaRaw("b")


class TestUnsupported:
    def test_unsupported_type_raises(self) -> None:
        with pytest.raises(TypeError):
            to_lua(object())
