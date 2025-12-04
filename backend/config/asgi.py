"""
ASGI config for Poste Public Manager
Gère les connexions HTTP et WebSocket
"""

import os
from django.conf import settings
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator, OriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Initialiser Django ASGI application tôt pour s'assurer que le setup est fait
django_asgi_app = get_asgi_application()

# Import après l'initialisation Django
from apps.sessions.routing import websocket_urlpatterns
from apps.postes.middleware import ClientCertificateMiddleware, ClientCertAuthMiddleware

# Configuration du routage WebSocket
websocket_application = ClientCertificateMiddleware(
    ClientCertAuthMiddleware(
        AuthMiddlewareStack(
            URLRouter(
                websocket_urlpatterns
            )
        )
    )
)

# En mode DEBUG, on n'applique pas la validation d'origine pour permettre
# les connexions depuis le client Rust sans en-tête Origin
if settings.DEBUG:
    websocket_with_origin = websocket_application
else:
    websocket_with_origin = AllowedHostsOriginValidator(websocket_application)

application = ProtocolTypeRouter({
    # Django ASGI application pour gérer les requêtes HTTP traditionnelles
    "http": django_asgi_app,

    # WebSocket handler avec support mTLS pour les clients
    "websocket": websocket_with_origin,
})
