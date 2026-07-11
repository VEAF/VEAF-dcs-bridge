# Lot LOT-016 — Vendor Leaflet locally in the web client

Status: 🔄 in-progress

**Effort**: S
**Branch**: fix/lot-016

## Problem Statement

The web client (`src/dcs_bridge/client/web/static/index.html`) loaded Leaflet 1.9.4
from the `unpkg.com` CDN with Subresource Integrity (SRI) hashes. The `leaflet.js`
`integrity` hash was **corrupted** (`…NV/XN2GqaE=` instead of the correct
`…NV1lvTlZBo=`), so browsers refused to execute the script:

```
None of the "sha256" hashes in the integrity attribute match … leaflet.js
Uncaught ReferenceError: L is not defined
```

The map never initialised. Beyond the specific typo, depending on an external CDN is
fragile for a tool that runs next to DCS, often on machines with no reliable internet.

Reproduced 2026-07-10 in Firefox against a local `dcs-client web`.

## Solution

Vendor the Leaflet 1.9.4 distribution into the served static tree and drop the CDN
dependency entirely:

- Add `static/vendor/leaflet/{leaflet.js,leaflet.css}` and the CSS-referenced
  `static/vendor/leaflet/images/*.png`, downloaded from unpkg and **verified against the
  official Leaflet 1.9.4 SRI hashes** before committing
  (js `sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=`,
  css `sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=`).
- Point `index.html` at the local files; remove the `integrity`/`crossorigin`
  attributes (no longer needed for same-origin assets).

Note: only the Leaflet library is vendored. The OpenStreetMap **tile layer** is still
fetched from the network at runtime — vendoring world tiles is out of scope; without
internet the library and markers work but the base map tiles are blank.

## User Stories

1. As a user launching `dcs-client web`, I want the map to render without depending on a
   third-party CDN, so a corrupted/blocked CDN asset can't break the whole client.
