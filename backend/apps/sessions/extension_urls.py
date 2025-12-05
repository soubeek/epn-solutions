"""
URLs pour les demandes de prolongation
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ExtensionRequestViewSet

router = DefaultRouter()
router.register(r'', ExtensionRequestViewSet, basename='extension-request')

app_name = 'extension_requests'

urlpatterns = [
    path('', include(router.urls)),
]
