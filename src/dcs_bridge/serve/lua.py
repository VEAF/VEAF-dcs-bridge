"""Python-to-Lua serialiser used by action backends to emit Lua snippets.

Backends build Lua by composing Python values (numbers, strings, lists, dicts)
into Lua literals with :func:`to_lua`. String escaping is centralised here so
that injection safety lives in one tested place (ADR-0005, decision *Execution*).

A :class:`LuaRaw` value is emitted verbatim (no quoting), which lets a backend
splice a Lua expression — e.g. ``country.id.USA`` or a reference to a local
variable — into an otherwise data-only table.
"""

from __future__ import annotations

import re
from typing import Any

# A Lua identifier usable as a bare table key (``foo = 1`` rather than ``["foo"] = 1``).
_LUA_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Lua reserved words cannot be used as bare keys.
_LUA_KEYWORDS = frozenset(
    {
        "and",
        "break",
        "do",
        "else",
        "elseif",
        "end",
        "false",
        "for",
        "function",
        "if",
        "in",
        "local",
        "nil",
        "not",
        "or",
        "repeat",
        "return",
        "then",
        "true",
        "until",
        "while",
    }
)

_STRING_ESCAPES = {
    "\\": "\\\\",
    '"': '\\"',
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
}


class LuaRaw:
    """A pre-formatted Lua expression emitted verbatim by :func:`to_lua`.

    Use this to splice a Lua reference (a global like ``country.id.USA`` or a
    local variable) into a table that :func:`to_lua` would otherwise quote.
    """

    __slots__ = ("expr",)

    def __init__(self, expr: str) -> None:
        """Store the raw Lua expression.

        Args:
            expr: Lua source emitted as-is (the caller guarantees its safety).
        """
        self.expr = expr

    def __repr__(self) -> str:
        """Return a debug representation."""
        return f"LuaRaw({self.expr!r})"

    def __eq__(self, other: object) -> bool:
        """Compare by wrapped expression (used in tests)."""
        return isinstance(other, LuaRaw) and other.expr == self.expr

    def __hash__(self) -> int:
        """Hash by wrapped expression."""
        return hash(self.expr)


def escape_string(value: str) -> str:
    """Escape a Python string into a double-quoted Lua string literal.

    Args:
        value: The raw string to escape.

    Returns:
        A Lua string literal including the surrounding double quotes.
    """
    out = []
    for ch in value:
        escaped = _STRING_ESCAPES.get(ch)
        if escaped is not None:
            out.append(escaped)
        elif ord(ch) < 0x20:
            out.append(f"\\{ord(ch)}")
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


def _format_key(key: str) -> str:
    """Format a dict key as a Lua table key.

    Args:
        key: The string key.

    Returns:
        ``key`` when it is a valid non-reserved identifier, otherwise
        ``["<escaped>"]``.
    """
    if _LUA_IDENTIFIER.match(key) and key not in _LUA_KEYWORDS:
        return key
    return f"[{escape_string(key)}]"


def to_lua(value: Any) -> str:
    """Serialise a Python value into a Lua literal.

    Supports ``None`` (→ ``nil``), ``bool``, ``int``/``float``, ``str`` (escaped),
    ``list``/``tuple`` (→ array table), ``dict`` (→ keyed table, string keys only),
    and :class:`LuaRaw` (emitted verbatim).

    Args:
        value: The Python value to serialise.

    Returns:
        A string of Lua source representing ``value``.

    Raises:
        TypeError: If ``value`` (or a nested element/key) has an unsupported type.
    """
    if isinstance(value, LuaRaw):
        return value.expr
    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, str):
        return escape_string(value)
    if isinstance(value, (list, tuple)):
        return "{" + ", ".join(to_lua(item) for item in value) + "}"
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"Lua table keys must be str, got {type(key).__name__}")
            parts.append(f"{_format_key(key)} = {to_lua(item)}")
        return "{" + ", ".join(parts) + "}"
    raise TypeError(f"Cannot serialise {type(value).__name__} to Lua")
