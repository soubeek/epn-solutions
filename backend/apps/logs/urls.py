"""
URLs pour l'app Logs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LogViewSet

router = DefaultRouter()
router.register(r'', LogViewSet, basename='log')

app_name = 'logs'

urlpatterns = [
    path('', include(router.urls)),
]
