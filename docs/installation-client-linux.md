# Installation du Client EPN sur Linux (Ubuntu 24.04)

## Prérequis

- Ubuntu 24.04 LTS (ou dérivé)
- Connexion réseau au serveur EPN
- Droits administrateur (sudo)

## Installation rapide (automatisée)

```bash
# Télécharger et exécuter le script d'installation
sudo ./scripts/install-client.sh --server 192.168.1.25 --token "votre-token-discovery"
```

## Installation manuelle

### 1. Dépendances système

```bash
sudo apt update && sudo apt upgrade -y

sudo apt install -y \
  build-essential \
  pkg-config \
  libssl-dev \
  libdbus-1-dev \
  libglib2.0-dev \
  libgtk-3-dev \
  libwebkit2gtk-4.1-dev \
  libayatana-appindicator3-dev \
  librsvg2-dev \
  libnotify-bin \
  xprintidle
```

### 2. Installation de Rust

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source ~/.cargo/env
```

### 3. Compilation du client

```bash
cd /chemin/vers/EPN_solutions/rust-client
cargo build --release
```

### 4. Installation des binaires

```bash
sudo mkdir -p /opt/epn-client
sudo mkdir -p /etc/epn-client
sudo cp target/release/epn-gui /opt/epn-client/
sudo chmod +x /opt/epn-client/epn-gui
```

### 5. Configuration

Créer `/etc/epn-client/config.yaml` :

```yaml
# ============== Connexion au serveur ==============
server_url: http://192.168.1.25:8001
ws_url: ws://192.168.1.25:8001

# ============== Token de découverte ==============
discovery_token: votre-token-ici

# ============== Comportement fin de session ==============
lock_on_expire: true
logout_on_expire: false
lock_delay_secs: 5

# ============== Nettoyage automatique ==============
enable_cleanup: true
cleanup_firefox: true
cleanup_libreoffice: true
cleanup_user_documents: true
cleanup_system_history: true

# ============== Surveillance d'inactivité ==============
inactivity_enabled: true
inactivity_warning_secs: 300
inactivity_timeout_secs: 600

# ============== Type de poste ==============
poste_type: bureautique
# poste_type: gaming
```

### 6. Création de l'utilisateur dédié

```bash
# Créer l'utilisateur "epn"
sudo useradd -m -s /bin/bash -c "Utilisateur EPN Public" epn

# Créer le dossier pour les certificats
sudo mkdir -p /home/epn/.epn-client
sudo chown epn:epn /home/epn/.epn-client
```

### 7. Configuration auto-login

#### Pour GDM (GNOME)

Éditer `/etc/gdm3/custom.conf` :

```ini
[daemon]
AutomaticLoginEnable=true
AutomaticLogin=epn
```

#### Pour LightDM (Xfce, LXDE, etc.)

Éditer `/etc/lightdm/lightdm.conf` :

```ini
[Seat:*]
autologin-user=epn
autologin-user-timeout=0
```

### 8. Service systemd

Créer `/etc/systemd/system/epn-client.service` :

```ini
[Unit]
Description=Client EPN - Gestion des postes publics
After=network-online.target graphical.target
Wants=network-online.target

[Service]
Type=simple
User=epn
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/epn/.Xauthority
ExecStart=/opt/epn-client/epn-gui
Restart=always
RestartSec=5

[Install]
WantedBy=graphical.target
```

Activer le service :

```bash
sudo systemctl daemon-reload
sudo systemctl enable epn-client
sudo systemctl start epn-client
```

## Enregistrement du poste

### Flux d'enregistrement

```
CLIENT                              SERVEUR
   │                                   │
   │  1. Connexion avec token          │
   │ ─────────────────────────────────►│
   │     (MAC, hostname, IP)           │
   │                                   │
   │  2. Poste créé "En attente"       │
   │ ◄─────────────────────────────────│
   │                                   │
   │      ┌─────────────────────┐      │
   │      │  ADMIN VALIDE LE    │      │
   │      │  POSTE DANS L'UI    │      │
   │      └─────────────────────┘      │
   │                                   │
   │  3. Certificat mTLS envoyé        │
   │ ◄─────────────────────────────────│
   │                                   │
   │  4. Client prêt                   │
   │ ══════════════════════════════════│
```

### Étapes

1. **Lancer le client** : Le service démarre automatiquement au boot
2. **Vérifier côté serveur** : Aller sur `http://serveur:3001` → Postes → "En attente"
3. **Valider le poste** : Cliquer "Valider" sur le nouveau poste
4. **Client prêt** : Le client reçoit son certificat et passe en mode opérationnel

## Utilisation

### Création d'une session (admin)

1. Interface admin → **Sessions** → **Nouvelle session**
2. Sélectionner utilisateur (ou "Session invité")
3. Sélectionner le poste
4. Définir la durée
5. Un code s'affiche (ex: `XK7M92`)

### Connexion (utilisateur)

1. L'écran affiche "Entrez votre code d'accès"
2. Saisir le code `XK7M92`
3. La session démarre

### Cycle de vie

| Temps restant | Événement |
|---------------|-----------|
| Session active | Compteur visible |
| 5 minutes | Notification orange |
| 1 minute | Notification rouge |
| 0 seconde | Nettoyage + Verrouillage |

| Inactivité | Événement |
|------------|-----------|
| 5 min sans activité | "Êtes-vous toujours là ?" |
| 10 min sans activité | Fin de session |

## Arborescence des fichiers

```
/opt/epn-client/
└── epn-gui                      # Binaire exécutable

/etc/epn-client/
└── config.yaml                  # Configuration

/home/epn/.epn-client/
├── client.crt                   # Certificat client (mTLS)
├── client.key                   # Clé privée
└── ca.crt                       # Certificat CA serveur

/etc/systemd/system/
└── epn-client.service           # Service systemd
```

## Dépannage

### Voir les logs du service

```bash
sudo journalctl -u epn-client -f
```

### Vérifier le statut

```bash
sudo systemctl status epn-client
```

### Tester la connexion au serveur

```bash
curl http://192.168.1.25:8001/api/health/
```

### Réinitialiser l'enregistrement

```bash
sudo rm -rf /home/epn/.epn-client/
sudo systemctl restart epn-client
```

### Lancer manuellement en mode debug

```bash
sudo -u epn DISPLAY=:0 RUST_LOG=debug /opt/epn-client/epn-gui
```

## Configuration Gaming (optionnel)

Pour un poste gaming, modifier `/etc/epn-client/config.yaml` :

```yaml
poste_type: gaming
gaming_enabled: true
gaming_auto_start_launchers:
  - steam
gaming_close_on_end: true
gaming_close_games_on_end: true
gaming_steam_big_picture: false
```

## Mode Kiosque

Le mode kiosque empêche les utilisateurs de fermer l'application ou d'accéder au bureau Ubuntu.

### Fonctionnalités

- **Plein écran forcé** : L'application s'affiche en plein écran
- **Pas de décorations** : Pas de barre de titre ni boutons de fenêtre
- **Toujours au premier plan** : L'application reste devant toutes les autres
- **Fermeture bloquée** : Impossible de fermer l'application (Alt+F4 désactivé)
- **Raccourcis système désactivés** : Alt+Tab, F11, Escape bloqués

### Configuration

Dans `/etc/epn-client/config.yaml` :

```yaml
# ============== Mode kiosque ==============
kiosk_mode: true
kiosk_admin_password: "votre-mot-de-passe-admin"
```

| Option | Type | Défaut | Description |
|--------|------|--------|-------------|
| `kiosk_mode` | bool | `true` | Active/désactive le mode kiosque |
| `kiosk_admin_password` | string | `null` | Mot de passe pour déverrouiller localement |

### Déverrouillage du mode kiosque

Il existe deux méthodes pour sortir du mode kiosque (pour la maintenance) :

#### 1. Déverrouillage local (raccourci clavier)

Appuyer sur **Ctrl+Alt+Shift+K** pour afficher la boîte de dialogue de mot de passe.
Entrer le mot de passe défini dans `kiosk_admin_password`.

#### 2. Déverrouillage à distance (interface admin)

1. Aller sur l'interface admin → **Postes**
2. Cliquer sur **Commandes** sur le poste concerné
3. Cliquer sur **Déverrouiller kiosque**

Le serveur envoie une commande WebSocket au client qui désactive le mode kiosque.

### Configuration GNOME (automatique)

Le script d'installation configure automatiquement GNOME pour :

- Masquer le dock Ubuntu
- Désactiver les raccourcis système (Super, Alt+Tab)
- Désactiver le bouton "Activités"
- Désactiver l'écran de verrouillage automatique GNOME

Ces paramètres sont appliqués via `gsettings` pour l'utilisateur `epn`.

### Configuration GNOME (manuelle)

Si vous n'utilisez pas le script d'installation, exécutez ces commandes :

```bash
# En tant qu'utilisateur epn
sudo -u epn dbus-launch gsettings set org.gnome.shell.extensions.dash-to-dock autohide true
sudo -u epn dbus-launch gsettings set org.gnome.shell.extensions.dash-to-dock dock-fixed false
sudo -u epn dbus-launch gsettings set org.gnome.shell.extensions.dash-to-dock intellihide true

# Désactiver les raccourcis système
sudo -u epn dbus-launch gsettings set org.gnome.desktop.wm.keybindings switch-applications "[]"
sudo -u epn dbus-launch gsettings set org.gnome.desktop.wm.keybindings switch-windows "[]"
sudo -u epn dbus-launch gsettings set org.gnome.mutter overlay-key ""
sudo -u epn dbus-launch gsettings set org.gnome.shell.keybindings toggle-overview "[]"

# Désactiver le bouton Activités
sudo -u epn dbus-launch gsettings set org.gnome.shell.extensions.dash-to-dock show-apps-button false

# Désactiver l'écran de verrouillage GNOME
sudo -u epn dbus-launch gsettings set org.gnome.desktop.screensaver lock-enabled false
sudo -u epn dbus-launch gsettings set org.gnome.desktop.session idle-delay 0
```

### Sécurité

> **Important** : Le mot de passe `kiosk_admin_password` est stocké en clair dans le fichier de configuration. Assurez-vous que le fichier `/etc/epn-client/config.yaml` a les permissions appropriées :
>
> ```bash
> sudo chmod 600 /etc/epn-client/config.yaml
> sudo chown root:root /etc/epn-client/config.yaml
> ```

### Désactiver le mode kiosque

Pour désactiver complètement le mode kiosque (développement/tests) :

```yaml
kiosk_mode: false
```

L'application se lancera alors comme une fenêtre normale.
