# ADR-0002 : Cache snapshot push-based dans dcs-serve

**Statut :** Accepté  
**Date :** 2026-06-07

## Contexte

`GET /api/units` doit répondre rapidement. Interroger DCS via TCP à chaque requête HTTP introduirait une latence de 100–5000ms (cycle de poll Lua + round-trip).

## Décision

`dcs-serve` maintient un Snapshot en mémoire mis à jour par deux mécanismes :
1. **Events** : le Lua bridge pousse les changements dès qu'ils arrivent.
2. **Full Refresh** : le Lua bridge envoie l'état complet toutes les 5 secondes.

`GET /api/units` sert toujours depuis le Snapshot. Si DCS est déconnecté, le Snapshot est marqué `stale: true` avec `last_updated`. Avant le premier Full Refresh, serve répond `503 { "ready": false }`.

## Alternatives considérées

**Stateless pur** : chaque `GET /api/units` déclenche un `exec_lua` pour lire l'état. Simple, mais latence imprévisible et charge CPU DCS proportionnelle aux clients connectés.

## Conséquences

- `dcs-serve` a un état interne — tests d'intégration nécessaires pour couvrir les cas stale/ready.
- Les clients WebSocket reçoivent les Events en temps réel + le Full Refresh toutes les 5s pour resynchroniser.
- La fraîcheur des données est bornée à 5s dans le pire cas (entre deux Full Refresh, sans Events).
