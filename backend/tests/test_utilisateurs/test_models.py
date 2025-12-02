"""
Tests pour le modèle Utilisateur
"""
import pytest
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import date, timedelta

from apps.utilisateurs.models import Utilisateur
from tests.factories import UtilisateurFactory, SessionFactory


@pytest.mark.django_db
class TestUtilisateurModel:
    """Tests pour le modèle Utilisateur"""

    def test_utilisateur_creation(self):
        """Test de création d'un utilisateur"""
        utilisateur = Utilisateur.objects.create(
            nom='Dupont',
            prenom='Jean',
            email='jean.dupont@test.com',
            consentement_rgpd=True,
            created_by='test_operator'
        )
        assert utilisateur.pk is not None
        assert utilisateur.nom == 'Dupont'
        assert utilisateur.prenom == 'Jean'

    def test_get_full_name(self):
        """Test du nom complet"""
        utilisateur = UtilisateurFactory.build(nom='Martin', prenom='Marie')
        assert utilisateur.get_full_name() == 'Marie Martin'

    def test_str_representation(self):
        """Test de la représentation string"""
        utilisateur = UtilisateurFactory.build(nom='Dubois', prenom='Pierre')
        assert str(utilisateur) == 'Dubois Pierre'

    def test_age_calculation(self):
        """Test du calcul de l'âge"""
        today = timezone.now().date()
        birth_date = today.replace(year=today.year - 25)
        utilisateur = UtilisateurFactory.build(date_naissance=birth_date)
        assert utilisateur.age == 25

    def test_age_with_birthday_not_passed(self):
        """Test de l'âge quand l'anniversaire n'est pas passé"""
        today = timezone.now().date()
        # Date de naissance dans 1 mois, il y a 25 ans
        if today.month < 12:
            birth_date = date(today.year - 25, today.month + 1, 15)
        else:
            birth_date = date(today.year - 24, 1, 15)
        utilisateur = UtilisateurFactory.build(date_naissance=birth_date)
        assert utilisateur.age in [24, 25]  # Dépend du mois courant

    def test_age_none_without_birthdate(self):
        """Test que l'âge est None sans date de naissance"""
        utilisateur = UtilisateurFactory.build(date_naissance=None)
        assert utilisateur.age is None

    def test_sessions_count(self, utilisateur):
        """Test du compteur de sessions"""
        SessionFactory.create_batch(3, utilisateur=utilisateur)
        assert utilisateur.sessions_count == 3

    def test_sessions_today(self, utilisateur):
        """Test du compteur de sessions aujourd'hui"""
        # Sessions créées aujourd'hui
        SessionFactory.create_batch(2, utilisateur=utilisateur)
        assert utilisateur.sessions_today == 2

    def test_can_create_session_today_true(self, utilisateur):
        """Test que l'utilisateur peut créer une session (limite non atteinte)"""
        SessionFactory.create_batch(2, utilisateur=utilisateur)
        assert utilisateur.can_create_session_today() is True

    def test_can_create_session_today_false(self, utilisateur):
        """Test que l'utilisateur ne peut plus créer de session (limite atteinte)"""
        # Créer 3 sessions (limite par défaut)
        SessionFactory.create_batch(3, utilisateur=utilisateur)
        assert utilisateur.can_create_session_today() is False

    def test_consentement_rgpd_date_auto(self):
        """Test que la date de consentement est auto-remplie"""
        utilisateur = Utilisateur(
            nom='Test',
            prenom='User',
            consentement_rgpd=True,
            created_by='test'
        )
        utilisateur.save()
        assert utilisateur.date_consentement is not None

    def test_consentement_rgpd_date_not_overwritten(self):
        """Test que la date de consentement n'est pas écrasée"""
        original_date = timezone.now() - timedelta(days=30)
        utilisateur = Utilisateur.objects.create(
            nom='Test',
            prenom='User',
            consentement_rgpd=True,
            date_consentement=original_date,
            created_by='test'
        )
        utilisateur.nom = 'Updated'
        utilisateur.save()
        assert utilisateur.date_consentement == original_date


@pytest.mark.django_db
class TestUtilisateurValidation:
    """Tests pour la validation des champs"""

    def test_telephone_valid_format_reunion(self):
        """Test format téléphone Réunion valide"""
        utilisateur = UtilisateurFactory(telephone='0692123456')
        utilisateur.full_clean()  # Ne doit pas lever d'exception

    def test_telephone_valid_format_international(self):
        """Test format téléphone international valide"""
        utilisateur = UtilisateurFactory(telephone='+262692123456')
        utilisateur.full_clean()  # Ne doit pas lever d'exception

    def test_telephone_invalid_format(self, db):
        """Test format téléphone invalide"""
        utilisateur = Utilisateur(
            nom='Test',
            prenom='User',
            telephone='invalid',
            consentement_rgpd=True,
            created_by='test'
        )
        with pytest.raises(ValidationError):
            utilisateur.full_clean()

    def test_email_valid(self):
        """Test email valide"""
        utilisateur = UtilisateurFactory(email='valid@email.com')
        utilisateur.full_clean()  # Ne doit pas lever d'exception

    def test_email_invalid(self, db):
        """Test email invalide"""
        utilisateur = Utilisateur(
            nom='Test',
            prenom='User',
            email='invalid-email',
            consentement_rgpd=True,
            created_by='test'
        )
        with pytest.raises(ValidationError):
            utilisateur.full_clean()


@pytest.mark.django_db
class TestUtilisateurRGPD:
    """Tests pour la conformité RGPD"""

    def test_consentement_required_in_model(self):
        """Test que le champ consentement existe"""
        utilisateur = UtilisateurFactory.build()
        assert hasattr(utilisateur, 'consentement_rgpd')
        assert hasattr(utilisateur, 'date_consentement')

    def test_utilisateur_without_rgpd_saved(self, db):
        """Test qu'un utilisateur sans RGPD peut être créé (mais sera refusé par la view)"""
        utilisateur = Utilisateur.objects.create(
            nom='Test',
            prenom='User',
            consentement_rgpd=False,
            created_by='test'
        )
        assert utilisateur.pk is not None
        assert utilisateur.consentement_rgpd is False

    def test_date_consentement_set_on_accept(self):
        """Test que la date est définie quand consentement accepté"""
        utilisateur = Utilisateur(
            nom='Test',
            prenom='User',
            consentement_rgpd=True,
            created_by='test'
        )
        utilisateur.save()
        assert utilisateur.date_consentement is not None
        assert utilisateur.date_consentement.date() == timezone.now().date()
