# 06 — Security: roles, tokens, per-action enforcement

Status: ⬜ ready
Type: feat

Ref: [ADR-0005](../../../docs/adr/0005-capability-aware-bridge.md) §8,9,10.

## What to build

- Roles `observer(0)/pilot(1)/operator(10)/administrator(90)/superuser(99+)`, aligned on
  VEAF levels.
- Token store (`{token, role, label, ucid?, expiry?}`), replacing the single API key.
- **Enforcement in the bridge**: each action's minimum role checked before execution;
  `exec_lua` gated to `superuser`. Resolved level propagated to VEAF (not relied upon).
- WEB delegated mode: resolve role from the connected user's UCID → `veaf-pilots.txt`,
  server-side only.

## Acceptance criteria

- [ ] An action is refused when the token's role is below its minimum; `exec_lua` requires
      `superuser`.
- [ ] Delegated (UCID→role) resolution happens server-side, never in the browser.
- [ ] Unit tests per role/action gate. Quality gate green.

## Blocked by
Ticket 03 (registry carries minimum-role).
