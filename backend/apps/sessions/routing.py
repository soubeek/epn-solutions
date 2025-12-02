"""
Routing WebSocket pour les sessions et le dashboard
"""

from django.urls import re_path
from .consumers import SessionConsumer
from apps.core.consumers import DashboardConsumer

websocket_urlpatterns = [
    # WebSocket pour le dashboard temps réel
    # ws://localhost:8001/ws/dashboard/
    re_path(r'ws/dashboard/$', DashboardConsumer.as_asgi()),

    # WebSocket pour une session spécifique
    # ws://localhost:8001/ws/sessions/<session_id>/
    re_path(r'ws/sessions/(?P<session_id>\d+)/$', SessionConsumer.as_asgi()),

    # WebSocket sans session spécifique (pour validation de code)
    # ws://localhost:8001/ws/sessions/
    re_path(r'ws/sessions/$', SessionConsumer.as_asgi()),
]
