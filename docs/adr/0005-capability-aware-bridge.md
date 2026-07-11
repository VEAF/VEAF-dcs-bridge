---
status: accepted
---

# Capability-aware bridge — semantic action façade over DCS / MIST / CTLD / VMCT

Today dcs-bridge is a low-level passthrough: `exec_lua` (raw RCE), a `spawn` that
hard-requires MIST, `get_units`/`get_mission`, and a single tout-ou-rien API key. It
exposes DCS complexity instead of hiding it, and it can only use whatever the caller
knows how to script by hand.

We want a bridge that **exposes high-level semantic actions**, **knows** the frameworks
loaded in the running mission (DCS core, MIST, CTLD, VMCT/VEAF), **routes** each action
to the best available backend, and gates everything with a **role-based security model
aligned on VEAF's own levels**. The design below was settled through a full design
interview; each point was decided explicitly.

## Decision

### 1. Shape — semantic action façade (not a passthrough, not an agent)

The bridge exposes **abstract actions** (verbs like `spawn`). Each action has one or
more **backend adapters** (DCS / MIST / CTLD / VMCT). At runtime the bridge picks the
adapter based on **detected capabilities + a preference order**. This is deterministic
routing over **static knowledge**, not a per-request LLM decision — the "it chooses"
is backend selection, tool selection stays with the client (LLM via MCP, human via
TUI/WEB).

### 2. Catalogue = union (portable + specific)

The catalogue contains every verb that **at least one** backend can perform. Two
families: **portable** actions (same verb, several backends, the bridge arbitrates,
e.g. `spawn_farp`) and **specific** actions exposed only when their single backend is
present (e.g. a CTLD crate op, a VEAF-only keyphrase). Not the intersection — that
would waste CTLD/VMCT richness.

### 3. Granularity — parameterised verbs + a searchable catalogue

To avoid a 10,000-tool explosion (DCS unit types, VEAF keyphrases, CTLD variants): a
**handful of parameterised verbs** (`spawn`, `remove`, `smoke`, `run_keyphrase`, …)
where the "what" is a **parameter**, plus a discovery tool `search_catalog(query)` /
`describe(action)`. The long tail lives as **queryable data** held statically in the
bridge, not as tools — the same principle as tool-search: the client loads only what it
searches. "Flagship" actions (`spawn_farp`) are **catalogue entries** of the generic
verb (`spawn(kind="farp")`), not dedicated tools.

### 4. Placement — serve is the brain

- **Lua**: two roles only — (i) announce capabilities at handshake, (ii) execute the
  Lua the backend sends. No catalogue/routing in Lua.
- **serve (Python)**: the catalogue, the routing, and Lua generation. Exposed via a
  generic API — `GET /api/catalog` (filtered by detected capabilities),
  `POST /api/action {name, args}`, `search_catalog`.
- **clients (MCP/TUI/WEB)**: presentation + proxy only, no domain knowledge. MCP maps
  the catalogue onto its handful of tools.

Rationale: the brain is testable (pytest) / typed (mypy) / gated by the quality gate,
and the catalogue is **generated from the repos** (CTLD/VMCT/DCS datamine) — a Python
build job, not embedded Lua.

### 5. Capability detection — framework + version, lockstep

Grain = **framework + version** (`{dcs, mist?, ctld?, veaf?}`), each action declaring a
required backend. A framework means **the exact version dcs-bridge was built against**
(lockstep): detection checks equality, not `>=`. A mission running a different version
(e.g. CTLD v1 when we target v2) → that capability is treated as absent (fallback to a
lower backend). Fine-grained feature detection is only a fallback for odd cases.
Detected once at the **Lua↔serve handshake** (re-announced on reconnect / mission
change), **cached** serve-side, never re-probed per action.

### 6. Execution — adapter-code Python→Lua

Each (action × backend) pair is a **small Python function** `(args, ctx) → Lua snippet`,
built on a **Python→Lua serialiser** (positions, escaped strings, tables) that
centralises injection safety. A declarative template is too weak: VEAF **composes a
keyphrase string** (`veafCommands.execute(pos, "-farp …", coalition)`), CTLD **fills
typed parameters** (v2 managers, e.g. `CTLDSceneManager:playSceneAtPos("FOB", …)`), DCS
**builds a nested groupData** (`coalition.addGroup`), MIST uses `mist.dynAdd`. A backend
targets a single framework at its pinned version. VEAF shortcuts: catalogue the **VMCT
default alias list statically**; per-mission custom aliases are out of scope for now
(rare).

### 7. Backend preference — hybrid, per action

A **global default order** `VMCT > CTLD > MIST > DCS` (higher-level = more integrated
result), **overridable per action** in the catalogue (some actions gain nothing from a
given framework). The client may **force a backend** via an optional `backend=`
parameter (debug/repro).

### 8. Security model — the bridge is the trust authority

By injecting Lua into the mission, the bridge occupies the **same trusted position as
the VEAF server-hook**. VEAF will not protect it: `veafCommands.execute` always
bypasses `veafSecurity`, and `veafRemote.executeCommandFromRemote` trusts the passed
level blindly. Therefore **enforcement lives in the bridge, not delegated to VEAF**.
Each catalogue action declares a **minimum role**; the bridge gates before executing,
then propagates the level to VEAF (for the few modules that re-check, and for
traceability) — but security never relies on VEAF.

### 9. Roles — a discrete list aligned on VEAF levels

| VEAF level | Role | Allows |
|---|---|---|
| 0 | `observer` | read-only (units, mission, catalogue) |
| 1 | `pilot` | public actions (simple spawn, public keyphrases) |
| 10 | `operator` | the full catalogue of routine actions |
| 90 | `administrator` | + VEAF admin commands |
| 99+ | `superuser` | + raw `exec_lua` (arbitrary code) |

`exec_lua` is isolated at the top (`superuser`) so VEAF admin can be granted without the
raw RCE — the bridge is deliberately stricter than the hook (which allows code at ≥90).
`veaf-pilots.txt` stays the source of truth for the delegated (UCID→level) mode. The
server-lifecycle tiers (30/50) are out of scope (the bridge does not restart/halt DCS).

### 10. Credentials — role-bearing tokens

The single API key is replaced by **N tokens**, each carrying a role
(`{token, role, label, ucid?, expiry?}`, stored serve-side, separate from
`dcs-serve.yaml`).

- **M2M (MCP)**: token with a **fixed role**.
- **WEB (identified users)**: token **bound to the connected user**; the role is
  resolved either **delegated to VMCT** (user's UCID → `veaf-pilots.txt`) or **fixed by
  the WEB server**. UCID→role resolution happens **server-side, never in the browser**.

### 11. Transport — Bearer + ephemeral WS ticket

- **REST**: `Authorization: Bearer <token>` (no more query param, no more `X-API-Key`).
- **WS from a browser** (cannot carry custom headers — the current cause of the leak):
  **ephemeral single-use ticket** (~10 s TTL) obtained via authenticated REST, then used
  to open the WS. A leaked ticket is already dead.
- **WEB**: the WEB server holds the durable token and hands the browser **only ephemeral
  tickets** — the token/role never appears in HTML or `/config.json` (which stops
  serving the key). Kills the "key in the URL" leak that motivated this work.

## Consequences

- **Gains**: high-level actions that hide DCS complexity; minimal token footprint
  (resolved catalogue + search instead of thousands of tools); graduated security
  aligned on VEAF; no credential in URLs/logs.
- **Costs**: serve now **generates Lua** (adapters — kept testable by asserting the
  emitted Lua); the **catalogue must be generated from the repos** (build step);
  **version lockstep** (a dcs-bridge build is pinned per framework); the auth rework is a
  **breaking change** (single key → tokens; MCP/TUI/WEB must adopt Bearer + tickets).
- **`exec_lua` stays** but is gated to `superuser`; it also makes
  [LOT-017](../../.backlog/LOT-017/PRD.md) (actionable MCP error messages) and the
  MIST-only `spawn` limitation obsolete once the façade lands.
- **Framework-upgrade coordination** (consequence of the lockstep in *Capability
  detection*): bumping a targeted CTLD/VEAF/MIST version is itself a dcs-bridge release —
  update the adapters + version pins + regenerate the catalogue, validate against a
  mission running that version, then ship. Server missions are expected to move to the
  targeted versions in step; a mission left on an older framework simply **degrades that
  capability to a lower backend** (or drops it) rather than breaking. To avoid frequent
  mismatches, dcs-bridge releases should be aligned with the VEAF server framework-update
  cadence, and the detection log must make a version mismatch obvious.

## Open questions (not decided here)

- **Spatial/context resolution** ("spawn near my helo"): who resolves contextual
  references into a position (client, serve, Lua). Deferred.
- **Per-mission custom VEAF aliases**: runtime discovery, deferred (default list only).
- **Fine-grained feature detection** as a fallback when a framework version cannot be
  read cleanly.
- **Catalogue generation pipeline**: exact format and build tooling for the CTLD/VMCT/
  DCS-datamine knowledge base.
