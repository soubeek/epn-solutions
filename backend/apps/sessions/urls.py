"""
URLs pour l'app Sessions
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SessionViewSet

router = DefaultRouter()
router.register(r'', SessionViewSet, basename='session')

app_name = 'sessions'

urlpatterns = [
    path('', include(router.urls)),
]
