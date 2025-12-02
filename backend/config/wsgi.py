"""
WSGI config for Poste Public Manager
Utilisé pour les serveurs WSGI comme Gunicorn
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
