"""
Routing WebSocket pour les sessions et le dashboard
"""

from django.urls import re_path
from .consumers import SessionConsumer
from apps.core.consumers import DashboardConsumer
from apps.postes.consumers import ClientConsumer

websocket_urlpatterns = [
    # WebSocket pour le dashboard temps réel (frontend admin)
    # ws://localhost:8001/ws/dashboard/
    re_path(r'ws/dashboard/$', DashboardConsumer.as_asgi()),

    # WebSocket pour une session spécifique (frontend admin)
    # ws://localhost:8001/ws/sessions/<session_id>/
    re_path(r'ws/sessions/(?P<session_id>\d+)/$', SessionConsumer.as_asgi()),

    # WebSocket sans session spécifique (frontend admin)
    # ws://localhost:8001/ws/sessions/
    re_path(r'ws/sessions/$', SessionConsumer.as_asgi()),

    # WebSocket pour les clients (postes) avec authentification mTLS
    # wss://server/ws/client/
    re_path(r'ws/client/$', ClientConsumer.as_asgi()),
]
