"""
Configuration Django pour Développement
"""

from .base import *

# Debug activé en dev
DEBUG = True

# Pas de redirection SSL en dev
SECURE_SSL_REDIRECT = False

# CORS plus permissif en dev
CORS_ALLOW_ALL_ORIGINS = True

# Django Debug Toolbar (optionnel)
if DEBUG:
    try:
        import debug_toolbar
        INSTALLED_APPS += ['debug_toolbar']
        MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
        INTERNAL_IPS = ['127.0.0.1', 'localhost']
    except ImportError:
        pass

# Email en console en dev
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Logging plus verbeux en dev (désactivé fichier pour tests)
LOGGING['root']['handlers'] = ['console']  # Only console for tests
LOGGING['root']['level'] = 'DEBUG'
LOGGING['loggers']['django']['level'] = 'DEBUG'
LOGGING['loggers']['apps']['level'] = 'DEBUG'
