# Guide d'Implémentation - Poste Public Manager

Ce document liste tous les fichiers à créer pour compléter le projet.

## ✅ Fichiers Créés (Structure de Base)

- [x] Structure de dossiers complète
- [x] `.gitignore`
- [x] `README.md`
- [x] `LICENSE`
- [x] `ansible/ansible.cfg`
- [x] `ansible/inventory/hosts.yml.example`
- [x] `ansible/inventory/group_vars/all.yml.example`
- [x] `ansible/roles/common/tasks/main.yml`
- [x] `ansible/roles/common/handlers/main.yml`
- [x] `ansible/roles/docker/tasks/main.yml`
- [x] `ansible/roles/docker/templates/daemon.json.j2`
- [x] `ansible/roles/docker/handlers/main.yml`
- [x] `ansible/roles/network/tasks/main.yml`
- [x] `ansible/roles/network/templates/netplan.yaml.j2`
- [x] `ansible/roles/network/templates/hosts.j2`
- [x] `ansible/roles/network/handlers/main.yml`
- [x] `ansible/roles/dnsmasq/tasks/main.yml`
- [x] `ansible/roles/dnsmasq/templates/dnsmasq.conf.j2`
- [x] `ansible/roles/dnsmasq/templates/pxelinux-default.j2`
- [x] `ansible/roles/dnsmasq/handlers/main.yml`
- [x] `docker/docker-compose.yml`
- [x] `docker/.env.example`
- [x] `backend/config/__init__.py`

## 📝 Fichiers Prioritaires à Créer

### 1. Backend Django (dans `/backend`)

#### Configuration Django
```
backend/config/
├── settings/
│   ├── __init__.py
│   ├── base.py          # Settings communs
│   ├── development.py   # Settings dev
│   └── production.py    # Settings prod
├── urls.py              # URLs principales
├── asgi.py              # Configuration ASGI (WebSocket)
├── wsgi.py              # Configuration WSGI
└── celery.py            # Configuration Celery
```

#### Applications Django

**apps/utilisateurs/** (Gestion utilisateurs)
```
models.py       # Modèle Utilisateur (nom, prénom, email, téléphone, photo, etc.)
serializers.py  # Serializers DRF
views.py        # ViewSets DRF
urls.py         # Routes API
admin.py        # Django Admin
signals.py      # Signals (logs automatiques)
```

**apps/postes/** (Gestion postes)
```
models.py       # Modèle Poste (nom, IP, MAC, statut)
serializers.py
views.py
urls.py
admin.py
```

**apps/sessions/** (Gestion sessions)
```
models.py       # Modèle Session (code, durée, temps_restant, etc.)
serializers.py
views.py
urls.py
admin.py
consumers.py    # WebSocket Consumers (Django Channels)
routing.py      # WebSocket routing
tasks.py        # Tâches Celery (nettoyage sessions expirées)
```

**apps/logs/** (Audit trail)
```
models.py       # Modèle Log (action, utilisateur, timestamp, détails)
serializers.py
views.py
urls.py
admin.py
```

**apps/auth/** (Authentification opérateurs)
```
serializers.py  # Login/Logout serializers
views.py        # Login/Logout views
urls.py
```

**apps/core/** (Fonctions communes)
```
models.py       # Modèles abstraits
management/commands/wait_for_db.py  # Commande Django wait_for_db
```

#### Requirements
```
requirements/
├── base.txt        # Dépendances de base
├── development.txt # Dépendances dev
└── production.txt  # Dépendances prod
```

#### Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements/production.txt .
RUN pip install -r production.txt
COPY . .
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
```

### 2. Frontend Vue.js (dans `/frontend`)

#### Structure
```
frontend/src/
├── main.js              # Point d'entrée
├── App.vue              # Composant racine
├── router/index.js      # Vue Router
├── stores/
│   ├── auth.js          # Store Pinia auth
│   ├── utilisateurs.js  # Store utilisateurs
│   ├── sessions.js      # Store sessions
│   ├── postes.js        # Store postes
│   └── websocket.js     # Store WebSocket
├── services/
│   ├── api.js           # Instance Axios
│   ├── auth.service.js  # Service auth
│   ├── utilisateurs.service.js
│   ├── sessions.service.js
│   ├── postes.service.js
│   └── websocket.service.js
├── views/
│   ├── LoginView.vue
│   ├── DashboardView.vue
│   ├── UtilisateursView.vue
│   ├── SessionsView.vue
│   ├── PostesView.vue
│   └── LogsView.vue
└── components/
    ├── common/
    │   ├── Layout.vue
    │   ├── Navbar.vue
    │   └── Sidebar.vue
    ├── dashboard/
    │   ├── Dashboard.vue
    │   └── StatsCard.vue
    ├── utilisateurs/
    │   ├── UtilisateursList.vue
    │   ├── UtilisateurForm.vue
    │   └── PhotoUpload.vue
    ├── sessions/
    │   ├── SessionsList.vue
    │   ├── SessionCreate.vue
    │   └── CodeDisplay.vue
    └── postes/
        ├── PostesList.vue
        └── PosteCard.vue
```

#### Configuration
```
package.json
vite.config.js
tailwind.config.js
postcss.config.js
Dockerfile
nginx.conf
```

### 3. Client Python Linux (dans `/client`)

```
client/
├── session_client.py   # Client principal
├── config.py           # Configuration
├── utils.py            # Utilitaires
├── requirements.txt    # Dépendances
└── systemd/
    └── session-client.service
```

### 4. Client Windows PyQt5 (dans `/client-windows`)

```
client-windows/
├── main.py             # Point d'entrée
├── ui/
│   ├── login_dialog.py
│   ├── session_window.py
│   └── time_widget.py
├── core/
│   ├── session_manager.py
│   ├── websocket_client.py
│   └── config.py
├── utils/
│   ├── windows_utils.py
│   └── cleanup.py
├── requirements.txt
└── build.py
```

### 5. Live Image Debian (dans `/live-image`)

```
live-image/
├── config/
│   ├── package-lists/
│   │   ├── desktop.list.chroot
│   │   ├── office.list.chroot
│   │   └── python.list.chroot
│   ├── includes.chroot/
│   │   ├── etc/systemd/system/session-client.service
│   │   └── usr/local/bin/session-client.sh
│   └── hooks/
│       └── live/9999-custom-setup.hook.chroot
├── auto/
│   ├── config
│   ├── build
│   └── clean
└── build.sh
```

### 6. Ansible Playbooks (dans `/ansible/playbooks`)

```
playbooks/
├── 00-all.yml              # Playbook principal (exécute tous les autres)
├── 01-prepare-server.yml   # Préparation du serveur
├── 02-configure-network.yml # Configuration réseau
├── 03-setup-pxe.yml        # Configuration PXE/TFTP
├── 04-build-live-image.yml # Build de l'image Live
└── 05-deploy-services.yml  # Déploiement Docker Compose
```

### 7. Documentation (dans `/docs`)

```
docs/
├── README.md               # Index de la documentation
├── INSTALLATION.md         # Guide d'installation complet
├── NETWORK.md              # Configuration réseau détaillée
├── USER_GUIDE.md           # Guide utilisateur pour opérateurs
├── API.md                  # Documentation de l'API REST
├── TROUBLESHOOTING.md      # Dépannage
└── MAINTENANCE.md          # Maintenance régulière
```

## 🚀 Ordre de Développement Recommandé

### Phase 1 : Backend Django (2-3 jours)
1. Configuration Django (settings, urls, asgi, wsgi, celery)
2. Modèles de base (Utilisateur, Poste, Session, Log)
3. Serializers DRF
4. ViewSets et routes API
5. Django Admin personnalisé
6. WebSocket Consumers (Django Channels)
7. Tâches Celery (nettoyage automatique)
8. Tests unitaires

### Phase 2 : Frontend Vue.js (2-3 jours)
1. Setup Vite + Vue 3 + Tailwind
2. Router et stores Pinia
3. Services API (Axios)
4. Service WebSocket
5. Composants de base (Layout, Navbar, etc.)
6. Vues principales (Dashboard, Utilisateurs, Sessions, Postes)
7. Formulaires et validation
8. Build production

### Phase 3 : Clients Python (1-2 jours)
1. Client Linux (session_client.py)
2. Client Windows (PyQt5)
3. Communication WebSocket
4. Gestion du countdown
5. Nettoyage automatique

### Phase 4 : Infrastructure (1-2 jours)
1. Rôles Ansible manquants (pxe-server, live-image, services)
2. Playbooks Ansible
3. Configuration Docker (Traefik, Nginx, etc.)
4. Build de l'image Debian Live

### Phase 5 : Tests et Documentation (1 jour)
1. Tests d'intégration
2. Documentation utilisateur
3. Documentation API
4. Guide de dépannage

## 📦 Dépendances Python

### Backend (requirements/base.txt)
```
Django==5.0
djangorestframework==3.14.0
django-cors-headers==4.3.1
django-filter==23.5
channels==4.0.0
channels-redis==4.1.0
daphne==4.0.0
celery==5.3.4
django-celery-beat==2.5.0
redis==5.0.1
psycopg2-binary==2.9.9
Pillow==10.1.0
python-decouple==3.8
djangorestframework-simplejwt==5.3.1
```

### Client (client/requirements.txt)
```
requests==2.31.0
websocket-client==1.6.4
```

### Client Windows (client-windows/requirements.txt)
```
PyQt5==5.15.10
requests==2.31.0
websocket-client==1.6.4
pywin32==306
```

## 🔑 Commandes Importantes

### Générer SECRET_KEY Django
```bash
openssl rand -hex 50
```

### Générer mot de passe Traefik
```bash
htpasswd -nb admin password
```

### Lancer le projet
```bash
cd docker
cp .env.example .env
# Éditer .env avec vos valeurs
docker compose up -d
```

### Accéder aux services
- Frontend : https://postes-publics.mairie.local
- Django Admin : https://postes-publics.mairie.local/admin
- API : https://postes-publics.mairie.local/api
- Pi-hole : https://pihole.mairie.local
- Traefik : https://traefik.mairie.local

## 🎯 Prochaines Étapes

1. **Créer les modèles Django** (Utilisateur, Poste, Session, Log)
2. **Configurer Django** (settings, urls, asgi, celery)
3. **Créer l'API REST** (serializers, views, urls)
4. **Implémenter WebSocket** (consumers, routing)
5. **Développer le frontend Vue.js**
6. **Créer les clients Python (Linux + Windows)**
7. **Finaliser Ansible** (playbooks, rôles manquants)
8. **Builder l'image Debian Live**
9. **Tester l'ensemble**
10. **Documenter**

---

**Note** : Ce projet est volumineux et nécessite environ **100-150 fichiers supplémentaires**.

Souhaitez-vous que je continue en créant :
1. Les modèles Django complets ?
2. Le frontend Vue.js de base ?
3. Les clients Python ?
4. Un autre composant spécifique ?

Indiquez-moi la priorité et je continuerai l'implémentation !
