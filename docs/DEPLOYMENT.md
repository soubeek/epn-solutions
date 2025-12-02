# Guide de Déploiement - EPN Solutions

Guide complet pour déployer le système de gestion des postes publics en production.

**Version** : 2.0.0
**Date** : 28 novembre 2025
**Pour** : Mairie de La Réunion

---

## Table des Matières

1. [Vue d'Ensemble](#vue-densemble)
2. [Prérequis](#prérequis)
3. [Déploiement du Serveur](#déploiement-du-serveur)
4. [Certificats SSL](#certificats-ssl)
5. [Déploiement des Clients](#déploiement-des-clients)
6. [Déploiement en Masse (Ansible)](#déploiement-en-masse-ansible)
7. [Vérifications](#vérifications)
8. [Maintenance](#maintenance)
9. [Troubleshooting](#troubleshooting)

---

## Vue d'Ensemble

### Architecture de Production

```
                        ┌─────────────────────┐
                        │     INTERNET        │
                        └──────────┬──────────┘
                                   │
                        ┌──────────▼──────────┐
                        │  Traefik (HTTPS)    │
                        │  Ports 80/443       │
                        │  Certificats SSL    │
                        └──────────┬──────────┘
                                   │
          ┌────────────────────────┼────────────────────────┐
          │                        │                        │
   ┌──────▼──────┐        ┌───────▼───────┐        ┌──────▼──────┐
   │  Frontend   │        │    Django     │        │   Nginx     │
   │   Vue.js    │        │   Daphne      │        │   Static    │
   │   (SPA)     │        │  (API + WS)   │        │  (media)    │
   └─────────────┘        └───────┬───────┘        └─────────────┘
                                  │
            ┌─────────────────────┼─────────────────────┐
            │                     │                     │
     ┌──────▼──────┐      ┌──────▼──────┐      ┌──────▼──────┐
     │ PostgreSQL  │      │    Redis    │      │   Celery    │
     │   (BDD)     │      │  (Cache/WS) │      │  (Tâches)   │
     └─────────────┘      └─────────────┘      └─────────────┘

   ┌─────────────────────────────────────────────────────────────┐
   │                    POSTES CLIENTS                           │
   │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
   │  │ Linux   │  │ Linux   │  │ Windows │  │ Windows │  ...   │
   │  │ Client  │  │ Client  │  │ Client  │  │ Client  │        │
   │  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │
   └─────────────────────────────────────────────────────────────┘
```

### Composants

**Serveur (Docker Compose) :**
| Service | Description | Port |
|---------|-------------|------|
| Traefik | Reverse proxy + TLS | 80, 443 |
| Django/Daphne | API REST + WebSocket | 8000 (interne) |
| PostgreSQL | Base de données | 5432 (interne) |
| Redis | Cache + Channel Layer | 6379 (interne) |
| Celery Worker | Tâches asynchrones | - |
| Celery Beat | Tâches planifiées | - |
| Frontend | Interface admin Vue.js | 80 (interne) |
| Pi-hole | DNS filtré (optionnel) | 53 |

**Client Rust/Tauri :**
- Application native cross-platform
- Communication WebSocket temps réel
- Verrouillage écran automatique
- Service systemd (Linux) / Service Windows

---

## Prérequis

### Serveur

**Matériel minimum :**
- CPU : 2 cores
- RAM : 4 GB
- Disque : 40 GB SSD
- Réseau : 100 Mbps

**Logiciels :**
- OS : Ubuntu 22.04+ / Debian 12+
- Docker 24.0+
- Docker Compose 2.20+
- OpenSSL (pour les certificats)

**Installation Docker :**
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Vérification
docker --version
docker compose version
```

### Clients Linux

**Matériel minimum :**
- CPU : 1 core
- RAM : 2 GB
- Disque : 1 GB

**Logiciels :**
- OS : Debian 11+ / Ubuntu 22.04+ / Arch Linux
- WebKit2GTK 4.1 (pour l'interface Tauri)
- libssl

```bash
# Debian/Ubuntu
sudo apt install -y libwebkit2gtk-4.1-0 libssl3

# Arch Linux
sudo pacman -S webkit2gtk-4.1 openssl
```

### Clients Windows

**Matériel minimum :**
- CPU : 1 core
- RAM : 2 GB
- Disque : 500 MB

**Logiciels :**
- Windows 10/11 (64-bit)
- WebView2 Runtime (inclus dans Windows 11, téléchargeable pour Windows 10)

---

## Déploiement du Serveur

### Étape 1 : Cloner le projet

```bash
# Sur le serveur
cd /opt
sudo git clone <url-repo> epn-solutions
sudo chown -R $USER:$USER epn-solutions
cd epn-solutions/docker
```

### Étape 2 : Générer les certificats SSL

```bash
# Rendre le script exécutable
chmod +x scripts/generate-certificates.sh

# Générer les certificats
# Remplacez par votre domaine et IP
./scripts/generate-certificates.sh \
    -d postes.mairie.local \
    -i 192.168.1.10 \
    -o ./certs
```

Le script génère :
- `ca.key` - Clé privée de l'autorité de certification (GARDER SECRET)
- `ca.crt` - Certificat CA (à distribuer aux clients)
- `server.key` - Clé privée du serveur
- `server.crt` - Certificat du serveur

### Étape 3 : Configurer l'environnement

```bash
# Copier le fichier exemple
cp .env.example .env

# Éditer la configuration
nano .env
```

**Configuration `.env` :**
```bash
# === DOMAINE ET RÉSEAU ===
SERVER_FQDN=postes.mairie.local
SERVER_IP=192.168.1.10
DOMAIN_NAME=mairie.local

# === BASE DE DONNÉES ===
POSTGRES_DB=poste_public
POSTGRES_USER=admin
POSTGRES_PASSWORD=VotreMotDePasseSecurise123!

# === DJANGO ===
SECRET_KEY=VotreCleSecreteUniqueEtLongue123456789
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@mairie.local
DJANGO_SUPERUSER_PASSWORD=AdminPassword123!
ALLOWED_HOSTS=postes.mairie.local,localhost,127.0.0.1

# === CORS ===
CORS_ALLOWED_ORIGINS=https://postes.mairie.local

# === TIMEZONE ===
TZ=Indian/Reunion

# === PI-HOLE (optionnel) ===
PIHOLE_PASSWORD=PiholePassword123!

# === TRAEFIK ===
# Générer avec: htpasswd -nb admin password
TRAEFIK_AUTH=admin:$$apr1$$xyz...
```

**Générer une SECRET_KEY :**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

**Générer TRAEFIK_AUTH :**
```bash
# Installer htpasswd si nécessaire
sudo apt install apache2-utils

# Générer le hash (doubler les $ pour docker-compose)
htpasswd -nb admin VotrePassword | sed 's/\$/\$\$/g'
```

### Étape 4 : Démarrer les services

```bash
# Démarrage avec certificats auto-signés (utilise docker-compose.override.yml)
docker compose up -d

# Vérifier les logs
docker compose logs -f

# Vérifier l'état des services
docker compose ps
```

**Sans Pi-hole (DNS filtré) :**
```bash
# Les services Pi-hole et Cloudflared sont optionnels
# Ils ne démarrent que si vous utilisez le profil dns-filtering
docker compose up -d

# OU avec filtrage DNS :
docker compose --profile dns-filtering up -d
```

### Étape 5 : Vérifier le déploiement

```bash
# Test API
curl -k https://localhost/api/health/

# Test avec le domaine (si DNS configuré)
curl --cacert certs/ca.crt https://postes.mairie.local/api/health/

# Accéder à l'admin Django
# https://postes.mairie.local/admin/

# Accéder au dashboard Traefik
# https://traefik.mairie.local/
```

---

## Certificats SSL

### Structure des certificats

```
docker/certs/
├── ca.key          # Clé privée CA (NE PAS DISTRIBUER)
├── ca.crt          # Certificat CA (à installer sur les clients)
├── server.key      # Clé privée serveur
└── server.crt      # Certificat serveur
```

### Installation sur les clients

#### Linux (Debian/Ubuntu)

```bash
# Copier le certificat CA
sudo cp ca.crt /usr/local/share/ca-certificates/epn-ca.crt

# Mettre à jour le magasin de certificats
sudo update-ca-certificates

# Vérifier
ls -la /etc/ssl/certs/ | grep epn
```

#### Linux (Arch Linux)

```bash
# Copier le certificat CA
sudo cp ca.crt /etc/ca-certificates/trust-source/anchors/epn-ca.crt

# Mettre à jour
sudo trust extract-compat
```

#### Windows

**Méthode graphique :**
1. Double-cliquer sur `ca.crt`
2. Cliquer "Installer le certificat..."
3. Sélectionner "Ordinateur local"
4. Sélectionner "Placer tous les certificats dans le magasin suivant"
5. Parcourir → "Autorités de certification racines de confiance"
6. Terminer l'installation

**Méthode PowerShell (administrateur) :**
```powershell
# Importer le certificat CA
Import-Certificate -FilePath "C:\chemin\vers\ca.crt" `
    -CertStoreLocation Cert:\LocalMachine\Root
```

**Méthode GPO (déploiement en masse) :**
1. Ouvrir "Gestion des stratégies de groupe"
2. Créer/éditer une GPO
3. Configuration ordinateur → Paramètres Windows → Paramètres de sécurité
4. Stratégies de clé publique → Autorités de certification racines de confiance
5. Importer le certificat ca.crt

### Renouvellement des certificats

```bash
# Les certificats serveur sont valides 2 ans
# Les certificats CA sont valides 10 ans

# Vérifier l'expiration
openssl x509 -in certs/server.crt -noout -dates

# Régénérer (force l'écrasement)
./scripts/generate-certificates.sh -d postes.mairie.local -i 192.168.1.10 -f

# Redémarrer Traefik
docker compose restart traefik
```

---

## Déploiement des Clients

### Client Linux

#### Étape 1 : Compiler le client (sur machine de développement)

```bash
cd rust-client

# Installer les dépendances Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env

# Compiler en release
cargo build --release

# Le binaire est dans target/release/epn-client
```

#### Étape 2 : Installer sur le poste client

```bash
# Copier les fichiers sur le client
scp target/release/epn-client admin@poste-01:/tmp/
scp docker/certs/ca.crt admin@poste-01:/tmp/

# Se connecter au client
ssh admin@poste-01

# Installer le certificat CA
sudo cp /tmp/ca.crt /usr/local/share/ca-certificates/epn-ca.crt
sudo update-ca-certificates

# Installer le binaire
sudo cp /tmp/epn-client /usr/local/bin/
sudo chmod 755 /usr/local/bin/epn-client

# Créer le répertoire de configuration
sudo mkdir -p /etc/epn-client

# Créer la configuration
sudo tee /etc/epn-client/config.yaml << 'EOF'
# Configuration EPN Client
server_url: https://postes.mairie.local
ws_url: wss://postes.mairie.local/ws
poste_id: POSTE-01

# Intervalles (secondes)
heartbeat_interval: 30
reconnect_delay: 5

# Comportement
warning_time: 300      # Avertissement 5 min avant fin
critical_time: 60      # Alerte critique 1 min avant fin
enable_screen_lock: true
lock_on_expire: true
logout_on_expire: false

# Logs
log_level: info
log_file: /var/log/epn-client/client.log
EOF

# Créer le répertoire de logs
sudo mkdir -p /var/log/epn-client
sudo chown root:root /var/log/epn-client
```

#### Étape 3 : Créer le service systemd

```bash
sudo tee /etc/systemd/system/epn-client.service << 'EOF'
[Unit]
Description=EPN Client - Gestion des sessions postes publics
Documentation=https://github.com/mairie/epn-solutions
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/epn-client --config /etc/epn-client/config.yaml
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=epn-client

# Sécurité
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/log/epn-client

# Environnement
Environment=DISPLAY=:0
Environment=RUST_LOG=info

[Install]
WantedBy=multi-user.target
EOF

# Activer et démarrer le service
sudo systemctl daemon-reload
sudo systemctl enable epn-client
sudo systemctl start epn-client

# Vérifier le statut
sudo systemctl status epn-client
```

### Client Windows

#### Étape 1 : Préparer l'installateur

```bash
# Sur la machine de développement (avec Rust installé)
cd rust-client

# Compiler pour Windows (nécessite cross-compilation ou VM Windows)
cargo build --release --target x86_64-pc-windows-msvc

# Le binaire est dans target/x86_64-pc-windows-msvc/release/epn-client.exe
```

#### Étape 2 : Créer le package d'installation

Créer un script PowerShell `install-epn-client.ps1` :

```powershell
# install-epn-client.ps1
# Script d'installation EPN Client pour Windows
# Exécuter en tant qu'Administrateur

param(
    [string]$ServerUrl = "https://postes.mairie.local",
    [string]$PosteId = $env:COMPUTERNAME
)

$ErrorActionPreference = "Stop"

Write-Host "=== Installation EPN Client ===" -ForegroundColor Green

# Répertoires
$InstallDir = "C:\Program Files\EPN-Client"
$ConfigDir = "C:\ProgramData\EPN-Client"
$LogDir = "C:\ProgramData\EPN-Client\logs"

# Créer les répertoires
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

# Copier le binaire
Write-Host "Installation du binaire..." -ForegroundColor Yellow
Copy-Item "epn-client.exe" -Destination "$InstallDir\epn-client.exe" -Force

# Installer le certificat CA
Write-Host "Installation du certificat CA..." -ForegroundColor Yellow
if (Test-Path "ca.crt") {
    Import-Certificate -FilePath "ca.crt" -CertStoreLocation Cert:\LocalMachine\Root
    Write-Host "Certificat CA installé" -ForegroundColor Green
} else {
    Write-Host "ATTENTION: ca.crt non trouvé, installer manuellement" -ForegroundColor Red
}

# Créer la configuration
Write-Host "Création de la configuration..." -ForegroundColor Yellow
$Config = @"
# Configuration EPN Client
server_url: $ServerUrl
ws_url: wss://$($ServerUrl -replace 'https://','')/ws
poste_id: $PosteId

# Intervalles (secondes)
heartbeat_interval: 30
reconnect_delay: 5

# Comportement
warning_time: 300
critical_time: 60
enable_screen_lock: true
lock_on_expire: true
logout_on_expire: false

# Logs
log_level: info
log_file: $LogDir\client.log
"@

$Config | Out-File -FilePath "$ConfigDir\config.yaml" -Encoding UTF8

# Créer le service Windows
Write-Host "Création du service Windows..." -ForegroundColor Yellow

# Utiliser NSSM ou sc.exe pour créer le service
$ServiceName = "EPNClient"
$ServiceDisplay = "EPN Client - Gestion Sessions"
$ServiceDescription = "Client de gestion des sessions pour postes publics EPN"

# Vérifier si le service existe déjà
$ExistingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($ExistingService) {
    Write-Host "Service existant, arrêt et suppression..." -ForegroundColor Yellow
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    sc.exe delete $ServiceName
    Start-Sleep -Seconds 2
}

# Créer le service avec sc.exe
$BinPath = "`"$InstallDir\epn-client.exe`" --config `"$ConfigDir\config.yaml`""
sc.exe create $ServiceName binPath= $BinPath start= auto DisplayName= $ServiceDisplay
sc.exe description $ServiceName $ServiceDescription
sc.exe failure $ServiceName reset= 86400 actions= restart/60000/restart/60000/restart/60000

# Démarrer le service
Write-Host "Démarrage du service..." -ForegroundColor Yellow
Start-Service -Name $ServiceName

# Vérifier le statut
$Service = Get-Service -Name $ServiceName
Write-Host ""
Write-Host "=== Installation terminée ===" -ForegroundColor Green
Write-Host "Service: $($Service.Status)" -ForegroundColor Cyan
Write-Host "Répertoire: $InstallDir" -ForegroundColor Cyan
Write-Host "Configuration: $ConfigDir\config.yaml" -ForegroundColor Cyan
Write-Host "Logs: $LogDir" -ForegroundColor Cyan
```

#### Étape 3 : Installer sur le poste Windows

1. Copier les fichiers sur le poste :
   - `epn-client.exe`
   - `ca.crt`
   - `install-epn-client.ps1`

2. Ouvrir PowerShell en Administrateur

3. Exécuter :
```powershell
cd C:\chemin\vers\fichiers
.\install-epn-client.ps1 -ServerUrl "https://postes.mairie.local" -PosteId "POSTE-WIN-01"
```

#### Vérification Windows

```powershell
# Vérifier le service
Get-Service EPNClient

# Voir les logs
Get-Content "C:\ProgramData\EPN-Client\logs\client.log" -Tail 50

# Redémarrer le service
Restart-Service EPNClient
```

---

## Déploiement en Masse (Ansible)

### Structure Ansible

```
deployment/ansible/
├── inventory/
│   └── hosts.ini
├── group_vars/
│   └── all.yml
├── roles/
│   ├── epn-client-linux/
│   │   ├── tasks/main.yml
│   │   ├── templates/
│   │   │   ├── config.yaml.j2
│   │   │   └── epn-client.service.j2
│   │   └── handlers/main.yml
│   └── epn-client-windows/
│       ├── tasks/main.yml
│       └── templates/
│           └── config.yaml.j2
├── deploy-linux.yml
└── deploy-windows.yml
```

### Configuration de l'inventaire

```ini
# inventory/hosts.ini

[linux_clients]
poste-01 ansible_host=192.168.1.101
poste-02 ansible_host=192.168.1.102
poste-03 ansible_host=192.168.1.103
poste-04 ansible_host=192.168.1.104
poste-05 ansible_host=192.168.1.105

[windows_clients]
poste-win-01 ansible_host=192.168.1.201
poste-win-02 ansible_host=192.168.1.202
poste-win-03 ansible_host=192.168.1.203

[linux_clients:vars]
ansible_user=admin
ansible_become=yes

[windows_clients:vars]
ansible_user=Administrateur
ansible_password={{ vault_windows_password }}
ansible_connection=winrm
ansible_winrm_server_cert_validation=ignore

[all:vars]
epn_server_url=https://postes.mairie.local
epn_ws_url=wss://postes.mairie.local/ws
```

### Variables globales

```yaml
# group_vars/all.yml
---
epn_server_url: "https://postes.mairie.local"
epn_ws_url: "wss://postes.mairie.local/ws"

epn_client_version: "1.0.0"
epn_heartbeat_interval: 30
epn_warning_time: 300
epn_critical_time: 60
epn_enable_screen_lock: true
epn_lock_on_expire: true
```

### Playbook Linux

```yaml
# deploy-linux.yml
---
- name: Déploiement EPN Client sur Linux
  hosts: linux_clients
  become: yes

  vars:
    epn_install_dir: /usr/local/bin
    epn_config_dir: /etc/epn-client
    epn_log_dir: /var/log/epn-client

  tasks:
    - name: Installer les dépendances
      apt:
        name:
          - libwebkit2gtk-4.1-0
          - libssl3
          - ca-certificates
        state: present
        update_cache: yes
      when: ansible_os_family == "Debian"

    - name: Créer les répertoires
      file:
        path: "{{ item }}"
        state: directory
        mode: '0755'
      loop:
        - "{{ epn_config_dir }}"
        - "{{ epn_log_dir }}"

    - name: Copier le certificat CA
      copy:
        src: files/ca.crt
        dest: /usr/local/share/ca-certificates/epn-ca.crt
        mode: '0644'
      notify: Update CA certificates

    - name: Copier le binaire
      copy:
        src: files/epn-client
        dest: "{{ epn_install_dir }}/epn-client"
        mode: '0755'
      notify: Restart EPN Client

    - name: Générer la configuration
      template:
        src: templates/config.yaml.j2
        dest: "{{ epn_config_dir }}/config.yaml"
        mode: '0644'
      notify: Restart EPN Client

    - name: Installer le service systemd
      template:
        src: templates/epn-client.service.j2
        dest: /etc/systemd/system/epn-client.service
        mode: '0644'
      notify:
        - Reload systemd
        - Restart EPN Client

    - name: Activer et démarrer le service
      systemd:
        name: epn-client
        enabled: yes
        state: started

  handlers:
    - name: Update CA certificates
      command: update-ca-certificates

    - name: Reload systemd
      systemd:
        daemon_reload: yes

    - name: Restart EPN Client
      systemd:
        name: epn-client
        state: restarted
```

### Template de configuration

```yaml
# roles/epn-client-linux/templates/config.yaml.j2
# Configuration EPN Client
# Généré par Ansible - Ne pas modifier manuellement

server_url: {{ epn_server_url }}
ws_url: {{ epn_ws_url }}
poste_id: {{ inventory_hostname | upper }}

# Intervalles (secondes)
heartbeat_interval: {{ epn_heartbeat_interval }}
reconnect_delay: 5

# Comportement
warning_time: {{ epn_warning_time }}
critical_time: {{ epn_critical_time }}
enable_screen_lock: {{ epn_enable_screen_lock | lower }}
lock_on_expire: {{ epn_lock_on_expire | lower }}
logout_on_expire: false

# Logs
log_level: info
log_file: {{ epn_log_dir }}/client.log
```

### Exécution du déploiement

```bash
# Tester la connexion
ansible -i inventory/hosts.ini all -m ping

# Déployer sur les clients Linux
ansible-playbook -i inventory/hosts.ini deploy-linux.yml

# Déployer sur un groupe spécifique
ansible-playbook -i inventory/hosts.ini deploy-linux.yml --limit poste-01,poste-02

# Déployer avec verbosité
ansible-playbook -i inventory/hosts.ini deploy-linux.yml -v

# Vérifier sans appliquer (dry-run)
ansible-playbook -i inventory/hosts.ini deploy-linux.yml --check
```

---

## Vérifications

### Serveur

```bash
# 1. État des conteneurs
docker compose ps

# 2. Logs des services
docker compose logs -f django
docker compose logs -f traefik

# 3. Test API
curl -k https://localhost/api/health/

# 4. Test WebSocket (nécessite wscat)
npm install -g wscat
wscat -c wss://localhost/ws/sessions/ --no-check

# 5. Vérifier la base de données
docker compose exec postgres psql -U admin -d poste_public -c "SELECT COUNT(*) FROM utilisateurs_utilisateur;"

# 6. Vérifier Redis
docker compose exec redis redis-cli ping

# 7. Accès aux interfaces
# - Frontend: https://postes.mairie.local/
# - Admin Django: https://postes.mairie.local/admin/
# - Traefik Dashboard: https://traefik.mairie.local/
```

### Client Linux

```bash
# 1. État du service
sudo systemctl status epn-client

# 2. Logs en temps réel
sudo journalctl -u epn-client -f

# 3. Test de connexion au serveur
curl --cacert /usr/local/share/ca-certificates/epn-ca.crt \
     https://postes.mairie.local/api/health/

# 4. Vérifier la configuration
cat /etc/epn-client/config.yaml

# 5. Test manuel du client
/usr/local/bin/epn-client --config /etc/epn-client/config.yaml --debug
```

### Client Windows

```powershell
# 1. État du service
Get-Service EPNClient

# 2. Logs
Get-Content "C:\ProgramData\EPN-Client\logs\client.log" -Tail 100

# 3. Test de connexion
Invoke-WebRequest -Uri "https://postes.mairie.local/api/health/" -UseBasicParsing

# 4. Redémarrer le service
Restart-Service EPNClient

# 5. Vérifier le certificat
Get-ChildItem Cert:\LocalMachine\Root | Where-Object { $_.Subject -like "*EPN*" }
```

---

## Maintenance

### Sauvegardes

#### Base de données (quotidienne)

```bash
# Script de backup
cat > /opt/epn-solutions/scripts/backup-db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/var/backups/epn-solutions"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

cd /opt/epn-solutions/docker
docker compose exec -T postgres pg_dump -U admin poste_public | gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

# Garder 30 jours de backups
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +30 -delete
EOF

chmod +x /opt/epn-solutions/scripts/backup-db.sh

# Cron job (tous les jours à 2h)
echo "0 2 * * * /opt/epn-solutions/scripts/backup-db.sh" | crontab -
```

#### Restauration

```bash
# Restaurer une sauvegarde
gunzip < /var/backups/epn-solutions/db_20251128_020000.sql.gz | \
    docker compose exec -T postgres psql -U admin poste_public
```

### Mise à jour du serveur

```bash
cd /opt/epn-solutions

# 1. Sauvegarder
./scripts/backup-db.sh

# 2. Mettre à jour le code
git pull origin main

# 3. Reconstruire les images
docker compose build

# 4. Redémarrer avec les nouvelles images
docker compose up -d

# 5. Vérifier
docker compose ps
docker compose logs -f --tail=100
```

### Mise à jour des clients

```bash
# Avec Ansible
cd /opt/epn-solutions/deployment/ansible

# Compiler le nouveau binaire et le placer dans files/
cp /chemin/vers/nouveau/epn-client roles/epn-client-linux/files/

# Déployer
ansible-playbook -i inventory/hosts.ini deploy-linux.yml
```

### Rotation des logs

```bash
# /etc/logrotate.d/epn-solutions
cat > /etc/logrotate.d/epn-solutions << 'EOF'
/var/log/epn-client/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 root root
    sharedscripts
    postrotate
        systemctl reload epn-client > /dev/null 2>&1 || true
    endscript
}
EOF
```

---

## Troubleshooting

### Problèmes serveur

#### Les conteneurs ne démarrent pas

```bash
# Vérifier les logs
docker compose logs

# Vérifier l'espace disque
df -h

# Vérifier les permissions
ls -la certs/
# Les clés doivent être en 600, les certificats en 644

# Recréer les conteneurs
docker compose down
docker compose up -d
```

#### Erreur de certificat SSL

```bash
# Vérifier le certificat
openssl x509 -in certs/server.crt -text -noout

# Vérifier la chaîne
openssl verify -CAfile certs/ca.crt certs/server.crt

# Régénérer si nécessaire
./scripts/generate-certificates.sh -d postes.mairie.local -i 192.168.1.10 -f
docker compose restart traefik
```

#### WebSocket ne fonctionne pas

```bash
# Vérifier que Daphne tourne
docker compose logs django | grep -i daphne

# Vérifier Redis
docker compose exec redis redis-cli ping

# Test WebSocket
wscat -c wss://localhost/ws/sessions/ --no-check
```

### Problèmes client

#### Client ne se connecte pas

```bash
# Vérifier la résolution DNS
ping postes.mairie.local

# Si pas de DNS, ajouter dans /etc/hosts
echo "192.168.1.10 postes.mairie.local" | sudo tee -a /etc/hosts

# Vérifier le certificat
curl -v --cacert /usr/local/share/ca-certificates/epn-ca.crt \
     https://postes.mairie.local/api/health/

# Logs détaillés
RUST_LOG=debug /usr/local/bin/epn-client --config /etc/epn-client/config.yaml
```

#### Erreur "certificate verify failed"

```bash
# Linux - Réinstaller le certificat
sudo rm /usr/local/share/ca-certificates/epn-ca.crt
sudo cp ca.crt /usr/local/share/ca-certificates/epn-ca.crt
sudo update-ca-certificates

# Windows (PowerShell admin)
Remove-Item Cert:\LocalMachine\Root\* -Include "*EPN*"
Import-Certificate -FilePath "ca.crt" -CertStoreLocation Cert:\LocalMachine\Root
```

#### Service ne démarre pas

```bash
# Linux
sudo systemctl status epn-client
sudo journalctl -u epn-client -n 100 --no-pager

# Vérifier la config
cat /etc/epn-client/config.yaml

# Test manuel
/usr/local/bin/epn-client --config /etc/epn-client/config.yaml

# Windows
Get-EventLog -LogName Application -Source EPNClient -Newest 20
```

---

## Checklist de déploiement

### Serveur

- [ ] Docker et Docker Compose installés
- [ ] Projet cloné dans /opt/epn-solutions
- [ ] Certificats SSL générés
- [ ] Fichier .env configuré
- [ ] Conteneurs démarrés
- [ ] API accessible (HTTPS)
- [ ] WebSocket fonctionnel
- [ ] Admin Django accessible
- [ ] Superuser créé
- [ ] Backup automatique configuré

### Client Linux

- [ ] Dépendances installées (webkit2gtk, libssl)
- [ ] Certificat CA installé
- [ ] Binaire installé (/usr/local/bin/epn-client)
- [ ] Configuration créée (/etc/epn-client/config.yaml)
- [ ] Service systemd actif
- [ ] Connexion au serveur OK
- [ ] Logs sans erreur

### Client Windows

- [ ] WebView2 Runtime installé
- [ ] Certificat CA importé
- [ ] Application installée (C:\Program Files\EPN-Client)
- [ ] Configuration créée (C:\ProgramData\EPN-Client)
- [ ] Service Windows actif
- [ ] Connexion au serveur OK

---

## Contacts

**Support Technique** : IT Mairie de La Réunion
**Documentation** : Ce document
**Version** : 2.0.0

---

Bonne mise en production !
