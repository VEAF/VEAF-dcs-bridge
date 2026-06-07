# ADR-0001 : Conversion de coordonnées effectuée côté Lua

**Statut :** Accepté  
**Date :** 2026-06-07

## Contexte

Les unités DCS ont des positions en coordonnées natives DCS (système de projection plate, origine par théâtre). Les consommateurs de l'API ont besoin de lat/lon. La conversion doit se faire quelque part.

## Décision

Le Lua bridge effectue la conversion via les API DCS natives (`coord.LOtoLL()`, `land.getHeight()`) et envoie les deux représentations dans chaque message : `position_dcs` et `position_geo`.

## Alternatives considérées

**Conversion côté Python (dcs-serve)** : nécessite d'implémenter la projection par théâtre en Python (paramètres custom, non-standard). Des projets comme `dcs-liberation` l'ont fait, mais c'est fragile si ED modifie les paramètres, et représente un travail de maintenance non négligeable.

## Conséquences

- Lua envoie plus de données (~2x les coordonnées), impact négligeable sur TCP.
- Zéro logique de projection côté Python — serve est agnostique au théâtre.
- Fiabilité garantie : `coord.LOtoLL()` est l'API officielle DCS, maintenue par ED.
- Tout nouveau théâtre DCS fonctionne sans modification de `dcs-serve`.
