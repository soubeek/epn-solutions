"""
Tests pour les views/API de Poste
"""
import pytest
from rest_framework import status

from apps.postes.models import Poste
from tests.factories import PosteFactory, SessionFactory


@pytest.mark.django_db
class TestPosteListView:
    """Tests pour la liste des postes"""

    def test_list_postes_authenticated(self, authenticated_client):
        """Test liste des postes avec authentification"""
        PosteFactory.create_batch(3)
        response = authenticated_client.get('/api/postes/')
        assert response.status_code == status.HTTP_200_OK
        data = response.data if isinstance(response.data, list) else response.data.get('results', [])
        assert len(data) >= 3

    def test_list_postes_unauthenticated(self, api_client):
        """Test liste des postes sans authentification"""
        response = api_client.get('/api/postes/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_filter_postes_by_statut(self, authenticated_client):
        """Test filtrage par statut"""
        PosteFactory(statut='disponible')
        PosteFactory(statut='occupe')
        PosteFactory(statut='maintenance')

        response = authenticated_client.get('/api/postes/?statut=disponible')
        assert response.status_code == status.HTTP_200_OK
        data = response.data if isinstance(response.data, list) else response.data.get('results', [])
        for poste in data:
            assert poste['statut'] == 'disponible'


@pytest.mark.django_db
class TestPosteCreateView:
    """Tests pour la création de postes"""

    def test_create_poste_success(self, authenticated_client):
        """Test création de poste réussie"""
        data = {
            'nom': 'NouveauPoste',
            'ip_address': '192.168.1.200',
            'statut': 'disponible'
        }
        response = authenticated_client.post('/api/postes/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['nom'] == 'NouveauPoste'

    def test_create_poste_duplicate_nom(self, authenticated_client, poste):
        """Test création avec nom dupliqué"""
        data = {
            'nom': poste.nom,  # Nom existant
            'ip_address': '192.168.1.201',
            'statut': 'disponible'
        }
        response = authenticated_client.post('/api/postes/', data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_poste_invalid_ip(self, authenticated_client):
        """Test création avec IP invalide"""
        data = {
            'nom': 'TestPoste',
            'ip_address': 'invalid-ip',
            'statut': 'disponible'
        }
        response = authenticated_client.post('/api/postes/', data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestPosteDetailView:
    """Tests pour le détail d'un poste"""

    def test_get_poste_detail(self, authenticated_client, poste):
        """Test récupération détail poste"""
        response = authenticated_client.get(f'/api/postes/{poste.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['nom'] == poste.nom

    def test_get_poste_not_found(self, authenticated_client):
        """Test poste inexistant"""
        response = authenticated_client.get('/api/postes/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestPosteUpdateView:
    """Tests pour la modification de postes"""

    def test_update_poste(self, authenticated_client, poste):
        """Test modification de poste"""
        data = {
            'nom': poste.nom,
            'ip_address': poste.ip_address,
            'emplacement': 'Nouvelle Salle'
        }
        response = authenticated_client.patch(
            f'/api/postes/{poste.id}/',
            data,
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['emplacement'] == 'Nouvelle Salle'


@pytest.mark.django_db
class TestPosteDeleteView:
    """Tests pour la suppression de postes"""

    def test_delete_poste(self, authenticated_client, poste):
        """Test suppression de poste"""
        poste_id = poste.id
        response = authenticated_client.delete(f'/api/postes/{poste_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Poste.objects.filter(id=poste_id).exists()


@pytest.mark.django_db
class TestPosteDisponiblesView:
    """Tests pour les postes disponibles"""

    def test_get_disponibles(self, authenticated_client):
        """Test récupération des postes disponibles"""
        PosteFactory(statut='disponible')
        PosteFactory(statut='disponible')
        PosteFactory(statut='occupe')

        response = authenticated_client.get('/api/postes/disponibles/')
        assert response.status_code == status.HTTP_200_OK
        for poste in response.data:
            assert poste['statut'] == 'disponible'


@pytest.mark.django_db
class TestPosteStatsView:
    """Tests pour les statistiques des postes"""

    def test_get_stats(self, authenticated_client):
        """Test récupération des statistiques"""
        PosteFactory.create_batch(5)

        response = authenticated_client.get('/api/postes/stats/')
        assert response.status_code == status.HTTP_200_OK
        assert 'total' in response.data
        assert 'par_statut' in response.data


@pytest.mark.django_db
class TestPosteHeartbeatView:
    """Tests pour le heartbeat des postes"""

    def test_heartbeat_success(self, authenticated_client, poste):
        """Test heartbeat réussi"""
        data = {
            'ip_address': poste.ip_address,
            'version_client': '2.0.0'
        }
        response = authenticated_client.post(f'/api/postes/{poste.id}/heartbeat/', data, format='json')
        assert response.status_code == status.HTTP_200_OK, f"Response: {response.data}"

        poste.refresh_from_db()
        assert poste.version_client == '2.0.0'

    def test_heartbeat_poste_not_found(self, authenticated_client):
        """Test heartbeat poste inexistant"""
        data = {
            'ip_address': '192.168.1.100',
            'version_client': '1.0.0'
        }
        response = authenticated_client.post('/api/postes/99999/heartbeat/', data, format='json')
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestPosteMarquerStatutViews:
    """Tests pour les changements de statut via API"""

    def test_marquer_disponible(self, authenticated_client, poste_occupe):
        """Test marquer disponible via API"""
        response = authenticated_client.post(f'/api/postes/{poste_occupe.id}/marquer_disponible/')
        assert response.status_code == status.HTTP_200_OK
        poste_occupe.refresh_from_db()
        assert poste_occupe.statut == 'disponible'

    def test_marquer_maintenance(self, authenticated_client, poste_disponible):
        """Test marquer maintenance via API"""
        response = authenticated_client.post(f'/api/postes/{poste_disponible.id}/marquer_maintenance/')
        assert response.status_code == status.HTTP_200_OK
        poste_disponible.refresh_from_db()
        assert poste_disponible.statut == 'maintenance'

    def test_marquer_hors_ligne(self, authenticated_client, poste_disponible):
        """Test marquer hors ligne via API"""
        response = authenticated_client.post(f'/api/postes/{poste_disponible.id}/marquer_hors_ligne/')
        assert response.status_code == status.HTTP_200_OK
        poste_disponible.refresh_from_db()
        assert poste_disponible.statut == 'hors_ligne'


@pytest.mark.django_db
class TestPosteSessionActiveView:
    """Tests pour la session active d'un poste"""

    def test_get_session_active(self, authenticated_client, poste):
        """Test récupération de la session active"""
        session = SessionFactory(poste=poste, statut='active')

        response = authenticated_client.get(f'/api/postes/{poste.id}/session_active/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == session.id

    def test_get_session_active_none(self, authenticated_client, poste):
        """Test pas de session active"""
        response = authenticated_client.get(f'/api/postes/{poste.id}/session_active/')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
