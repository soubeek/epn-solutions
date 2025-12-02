# Guide de Référence Rapide - Poste Public Manager

## 🚀 Démarrage Ultra-Rapide

### Prérequis
- Mini PC avec Ubuntu Server 24.04 LTS
- Accès root
- Connexion Internet
- IP statique configurée

### Installation en 5 Commandes

```bash
# 1. Cloner ou extraire le projet
cd /opt
git clone <votre-repo> poste-public-manager
cd poste-public-manager

# 2. Copier et éditer la configuration
cp ansible/inventory/hosts.yml.example ansible/inventory/hosts.yml
cp ansible/inventory/group_vars/all.yml.example ansible/inventory/group_vars/all.yml
# Éditer ces fichiers selon votre réseau

# 3. Copier et éditer les variables Docker
cp docker/.env.example docker/.env
# Éditer docker/.env avec vos mots de passe

# 4. Lancer l'installation automatique
chmod +x quick-start.sh
sudo ./quick-start.sh

# 5. Accéder à l'interface
# https://postes-publics.mairie.local (ou votre IP)
```

## 📁 Structure du Projet

```
.
├── ansible/                    # Déploiement automatisé
│   ├── inventory/             # Configuration serveurs
│   ├── roles/                 # Rôles Ansible
│   └── playbooks/             # Playbooks d'installation
├── backend/                   # API Django (Python)
│   ├── config/               # Configuration Django
│   ├── apps/                 # Applications Django
│   └── requirements/         # Dépendances Python
├── frontend/                  # Interface admin (Vue.js)
│   ├── src/                  # Code source
│   └── public/               # Assets publics
├── client/                    # Client Python pour Linux (PXE)
├── client-windows/            # Client Windows (PyQt5)
├── live-image/               # Image Debian Live
├── docker/                   # Configuration Docker
│   └── docker-compose.yml    # Orchestration services
├── docs/                     # Documentation
└── scripts/                  # Scripts utilitaires
```

## 🔑 Fichiers Importants

| Fichier | Description |
|---------|-------------|
| `README.md` | Documentation principale |
| `IMPLEMENTATION_GUIDE.md` | Guide d'implémentation complet |
| `PROJECT_STATUS.md` | État du projet |
| `quick-start.sh` | Installation automatique |
| `docker/docker-compose.yml` | Services Docker |
| `docker/.env` | Variables d'environnement |
| `ansible/inventory/hosts.yml` | Serveurs cibles |
| `ansible/inventory/group_vars/all.yml` | Variables globales |

## 🔧 Configuration Réseau (Important !)

### Architecture Réseau

```
┌─────────────────────────────────────┐
│   Routeur/DHCP Mairie (Gateway)    │
│         192.168.1.1                 │
└────────────┬────────────────────────┘
             │
             │ Réseau LAN 192.168.1.0/24
             │
        ┌────┴─────┬──────────┬──────────┐
        │          │          │          │
   ┌────▼────┐ ┌──▼───┐  ┌───▼──┐  ┌───▼──┐
   │ Mini PC │ │Poste1│  │Poste2│  │PosteN│
   │  Serveur│ │ PXE  │  │ PXE  │  │ PXE  │
   │.1.10    │ │.1.100│  │.1.101│  │.1.102│
   └─────────┘ └──────┘  └──────┘  └──────┘
```

### Configuration Serveur (Mini PC)

```yaml
# 1 seule carte réseau (eth0 ou enp3s0)
IP statique:    192.168.1.10/24
Gateway:        192.168.1.1 (routeur mairie)
DNS:            127.0.0.1 (Pi-hole local)
DNS secondaire: 192.168.1.1 (backup)
```

### Services sur le Mini PC

| Port | Service | Description |
|------|---------|-------------|
| 22 | SSH | Administration |
| 53 | DNS | Pi-hole |
| 69 | TFTP | Dnsmasq (boot PXE) |
| 80 | HTTP | Traefik → Services |
| 443 | HTTPS | Traefik → Services |
| 8080 | HTTP | Nginx (image Live) |

## 🐳 Services Docker

### Liste des Services

```bash
docker compose ps
```

| Service | Port | Accès |
|---------|------|-------|
| **Traefik** | 80, 443 | Reverse proxy |
| **Django** | 8000 (interne) | API + WebSocket |
| **PostgreSQL** | 5432 (interne) | Base de données |
| **Redis** | 6379 (interne) | Cache + Broker |
| **Pi-hole** | 53, 80 | DNS + Web UI |
| **Nginx** | 8080 | Fichiers statiques |
| **Frontend** | 80 (interne) | Interface Vue.js |
| **Celery** | - | Tâches asynchrones |

### Commandes Docker Utiles

```bash
# Démarrer tous les services
cd docker
docker compose up -d

# Voir l'état
docker compose ps

# Voir les logs
docker compose logs -f

# Logs d'un service spécifique
docker compose logs -f django

# Redémarrer un service
docker compose restart django

# Arrêter tout
docker compose down

# Supprimer les volumes (ATTENTION : perte de données)
docker compose down -v

# Reconstruire une image
docker compose build django
docker compose up -d django

# Accéder au shell Django
docker compose exec django python manage.py shell

# Exécuter une migration
docker compose exec django python manage.py migrate

# Créer un superuser
docker compose exec django python manage.py createsuperuser
```

## 🌐 URLs d'Accès

| Service | URL | Identifiant | Mot de passe |
|---------|-----|-------------|--------------|
| **Interface Admin** | `https://postes-publics.mairie.local` | admin | Voir `.env` |
| **Django Admin** | `https://postes-publics.mairie.local/admin` | admin | `DJANGO_SUPERUSER_PASSWORD` |
| **Pi-hole** | `https://pihole.mairie.local/admin` | - | `PIHOLE_PASSWORD` |
| **Traefik** | `https://traefik.mairie.local` | admin | Voir `.env` |
| **API** | `https://postes-publics.mairie.local/api` | - | Token JWT |

## 🔐 Sécurité

### Mots de Passe Critiques à Changer

Dans `docker/.env` :

```bash
# PostgreSQL
POSTGRES_PASSWORD=VotreMotDePasseSecure123!

# Django
SECRET_KEY=$(openssl rand -hex 50)
DJANGO_SUPERUSER_PASSWORD=AdminSecure123!

# Pi-hole
PIHOLE_PASSWORD=PiholeSecure123!
```

### Générer un SECRET_KEY Django

```bash
openssl rand -hex 50
```

### Générer un mot de passe Traefik

```bash
htpasswd -nb admin password
```

## 📊 Workflow Standard

### 1. Enregistrer un Utilisateur

```
Interface Web → Utilisateurs → Nouveau
↓
Remplir le formulaire (nom, prénom, pièce d'identité)
↓
Uploader photo (optionnel)
↓
Cocher consentement RGPD
↓
Enregistrer
```

### 2. Créer une Session

```
Interface Web → Sessions → Nouvelle Session
↓
Sélectionner l'utilisateur
↓
Choisir la durée (30min, 1h, 2h, personnalisé)
↓
Générer le code
↓
Code affiché (ex: A7BX92)
```

### 3. Démarrer sur le Poste Client

```
Poste démarre en PXE
↓
Charge l'image Debian Live
↓
Dialogue de saisie du code
↓
Utilisateur entre le code
↓
Session démarre avec countdown visible
```

### 4. Gestion de la Session

```
Interface Web → Sessions → Session Active
↓
Voir temps restant en temps réel
↓
Options :
  - Ajouter du temps
  - Voir l'activité
  - Terminer manuellement
```

### 5. Fin de Session

```
Temps écoulé OU Fermeture manuelle
↓
Avertissements (5min, 2min, 1min, 30s, 10s)
↓
Nettoyage automatique du poste
  - Suppression fichiers utilisateur
  - Nettoyage cache navigateur
  - Vidage corbeille
↓
Poste prêt pour nouvel utilisateur
```

## 🔍 Dépannage Express

### Problème : Services ne démarrent pas

```bash
# Vérifier les logs
cd docker
docker compose logs

# Vérifier l'état
docker compose ps

# Redémarrer un service
docker compose restart <service>
```

### Problème : PXE ne boot pas

```bash
# Vérifier dnsmasq
systemctl status dnsmasq
journalctl -u dnsmasq -f

# Vérifier TFTP
tftp 192.168.1.10 -c get pxelinux.0

# Vérifier les fichiers
ls -la /srv/tftp/
```

### Problème : Pi-hole ne résout pas

```bash
# Vérifier Pi-hole
docker compose logs pihole

# Tester DNS
nslookup google.com 127.0.0.1

# Vérifier Cloudflared
docker compose logs cloudflared
```

### Problème : Connexion refusée à l'interface

```bash
# Vérifier Traefik
docker compose logs traefik

# Vérifier le pare-feu
sudo ufw status
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

## 📚 Documentation Complète

- **Installation** : `docs/INSTALLATION.md`
- **Réseau** : `docs/NETWORK.md`
- **Utilisation** : `docs/USER_GUIDE.md`
- **API** : `docs/API.md`
- **Dépannage** : `docs/TROUBLESHOOTING.md`
- **Maintenance** : `docs/MAINTENANCE.md`

## 🆘 Support

1. Consulter `TROUBLESHOOTING.md`
2. Vérifier les logs : `docker compose logs`
3. Vérifier GitHub Issues
4. Contact : support@votre-mairie.fr

## 📝 Logs Importants

```bash
# Logs système
/var/log/syslog
/var/log/dnsmasq.log

# Logs Docker
docker compose logs -f

# Logs Django
docker compose logs -f django

# Logs Nginx
docker compose logs -f nginx-static

# Logs client Python (sur les postes)
/var/log/session-client.log
```

## 🔄 Mises à Jour

### Mettre à jour le code

```bash
cd /opt/poste-public-manager
git pull

# Reconstruire les images
cd docker
docker compose build
docker compose up -d
```

### Mettre à jour la base de données

```bash
docker compose exec django python manage.py migrate
```

## 💾 Backup

### Sauvegarder la base de données

```bash
docker compose exec postgres pg_dump -U admin poste_public > backup-$(date +%Y%m%d).sql
```

### Restaurer la base de données

```bash
docker compose exec -T postgres psql -U admin poste_public < backup-20250119.sql
```

## 🎯 Commandes les Plus Utiles

```bash
# Redémarrer tout
docker compose restart

# Voir l'utilisation des ressources
docker stats

# Nettoyer Docker
docker system prune -a

# Voir les logs en temps réel
docker compose logs -f

# Accéder au shell d'un conteneur
docker compose exec django bash
docker compose exec postgres psql -U admin poste_public

# Vérifier la configuration
docker compose config
```

---

**Astuce** : Ajoutez ce fichier à vos favoris pour un accès rapide ! 🔖
