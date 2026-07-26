# Prérequis

## DCS World

dcs-bridge nécessite **DCS World** installé sur le serveur de mission (version Open Beta ou Stable).

## Lever la sanitisation des scripts (obligatoire)

`dcs-bridge.lua` dialogue avec `dcs-serve` via une socket TCP, qu'il obtient avec
`require("socket")`. Or DCS **sanitise** le scripting de mission par défaut : avant
l'exécution du moindre script de mission, `MissionScripting.lua` supprime `require` ainsi
que les modules `os`, `io` et `lfs`. Sur une installation DCS intacte, le bridge échoue
donc dès sa première ligne et rien ne se connecte jamais.

Cette modification de votre installation DCS n'est à faire qu'une fois, et elle est
nécessaire **quelle que soit la méthode d'injection choisie ci-dessous** — y compris
VMCT, qui automatise l'injection du script mais ne lève pas le bac à sable.

**DCS étant fermé**, ouvrez `DCS World/Scripts/MissionScripting.lua` et retirez la
sanitisation : supprimez ou commentez tout ce qui se trouve sous la ligne commençant par

```lua
local function sanitizeModule(name)
```

!!! warning "Mesurez ce que vous autorisez"
    Lever la sanitisation permet à **n'importe quel** script de mission exécuté sur cette
    machine de lire et écrire des fichiers et de lancer des programmes. Ne le faites que
    sur un serveur dont vous maîtrisez les missions, et jamais pour ouvrir un `.miz` de
    provenance douteuse.

!!! note "À réappliquer après chaque mise à jour de DCS"
    Une mise à jour de DCS restaure le `MissionScripting.lua` d'origine, et le bridge
    cesse silencieusement de se connecter — cherchez l'erreur sur `require` dans
    `DCS.log`. Refaites cette modification après chaque mise à jour.

Plusieurs scripts DCS répandus exigent la même modification (DCS-SimpleTextToSpeech de
SRS, par exemple) : elle est peut-être déjà en place sur votre serveur.

## Injection du script

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
- **Réseau** : le serveur DCS doit pouvoir atteindre `dcs-serve` sur le port TCP configuré (défaut : 7777)
