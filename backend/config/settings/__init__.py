"""
Configuration Django pour Poste Public Manager
Importe les settings selon l'environnement
"""

import os

# Déterminer l'environnement (par défaut: production)
DJANGO_ENV = os.getenv('DJANGO_ENV', 'production')

if DJANGO_ENV == 'development':
    from .development import *
elif DJANGO_ENV == 'production':
    from .production import *
else:
    from .base import *
