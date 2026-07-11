"""Capability detection — framework + version lockstep (ADR-0005).

At the Lua↔serve handshake the Lua bridge announces which frameworks are loaded
in the running mission and their versions. serve matches each announced version
against the **exact version this build targets** (lockstep, equality — not
``>=``); a mismatch marks that capability **absent** so routing falls back to a
lower backend. DCS is always present (no lockstep). The result is cached and
refreshed on reconnect / mission change, never re-probed per action.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

# The frameworks the bridge knows about, in a stable order.
FRAMEWORKS: tuple[str, ...] = ("dcs", "mist", "ctld", "veaf")

# The exact framework versions THIS build of dcs-bridge targets (lockstep).
# ``None`` means "no version lockstep" — the framework counts as present as soon
# as it is announced (DCS is the only such case). These strings must match the
# announced version verbatim; bumping a target is itself a dcs-bridge release
# (ADR-0005, *Framework-upgrade coordination*).
TARGETED_VERSIONS: Mapping[str, str | None] = {
    "dcs": None,
    "mist": "4.5.126",
    "ctld": "2.0",
    "veaf": "6",
}


class FrameworkStatus(BaseModel):
    """Detection result for a single framework."""

    model_config = ConfigDict(frozen=True)

    present: bool
    version: str | None
    targeted: str | None
    reason: str | None = None


def evaluate(framework: str, version: str | None, targeted: str | None) -> FrameworkStatus:
    """Decide whether a framework is usable, applying version lockstep.

    Args:
        framework: Framework key (``dcs``/``mist``/``ctld``/``veaf``).
        version: Version announced by the mission, or ``None`` if not loaded.
        targeted: The version this build targets, or ``None`` for no lockstep.

    Returns:
        A :class:`FrameworkStatus`. DCS is always present. A loaded framework
        with no lockstep is present. A version mismatch is reported absent.
    """
    if framework == "dcs":
        return FrameworkStatus(present=True, version=version, targeted=None)
    if version is None:
        return FrameworkStatus(present=False, version=None, targeted=targeted, reason="not loaded")
    if targeted is None:
        return FrameworkStatus(present=True, version=version, targeted=None)
    if version == targeted:
        return FrameworkStatus(present=True, version=version, targeted=targeted)
    return FrameworkStatus(
        present=False,
        version=version,
        targeted=targeted,
        reason=f"version mismatch (found {version}, targeted {targeted})",
    )


class CapabilityState:
    """Cached capability set for the currently connected mission.

    Updated from the Lua handshake and cleared on disconnect. Read by
    ``GET /api/capabilities`` and (later tickets) by catalogue filtering / routing.
    """

    def __init__(self, targeted: Mapping[str, str | None] = TARGETED_VERSIONS) -> None:
        """Initialise an empty capability state.

        Args:
            targeted: The per-framework targeted versions (overridable for tests).
        """
        self._targeted = targeted
        self._frameworks: dict[str, FrameworkStatus] = {}

    @property
    def frameworks(self) -> dict[str, FrameworkStatus]:
        """The last evaluated per-framework statuses (empty until a handshake)."""
        return dict(self._frameworks)

    def update(self, announced: Mapping[str, str | None]) -> None:
        """Re-evaluate all frameworks from a handshake announcement.

        Args:
            announced: Framework key → announced version (missing key or ``None``
                means the framework is not loaded). DCS is always evaluated.
        """
        result: dict[str, FrameworkStatus] = {}
        for framework in FRAMEWORKS:
            status = evaluate(framework, announced.get(framework), self._targeted.get(framework))
            result[framework] = status
            if status.reason == "not loaded":
                continue
            if status.present:
                logger.info("capability %s present (version=%s)", framework, status.version)
            else:
                logger.warning("capability %s absent — %s", framework, status.reason)
        self._frameworks = result

    def clear(self) -> None:
        """Forget all capabilities (called when the mission disconnects)."""
        self._frameworks = {}

    def is_present(self, framework: str) -> bool:
        """Return whether a framework is currently present at the targeted version.

        Args:
            framework: Framework key.

        Returns:
            ``True`` if detected and lockstep-matched, else ``False``.
        """
        status = self._frameworks.get(framework)
        return status is not None and status.present
