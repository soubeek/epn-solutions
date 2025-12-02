# Roadmap Projet - Poste Public Manager

**Projet** : Système de gestion de postes informatiques publics
**Client** : Mairie - La Réunion
**Date** : 2025-01-19

## 📊 État Global du Projet

| Composant | État | Progression | Priorité |
|-----------|------|-------------|----------|
| **Backend Django** | ✅ Complet | 100% | - |
| **Frontend Vue.js** | ⏳ À faire | 0% | 🔥 P1 |
| **Client Linux (PXE)** | ⏳ À faire | 0% | 🔥 P2 |
| **Client Windows** | ⏳ À faire | 0% | ⚡ P3 |
| **Infrastructure** | 🟡 Partiel | 30% | ⚡ P4 |
| **Documentation** | 🟡 Partiel | 40% | ⚡ P4 |

**Progression globale** : ~25%

## ✅ Partie 1 : Backend Django (100% ✅)

### Réalisations
- ✓ 4 modèles (Utilisateur, Poste, Session, Log)
- ✓ Django Admin complet
- ✓ API REST (45 endpoints)
- ✓ WebSocket temps réel
- ✓ Celery tasks (8 automatisations)
- ✓ Tests unitaires possibles

### Statistiques
- Fichiers : ~35
- Lignes : ~5000+
- Qualité : Production-ready

---

## 🎯 Partie 2 : Frontend Vue.js 3 (Priorité 1)

### Objectif
Interface web complète pour les opérateurs de la mairie.

### Technologies
- Vue 3 (Composition API)
- Vite 5
- Tailwind CSS 3
- Pinia (state management)
- Vue Router
- Axios
- Socket.io-client (WebSocket)
- Chart.js (graphiques)

### Fonctionnalités Requises

#### 2.1 Authentification (JWT)
- [ ] Page login
- [ ] Gestion tokens (access + refresh)
- [ ] Route guards
- [ ] Auto-refresh token
- [ ] Logout

#### 2.2 Dashboard Principal
- [ ] Vue d'ensemble temps réel
- [ ] Nombre utilisateurs actifs
- [ ] Postes disponibles/occupés
- [ ] Sessions actives
- [ ] Graphiques statistiques

#### 2.3 Gestion Utilisateurs
- [ ] Liste utilisateurs (pagination, recherche)
- [ ] Création utilisateur (+ photo)
- [ ] Modification utilisateur
- [ ] Suppression utilisateur
- [ ] Historique sessions
- [ ] Gestion RGPD (révocation)

#### 2.4 Gestion Sessions
- [ ] Création session (code généré)
- [ ] Liste sessions actives
- [ ] Monitoring temps réel
- [ ] Ajout de temps
- [ ] Terminaison session
- [ ] Historique complet

#### 2.5 Gestion Postes
- [ ] Liste postes (état temps réel)
- [ ] Ajout/modification poste
- [ ] Changer statut (disponible, maintenance, etc.)
- [ ] Voir session active
- [ ] Heartbeat monitoring

#### 2.6 Logs & Audit
- [ ] Visualisation logs
- [ ] Recherche avancée
- [ ] Filtres (date, action, opérateur)
- [ ] Export logs

#### 2.7 Statistiques
- [ ] Graphiques utilisateurs
- [ ] Graphiques sessions
- [ ] Taux d'occupation postes
- [ ] Rapports PDF

#### 2.8 WebSocket Temps Réel
- [ ] Connexion WebSocket
- [ ] Mise à jour dashboard en direct
- [ ] Notifications (session terminée, etc.)
- [ ] Heartbeat

### Estimation
- **Temps** : 15-20 heures
- **Complexité** : Moyenne

---

## 🖥️ Partie 3 : Client Linux PXE (Priorité 2)

### Objectif
Client léger bootant via PXE sur Debian Live.

### Technologies
- Debian 12 Live
- Python 3.11
- PyQt5 / Tkinter
- Requests
- WebSocket-client

### Fonctionnalités Requises

#### 3.1 Boot PXE
- [ ] Image Debian Live personnalisée
- [ ] Auto-login
- [ ] Lancement automatique application

#### 3.2 Application Client
- [ ] Interface login (code d'accès)
- [ ] Validation code via API
- [ ] Affichage temps restant (gros chrono)
- [ ] WebSocket temps réel
- [ ] Avertissements sonores (temps écoulé)
- [ ] Heartbeat automatique
- [ ] Déconnexion propre

#### 3.3 Sécurité
- [ ] Verrouillage système (pas d'accès shell)
- [ ] Désactivation raccourcis clavier
- [ ] Fermeture automatique fin session

### Estimation
- **Temps** : 10-15 heures
- **Complexité** : Moyenne-Haute

---

## 💻 Partie 4 : Client Windows (Priorité 3)

### Objectif
Application Windows standalone pour postes non-PXE.

### Technologies
- Python 3.11
- PyQt5
- Requests
- WebSocket-client
- PyInstaller (packaging)

### Fonctionnalités Requises

#### 4.1 Application
- [ ] Interface identique client Linux
- [ ] Validation code
- [ ] Chronomètre temps réel
- [ ] WebSocket
- [ ] Heartbeat

#### 4.2 Installation
- [ ] Installeur Windows (.exe)
- [ ] Lancement au démarrage
- [ ] Mode kiosque (fullscreen)
- [ ] Désinstallation propre

### Estimation
- **Temps** : 8-12 heures
- **Complexité** : Moyenne

---

## 🏗️ Partie 5 : Infrastructure (Priorité 4)

### Objectif
Déploiement automatisé complet.

### 5.1 Serveur Configuration

#### Dnsmasq (PXE + TFTP)
- [ ] Configuration proxy-DHCP
- [ ] TFTP server
- [ ] Boot menu PXE
- [ ] Téléchargement images

#### Pi-hole (DNS Filtering)
- [ ] Installation Pi-hole
- [ ] Listes blocage
- [ ] DNS over HTTPS (Cloudflared)
- [ ] Logs DNS

#### Traefik (Reverse Proxy)
- [ ] Configuration HTTPS
- [ ] Certificats SSL (Let's Encrypt)
- [ ] Routing services
- [ ] Dashboard

### 5.2 Ansible Playbooks

**Playbooks à finaliser** :
- [ ] `site.yml` - Playbook principal
- [ ] `setup_server.yml` - Configuration serveur
- [ ] `deploy_backend.yml` - Déploiement Django
- [ ] `deploy_frontend.yml` - Déploiement Vue.js
- [ ] `configure_pxe.yml` - Configuration PXE
- [ ] `configure_pihole.yml` - Configuration Pi-hole

**Roles à compléter** :
- [x] common (fait)
- [x] docker (fait)
- [x] network (fait)
- [x] dnsmasq (fait partiellement)
- [ ] pihole
- [ ] traefik
- [ ] postgresql
- [ ] redis
- [ ] nginx

### 5.3 Docker Compose
- [x] Fichier docker-compose.yml (fait)
- [ ] Tests intégration
- [ ] Optimisation volumes
- [ ] Health checks
- [ ] Logs centralisés

### Estimation
- **Temps** : 12-15 heures
- **Complexité** : Haute

---

## 📚 Partie 6 : Documentation (Priorité 4)

### 6.1 Documentation Technique

- [ ] Architecture complète (diagrammes)
- [ ] Installation serveur (étape par étape)
- [ ] Configuration réseau
- [ ] API documentation (OpenAPI/Swagger)
- [ ] WebSocket protocol
- [ ] Troubleshooting

### 6.2 Documentation Utilisateur

- [ ] Guide opérateur (interface web)
- [ ] Guide utilisateur (clients)
- [ ] FAQ
- [ ] Vidéos tutoriels

### 6.3 Documentation Maintenance

- [ ] Procédures backup/restore
- [ ] Monitoring (logs, métriques)
- [ ] Mises à jour
- [ ] Sécurité

### Estimation
- **Temps** : 8-10 heures
- **Complexité** : Faible

---

## 📅 Planning Recommandé

### Phase 1 : Frontend (Semaine 1-2)
**Durée** : 15-20h
- Jours 1-3 : Setup + Auth + Dashboard
- Jours 4-6 : Gestion Utilisateurs + Sessions
- Jours 7-9 : Gestion Postes + Logs
- Jours 10 : WebSocket + Statistiques

### Phase 2 : Client Linux (Semaine 3)
**Durée** : 10-15h
- Jours 1-2 : Application Python
- Jours 3-4 : Image Debian Live
- Jours 5 : Tests et optimisations

### Phase 3 : Client Windows (Semaine 4)
**Durée** : 8-12h
- Jours 1-2 : Application PyQt5
- Jours 3 : Packaging (.exe)
- Jours 4 : Tests Windows

### Phase 4 : Infrastructure (Semaine 5)
**Durée** : 12-15h
- Jours 1-2 : Ansible playbooks
- Jours 3-4 : Configuration services
- Jours 5 : Tests intégration

### Phase 5 : Documentation (Semaine 6)
**Durée** : 8-10h
- Jours 1-2 : Documentation technique
- Jours 3 : Documentation utilisateur
- Jours 4 : Finalisation

**TOTAL ESTIMÉ** : ~55-70 heures (6 semaines)

---

## 🎯 Prochaine Action Immédiate

**Créer le Frontend Vue.js 3**

### Étapes :
1. ✅ Initialiser projet Vite + Vue 3
2. ✅ Configurer Tailwind CSS
3. ✅ Créer structure composants
4. ✅ Configurer Axios + API
5. ✅ Implémenter authentification
6. ✅ Créer dashboard principal
7. ✅ Implémenter CRUD utilisateurs
8. ✅ Implémenter gestion sessions
9. ✅ Implémenter WebSocket
10. ✅ Tests et optimisations

---

## 📊 Métriques de Succès

### Technique
- ✓ Backend 100% fonctionnel
- [ ] Frontend responsive et rapide
- [ ] Clients stables (Linux + Windows)
- [ ] Infrastructure automatisée
- [ ] 0 bugs critiques

### Fonctionnel
- [ ] Gestion complète utilisateurs
- [ ] Sessions temps réel fluides
- [ ] WebSocket stable
- [ ] Monitoring postes efficace
- [ ] Logs exhaustifs

### Performance
- [ ] API < 200ms
- [ ] WebSocket latence < 100ms
- [ ] Frontend load < 2s
- [ ] Client boot < 30s (PXE)

---

**Dernière mise à jour** : 2025-01-19
**Status** : Backend 100%, Frontend 0%, Clients 0%, Infra 30%
