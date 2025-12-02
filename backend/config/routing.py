"""
Configuration du routing WebSocket pour Django Channels
"""

from django.urls import path
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

from apps.core.consumers import DashboardConsumer, SessionConsumer

websocket_urlpatterns = [
    path('ws/dashboard/', DashboardConsumer.as_asgi()),
    path('ws/sessions/', SessionConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
