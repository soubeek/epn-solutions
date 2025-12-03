"""
Modèle Log pour l'audit trail
Enregistre toutes les actions importantes du système
"""

from django.db import models
from django.utils import timezone


class Log(models.Model):
    """
    Modèle pour les logs et l'audit trail
    Enregistre toutes les actions effectuées dans le système
    """

    ACTION_CHOICES = [
        # Utilisateurs
        ('creation_utilisateur', 'Création utilisateur'),
        ('modification_utilisateur', 'Modification utilisateur'),
        ('suppression_utilisateur', 'Suppression utilisateur'),

        # Sessions
        ('generation_code', 'Génération code'),
        ('demarrage_session', 'Démarrage session'),
        ('ajout_temps', 'Ajout de temps'),
        ('fermeture', 'Fermeture session'),
        ('expiration', 'Expiration session'),
        ('suspension', 'Suspension session'),
        ('reprise', 'Reprise session'),

        # Postes
        ('connexion_poste', 'Connexion poste client'),
        ('deconnexion_poste', 'Déconnexion poste client'),
        ('changement_statut_poste', 'Changement statut poste'),

        # Opérateurs
        ('connexion_operateur', 'Connexion opérateur'),
        ('deconnexion_operateur', 'Déconnexion opérateur'),

        # Système
        ('erreur', 'Erreur système'),
        ('warning', 'Avertissement'),
        ('info', 'Information'),
    ]

    # Relation (optionnelle) vers une session
    session = models.ForeignKey(
        'poste_sessions.Session',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs',
        verbose_name="Session"
    )

    # Type d'action
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        db_index=True,
        verbose_name="Action"
    )

    # Qui a effectué l'action
    operateur = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Opérateur",
        help_text="Nom de l'opérateur ou 'system' pour les actions automatiques"
    )

    # Détails de l'action
    details = models.TextField(
        verbose_name="Détails",
        help_text="Description détaillée de l'action"
    )

    # Informations réseau
    ip_address = models.GenericIPAddressField(
        protocol='IPv4',
        blank=True,
        null=True,
        verbose_name="Adresse IP",
        help_text="IP de l'utilisateur ou du poste ayant effectué l'action"
    )

    # Métadonnées supplémentaires (JSON)
    metadata = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Métadonnées",
        help_text="Données supplémentaires au format JSON"
    )

    # Timestamp
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Date de création"
    )

    class Meta:
        db_table = 'logs'
        ordering = ['-created_at']
        verbose_name = 'Log'
        verbose_name_plural = 'Logs'
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['action']),
            models.Index(fields=['session']),
            models.Index(fields=['operateur']),
            models.Index(fields=['created_at', 'action']),
        ]

    def __str__(self):
        return f"{self.get_action_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"

    @classmethod
    def log_action(cls, action, details, operateur=None, session=None, ip_address=None, metadata=None):
        """
        Méthode utilitaire pour créer un log

        Args:
            action: Type d'action (doit être dans ACTION_CHOICES)
            details: Description de l'action
            operateur: Nom de l'opérateur (optionnel)
            session: Session concernée (optionnel)
            ip_address: Adresse IP (optionnel)
            metadata: Données supplémentaires (optionnel)

        Returns:
            Instance de Log créée
        """
        return cls.objects.create(
            action=action,
            details=details,
            operateur=operateur or 'system',
            session=session,
            ip_address=ip_address,
            metadata=metadata
        )

    @classmethod
    def log_utilisateur_creation(cls, utilisateur, operateur):
        """Log la création d'un utilisateur"""
        return cls.log_action(
            action='creation_utilisateur',
            details=f"Utilisateur {utilisateur.get_full_name()} créé",
            operateur=operateur,
            metadata={'utilisateur_id': utilisateur.id}
        )

    @classmethod
    def log_session_demarrage(cls, session):
        """Log le démarrage d'une session"""
        return cls.log_action(
            action='demarrage_session',
            details=f"Session {session.code_acces} démarrée pour {session.utilisateur.get_full_name()} sur {session.poste.nom}",
            operateur=session.operateur,
            session=session,
            metadata={
                'utilisateur_id': session.utilisateur.id,
                'poste_id': session.poste.id,
                'duree_initiale': session.duree_initiale
            }
        )

    @classmethod
    def log_erreur(cls, details, operateur=None, metadata=None):
        """Log une erreur système"""
        return cls.log_action(
            action='erreur',
            details=details,
            operateur=operateur,
            metadata=metadata
        )

    @classmethod
    def cleanup_old_logs(cls, days=90):
        """
        Supprime les logs plus anciens que X jours

        Args:
            days: Nombre de jours à conserver (défaut: 90)

        Returns:
            Nombre de logs supprimés
        """
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        deleted_count, _ = cls.objects.filter(created_at__lt=cutoff_date).delete()
        return deleted_count
