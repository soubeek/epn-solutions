# Modèles Django Restants à Créer

Voici les modèles restants à créer pour compléter le backend Django.

## apps/postes/models.py

```python
"""Modèle Poste"""
from django.db import models
from django.utils import timezone
from apps.core.models import TimeStampedModel

class Poste(TimeStampedModel):
    STATUT_CHOICES = [
        ('disponible', 'Disponible'),
        ('occupe', 'Occupé'),
        ('reserve', 'Réservé'),
        ('hors_ligne', 'Hors ligne'),
        ('maintenance', 'En maintenance'),
    ]

    nom = models.CharField(max_length=50, unique=True)
    ip_address = models.GenericIPAddressField(protocol='IPv4')
    mac_address = models.CharField(max_length=17, blank=True, null=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='disponible')
    derniere_connexion = models.DateTimeField(blank=True, null=True)
    version_client = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    # Méthodes
    def marquer_disponible(self):
        self.statut = 'disponible'
        self.save()

    def marquer_occupe(self):
        self.statut = 'occupe'
        self.save()
```

## apps/sessions/models.py

```python
"""Modèle Session"""
import secrets
import string
from django.db import models
from django.utils import timezone
from apps.core.models import TimeStampedModel

class Session(TimeStampedModel):
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('active', 'Active'),
        ('terminee', 'Terminée'),
        ('suspendue', 'Suspendue'),
        ('expiree', 'Expirée'),
    ]

    utilisateur = models.ForeignKey('utilisateurs.Utilisateur', on_delete=models.CASCADE, related_name='sessions')
    poste = models.ForeignKey('postes.Poste', on_delete=models.CASCADE, related_name='sessions')
    code_acces = models.CharField(max_length=10, unique=True, db_index=True)
    duree_initiale = models.IntegerField()  # en secondes
    temps_restant = models.IntegerField()  # en secondes
    temps_ajoute = models.IntegerField(default=0)
    debut_session = models.DateTimeField(blank=True, null=True)
    fin_session = models.DateTimeField(blank=True, null=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    operateur = models.CharField(max_length=100)
    notes = models.TextField(blank=True, null=True)

    @staticmethod
    def generer_code():
        alphabet = string.ascii_uppercase + string.digits
        alphabet = alphabet.replace('O', '').replace('0', '').replace('I', '').replace('1', '')
        while True:
            code = ''.join(secrets.choice(alphabet) for _ in range(6))
            if not Session.objects.filter(code_acces=code).exists():
                return code

    def save(self, *args, **kwargs):
        if not self.code_acces:
            self.code_acces = self.generer_code()
        super().save(*args, **kwargs)

    def ajouter_temps(self, secondes, operateur):
        self.temps_restant += secondes
        self.temps_ajoute += secondes
        self.save()

    def terminer(self, operateur):
        self.statut = 'terminee'
        self.fin_session = timezone.now()
        self.temps_restant = 0
        self.save()
        self.poste.marquer_disponible()
```

## apps/logs/models.py

```python
"""Modèle Log"""
from django.db import models
from django.utils import timezone

class Log(models.Model):
    ACTION_CHOICES = [
        ('creation_utilisateur', 'Création utilisateur'),
        ('modification_utilisateur', 'Modification utilisateur'),
        ('suppression_utilisateur', 'Suppression utilisateur'),
        ('generation_code', 'Génération code'),
        ('demarrage_session', 'Démarrage session'),
        ('ajout_temps', 'Ajout de temps'),
        ('fermeture', 'Fermeture session'),
        ('expiration', 'Expiration session'),
        ('connexion_operateur', 'Connexion opérateur'),
        ('connexion_poste', 'Connexion poste client'),
        ('deconnexion_poste', 'Déconnexion poste client'),
        ('erreur', 'Erreur système'),
    ]

    session = models.ForeignKey('sessions.Session', on_delete=models.SET_NULL, null=True, blank=True, related_name='logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    operateur = models.CharField(max_length=100, blank=True, null=True)
    details = models.TextField()
    ip_address = models.GenericIPAddressField(protocol='IPv4', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

## Créer ces fichiers avec :

```bash
# Copier le contenu ci-dessus dans les fichiers respectifs
# Puis créer les __init__.py et apps.py pour chaque app
```

## Requirements à créer

### backend/requirements/base.txt
```
Django==5.0.1
djangorestframework==3.14.0
django-cors-headers==4.3.1
django-filter==23.5
channels==4.0.0
channels-redis==4.1.0
daphne==4.0.0
django-redis==5.4.0
celery==5.3.4
django-celery-beat==2.5.0
redis==5.0.1
psycopg2-binary==2.9.9
Pillow==10.1.0
python-decouple==3.8
djangorestframework-simplejwt==5.3.1
```

### backend/requirements/production.txt
```
-r base.txt
gunicorn==21.2.0
```

### backend/requirements/development.txt
```
-r base.txt
django-debug-toolbar==4.2.0
ipython==8.18.1
```

## Dockerfile

### backend/Dockerfile
```dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/production.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create log directory
RUN mkdir -p /var/log/poste-public

# Collect static files will be done in docker-compose command
RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
```

## À Faire Ensuite

1. ✅ Créer les fichiers de modèles
2. ✅ Créer requirements
3. ✅ Créer Dockerfile
4. ☐ Créer les serializers DRF
5. ☐ Créer les ViewSets
6. ☐ Créer les URLs
7. ☐ Créer Django Admin
8. ☐ Créer les WebSocket consumers
9. ☐ Créer les tâches Celery
