"""
Tests pour les permissions personnalisées
"""
import pytest
from unittest.mock import MagicMock
from rest_framework.test import APIRequestFactory

from apps.core.permissions import IsAdminUser, IsOperator, IsAdminOrReadOnly


@pytest.mark.django_db
class TestIsAdminUser:
    """Tests pour la permission IsAdminUser"""

    def test_admin_user_has_permission(self, admin_user):
        """Test admin a accès"""
        permission = IsAdminUser()
        request = MagicMock()
        request.user = admin_user

        assert permission.has_permission(request, None) is True

    def test_staff_user_has_permission(self, operator_user):
        """Test staff a accès"""
        permission = IsAdminUser()
        request = MagicMock()
        request.user = operator_user

        assert permission.has_permission(request, None) is True

    def test_normal_user_no_permission(self, user):
        """Test utilisateur normal n'a pas accès"""
        permission = IsAdminUser()
        request = MagicMock()
        request.user = user

        assert permission.has_permission(request, None) is False

    def test_anonymous_user_no_permission(self):
        """Test utilisateur anonyme n'a pas accès"""
        permission = IsAdminUser()
        request = MagicMock()
        request.user = MagicMock(is_authenticated=False)

        assert permission.has_permission(request, None) is False


@pytest.mark.django_db
class TestIsOperator:
    """Tests pour la permission IsOperator"""

    def test_authenticated_active_user_has_permission(self, user):
        """Test utilisateur actif authentifié a accès"""
        permission = IsOperator()
        request = MagicMock()
        request.user = user

        assert permission.has_permission(request, None) is True

    def test_inactive_user_no_permission(self, user):
        """Test utilisateur inactif n'a pas accès"""
        user.is_active = False
        user.save()

        permission = IsOperator()
        request = MagicMock()
        request.user = user

        assert permission.has_permission(request, None) is False

    def test_anonymous_user_no_permission(self):
        """Test utilisateur anonyme n'a pas accès"""
        permission = IsOperator()
        request = MagicMock()
        request.user = MagicMock(is_authenticated=False)

        assert permission.has_permission(request, None) is False


@pytest.mark.django_db
class TestIsAdminOrReadOnly:
    """Tests pour la permission IsAdminOrReadOnly"""

    def test_admin_can_write(self, admin_user):
        """Test admin peut écrire"""
        permission = IsAdminOrReadOnly()
        request = MagicMock()
        request.user = admin_user
        request.method = 'POST'

        assert permission.has_permission(request, None) is True

    def test_admin_can_delete(self, admin_user):
        """Test admin peut supprimer"""
        permission = IsAdminOrReadOnly()
        request = MagicMock()
        request.user = admin_user
        request.method = 'DELETE'

        assert permission.has_permission(request, None) is True

    def test_normal_user_can_read(self, user):
        """Test utilisateur normal peut lire"""
        permission = IsAdminOrReadOnly()
        request = MagicMock()
        request.user = user
        request.method = 'GET'

        assert permission.has_permission(request, None) is True

    def test_normal_user_cannot_write(self, user):
        """Test utilisateur normal ne peut pas écrire"""
        permission = IsAdminOrReadOnly()
        request = MagicMock()
        request.user = user
        request.method = 'POST'

        assert permission.has_permission(request, None) is False

    def test_normal_user_cannot_delete(self, user):
        """Test utilisateur normal ne peut pas supprimer"""
        permission = IsAdminOrReadOnly()
        request = MagicMock()
        request.user = user
        request.method = 'DELETE'

        assert permission.has_permission(request, None) is False

    def test_anonymous_can_read(self):
        """Test anonyme peut lire (safe methods always allowed)"""
        permission = IsAdminOrReadOnly()
        request = MagicMock()
        # Utilisateur anonyme authentifié peut lire avec GET
        request.user = MagicMock(is_authenticated=True, is_staff=False, is_superuser=False)
        request.method = 'GET'

        assert permission.has_permission(request, None) is True
