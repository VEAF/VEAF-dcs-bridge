# ADR-0003 : Reconnexion TCP Lua bridge — retry infini avec backoff exponentiel

**Statut :** Accepté  
**Date :** 2026-06-07

## Contexte

Le Lua bridge ouvre une connexion TCP sortante vers `dcs-serve`. Si `dcs-serve` est indisponible (redémarrage, crash réseau), le bridge doit gérer la reconnexion sans bloquer la mission DCS.

Le scheduler Lua (`timer.scheduleFunction`) tourne dans le thread de simulation — tout blocage gèle la mission.

## Décision

Retry infini avec backoff exponentiel. Après N secondes sans connexion établie, un warning est émis dans le log DCS. Le backoff est plafonné à une valeur max configurable (défaut 60s). La mission continue normalement pendant les tentatives.

La socket est configurée avec un timeout très court (`settimeout(0.0001)`) — les appels sont non-bloquants.

## Alternatives considérées

**Witchcraft (retry immédiat sans backoff)** : retry à chaque step (100ms) — génère du bruit dans les logs et charge CPU inutile lors d'une indisponibilité longue.

**Abandon après N secondes** : simple, mais perd la connexion définitivement si serve redémarre plus tard. Inacceptable pour un outil de monitoring de mission longue durée.

## Conséquences

- La mission DCS reste jouable même si `dcs-serve` est absent.
- Le log DCS signale clairement l'indisponibilité du bridge sans spammer.
- `dcs-serve` peut redémarrer à tout moment — le bridge se reconnecte automatiquement.
