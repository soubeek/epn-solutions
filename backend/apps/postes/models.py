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
        ('disponible', 'Disponible'),
        ('occupe', 'Occupé'),
        ('reserve', 'Réservé'),
        ('hors_ligne', 'Hors ligne'),
        ('maintenance', 'En maintenance'),
    ]

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
        blank=True,
        null=True,
        verbose_name="Adresse MAC",
        help_text="Format: AA:BB:CC:DD:EE:FF"
    )

    # État
    statut = models.CharField(
        max_length=20,
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
