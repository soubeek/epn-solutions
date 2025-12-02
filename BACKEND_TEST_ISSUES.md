# Problèmes Rencontrés lors du Test du Backend

**Date** : 19 novembre 2025
**Objectif** : Tester le frontend Vue.js avec le backend Django

## Résumé

Le backend Django a été conçu pour fonctionner avec :
- PostgreSQL (base de données)
- Redis (cache + Celery + Channels)
- Celery (tâches asynchrones)
- Channels (WebSocket)

Pour un test rapide sans infrastructure complète, plusieurs tentatives d'adaptation ont été faites.

## Problèmes Rencontrés

### 1. Dépendances Manquantes

**Problème** : Pillow 10.1.0 incompatible avec Python 3.13

**Solution appliquée** :
```bash
pip install Pillow  # Version latest (12.0.0) compatible
```

### 2. Configuration Base de Données

**Problème** : Backend configuré pour PostgreSQL

**Solution tentée** :
- Ajout de USE_SQLITE dans settings/base.py
- Fichier .env créé avec USE_SQLITE=True
- Configuration conditionnelle ajoutée

### 3. Configuration Logging

**Problème** : Logs configurés pour écrire dans /var/log/poste-public/ (permissions requises)

**Solutions appliquées** :
- Changé le chemin vers BASE_DIR / 'logs' / 'django.log'
- Désactivé le handler 'file' complètement
- Conservé seulement handler 'console'

### 4. Conflits de Noms d'Applications

**Problème 1** : `apps.sessions` vs `django.contrib.sessions`

**Solution appliquée** :
```python
# apps/sessions/apps.py
class SessionsConfig(AppConfig):
    label = 'poste_sessions'  # Éviter conflit
```

**Problème 2** : `apps.auth` vs `django.contrib.auth`

**Solution appliquée** :
- Désactivé `apps.auth` dans INSTALLED_APPS (pas de models, juste URLs)

### 5. Configuration Celery

**Problème** : Import de Celery dans config/__init__.py

**Solution appliquée** :
- Commenté l'import de celery dans config/__init__.py
- Désactivé 'channels' et 'django_celery_beat' dans INSTALLED_APPS

### 6. Configuration Cache/Redis

**Problème** : Cache configuré pour utiliser Redis (django_redis)

**Solution appliquée** :
```python
USE_REDIS_CACHE = config('USE_REDIS_CACHE', default=False, cast=bool)

if USE_REDIS_CACHE:
    # Redis cache
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'poste-public-cache',
        }
    }
```

### 7. WebSocket/Channels dans le Code

**Problème actuel** : Le code applicatif importe channels

```python
# apps/sessions/websocket_utils.py
from channels.layers import get_channel_layer
ModuleNotFoundError: No module named 'channels'
```

**Blocage** : Les vues (views.py) importent websocket_utils qui nécessite channels.

## Modifications Effectuées

### Fichiers Modifiés

1. **config/settings/base.py**
   - Ajout USE_SQLITE pour choix de DB
   - Désactivé channels et django_celery_beat dans INSTALLED_APPS
   - Désactivé apps.auth (conflit de nom)
   - Modifié LOGGING (retrait handler 'file')
   - Ajout USE_REDIS_CACHE pour choix de cache

2. **config/settings/development.py**
   - Modifié LOGGING pour utiliser seulement console

3. **config/__init__.py**
   - Commenté import de Celery

4. **apps/sessions/apps.py**
   - Ajout label = 'poste_sessions'

5. **backend/.env** (créé)
   - Configuration pour SQLite et développement

## Prochaines Options

### Option 1 : Installation Complète (Recommandé pour Production)

Installer toutes les dépendances :
```bash
# PostgreSQL
docker run -d -p 5432:5432 -e POSTGRES_DB=poste_public -e POSTGRES_USER=admin -e POSTGRES_PASSWORD=password postgres:16

# Redis
docker run -d -p 6379:6379 redis:7-alpine

# Installer toutes les dépendances
pip install -r requirements/base.txt
```

### Option 2 : Simplification Code (pour Tests Rapides)

Modifier le code pour rendre WebSocket/Celery optionnels :
- Wrapper les imports de channels dans try/except
- Désactiver fonctionnalités temps réel pour tests
- Focus sur API REST seulement

### Option 3 : Mock/Stub (Solution Intermédiaire)

Créer des mocks pour channels et celery :
```python
# mock_channels.py
class MockChannelLayer:
    async def group_send(self, *args, **kwargs):
        pass

def get_channel_layer():
    return MockChannelLayer()
```

### Option 4 : Docker Compose (Recommandé)

Utiliser Docker Compose pour lancer tout l'environnement :
```bash
cd backend
docker-compose up -d
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Recommandation

**Pour continuer les tests frontend/backend :**

La solution la plus rapide et propre est **Option 4 (Docker Compose)** :

1. Le backend a probablement un fichier `docker-compose.yml`
2. Lance PostgreSQL + Redis + Django en un seul commande
3. Pas de modifications du code nécessaires
4. Environnement identique à la production

**Commandes à exécuter** :
```bash
cd /home/wb/Projets/Mairie/01-Develop/100-Park/EPN_solutions/backend

# Si docker-compose.yml existe
docker-compose up -d postgres redis

# Attendre que PostgreSQL démarre (5-10s)
sleep 10

# Migrations
source venv/bin/activate
python manage.py migrate
python manage.py createsuperuser --username admin --email admin@example.com

# Lancer serveur
python manage.py runserver 0.0.0.0:8000
```

## État Actuel

- ✅ Environnement virtuel créé
- ✅ Dépendances essentielles installées (Django, DRF, JWT, Pillow)
- ✅ Configuration SQLite ajoutée
- ✅ Conflits d'apps résolus
- ✅ Logging simplifié
- ✅ Cache local configuré
- ❌ **Bloqué sur** : Imports de channels dans le code applicatif

## Temps Passé

~30 minutes de débogage et adaptations

## Décision

Soit :
1. Utiliser Docker Compose (5 min de setup)
2. Modifier le code pour rendre WebSocket optionnel (30+ min)
3. Installer channels/redis manuellement (15 min)

**Recommandation** : Docker Compose est la solution la plus propre et rapide.
