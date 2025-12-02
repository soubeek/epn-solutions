"""
URLs pour l'app Postes
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PosteViewSet

router = DefaultRouter()
router.register(r'', PosteViewSet, basename='poste')

app_name = 'postes'

urlpatterns = [
    path('', include(router.urls)),
]
