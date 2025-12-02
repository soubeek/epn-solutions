# Backend Django - Poste Public Manager

API REST et WebSocket pour la gestion des postes publics.

## 🏗️ Architecture

- **Framework** : Django 5.0 + Django REST Framework
- **Base de données** : PostgreSQL 15
- **Cache** : Redis 7
- **WebSocket** : Django Channels
- **Tâches asynchrones** : Celery + Beat
- **Serveur ASGI** : Daphne

## 📦 Structure

```
backend/
├── config/              # Configuration Django
│   ├── settings/        # Settings (base, dev, prod)
│   ├── urls.py          # URLs principales
│   ├── asgi.py          # Configuration ASGI
│   ├── wsgi.py          # Configuration WSGI
│   └── celery.py        # Configuration Celery
├── apps/                # Applications Django
│   ├── core/            # Utilitaires communs
│   ├── utilisateurs/    # Gestion utilisateurs
│   ├── postes/          # Gestion postes
│   ├── sessions/        # Gestion sessions
│   ├── logs/            # Logs et audit
│   └── auth/            # Authentification
├── static/              # Fichiers statiques
├── media/               # Fichiers media (photos)
├── requirements/        # Dépendances Python
├── Dockerfile           # Image Docker
└── manage.py            # CLI Django
```

## 🚀 Démarrage Rapide

### Avec Docker (Recommandé)

```bash
# Dans le répertoire docker/
docker compose up -d django
docker compose logs -f django
```

### En local (Développement)

```bash
# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements/development.txt

# Créer un fichier .env
cp .env.example .env
# Éditer .env avec vos paramètres

# Appliquer les migrations
python manage.py migrate

# Créer un superuser
python manage.py createsuperuser

# Collecter les fichiers statiques
python manage.py collectstatic

# Démarrer le serveur de développement
python manage.py runserver
```

## 📝 Modèles de Données

### Utilisateur
- Informations personnelles (nom, prénom, email, téléphone)
- Pièce d'identité
- Photo (optionnelle)
- Consentement RGPD

### Poste
- Nom, IP, MAC
- Statut (disponible, occupé, hors ligne, maintenance)
- Dernière connexion

### Session
- Code d'accès unique (6 caractères)
- Utilisateur et Poste
- Durée initiale et temps restant
- Statut (en_attente, active, terminée)

### Log
- Action (création, modification, connexion, etc.)
- Utilisateur/Session concerné
- Détails et timestamp

## 🔌 API REST

Base URL : `/api/`

### Endpoints Principaux

#### Authentification
- `POST /api/token/` - Obtenir un token JWT
- `POST /api/token/refresh/` - Rafraîchir le token
- `POST /api/auth/login/` - Connexion
- `POST /api/auth/logout/` - Déconnexion

#### Utilisateurs
- `GET /api/utilisateurs/` - Liste
- `POST /api/utilisateurs/` - Créer
- `GET /api/utilisateurs/{id}/` - Détails
- `PUT /api/utilisateurs/{id}/` - Modifier
- `DELETE /api/utilisateurs/{id}/` - Supprimer

#### Postes
- `GET /api/postes/` - Liste
- `POST /api/postes/` - Créer
- `GET /api/postes/{id}/` - Détails
- `PUT /api/postes/{id}/status/` - Changer statut

#### Sessions
- `GET /api/sessions/` - Liste
- `POST /api/sessions/` - Créer (génère le code)
- `POST /api/sessions/validate-code/` - Valider un code
- `POST /api/sessions/{id}/add-time/` - Ajouter du temps
- `POST /api/sessions/{id}/terminate/` - Terminer

#### Logs
- `GET /api/logs/` - Liste
- `GET /api/logs/{id}/` - Détails

## 🔌 WebSocket

URL : `ws://localhost:8000/ws/poste/{ip_address}/`

### Messages

**Client → Serveur :**
```json
{
  "type": "heartbeat",
  "temps_restant": 1800,
  "code": "ABC123"
}
```

**Serveur → Client :**
```json
{
  "action": "add_time",
  "seconds": 600
}
```

```json
{
  "action": "close_session"
}
```

## ⚙️ Configuration

### Variables d'environnement

Copier `.env.example` vers `.env` et configurer :

```bash
# Django
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
POSTGRES_DB=poste_public
POSTGRES_USER=admin
POSTGRES_PASSWORD=password
DB_HOST=postgres
DB_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0

# Email (optionnel)
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@example.com
EMAIL_HOST_PASSWORD=password
```

## 🔧 Commandes Django Utiles

```bash
# Migrations
python manage.py makemigrations
python manage.py migrate

# Superuser
python manage.py createsuperuser

# Collecte des fichiers statiques
python manage.py collectstatic

# Shell Django
python manage.py shell

# Tests
python manage.py test

# Attendre que la DB soit prête (dans Docker)
python manage.py wait_for_db
```

## 🧪 Tests

```bash
# Tous les tests
pytest

# Avec coverage
pytest --cov=apps --cov-report=html

# Tests spécifiques
pytest apps/utilisateurs/tests/
```

## 📊 Celery

### Tâches Planifiées

- **Nettoyage sessions expirées** : Toutes les 5 minutes
- **Avertissements fin de session** : Toutes les 10 secondes
- **Nettoyage logs anciens** : Tous les jours à 3h
- **Backup automatique** : Tous les jours à 2h

### Commandes Celery

```bash
# Worker
celery -A config worker -l info

# Beat (scheduler)
celery -A config beat -l info

# Monitor (Flower)
celery -A config flower
```

## 🔐 Sécurité

- Authentification JWT
- CORS configuré
- CSRF protection
- Validation des données
- Hachage des mots de passe
- HTTPS en production
- Rate limiting (optionnel)

## 📖 Documentation API

- **Django Admin** : http://localhost:8000/admin/
- **API Browsable** : http://localhost:8000/api/
- **Swagger** (à ajouter) : http://localhost:8000/api/docs/

## 🐛 Dépannage

### La base de données n'est pas prête

```bash
python manage.py wait_for_db
```

### Erreur de migration

```bash
python manage.py migrate --fake-initial
```

### Problème de permissions sur les fichiers media

```bash
chmod -R 755 media/
chown -R www-data:www-data media/
```

## 📝 Logs

Les logs se trouvent dans :
- Console : Sortie standard
- Fichier : `/var/log/poste-public/django.log`

## 🤝 Contribution

1. Créer une branche feature
2. Faire les modifications
3. Écrire des tests
4. Soumettre une PR

## 📄 Licence

MIT
