# Prérequis

## DCS World

dcs-bridge nécessite **DCS World** installé sur le serveur de mission (version Open Beta ou Stable).

Le script Lua `dcs-bridge.lua` doit être injecté dans chaque mission. Deux méthodes sont disponibles :

### Méthode 1 — MissionScripting.lua (persistant)

Ajouter la ligne suivante dans `DCS World/Scripts/MissionScripting.lua` :

```lua
dofile([[C:\chemin\vers\dcs-bridge.lua]])
```

Cette méthode charge le bridge pour **toutes les missions** de ce serveur.

### Méthode 2 — Trigger DO SCRIPT FILE (par mission)

Dans l'éditeur de mission DCS, créer un trigger :

- **Condition** : Mission Start
- **Action** : DO SCRIPT FILE → sélectionner `dcs-bridge.lua`

Cette méthode active le bridge uniquement pour la mission concernée.

## VMCT v6 (recommandé)

[VMCT v6](https://veaf.github.io/documentation/dev/) est l'outil VEAF recommandé pour injecter automatiquement `dcs-bridge.lua` dans vos missions sans modifier `MissionScripting.lua`.

Consultez la [documentation VEAF](https://veaf.github.io/documentation/dev/) pour les instructions d'installation et de configuration de VMCT.

## Machine hôte de dcs-serve

- **OS** : Windows 10/11, Linux, ou macOS
- **Python** : 3.11 ou supérieur (uniquement si vous installez via `pip` ou Poetry)
- **Réseau** : le serveur DCS doit pouvoir atteindre `dcs-serve` sur le port TCP configuré (défaut : 9999)
