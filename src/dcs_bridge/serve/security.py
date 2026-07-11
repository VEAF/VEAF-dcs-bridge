"""Role-based security model — roles, tokens, level resolution (ADR-0005).

By injecting Lua into the mission the bridge occupies the same trusted position
as the VEAF server-hook, so enforcement lives **here**, not delegated to VEAF
(which bypasses its own security for `veafCommands.execute`). Each catalogue
action declares a minimum role; the bridge gates before executing. The single
API key is replaced by role-bearing tokens.
"""

from __future__ import annotations

import logging
import secrets
from enum import IntEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

# Default lifetime of an ephemeral WebSocket ticket, in seconds.
WS_TICKET_TTL = 10.0


class Role(IntEnum):
    """Bridge roles, aligned on VEAF security levels (ADR-0005 *Roles*).

    ``exec_lua`` (raw code) is isolated at ``SUPERUSER`` so VEAF admin can be
    granted without the raw RCE — the bridge is deliberately stricter than the
    hook (which allows code at ≥90).
    """

    OBSERVER = 0
    PILOT = 1
    OPERATOR = 10
    ADMINISTRATOR = 90
    SUPERUSER = 99


_ROLE_BY_NAME: dict[str, Role] = {r.name.lower(): r for r in Role}


def role_for_name(name: str) -> Role:
    """Resolve a role name (e.g. ``"operator"``) to a :class:`Role`.

    Args:
        name: Case-insensitive role name.

    Returns:
        The matching :class:`Role`.

    Raises:
        ValueError: If ``name`` is not a known role.
    """
    try:
        return _ROLE_BY_NAME[name.strip().lower()]
    except KeyError:
        raise ValueError(f"unknown role: {name!r} (expected one of {sorted(_ROLE_BY_NAME)})") from None


def role_for_level(level: int) -> Role:
    """Map a numeric VEAF level to the highest role it satisfies.

    Args:
        level: A VEAF security level.

    Returns:
        The highest :class:`Role` whose value is ``<= level`` (``OBSERVER`` floor).
    """
    best = Role.OBSERVER
    for role in sorted(Role, key=lambda r: r.value):
        if role.value <= level:
            best = role
    return best


def role_allows(role: Role, minimum: Role) -> bool:
    """Return whether ``role`` meets or exceeds ``minimum``.

    Args:
        role: The caller's role.
        minimum: The action's minimum required role.

    Returns:
        ``True`` if ``role >= minimum``.
    """
    return role >= minimum


class Token(BaseModel):
    """A role-bearing credential (replaces the single API key)."""

    model_config = ConfigDict(frozen=True)

    token: str
    role: Role
    label: str = ""
    ucid: str | None = None
    expiry: float | None = None  # epoch seconds; None = never expires


class TokenStore:
    """In-memory set of tokens, resolved by their opaque token string."""

    def __init__(self, tokens: list[Token]) -> None:
        """Index the given tokens by their token string.

        Args:
            tokens: The tokens to serve.
        """
        self._by_token: dict[str, Token] = {t.token: t for t in tokens}

    def resolve(self, token: str | None, *, now: float) -> Token | None:
        """Resolve a token string to a live :class:`Token`.

        Args:
            token: The presented token string (or ``None``).
            now: Current epoch seconds, for expiry checks.

        Returns:
            The matching non-expired :class:`Token`, or ``None``.
        """
        if not token:
            return None
        found = self._by_token.get(token)
        if found is None:
            return None
        if found.expiry is not None and now >= found.expiry:
            logger.info("token %r expired", found.label or found.token[:6])
            return None
        return found


class Ticket(BaseModel):
    """A single-use, short-lived credential to open a WebSocket from a browser."""

    model_config = ConfigDict(frozen=True)

    ticket: str
    role: Role
    ucid: str | None = None
    expiry: float  # epoch seconds


class TicketStore:
    """Issues and consumes ephemeral single-use WebSocket tickets (ADR-0005).

    A browser cannot send custom WS headers, so it first obtains a ticket over
    authenticated REST, then opens the socket with it. A ticket is single-use and
    expires after a few seconds, so a leaked ticket is already dead.
    """

    def __init__(self, ttl: float = WS_TICKET_TTL) -> None:
        """Initialise an empty ticket store.

        Args:
            ttl: Ticket lifetime in seconds.
        """
        self._ttl = ttl
        self._by_ticket: dict[str, Ticket] = {}

    @property
    def ttl(self) -> float:
        """The ticket lifetime in seconds."""
        return self._ttl

    def issue(self, token: Token, *, now: float, ticket: str | None = None) -> Ticket:
        """Issue a ticket carrying the caller's role, expiring after the TTL.

        Args:
            token: The authenticated token the ticket is derived from.
            now: Current epoch seconds.
            ticket: An explicit ticket string (tests); a random one otherwise.

        Returns:
            The issued :class:`Ticket`.
        """
        value = ticket or secrets.token_urlsafe(24)
        issued = Ticket(ticket=value, role=token.role, ucid=token.ucid, expiry=now + self._ttl)
        self._by_ticket[value] = issued
        return issued

    def consume(self, ticket: str | None, *, now: float) -> Ticket | None:
        """Consume a ticket, returning it once if valid (single-use).

        Args:
            ticket: The presented ticket string (or ``None``).
            now: Current epoch seconds, for expiry.

        Returns:
            The :class:`Ticket` if present and unexpired, else ``None``. The
            ticket is removed on the first lookup whether or not it had expired.
        """
        if not ticket:
            return None
        found = self._by_ticket.pop(ticket, None)
        if found is None:
            return None
        if now >= found.expiry:
            return None
        return found


def build_token_store(*, tokens: list[Token] | None = None, legacy_api_key: str = "") -> TokenStore:
    """Build a token store, optionally including a legacy superuser API key.

    The single pre-ADR-0005 API key is kept as a ``SUPERUSER`` token so existing
    clients keep working during the transition; scoped tokens are added on top.

    Args:
        tokens: Explicit scoped tokens.
        legacy_api_key: The historical single API key, mapped to ``SUPERUSER`` if
            non-empty.

    Returns:
        A populated :class:`TokenStore`.
    """
    all_tokens = list(tokens or [])
    if legacy_api_key:
        all_tokens.append(Token(token=legacy_api_key, role=Role.SUPERUSER, label="legacy-api-key"))
    return TokenStore(all_tokens)


def _coerce_role(raw_role: Any) -> Role:
    """Coerce a role given as a :class:`Role`, an integer level, or a name.

    Args:
        raw_role: The raw role value.

    Returns:
        The resolved :class:`Role`.

    Raises:
        ValueError: If a string name is unknown.
    """
    if isinstance(raw_role, Role):
        return raw_role
    if isinstance(raw_role, bool):  # bool is an int subclass — treat as a name
        raise ValueError(f"invalid role: {raw_role!r}")
    if isinstance(raw_role, int):
        return role_for_level(raw_role)
    return role_for_name(str(raw_role))


def tokens_from_records(records: list[dict[str, Any]]) -> list[Token]:
    """Build tokens from a list of plain dict records, skipping invalid ones.

    Args:
        records: Each with ``token`` and ``role`` (a :class:`Role`, an integer
            VEAF level, or a role name) and optional ``label``/``ucid``/``expiry``.

    Returns:
        The parsed tokens (records missing ``token``/``role`` or with an invalid
        role/expiry are logged and skipped, so one bad record does not drop the
        rest).
    """
    tokens: list[Token] = []
    for record in records:
        raw_token = record.get("token")
        raw_role = record.get("role")
        if not raw_token or raw_role is None:
            logger.warning("skipping token record without token/role: %r", record)
            continue
        try:
            role = _coerce_role(raw_role)
            expiry = float(record["expiry"]) if record.get("expiry") is not None else None
        except (ValueError, TypeError) as exc:
            logger.warning("skipping invalid token record %r: %s", record, exc)
            continue
        tokens.append(
            Token(
                token=str(raw_token),
                role=role,
                label=str(record.get("label", "")),
                ucid=(str(record["ucid"]) if record.get("ucid") is not None else None),
                expiry=expiry,
            )
        )
    return tokens


def load_tokens(path: Path) -> list[Token]:
    """Load scoped tokens from a YAML file (absent/invalid → empty list).

    Args:
        path: Path to a YAML file holding a list of token records.

    Returns:
        The parsed tokens.
    """
    if not path.exists():
        return []
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    except yaml.YAMLError as exc:
        logger.warning("failed to parse tokens file %s: %s; ignoring", path, exc)
        return []
    if not isinstance(raw, list):
        logger.warning("tokens file %s must be a list; ignoring", path)
        return []
    return tokens_from_records([r for r in raw if isinstance(r, dict)])


def parse_veaf_pilots(text: str) -> dict[str, int]:
    """Parse a ``veaf-pilots.txt`` mapping of UCID → level.

    Tolerant of the common formats: one entry per line, ``ucid`` and integer
    ``level`` separated by ``=``, ``,``, ``;`` or whitespace. Blank lines and
    lines starting with ``#``/``--`` are ignored.

    Args:
        text: The file contents.

    Returns:
        A mapping of UCID string → integer level (unparseable lines skipped).
    """
    entries: dict[str, int] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("--"):
            continue
        parts = [p for p in line.replace("=", " ").replace(",", " ").replace(";", " ").split() if p]
        if len(parts) < 2:
            continue
        ucid, level_str = parts[0], parts[1]
        try:
            entries[ucid] = int(level_str)
        except ValueError:
            continue
    return entries


def resolve_role_from_ucid(ucid: str, pilots: dict[str, int], *, default: Role = Role.OBSERVER) -> Role:
    """Resolve a connected user's UCID to a role via the pilots mapping.

    This runs **server-side only** (never in the browser) — the delegated mode of
    ADR-0005 *Credentials*.

    Args:
        ucid: The user's UCID.
        pilots: A UCID → level mapping (see :func:`parse_veaf_pilots`).
        default: Role for an unknown UCID.

    Returns:
        The resolved :class:`Role`.
    """
    level = pilots.get(ucid)
    if level is None:
        return default
    return role_for_level(level)
