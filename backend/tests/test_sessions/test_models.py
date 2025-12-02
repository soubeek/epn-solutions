"""
Tests pour le modèle Session
"""
import pytest
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock

from apps.sessions.models import Session
from tests.factories import SessionFactory, UtilisateurFactory, PosteFactory


@pytest.mark.django_db
class TestSessionModel:
    """Tests pour le modèle Session"""

    def test_session_creation(self, utilisateur, poste):
        """Test de création d'une session"""
        session = Session.objects.create(
            utilisateur=utilisateur,
            poste=poste,
            duree_initiale=3600,
            temps_restant=3600,
            operateur='test_op'
        )
        assert session.pk is not None
        assert session.statut == 'en_attente'
        assert len(session.code_acces) == 6

    def test_generer_code_unique(self):
        """Test que les codes générés sont uniques"""
        codes = set()
        for _ in range(100):
            code = Session.generer_code()
            assert code not in codes
            codes.add(code)
        assert len(codes) == 100

    def test_generer_code_no_ambiguous_chars(self):
        """Test que les codes ne contiennent pas de caractères ambigus"""
        ambiguous = {'O', '0', 'I', '1'}
        for _ in range(100):
            code = Session.generer_code()
            for char in code:
                assert char not in ambiguous

    def test_generer_code_length(self):
        """Test de la longueur du code"""
        code = Session.generer_code(longueur=8)
        assert len(code) == 8

    def test_code_auto_generated_on_save(self, utilisateur, poste):
        """Test que le code est généré automatiquement à la sauvegarde"""
        session = Session(
            utilisateur=utilisateur,
            poste=poste,
            duree_initiale=3600,
            temps_restant=3600,
            operateur='test_op'
        )
        assert session.code_acces == ''
        session.save()
        assert len(session.code_acces) == 6

    def test_temps_restant_initialized(self, utilisateur, poste):
        """Test que temps_restant est initialisé avec duree_initiale"""
        session = Session.objects.create(
            utilisateur=utilisateur,
            poste=poste,
            duree_initiale=1800,
            operateur='test_op'
        )
        assert session.temps_restant == 1800

    def test_duree_totale_property(self):
        """Test du calcul de durée totale"""
        session = SessionFactory.build(duree_initiale=3600, temps_ajoute=600)
        assert session.duree_totale == 4200

    def test_temps_ecoule_no_start(self, session):
        """Test temps écoulé sans démarrage"""
        assert session.temps_ecoule == 0

    def test_temps_ecoule_with_start(self, utilisateur, poste):
        """Test temps écoulé avec session démarrée"""
        session = SessionFactory(
            utilisateur=utilisateur,
            poste=poste,
            statut='active',
            debut_session=timezone.now() - timedelta(minutes=10)
        )
        # Le temps écoulé devrait être environ 600 secondes (10 minutes)
        assert 590 <= session.temps_ecoule <= 610

    def test_est_expiree_false(self):
        """Test session non expirée"""
        session = SessionFactory.build(temps_restant=100)
        assert not session.est_expiree

    def test_est_expiree_true(self):
        """Test session expirée"""
        session = SessionFactory.build(temps_restant=0)
        assert session.est_expiree

    def test_est_expiree_negative(self):
        """Test session avec temps négatif"""
        session = SessionFactory.build(temps_restant=-10)
        assert session.est_expiree

    def test_pourcentage_utilise(self):
        """Test calcul pourcentage utilisé"""
        session = SessionFactory.build(
            duree_initiale=3600,
            temps_ajoute=0,
            debut_session=timezone.now() - timedelta(minutes=30)
        )
        # 30 minutes sur 60 = 50%
        assert 45 <= session.pourcentage_utilise <= 55

    def test_minutes_restantes(self):
        """Test calcul minutes restantes"""
        session = SessionFactory.build(temps_restant=1800)
        assert session.minutes_restantes == 30

    def test_ajouter_temps(self, utilisateur, poste):
        """Test ajout de temps à une session"""
        session = SessionFactory(
            utilisateur=utilisateur,
            poste=poste,
            temps_restant=1800,
            temps_ajoute=0
        )
        initial_temps = session.temps_restant

        with patch('apps.logs.models.Log.objects.create'):
            session.ajouter_temps(600, 'test_op')

        session.refresh_from_db()
        assert session.temps_restant == initial_temps + 600
        assert session.temps_ajoute == 600

    def test_demarrer_session(self, utilisateur, poste):
        """Test démarrage d'une session"""
        session = SessionFactory(
            utilisateur=utilisateur,
            poste=poste,
            statut='en_attente'
        )

        with patch('apps.logs.models.Log.objects.create'):
            session.demarrer()

        session.refresh_from_db()
        assert session.statut == 'active'
        assert session.debut_session is not None

    def test_demarrer_marks_poste_occupe(self, utilisateur, poste_disponible):
        """Test que démarrer marque le poste comme occupé"""
        session = SessionFactory(
            utilisateur=utilisateur,
            poste=poste_disponible,
            statut='en_attente'
        )

        with patch('apps.logs.models.Log.objects.create'):
            session.demarrer()

        poste_disponible.refresh_from_db()
        assert poste_disponible.statut == 'occupe'

    def test_demarrer_increments_user_sessions(self, utilisateur, poste):
        """Test que démarrer incrémente le compteur de sessions utilisateur"""
        initial_count = utilisateur.nombre_sessions_total
        session = SessionFactory(
            utilisateur=utilisateur,
            poste=poste,
            statut='en_attente'
        )

        with patch('apps.logs.models.Log.objects.create'):
            session.demarrer()

        utilisateur.refresh_from_db()
        assert utilisateur.nombre_sessions_total == initial_count + 1

    def test_terminer_session(self, utilisateur, poste):
        """Test terminaison d'une session"""
        session = SessionFactory(
            utilisateur=utilisateur,
            poste=poste,
            statut='active',
            debut_session=timezone.now()
        )

        with patch('apps.logs.models.Log.objects.create'):
            session.terminer('test_op', 'fermeture_normale')

        session.refresh_from_db()
        assert session.statut == 'terminee'
        assert session.fin_session is not None
        assert session.temps_restant == 0

    def test_terminer_frees_poste(self, utilisateur, poste_occupe):
        """Test que terminer libère le poste"""
        session = SessionFactory(
            utilisateur=utilisateur,
            poste=poste_occupe,
            statut='active',
            debut_session=timezone.now()
        )

        with patch('apps.logs.models.Log.objects.create'):
            session.terminer('test_op')

        poste_occupe.refresh_from_db()
        assert poste_occupe.statut == 'disponible'

    def test_suspendre_session(self, utilisateur, poste):
        """Test suspension d'une session"""
        session = SessionFactory(
            utilisateur=utilisateur,
            poste=poste,
            statut='active'
        )

        with patch('apps.logs.models.Log.objects.create'):
            session.suspendre('test_op')

        session.refresh_from_db()
        assert session.statut == 'suspendue'

    def test_reprendre_session(self, utilisateur, poste):
        """Test reprise d'une session suspendue"""
        session = SessionFactory(
            utilisateur=utilisateur,
            poste=poste,
            statut='suspendue'
        )

        with patch('apps.logs.models.Log.objects.create'):
            session.reprendre('test_op')

        session.refresh_from_db()
        assert session.statut == 'active'

    def test_reprendre_non_suspendue_no_change(self, utilisateur, poste):
        """Test que reprendre ne fait rien si session non suspendue"""
        session = SessionFactory(
            utilisateur=utilisateur,
            poste=poste,
            statut='active'
        )

        with patch('apps.logs.models.Log.objects.create'):
            session.reprendre('test_op')

        session.refresh_from_db()
        assert session.statut == 'active'

    def test_decremente_temps(self, utilisateur, poste):
        """Test décrémentation du temps"""
        session = SessionFactory(
            utilisateur=utilisateur,
            poste=poste,
            statut='active',
            temps_restant=100
        )

        session.decremente_temps(10)

        session.refresh_from_db()
        assert session.temps_restant == 90

    def test_decremente_temps_expire_session(self, utilisateur, poste):
        """Test que décrementer à 0 expire la session"""
        session = SessionFactory(
            utilisateur=utilisateur,
            poste=poste,
            statut='active',
            temps_restant=5
        )

        with patch('apps.logs.models.Log.objects.create'):
            session.decremente_temps(10)

        session.refresh_from_db()
        assert session.temps_restant == 0
        assert session.statut == 'expiree'
        assert session.fin_session is not None

    def test_session_str(self, utilisateur, poste):
        """Test représentation string de la session"""
        session = SessionFactory(
            utilisateur=utilisateur,
            poste=poste,
            code_acces='ABC123'
        )
        expected = f"Session ABC123 - {utilisateur.get_full_name()}"
        assert str(session) == expected


@pytest.mark.django_db
class TestSessionStatutTransitions:
    """Tests pour les transitions de statut"""

    def test_valid_transition_en_attente_to_active(self, session):
        """Test transition valide en_attente -> active"""
        with patch('apps.logs.models.Log.objects.create'):
            session.demarrer()
        assert session.statut == 'active'

    def test_valid_transition_active_to_terminee(self, session_active):
        """Test transition valide active -> terminee"""
        with patch('apps.logs.models.Log.objects.create'):
            session_active.terminer('test_op')
        assert session_active.statut == 'terminee'

    def test_valid_transition_active_to_suspendue(self, session_active):
        """Test transition valide active -> suspendue"""
        with patch('apps.logs.models.Log.objects.create'):
            session_active.suspendre('test_op')
        assert session_active.statut == 'suspendue'

    def test_valid_transition_suspendue_to_active(self, utilisateur, poste):
        """Test transition valide suspendue -> active"""
        session = SessionFactory(
            utilisateur=utilisateur,
            poste=poste,
            statut='suspendue'
        )
        with patch('apps.logs.models.Log.objects.create'):
            session.reprendre('test_op')
        assert session.statut == 'active'
