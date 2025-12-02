"""
Factories pour la génération de données de test avec Factory Boy
"""
import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.utilisateurs.models import Utilisateur
from apps.postes.models import Poste
from apps.sessions.models import Session
from apps.logs.models import Log

User = get_user_model()


class UserFactory(DjangoModelFactory):
    """Factory pour les utilisateurs Django (auth)"""

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'user_{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@test.com')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')
    is_active = True
    is_staff = False
    is_superuser = False


class UtilisateurFactory(DjangoModelFactory):
    """Factory pour les utilisateurs du registre EPN"""

    class Meta:
        model = Utilisateur

    nom = factory.Faker('last_name', locale='fr_FR')
    prenom = factory.Faker('first_name', locale='fr_FR')
    # Use sequence for email to avoid issues with special characters in French names
    email = factory.Sequence(lambda n: f'user{n}@test.com')
    telephone = factory.Sequence(lambda n: f'0692{100000 + n:06d}')
    carte_identite = factory.Sequence(lambda n: f'ID{n:08d}')
    adresse = factory.Faker('address', locale='fr_FR')
    date_naissance = factory.Faker('date_of_birth', minimum_age=18, maximum_age=80)
    consentement_rgpd = True
    date_consentement = factory.LazyFunction(timezone.now)
    created_by = 'test_operator'
    notes = ''
    nombre_sessions_total = 0


class PosteFactory(DjangoModelFactory):
    """Factory pour les postes informatiques"""

    class Meta:
        model = Poste

    nom = factory.Sequence(lambda n: f'Poste-{n:02d}')
    ip_address = factory.Sequence(lambda n: f'192.168.1.{100 + n}')
    mac_address = factory.Sequence(lambda n: f'AA:BB:CC:DD:EE:{n:02X}')
    statut = 'disponible'
    derniere_connexion = factory.LazyFunction(timezone.now)
    version_client = '1.0.0'
    emplacement = factory.Faker('word')
    notes = ''
    nombre_sessions_total = 0


class SessionFactory(DjangoModelFactory):
    """Factory pour les sessions"""

    class Meta:
        model = Session

    utilisateur = factory.SubFactory(UtilisateurFactory)
    poste = factory.SubFactory(PosteFactory)
    duree_initiale = 3600  # 1 heure en secondes
    temps_restant = 3600
    temps_ajoute = 0
    statut = 'en_attente'
    operateur = 'test_operator'
    notes = ''

    @factory.lazy_attribute
    def code_acces(self):
        """Génère un code d'accès unique"""
        return Session.generer_code()


class SessionActiveFactory(SessionFactory):
    """Factory pour les sessions actives"""

    statut = 'active'
    debut_session = factory.LazyFunction(timezone.now)


class SessionTermineeFactory(SessionFactory):
    """Factory pour les sessions terminées"""

    statut = 'terminee'
    temps_restant = 0
    debut_session = factory.LazyFunction(lambda: timezone.now() - timedelta(hours=1))
    fin_session = factory.LazyFunction(timezone.now)


class LogFactory(DjangoModelFactory):
    """Factory pour les logs"""

    class Meta:
        model = Log

    session = factory.SubFactory(SessionFactory)
    utilisateur = factory.SubFactory(UtilisateurFactory)
    poste = factory.SubFactory(PosteFactory)
    action = 'test_action'
    operateur = 'test_operator'
    details = 'Test log entry'
    ip_address = '127.0.0.1'
