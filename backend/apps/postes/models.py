"""
Modèle Poste pour la gestion des postes informatiques
"""

from django.db import models
from django.utils import timezone
from apps.core.models import TimeStampedModel


class Poste(TimeStampedModel):
    """
    Modèle pour les postes informatiques publics
    """

    STATUT_CHOICES = [
        ('en_attente_validation', 'En attente de validation'),
        ('disponible', 'Disponible'),
        ('occupe', 'Occupé'),
        ('reserve', 'Réservé'),
        ('hors_ligne', 'Hors ligne'),
        ('maintenance', 'En maintenance'),
    ]

    TYPE_POSTE_CHOICES = [
        ('bureautique', 'Bureautique'),
        ('gaming', 'Gaming'),
    ]

    # Type de poste
    type_poste = models.CharField(
        max_length=20,
        choices=TYPE_POSTE_CHOICES,
        default='bureautique',
        verbose_name="Type de poste",
        help_text="Bureautique (navigateur, office) ou Gaming (Steam, launchers)"
    )

    # Identification
    nom = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Nom du poste",
        help_text="Ex: Poste-01, PC-Public-A, etc."
    )

    # Réseau
    ip_address = models.GenericIPAddressField(
        protocol='IPv4',
        verbose_name="Adresse IP",
        help_text="Adresse IP du poste (ex: 192.168.1.100)"
    )
    mac_address = models.CharField(
        max_length=17,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Adresse MAC",
        help_text="Format: AA:BB:CC:DD:EE:FF"
    )

    # État
    statut = models.CharField(
        max_length=25,
        choices=STATUT_CHOICES,
        default='disponible',
        verbose_name="Statut"
    )

    # Connexion
    derniere_connexion = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Dernière connexion"
    )
    version_client = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Version du client",
        help_text="Version du logiciel client installé"
    )

    # Informations supplémentaires
    emplacement = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Emplacement physique",
        help_text="Ex: Salle principale, Bureau 2, etc."
    )
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notes",
        help_text="Notes techniques ou remarques"
    )

    # Statistiques
    nombre_sessions_total = models.IntegerField(
        default=0,
        verbose_name="Nombre de sessions total"
    )

    # Certificat client (mTLS)
    certificate_cn = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        verbose_name="CN du certificat",
        help_text="Common Name du certificat (auto-généré)"
    )
    certificate_fingerprint = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name="Empreinte certificat",
        help_text="SHA256 fingerprint du certificat"
    )
    certificate_issued_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Certificat délivré le"
    )
    certificate_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Certificat expire le"
    )
    is_certificate_revoked = models.BooleanField(
        default=False,
        verbose_name="Certificat révoqué"
    )

    # Token d'enregistrement (temporaire, usage unique)
    registration_token = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name="Token d'enregistrement",
        help_text="Token temporaire pour l'enregistrement du client"
    )
    registration_token_expires = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Expiration du token"
    )

    # Champs de découverte automatique
    discovered_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de découverte",
        help_text="Date de la première découverte automatique"
    )
    discovered_hostname = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Hostname découvert",
        help_text="Hostname reporté par le client lors de la découverte"
    )
    validated_by = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Validé par",
        help_text="Utilisateur ayant validé ce poste"
    )
    validated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de validation"
    )

    class Meta:
        db_table = 'postes'
        ordering = ['nom']
        verbose_name = 'Poste'
        verbose_name_plural = 'Postes'
        indexes = [
            models.Index(fields=['statut']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['mac_address']),
        ]

    def __str__(self):
        return f"{self.nom} ({self.ip_address})"

    @property
    def est_en_ligne(self):
        """
        Vérifie si le poste est en ligne
        Considéré en ligne si dernière connexion < 60 secondes
        """
        if not self.derniere_connexion:
            return False
        delta = timezone.now() - self.derniere_connexion
        return delta.total_seconds() < 60

    @property
    def session_active(self):
        """Retourne la session active du poste (s'il y en a une)"""
        return self.sessions.filter(statut='active').first()

    @property
    def est_disponible(self):
        """Vérifie si le poste est disponible pour une nouvelle session"""
        return self.statut == 'disponible' and not self.session_active

    def marquer_disponible(self):
        """Marque le poste comme disponible"""
        self.statut = 'disponible'
        self.save(update_fields=['statut'])

    def marquer_occupe(self):
        """Marque le poste comme occupé"""
        self.statut = 'occupe'
        self.save(update_fields=['statut'])

    def marquer_hors_ligne(self):
        """Marque le poste comme hors ligne"""
        self.statut = 'hors_ligne'
        self.save(update_fields=['statut'])

    def mettre_a_jour_connexion(self, version_client=None):
        """Met à jour la dernière connexion et optionnellement la version du client"""
        self.derniere_connexion = timezone.now()
        if version_client:
            self.version_client = version_client
        self.save(update_fields=['derniere_connexion', 'version_client'])

    # Méthodes certificat
    @property
    def is_registered(self):
        """Vérifie si le poste a un certificat valide"""
        return (
            self.certificate_cn is not None
            and not self.is_certificate_revoked
            and (self.certificate_expires_at is None or self.certificate_expires_at > timezone.now())
        )

    @property
    def has_pending_registration(self):
        """Vérifie si un token d'enregistrement est en attente"""
        return (
            self.registration_token is not None
            and self.registration_token_expires is not None
            and self.registration_token_expires > timezone.now()
        )

    def revoke_certificate(self):
        """Révoque le certificat du poste"""
        self.is_certificate_revoked = True
        self.save(update_fields=['is_certificate_revoked'])

    def clear_registration_token(self):
        """Supprime le token d'enregistrement"""
        self.registration_token = None
        self.registration_token_expires = None
        self.save(update_fields=['registration_token', 'registration_token_expires'])

    # Méthodes de découverte
    @property
    def is_pending_validation(self):
        """Vérifie si le poste est en attente de validation"""
        return self.statut == 'en_attente_validation'

    def validate_discovery(self, username):
        """Valide un poste découvert automatiquement"""
        self.statut = 'hors_ligne'
        self.validated_by = username
        self.validated_at = timezone.now()
        self.save(update_fields=['statut', 'validated_by', 'validated_at'])
