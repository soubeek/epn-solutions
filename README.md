# 🖥️ Système de Gestion de Postes Publics pour Collectivité Territoriale

> Solution complète de gestion d'espaces publics numériques (EPN) pour mairies et collectivités

## 📋 Vue d'ensemble

Ce projet fournit une solution clé en main pour gérer des postes informatiques publics dans une mairie ou collectivité territoriale. Il comprend :

- ✅ Déploiement automatisé via PXE boot (Debian Live)
- ✅ Interface web d'administration complète
- ✅ Système d'enregistrement des utilisateurs (conforme RGPD)
- ✅ Génération de codes d'accès temporaires
- ✅ Contrôle à distance des sessions (ajout de temps, fermeture)
- ✅ Filtrage DNS avec Pi-hole
- ✅ Support Linux (PXE) et Windows (client local)

## 🏗️ Architecture

### Infrastructure Matérielle

**Serveur Mini PC Tout-en-un** :
- Processeur : Intel i5/i7 ou AMD Ryzen 5/7 (4+ cores)
- RAM : 16-32 GB
- Stockage : SSD 512GB+
- Réseau : **1 seule carte réseau** (eth0)
- OS : Ubuntu Server 24.04 LTS

### Stack Technologique

**Backend** :
- Django 5.0+ avec Django REST Framework
- Django Channels pour WebSocket temps réel
- PostgreSQL 15 (base de données)
- Redis 7 (cache + sessions + broker Celery)
- Celery + Beat (tâches asynchrones)

**Frontend** :
- Vue.js 3 (Composition API)
- Vite 5
- Tailwind CSS 3
- Pinia (state management)

**Infrastructure** :
- Docker + Docker Compose
- Traefik 2.x (reverse proxy)
- Nginx (fichiers statiques)
- Pi-hole (DNS filtré)
- Cloudflared (DNS over HTTPS)
- Dnsmasq (TFTP + Proxy-DHCP)

**Clients** :
- Linux : Image Debian Live bootée via PXE
- Windows : Application PyQt5 (mode kiosque)

## 🚀 Installation Rapide

### Prérequis

- Mini PC avec Ubuntu Server 24.04 LTS installé
- Accès root (sudo)
- Connexion Internet
- IP statique configurée (192.168.1.10 recommandé)

### Installation avec Ansible

```bash
# 1. Cloner le projet
git clone https://github.com/votre-org/poste-public-manager.git
cd poste-public-manager

# 2. Installer Ansible sur votre machine de contrôle
sudo apt update && sudo apt install -y ansible

# 3. Configurer l'inventaire
cp ansible/inventory/hosts.yml.example ansible/inventory/hosts.yml
# Éditer hosts.yml avec l'IP de votre serveur

# 4. Configurer les variables
cp ansible/inventory/group_vars/all.yml.example ansible/inventory/group_vars/all.yml
# Éditer all.yml avec vos paramètres

# 5. Lancer le déploiement complet
cd ansible
ansible-playbook playbooks/00-all.yml -i inventory/hosts.yml

# Ou étape par étape :
ansible-playbook playbooks/01-prepare-server.yml -i inventory/hosts.yml
ansible-playbook playbooks/02-configure-network.yml -i inventory/hosts.yml
ansible-playbook playbooks/03-setup-pxe.yml -i inventory/hosts.yml
ansible-playbook playbooks/04-build-live-image.yml -i inventory/hosts.yml
ansible-playbook playbooks/05-deploy-services.yml -i inventory/hosts.yml
```

### Installation Manuelle

Consultez [docs/INSTALLATION.md](docs/INSTALLATION.md) pour l'installation manuelle pas à pas.

## 📖 Documentation

- **[Guide d'Installation](docs/INSTALLATION.md)** - Installation complète du système
- **[Configuration Réseau](docs/NETWORK.md)** - Configuration réseau détaillée (proxy-DHCP, DNS, etc.)
- **[Guide Utilisateur](docs/USER_GUIDE.md)** - Mode d'emploi pour les opérateurs
- **[API Documentation](docs/API.md)** - Documentation de l'API REST
- **[Dépannage](docs/TROUBLESHOOTING.md)** - Solutions aux problèmes courants
- **[Maintenance](docs/MAINTENANCE.md)** - Tâches de maintenance régulières

## 🔧 Configuration

### Variables Principales

Éditez `docker/.env` ou `ansible/inventory/group_vars/all.yml` :

```bash
# Base de données
POSTGRES_USER=admin
POSTGRES_PASSWORD=VotreMotDePasseSecure123!
DATABASE_NAME=poste_public

# Django
SECRET_KEY=votre-cle-secrete-django-tres-longue
ADMIN_PASSWORD=AdminSecure123!
ALLOWED_HOSTS=localhost,192.168.1.10,postes-publics.mairie.local

# Pi-hole
PIHOLE_PASSWORD=PiholeSecure123!

# Réseau
SERVER_IP=192.168.1.10
GATEWAY_IP=192.168.1.1
DHCP_RANGE_START=192.168.1.100
DHCP_RANGE_END=192.168.1.120
```

## 🎯 Utilisation

### Interface d'Administration

Accédez à l'interface web :
- URL : `https://postes-publics.mairie.local` ou `https://192.168.1.10`
- Identifiant : `admin`
- Mot de passe : celui défini dans `.env`

### Workflow Standard

1. **Enregistrer un utilisateur**
   - Menu "Utilisateurs" → "Nouvel utilisateur"
   - Remplir le formulaire (nom, prénom, pièce d'identité, photo optionnelle)
   - Cocher le consentement RGPD

2. **Générer un code d'accès**
   - Menu "Sessions" → "Nouvelle session"
   - Sélectionner l'utilisateur
   - Choisir la durée (30min, 1h, 2h, personnalisé)
   - Le code s'affiche (ex: `A7BX92`)

3. **Démarrer la session sur le poste**
   - Le poste boote via PXE (Linux) ou démarre le client (Windows)
   - L'utilisateur saisit le code
   - La session démarre avec countdown visible

4. **Gestion de la session**
   - Ajouter du temps si nécessaire
   - Voir l'activité en temps réel
   - Terminer la session manuellement si besoin

5. **Fin automatique**
   - Le poste se nettoie automatiquement
   - Tous les fichiers utilisateur sont supprimés
   - Le registre est mis à jour (logs conservés)

## 🔐 Sécurité et RGPD

- ✅ Données chiffrées en base (PostgreSQL)
- ✅ Communications HTTPS (Traefik + Let's Encrypt)
- ✅ Consentement RGPD obligatoire
- ✅ Logs d'audit complets
- ✅ Nettoyage automatique des données utilisateur après session
- ✅ Filtrage DNS (blocage sites malveillants)
- ✅ Réseau isolé (postes publics séparés du réseau administratif)

## 🤝 Support

- **Issues** : [GitHub Issues](https://github.com/votre-org/poste-public-manager/issues)
- **Email** : support@votre-mairie.fr
- **Documentation** : [Wiki](https://github.com/votre-org/poste-public-manager/wiki)

## 📝 Licence

Ce projet est sous licence **MIT**. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 🙏 Contribution

Les contributions sont les bienvenues ! Veuillez consulter [CONTRIBUTING.md](CONTRIBUTING.md) pour les directives.

## 👥 Auteurs

- **Votre Nom** - Développement initial

## 🌟 Remerciements

- L'équipe Django pour leur excellent framework
- La communauté Debian pour live-build
- Pi-hole pour le filtrage DNS
- Anthropic Claude pour l'assistance au développement

---

**Fait avec ❤️ pour les collectivités territoriales**
