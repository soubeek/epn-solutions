"""
Fixtures partagées pour les tests
"""
import pytest
from django.contrib.auth import get_user_model
from django.db import connections
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from tests.factories import (
    UserFactory,
    UtilisateurFactory,
    PosteFactory,
    SessionFactory,
)

User = get_user_model()


@pytest.fixture(autouse=True)
def _ensure_atomic_requests_setting():
    """Ensure ATOMIC_REQUESTS is in connections.settings for all databases."""
    # This fixes a compatibility issue where pytest-django's test database
    # creation doesn't always preserve all settings keys
    for alias in connections:
        if alias in connections.settings:
            if 'ATOMIC_REQUESTS' not in connections.settings[alias]:
                connections.settings[alias]['ATOMIC_REQUESTS'] = True


@pytest.fixture
def api_client():
    """Client API non authentifié"""
    return APIClient()


@pytest.fixture
def user(db):
    """Utilisateur Django standard"""
    return UserFactory()


@pytest.fixture
def admin_user(db):
    """Utilisateur Django admin"""
    return UserFactory(is_staff=True, is_superuser=True)


@pytest.fixture
def operator_user(db):
    """Utilisateur Django opérateur (staff)"""
    return UserFactory(is_staff=True, is_superuser=False)


@pytest.fixture
def authenticated_client(api_client, user):
    """Client API authentifié avec un utilisateur standard"""
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """Client API authentifié avec un admin"""
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def operator_client(api_client, operator_user):
    """Client API authentifié avec un opérateur"""
    refresh = RefreshToken.for_user(operator_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def utilisateur(db):
    """Utilisateur du registre EPN"""
    return UtilisateurFactory()


@pytest.fixture
def utilisateur_avec_rgpd(db):
    """Utilisateur avec consentement RGPD"""
    return UtilisateurFactory(consentement_rgpd=True)


@pytest.fixture
def poste(db):
    """Poste informatique"""
    return PosteFactory()


@pytest.fixture
def poste_disponible(db):
    """Poste disponible"""
    return PosteFactory(statut='disponible')


@pytest.fixture
def poste_occupe(db):
    """Poste occupé"""
    return PosteFactory(statut='occupe')


@pytest.fixture
def session(db, utilisateur, poste):
    """Session en attente"""
    return SessionFactory(utilisateur=utilisateur, poste=poste)


@pytest.fixture
def session_active(db, utilisateur, poste):
    """Session active"""
    return SessionFactory(
        utilisateur=utilisateur,
        poste=poste,
        statut='active'
    )


@pytest.fixture
def session_terminee(db, utilisateur, poste):
    """Session terminée"""
    return SessionFactory(
        utilisateur=utilisateur,
        poste=poste,
        statut='terminee',
        temps_restant=0
    )
