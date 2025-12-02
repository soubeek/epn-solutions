"""
Tests pour le modèle Poste
"""
import pytest
from django.utils import timezone
from datetime import timedelta

from apps.postes.models import Poste
from tests.factories import PosteFactory, SessionFactory


@pytest.mark.django_db
class TestPosteModel:
    """Tests pour le modèle Poste"""

    def test_poste_creation(self):
        """Test de création d'un poste"""
        poste = Poste.objects.create(
            nom='Poste-Test',
            ip_address='192.168.1.100',
            statut='disponible'
        )
        assert poste.pk is not None
        assert poste.nom == 'Poste-Test'
        assert poste.statut == 'disponible'

    def test_str_representation(self):
        """Test de la représentation string"""
        poste = PosteFactory.build(nom='PC-01', ip_address='192.168.1.50')
        assert str(poste) == 'PC-01 (192.168.1.50)'

    def test_unique_nom(self, db):
        """Test que le nom est unique"""
        PosteFactory(nom='UniquePoste')
        with pytest.raises(Exception):  # IntegrityError
            PosteFactory(nom='UniquePoste')


@pytest.mark.django_db
class TestPosteEstEnLigne:
    """Tests pour la propriété est_en_ligne"""

    def test_est_en_ligne_true_recent_connection(self):
        """Test en ligne si connexion récente (<60s)"""
        poste = PosteFactory.build(derniere_connexion=timezone.now())
        assert poste.est_en_ligne is True

    def test_est_en_ligne_false_old_connection(self):
        """Test hors ligne si connexion ancienne (>60s)"""
        poste = PosteFactory.build(
            derniere_connexion=timezone.now() - timedelta(seconds=120)
        )
        assert poste.est_en_ligne is False

    def test_est_en_ligne_false_no_connection(self):
        """Test hors ligne si jamais connecté"""
        poste = PosteFactory.build(derniere_connexion=None)
        assert poste.est_en_ligne is False

    def test_est_en_ligne_boundary_59_seconds(self):
        """Test en ligne à la limite (59s)"""
        poste = PosteFactory.build(
            derniere_connexion=timezone.now() - timedelta(seconds=59)
        )
        assert poste.est_en_ligne is True

    def test_est_en_ligne_boundary_61_seconds(self):
        """Test hors ligne juste après la limite (61s)"""
        poste = PosteFactory.build(
            derniere_connexion=timezone.now() - timedelta(seconds=61)
        )
        assert poste.est_en_ligne is False


@pytest.mark.django_db
class TestPosteSessionActive:
    """Tests pour la propriété session_active"""

    def test_session_active_none(self, poste):
        """Test pas de session active"""
        assert poste.session_active is None

    def test_session_active_exists(self, poste):
        """Test session active existe"""
        session = SessionFactory(poste=poste, statut='active')
        assert poste.session_active == session

    def test_session_active_ignores_terminated(self, poste):
        """Test ignore les sessions terminées"""
        SessionFactory(poste=poste, statut='terminee')
        assert poste.session_active is None

    def test_session_active_ignores_pending(self, poste):
        """Test ignore les sessions en attente"""
        SessionFactory(poste=poste, statut='en_attente')
        assert poste.session_active is None


@pytest.mark.django_db
class TestPosteEstDisponible:
    """Tests pour la propriété est_disponible"""

    def test_est_disponible_true(self, db):
        """Test poste disponible"""
        poste = PosteFactory(statut='disponible')
        assert poste.est_disponible is True

    def test_est_disponible_false_wrong_statut(self):
        """Test poste non disponible si mauvais statut"""
        poste = PosteFactory.build(statut='occupe')
        assert poste.est_disponible is False

    def test_est_disponible_false_with_active_session(self, poste_disponible):
        """Test poste non disponible si session active"""
        SessionFactory(poste=poste_disponible, statut='active')
        assert poste_disponible.est_disponible is False


@pytest.mark.django_db
class TestPosteStatutChanges:
    """Tests pour les changements de statut"""

    def test_marquer_disponible(self, poste_occupe):
        """Test marquer disponible"""
        poste_occupe.marquer_disponible()
        poste_occupe.refresh_from_db()
        assert poste_occupe.statut == 'disponible'

    def test_marquer_occupe(self, poste_disponible):
        """Test marquer occupé"""
        poste_disponible.marquer_occupe()
        poste_disponible.refresh_from_db()
        assert poste_disponible.statut == 'occupe'

    def test_marquer_hors_ligne(self, poste_disponible):
        """Test marquer hors ligne"""
        poste_disponible.marquer_hors_ligne()
        poste_disponible.refresh_from_db()
        assert poste_disponible.statut == 'hors_ligne'


@pytest.mark.django_db
class TestPosteMettreAJourConnexion:
    """Tests pour la mise à jour de connexion"""

    def test_mettre_a_jour_connexion(self, poste):
        """Test mise à jour connexion"""
        old_time = poste.derniere_connexion
        poste.mettre_a_jour_connexion()
        poste.refresh_from_db()
        assert poste.derniere_connexion > old_time

    def test_mettre_a_jour_connexion_with_version(self, poste):
        """Test mise à jour connexion avec version"""
        poste.mettre_a_jour_connexion(version_client='2.0.0')
        poste.refresh_from_db()
        assert poste.version_client == '2.0.0'

    def test_mettre_a_jour_connexion_keeps_version(self, poste):
        """Test mise à jour connexion garde la version si non spécifiée"""
        poste.version_client = '1.5.0'
        poste.save()
        poste.mettre_a_jour_connexion()
        poste.refresh_from_db()
        assert poste.version_client == '1.5.0'
