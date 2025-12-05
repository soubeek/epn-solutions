"""
Modèle Utilisateur pour le registre des utilisateurs
Conforme RGPD
"""

import secrets
import string

from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from django.conf import settings
from apps.core.models import TimeStampedModel


class Utilisateur(TimeStampedModel):
    """
    Modèle pour le registre des utilisateurs des postes publics
    Enregistre les informations conformément à la réglementation RGPD
    """

    # Informations personnelles
    nom = models.CharField(
        max_length=100,
        verbose_name="Nom de famille"
    )
    prenom = models.CharField(
        max_length=100,
        verbose_name="Prénom"
    )
    email = models.EmailField(
        blank=True,
        null=True,
        verbose_name="Email"
    )

    # Téléphone (format Réunion)
    phone_regex = RegexValidator(
        regex=r'^\+?262\d{9}$|^0\d{9}$',
        message="Le numéro doit être au format: '+262692123456' ou '0692123456'"
    )
    telephone = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        null=True,
        verbose_name="Téléphone"
    )

    # Pièce d'identité
    carte_identite = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Numéro de pièce d'identité",
        help_text="Numéro de carte d'identité, passeport, ou autre document officiel"
    )

    # Adresse
    adresse = models.TextField(
        blank=True,
        null=True,
        verbose_name="Adresse"
    )

    # Date de naissance
    date_naissance = models.DateField(
        blank=True,
        null=True,
        verbose_name="Date de naissance"
    )

    # Photo (optionnelle)
    photo = models.ImageField(
        upload_to='photos/%Y/%m/',
        blank=True,
        null=True,
        verbose_name="Photo"
    )

    # RGPD
    consentement_rgpd = models.BooleanField(
        default=False,
        verbose_name="Consentement RGPD",
        help_text="L'utilisateur a consenti au traitement de ses données personnelles"
    )
    date_consentement = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Date du consentement"
    )

    # Métadonnées
    created_by = models.CharField(
        max_length=100,
        verbose_name="Créé par",
        help_text="Nom de l'opérateur ayant créé la fiche"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notes",
        help_text="Notes internes (non affichées à l'utilisateur)"
    )

    # Utilisateur invité (anonyme)
    is_guest = models.BooleanField(
        default=False,
        verbose_name="Utilisateur invité",
        help_text="True si c'est un utilisateur invité anonyme"
    )

    # Statistiques
    nombre_sessions_total = models.IntegerField(
        default=0,
        verbose_name="Nombre de sessions total"
    )
    derniere_session = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Dernière session"
    )

    class Meta:
        db_table = 'utilisateurs'
        ordering = ['-created_at']
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
        indexes = [
            models.Index(fields=['nom', 'prenom']),
            models.Index(fields=['email']),
            models.Index(fields=['carte_identite']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        if self.is_guest:
            return self.nom  # Returns "GUEST-ABC123"
        return f"{self.nom} {self.prenom}"

    def get_full_name(self):
        """Retourne le nom complet ou l'identifiant guest"""
        if self.is_guest:
            return self.nom  # Returns "GUEST-ABC123"
        return f"{self.prenom} {self.nom}"

    @property
    def age(self):
        """Calcule l'âge à partir de la date de naissance"""
        if self.date_naissance:
            today = timezone.now().date()
            return today.year - self.date_naissance.year - (
                (today.month, today.day) < (self.date_naissance.month, self.date_naissance.day)
            )
        return None

    @property
    def sessions_count(self):
        """Nombre total de sessions"""
        return self.sessions.count()

    @property
    def sessions_today(self):
        """Nombre de sessions aujourd'hui"""
        today = timezone.now().date()
        return self.sessions.filter(created_at__date=today).count()

    def can_create_session_today(self):
        """Vérifie si l'utilisateur peut créer une session aujourd'hui"""
        if self.is_guest:
            return True  # Pas de limite pour les guests
        max_sessions = settings.POSTE_PUBLIC.get('MAX_SESSIONS_PER_USER_PER_DAY', 3)
        return self.sessions_today < max_sessions

    def save(self, *args, **kwargs):
        """Override save pour gérer la date de consentement RGPD"""
        # Les guests n'ont pas besoin de consentement explicite
        if not self.is_guest:
            if self.consentement_rgpd and not self.date_consentement:
                self.date_consentement = timezone.now()
        super().save(*args, **kwargs)

    @classmethod
    def create_guest(cls, created_by):
        """
        Crée un utilisateur invité anonyme

        Args:
            created_by: Nom de l'opérateur créant la session

        Returns:
            Nouvelle instance Utilisateur marquée comme guest
        """
        identifier = cls._generate_guest_identifier()
        return cls.objects.create(
            nom=identifier,
            prenom="",
            is_guest=True,
            consentement_rgpd=True,  # Consentement implicite
            created_by=created_by,
            notes="Session invité anonyme"
        )

    @staticmethod
    def _generate_guest_identifier():
        """Génère un identifiant unique pour les guests (format GUEST-ABC123)"""
        alphabet = string.ascii_uppercase + string.digits
        # Éviter les caractères ambigus
        alphabet = alphabet.replace('O', '').replace('0', '').replace('I', '').replace('1', '')

        max_attempts = 100
        for _ in range(max_attempts):
            suffix = ''.join(secrets.choice(alphabet) for _ in range(6))
            identifier = f"GUEST-{suffix}"
            if not Utilisateur.objects.filter(nom=identifier).exists():
                return identifier

        # Fallback avec timestamp si trop de collisions
        return f"GUEST-{timezone.now().strftime('%H%M%S')}"
