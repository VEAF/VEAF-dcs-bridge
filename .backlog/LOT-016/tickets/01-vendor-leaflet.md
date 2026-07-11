# 01 — Vendor Leaflet 1.9.4 into the static tree

Status: ✅ done
Type: fix

## What to build

- Download Leaflet 1.9.4 `leaflet.js`, `leaflet.css`, and the CSS-referenced images into
  `src/dcs_bridge/client/web/static/vendor/leaflet/` (`images/` subfolder for the PNGs).
- Verify each downloaded file against the official Leaflet 1.9.4 SRI hash before adding
  it to the repo (supply-chain guard).
- Update `index.html`: reference `vendor/leaflet/leaflet.css` and
  `vendor/leaflet/leaflet.js`; remove the `integrity` and `crossorigin` attributes.
- No change to the WebSocket / marker logic.

## Acceptance criteria

- [x] `index.html` references local `vendor/leaflet/*` assets; no `unpkg.com`, no
      `integrity=` attribute.
- [x] `leaflet.js` / `leaflet.css` hashes match the official Leaflet 1.9.4 SRI values.
- [x] A `StaticFiles` mount serves `/vendor/leaflet/leaflet.js`, `.css`, and the images
      with HTTP 200 (covered by `test_web_server.py`).
- [x] Browser check: Leaflet loads (`L` defined, v1.9.4), `.leaflet-container`
      initialised, console clean (verified in the internal preview pane).
- [x] Quality gate green (ruff, mypy, pytest).

## Blocked by

None.
