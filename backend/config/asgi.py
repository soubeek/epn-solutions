"""
ASGI config for Poste Public Manager
Gère les connexions HTTP et WebSocket
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Initialiser Django ASGI application tôt pour s'assurer que le setup est fait
django_asgi_app = get_asgi_application()

# Import après l'initialisation Django
from apps.sessions.routing import websocket_urlpatterns
from apps.postes.middleware import ClientCertificateMiddleware, ClientCertAuthMiddleware

application = ProtocolTypeRouter({
    # Django ASGI application pour gérer les requêtes HTTP traditionnelles
    "http": django_asgi_app,

    # WebSocket handler avec support mTLS pour les clients
    # Les middlewares s'appliquent dans l'ordre : Certificate -> CertAuth -> Auth -> URLRouter
    "websocket": AllowedHostsOriginValidator(
        ClientCertificateMiddleware(
            ClientCertAuthMiddleware(
                AuthMiddlewareStack(
                    URLRouter(
                        websocket_urlpatterns
                    )
                )
            )
        )
    ),
})
