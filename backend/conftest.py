"""
Configuration globale pytest pour le projet EPN Solutions
"""
import pytest
from django.conf import settings


def pytest_configure():
    """Configure Django settings for tests"""
    settings.DEBUG = False
    # Utiliser une base de données SQLite en mémoire pour les tests
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
    # Désactiver les throttles pour les tests
    settings.REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
    settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {}
