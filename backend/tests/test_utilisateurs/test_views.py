"""
Tests pour les views/API de Utilisateur
"""
import pytest
from rest_framework import status

from apps.utilisateurs.models import Utilisateur
from tests.factories import UtilisateurFactory, SessionFactory


@pytest.mark.django_db
class TestUtilisateurListView:
    """Tests pour la liste des utilisateurs"""

    def test_list_utilisateurs_authenticated(self, authenticated_client):
        """Test liste des utilisateurs avec authentification"""
        UtilisateurFactory.create_batch(3)
        response = authenticated_client.get('/api/utilisateurs/')
        assert response.status_code == status.HTTP_200_OK
        data = response.data if isinstance(response.data, list) else response.data.get('results', [])
        assert len(data) >= 3

    def test_list_utilisateurs_unauthenticated(self, api_client):
        """Test liste des utilisateurs sans authentification"""
        response = api_client.get('/api/utilisateurs/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_search_utilisateurs(self, authenticated_client):
        """Test recherche d'utilisateurs"""
        UtilisateurFactory(nom='Dupont', prenom='Jean')
        UtilisateurFactory(nom='Martin', prenom='Marie')

        response = authenticated_client.get('/api/utilisateurs/?search=Dupont')
        assert response.status_code == status.HTTP_200_OK
        data = response.data if isinstance(response.data, list) else response.data.get('results', [])
        assert len(data) >= 1
        assert any('Dupont' in u.get('nom', '') for u in data)


@pytest.mark.django_db
class TestUtilisateurCreateView:
    """Tests pour la création d'utilisateurs"""

    def test_create_utilisateur_success(self, authenticated_client):
        """Test création d'utilisateur réussie"""
        data = {
            'nom': 'Nouveau',
            'prenom': 'User',
            'email': 'nouveau@test.com',
            'consentement_rgpd': True,
            'created_by': 'test_operator'
        }
        response = authenticated_client.post('/api/utilisateurs/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED, f"Response: {response.data}"
        assert response.data['nom'] == 'Nouveau'
        assert response.data['prenom'] == 'User'

    def test_create_utilisateur_without_rgpd(self, authenticated_client):
        """Test création sans consentement RGPD - should fail"""
        data = {
            'nom': 'Test',
            'prenom': 'User',
            'email': 'test@test.com',
            'consentement_rgpd': False,
            'created_by': 'test_operator'
        }
        response = authenticated_client.post('/api/utilisateurs/', data, format='json')
        # Must fail - RGPD consent is mandatory per serializer validation
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_utilisateur_invalid_email(self, authenticated_client):
        """Test création avec email invalide"""
        data = {
            'nom': 'Test',
            'prenom': 'User',
            'email': 'invalid-email',
            'consentement_rgpd': True,
            'created_by': 'test_operator'
        }
        response = authenticated_client.post('/api/utilisateurs/', data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_utilisateur_missing_required_fields(self, authenticated_client):
        """Test création sans champs requis"""
        data = {
            'email': 'test@test.com'
            # nom and prenom missing
        }
        response = authenticated_client.post('/api/utilisateurs/', data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestUtilisateurDetailView:
    """Tests pour le détail d'un utilisateur"""

    def test_get_utilisateur_detail(self, authenticated_client, utilisateur):
        """Test récupération détail utilisateur"""
        response = authenticated_client.get(f'/api/utilisateurs/{utilisateur.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['nom'] == utilisateur.nom

    def test_get_utilisateur_not_found(self, authenticated_client):
        """Test utilisateur inexistant"""
        response = authenticated_client.get('/api/utilisateurs/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestUtilisateurUpdateView:
    """Tests pour la modification d'utilisateurs"""

    def test_update_utilisateur(self, authenticated_client, utilisateur):
        """Test modification d'utilisateur (using PATCH for partial update)"""
        data = {
            'nom': 'NouveauNom',
            # Include contact info since serializer validate() requires at least one
            'email': utilisateur.email
        }
        response = authenticated_client.patch(
            f'/api/utilisateurs/{utilisateur.id}/',
            data,
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK, f"Response: {response.data}"
        assert response.data['nom'] == 'NouveauNom'

    def test_partial_update_utilisateur(self, authenticated_client, utilisateur):
        """Test modification partielle"""
        data = {'email': 'nouveau@email.com'}
        response = authenticated_client.patch(
            f'/api/utilisateurs/{utilisateur.id}/',
            data,
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == 'nouveau@email.com'


@pytest.mark.django_db
class TestUtilisateurDeleteView:
    """Tests pour la suppression d'utilisateurs"""

    def test_delete_utilisateur(self, authenticated_client, utilisateur):
        """Test suppression d'utilisateur"""
        user_id = utilisateur.id
        response = authenticated_client.delete(f'/api/utilisateurs/{user_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Utilisateur.objects.filter(id=user_id).exists()


@pytest.mark.django_db
class TestUtilisateurStatsView:
    """Tests pour les statistiques utilisateurs"""

    def test_get_stats(self, authenticated_client):
        """Test récupération des statistiques"""
        UtilisateurFactory.create_batch(5)

        response = authenticated_client.get('/api/utilisateurs/stats/')
        assert response.status_code == status.HTTP_200_OK
        assert 'total' in response.data


@pytest.mark.django_db
class TestUtilisateurSessionsView:
    """Tests pour les sessions d'un utilisateur"""

    def test_get_utilisateur_sessions(self, authenticated_client, utilisateur):
        """Test récupération des sessions d'un utilisateur"""
        SessionFactory.create_batch(3, utilisateur=utilisateur)

        response = authenticated_client.get(f'/api/utilisateurs/{utilisateur.id}/sessions/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3


@pytest.mark.django_db
class TestCanCreateSessionView:
    """Tests pour vérifier si un utilisateur peut créer une session"""

    def test_can_create_session_true(self, authenticated_client, utilisateur):
        """Test utilisateur peut créer une session"""
        SessionFactory(utilisateur=utilisateur)  # 1 session

        response = authenticated_client.get(f'/api/utilisateurs/{utilisateur.id}/can_create_session/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['can_create'] is True
        assert response.data['sessions_today'] == 1

    def test_can_create_session_false(self, authenticated_client, utilisateur):
        """Test utilisateur ne peut plus créer de session"""
        SessionFactory.create_batch(3, utilisateur=utilisateur)  # Limite atteinte

        response = authenticated_client.get(f'/api/utilisateurs/{utilisateur.id}/can_create_session/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['can_create'] is False
        assert response.data['sessions_today'] == 3


@pytest.mark.django_db
class TestRevokeConsentView:
    """Tests pour la révocation du consentement RGPD"""

    def test_revoke_consent(self, authenticated_client, utilisateur_avec_rgpd):
        """Test révocation du consentement"""
        assert utilisateur_avec_rgpd.consentement_rgpd is True

        response = authenticated_client.post(
            f'/api/utilisateurs/{utilisateur_avec_rgpd.id}/revoke_consent/'
        )
        assert response.status_code == status.HTTP_200_OK

        utilisateur_avec_rgpd.refresh_from_db()
        assert utilisateur_avec_rgpd.consentement_rgpd is False
