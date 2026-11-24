# JOAL pour Home Assistant

Intégration personnalisée pour piloter [JOAL](https://github.com/anthonyraymond/joal) depuis Home Assistant, via la même connexion WebSocket/STOMP que son interface web. Les mises à jour arrivent en temps réel, sans interrogation périodique.

## Prérequis

L'interface web de JOAL doit être activée :

```
--spring.main.web-environment=true
--server.port=PORT
--joal.ui.path.prefix=PREFIXE
--joal.ui.secret-token=TOKEN
```

## Installation

### Via HACS
1. HACS → menu ⋮ → **Dépôts personnalisés**
2. Ajoutez `https://github.com/bpoiriervernay-afk/hass-poirier`, catégorie **Intégration**
3. Installez **JOAL**, puis redémarrez Home Assistant

### Manuelle
Copiez `custom_components/joal` dans le dossier `config/custom_components/` de Home Assistant, puis redémarrez.

## Configuration

**Paramètres → Appareils et services → Ajouter une intégration → JOAL**

| Champ | Exemple |
|---|---|
| Adresse web | `http://192.168.1.10` ou `https://joal.exemple.fr` |
| Port | `8080` |
| Préfixe | valeur de `--joal.ui.path.prefix` |
| Secret token | valeur de `--joal.ui.secret-token` |

## Entités

| Type | Entité | Plage |
|---|---|---|
| Capteur | Nombre de torrents | — |
| Capteur | Vitesse d'émission | — |
| Capteur | Client actif | — |
| Nombre | Taux d'upload minimum | 1 – 10000 kB/s |
| Nombre | Taux d'upload maximum | 1 – 10000 kB/s |
| Nombre | Uploads simultanés | 1 – 500 |
| Nombre | Taux souhaité | 0.0 – 10.0 |
| Liste | Client de torrent | clients disponibles dans JOAL |
| Interrupteur | Ratio cible | désactivé = `-1` |
| Interrupteur | Garder les torrents sans peers | — |
| Interrupteur | Seed actif | démarre / arrête la session |

Le **taux souhaité** est mémorisé même quand le ratio cible est désactivé, et réappliqué à la réactivation.

## Dépannage

```yaml
logger:
  logs:
    custom_components.joal: debug
```

## Avertissement

Projet non officiel, sans lien avec JOAL ni son auteur. Respectez les règles des trackers que vous utilisez.
