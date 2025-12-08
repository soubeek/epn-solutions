"""
Configuration Django de base pour Poste Public Manager
Paramètres communs à tous les environnements
"""

import os
from pathlib import Path
from decouple import config, Csv

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# En production, SECRET_KEY doit etre defini dans les variables d'environnement
_secret_key_default = 'dev-only-insecure-key-do-not-use-in-production'
SECRET_KEY = config('SECRET_KEY', default=_secret_key_default)

# Verifier que SECRET_KEY est defini en production
import sys
if not config('DEBUG', default=False, cast=bool) and SECRET_KEY == _secret_key_default:
    print("ERREUR CRITIQUE: SECRET_KEY non defini en production!", file=sys.stderr)
    print("Definissez SECRET_KEY dans vos variables d'environnement.", file=sys.stderr)
    print("Generer avec: python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\"", file=sys.stderr)
    sys.exit(1)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# Application definition
INSTALLED_APPS = [
    # Django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'channels',
    'django_celery_beat',

    # Local apps
    'apps.core',
    'apps.utilisateurs',
    'apps.postes',
    'apps.sessions',
    'apps.logs',
    # 'apps.auth',  # Désactivé car conflit avec django.contrib.auth et pas de models
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
USE_SQLITE = config('USE_SQLITE', default=False, cast=bool)

if USE_SQLITE:
    # SQLite pour tests locaux
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            'ATOMIC_REQUESTS': True,
        }
    }
else:
    # PostgreSQL pour production
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('POSTGRES_DB', default='poste_public'),
            'USER': config('POSTGRES_USER', default='admin'),
            'PASSWORD': config('POSTGRES_PASSWORD', default='password'),
            'HOST': config('DB_HOST', default='postgres'),
            'PORT': config('DB_PORT', default='5432'),
            'CONN_MAX_AGE': 600,
            'ATOMIC_REQUESTS': True,
            'OPTIONS': {
                'connect_timeout': 10,
            }
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Indian/Reunion'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
    'DATE_FORMAT': '%Y-%m-%d',
    'TIME_FORMAT': '%H:%M:%S',
}

# CORS Configuration
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://localhost:8080',
    cast=Csv()
)
CORS_ALLOW_CREDENTIALS = True

# Channels (WebSocket)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(config('REDIS_HOST', default='redis'), config('REDIS_PORT', default=6379, cast=int))],
            'capacity': 1500,
            'expiry': 10,
        },
    },
}

# Cache (Local Memory pour tests, Redis pour production)
USE_REDIS_CACHE = config('USE_REDIS_CACHE', default=False, cast=bool)

if USE_REDIS_CACHE:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': config('REDIS_URL', default='redis://redis:6379/0'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            },
            'KEY_PREFIX': 'poste_public',
            'TIMEOUT': 300,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'poste-public-cache',
        }
    }

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # DB pour tests sans Redis
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 86400  # 24 heures
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = 'Lax'

# Celery Configuration
CELERY_BROKER_URL = config('REDIS_URL', default='redis://redis:6379/0')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

# Email Configuration (optionnel)
EMAIL_BACKEND = config(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@localhost')

# Logging
# Créer le répertoire de logs s'il n'existe pas
import os
LOG_DIR = BASE_DIR / 'logs'
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'detailed': {
            'format': '[{asctime}] {levelname} {name} {module}:{lineno} - {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOG_DIR / 'django.log'),
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOG_DIR / 'errors.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'detailed',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = not DEBUG

# Custom settings pour Poste Public Manager
POSTE_PUBLIC = {
    'CODE_LENGTH': 6,  # Longueur du code d'accès
    'CODE_EXPIRY_HOURS': 24,  # Expiration du code en heures
    'DEFAULT_SESSION_DURATION': 3600,  # Durée par défaut (secondes) - 1h
    'WARNING_TIMES': [300, 120, 60, 30, 10],  # Avertissements (secondes)
    'HEARTBEAT_INTERVAL': 10,  # Interval heartbeat (secondes)
    'MAX_SESSIONS_PER_USER_PER_DAY': 3,  # Max sessions par utilisateur/jour
    'PHOTO_MAX_SIZE': 5 * 1024 * 1024,  # 5MB max pour les photos
    'ALLOWED_PHOTO_FORMATS': ['JPEG', 'PNG'],
}

# ============== Configuration mTLS (certificats clients) ==============
# Chemin vers le certificat et la clé de la CA interne
CA_CERT_PATH = config('CA_CERT_PATH', default=str(BASE_DIR / 'certs' / 'ca.crt'))
CA_KEY_PATH = config('CA_KEY_PATH', default=str(BASE_DIR / 'certs' / 'ca.key'))
# Mot de passe de la clé CA (None = pas de chiffrement)
CA_KEY_PASSWORD = config('CA_KEY_PASSWORD', default=None)
# Durée de validité des certificats clients (en jours)
CLIENT_CERT_VALIDITY_DAYS = config('CLIENT_CERT_VALIDITY_DAYS', default=365, cast=int)
# Nom de l'organisation dans les certificats
CA_ORGANIZATION_NAME = config('CA_ORGANIZATION_NAME', default='EPN')

# ============== Configuration découverte automatique clients ==============
# Token partagé pour l'auto-découverte des clients
# Générer avec: python -c "import secrets; print(secrets.token_urlsafe(32))"
DISCOVERY_TOKEN = config('DISCOVERY_TOKEN', default=None)
# Token précédent pour rotation gracieuse (optionnel)
DISCOVERY_TOKEN_PREVIOUS = config('DISCOVERY_TOKEN_PREVIOUS', default=None)
