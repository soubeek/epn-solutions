"""
Configuration Django pour Production
"""

from .base import *

# Debug doit être False en production
DEBUG = False

# Security
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
SECURE_HSTS_SECONDS = 31536000  # 1 an
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

# Logging en production
LOGGING['handlers']['file']['filename'] = '/var/log/poste-public/django.log'
LOGGING['root']['level'] = 'WARNING'
LOGGING['loggers']['django']['level'] = 'WARNING'
LOGGING['loggers']['apps']['level'] = 'INFO'

# Email backend en production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
