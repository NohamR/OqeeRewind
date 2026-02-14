<p align="center">
    <img src="docs/images/logo_bg.png" width="256"> <a href="https://github.com/NohamR/OqeeRewind">OqeeRewind</a>
    <br/>
    <sup><em>Téléchargeur Oqee TV Live</em></sup>
</p>

<p align="center">
    <a href="https://github.com/NohamR/OqeeRewind/blob/master/LICENSE">
        <img src="https://img.shields.io/:license-MIT-blue.svg" alt="Licence">
    </a>
    <a href="https://github.com/astral-sh/uv">
        <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Onyx-Nostalgia/uv/refs/heads/fix/logo-badge/assets/badge/v0.json" alt="Gestionnaire: uv">
    </a>
    <a href="https://deepwiki.com/NohamR/OqeeRewind"><img src="https://deepwiki.com/badge.svg" alt="Demandez à DeepWiki"></a>
    <br>
    Français | <a href="README.md">English</a>
</p>

## Avertissement Légal

Cette application n'est pas affiliée à Oqee. Cette application vous permet de télécharger des vidéos pour une visualisation hors ligne, ce qui peut être interdit par la loi dans votre pays. L'utilisation de cette application peut également entraîner une violation des Conditions d'utilisation entre vous et le fournisseur de flux. Cet outil n'est pas responsable de vos actions ; veuillez prendre une décision éclairée avant d'utiliser cette application.

## Installation

### Prérequis
- Python 3.9+
- [uv](https://docs.astral.sh/uv/)
- Go ([Guide d'installation](https://go.dev/doc/install))
- ffmpeg
- [mp4ff-decrypt](https://github.com/Eyevinn/mp4ff)
```bash
go install github.com/Eyevinn/mp4ff/cmd/mp4ff-decrypt@latest
```

### Étapes
Clonez le dépôt et installez les dépendances :

```bash
git clone https://github.com/NohamR/OqeeRewind && cd OqeeRewind
uv sync
```

### Configuration
Le script supporte trois méthodes d'authentification, toutes détectées automatiquement :
1. Connexion par IP : Si vous êtes sur un réseau Free, l'authentification se fait automatiquement via votre adresse IP (aucun identifiant requis)
2. Compte Freebox : Utilisez vos identifiants de compte Free (nom d'utilisateur contenant "fbx")
3. Compte OQEE : Utilisez vos identifiants de compte OQEE standard

Créez un fichier `.env` dans le répertoire racine et ajoutez vos identifiants Oqee (la connexion par IP est utilisée en dernier recours si les identifiants échouent) :
```bash
OQEE_USERNAME=votre_nom_utilisateur
OQEE_PASSWORD=votre_mot_de_passe
```

Optionnellement, vous pouvez définir les variables d'environnement suivantes dans le fichier `.env` :
```bash
OUTPUT_DIR=./downloads
API_KEY=votre_cle_api_ici
API_URL=https://example.com/get-cached-keys
```

## Utilisation

### Mode Interactif
Si vous exécutez le script sans arguments, il vous guidera à travers la sélection des chaînes et le choix des dates.

```bash
uv run main.py
```
https://github.com/user-attachments/assets/54a50828-c0e9-4a29-81c7-e188c238a998


### Mode CLI
Vous pouvez automatiser le téléchargement en fournissant des arguments.

```bash
usage: main.py [-h] [--start-date START_DATE] [--end-date END_DATE]
               [--duration DURATION] [--channel-id CHANNEL_ID] [--video VIDEO]
               [--audio AUDIO] [--title TITLE] [--username USERNAME]
               [--password PASSWORD] [--key KEY] [--output-dir OUTPUT_DIR]
               [--widevine-device WIDEVINE_DEVICE]
               [--bruteforce-batch-size BRUTEFORCE_BATCH_SIZE]
               [--segment-batch-size SEGMENT_BATCH_SIZE] [--manifest]
               [--manifest-output MANIFEST_OUTPUT]
               [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}]
options:
  -h, --help            show this help message and exit
  --start-date START_DATE
                        Start date and time in YYYY-MM-DD HH:MM:SS format
  --end-date END_DATE   End date and time in YYYY-MM-DD HH:MM:SS format
  --duration DURATION   Duration in HH:MM:SS format (alternative to --end-date)
  --channel-id CHANNEL_ID
                        Channel ID to download from
  --video VIDEO         Video quality selection (e.g., 'best', '1080p', '720p', '1080p+best', '720p+worst')
  --audio AUDIO         Audio track selection (e.g., 'best', 'fra_main')
  --title TITLE         Title for the download (default: channel_id_start_date)
  --username USERNAME   Oqee username for authentication
  --password PASSWORD   Oqee password for authentication
  --key KEY             DRM key for decryption (can be specified multiple times)
  --output-dir OUTPUT_DIR
                        Output directory for downloaded files (default: ./downloads)
  --widevine-device WIDEVINE_DEVICE
                        Path to Widevine device file (default: ./widevine/device.wvd)
  --bruteforce-batch-size BRUTEFORCE_BATCH_SIZE
                        Batch size for bruteforce (default: 20000)
  --segment-batch-size SEGMENT_BATCH_SIZE
                        Batch size for segment downloads (default: 64)
  --manifest            Generate an MPD manifest file instead of downloading
  --manifest-output MANIFEST_OUTPUT
                        Output path for the generated manifest file (default: ./downloads/manifest.mpd)
  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the logging level (default: INFO)
```
https://github.com/user-attachments/assets/cc76990a-3d13-4be1-bb3c-ba8d87e6eaba


#### Exemples

**Télécharger un programme spécifique avec une durée :**
```bash
uv run main.py --channel-id 536 --start-date "2025-12-19 12:00:00" --duration "01:30:00" --video "1080p+best" --audio "best" --title "Enregistrement"
```

**Télécharger avec des clés DRM manuelles :**
```bash
uv run main.py --channel-id 536 --start-date "2025-12-19 12:00:00" --duration "00:05:00" --key "KID:KEY" --key "KID2:KEY2"
```

**Générer uniquement le manifeste MPD (sans téléchargement) :**
```bash
uv run main.py --channel-id 536 --start-date "2025-01-01 12:00:00" --manifest --manifest-output "./downloads/my_manifest.mpd"
```

## Déchiffrement DRM

### Instructions (Widevine)
Afin de déchiffrer le contenu DRM, vous devrez disposer d'un CDM dumpé, après quoi vous devrez placer les fichiers CDM dans le répertoire `./widevine/`. Pour des raisons légales, nous n'incluons pas le CDM avec le logiciel, et vous devrez vous en procurer un vous-même.

## À faire

### Terminé
- [x] Implémentation du bruteforce
- [x] Support des informations EPG
- [x] Licence
- [x] Linting du code
- [x] Implémentation de la licence Oqee Widevine (.wvd)
- [x] Implémentation complète
- [x] Vérification de l'installation de mp4ff
- [x] Implémentation des arguments CLI + documentation
- [x] Traduction complète Français/Anglais
- [x] Ajout de plus de commentaires dans le code
- [x] Système de journalisation
- [x] Améliorations du README :
    - [x] Bibliothèques utilisées
    - [x] Instructions d'utilisation
    - [x] Exigences d'installation (pip + mp4ff + ffmpeg)
    - [x] GIF de démonstration

### En cours
- [ ] Meilleur système de sortie
- [ ] Support du restream direct en direct


## Bibliothèques Utilisées
- [**aiohttp**](https://github.com/aio-libs/aiohttp) - Framework client/serveur HTTP asynchrone
- [**InquirerPy**](https://github.com/kazhala/InquirerPy) - Invites interactives en ligne de commande
- [**python-dotenv**](https://github.com/theskumar/python-dotenv) - Gestion des variables d'environnement
- [**pywidevine**](https://github.com/rlaphoenix/pywidevine) - Implémentation CDM Widevine
- [**Requests**](https://github.com/psf/requests) - Bibliothèque HTTP
