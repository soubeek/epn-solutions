"""
URLs pour l'app Utilisateurs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UtilisateurViewSet

router = DefaultRouter()
router.register(r'', UtilisateurViewSet, basename='utilisateur')

app_name = 'utilisateurs'

urlpatterns = [
    path('', include(router.urls)),
]
