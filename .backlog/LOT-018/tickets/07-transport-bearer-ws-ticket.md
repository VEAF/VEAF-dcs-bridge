# 07 — Transport: Bearer + ephemeral WS ticket, kill key-in-URL

Status: ✅ done
Type: fix

Ref: [ADR-0005](../../../docs/adr/0005-capability-aware-bridge.md) — decision *Transport*.

## What to build

- **REST**: `Authorization: Bearer <token>`; drop `X-API-Key` and the `api_key` query
  param.
- **WS**: ephemeral single-use ticket (~10 s TTL) obtained via authenticated REST, used to
  open the socket (browsers can't send custom WS headers).
- **WEB**: the WEB server holds the durable token and hands the browser only ephemeral
  tickets; `/config.json` no longer serves the key, no credential in the URL hash.

## Acceptance criteria

- [ ] No credential appears in any URL, log line, or `/config.json`.
- [ ] A leaked/expired ticket is rejected; REST requires Bearer.
- [ ] Unit tests: ticket issue/consume/expiry, Bearer auth. Quality gate green.

## Blocked by
Ticket 06 (tokens).
