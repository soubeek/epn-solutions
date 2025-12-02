"""
Modèle Session pour la gestion des sessions utilisateurs
"""

import secrets
import string
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.conf import settings
from apps.core.models import TimeStampedModel


class Session(TimeStampedModel):
    """
    Modèle pour les sessions des postes publics
    Gère les codes d'accès, la durée et l'état des sessions
    """

    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('active', 'Active'),
        ('terminee', 'Terminée'),
        ('suspendue', 'Suspendue'),
        ('expiree', 'Expirée'),
    ]

    # Relations
    utilisateur = models.ForeignKey(
        'utilisateurs.Utilisateur',
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name="Utilisateur"
    )
    poste = models.ForeignKey(
        'postes.Poste',
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name="Poste"
    )

    # Code d'accès
    code_acces = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        verbose_name="Code d'accès",
        help_text="Code unique pour démarrer la session"
    )

    # Durées (en secondes)
    duree_initiale = models.IntegerField(
        validators=[MinValueValidator(60)],
        verbose_name="Durée initiale",
        help_text="Durée initiale en secondes (minimum 60s = 1min)"
    )
    temps_restant = models.IntegerField(
        verbose_name="Temps restant",
        help_text="Temps restant en secondes"
    )
    temps_ajoute = models.IntegerField(
        default=0,
        verbose_name="Temps ajouté",
        help_text="Temps total ajouté en secondes"
    )

    # Dates
    debut_session = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Début de session"
    )
    fin_session = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Fin de session"
    )

    # Statut
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='en_attente',
        verbose_name="Statut"
    )

    # Métadonnées
    operateur = models.CharField(
        max_length=100,
        verbose_name="Opérateur",
        help_text="Nom de l'opérateur ayant créé la session"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notes"
    )

    class Meta:
        db_table = 'sessions'
        ordering = ['-created_at']
        verbose_name = 'Session'
        verbose_name_plural = 'Sessions'
        indexes = [
            models.Index(fields=['statut']),
            models.Index(fields=['code_acces']),
            models.Index(fields=['utilisateur', 'poste']),
            models.Index(fields=['debut_session']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"Session {self.code_acces} - {self.utilisateur.get_full_name()}"

    @staticmethod
    def generer_code(longueur=6):
        """
        Génère un code d'accès unique
        Évite les caractères ambigus (O/0, I/1)
        """
        alphabet = string.ascii_uppercase + string.digits
        # Retirer les caractères ambigus
        alphabet = alphabet.replace('O', '').replace('0', '').replace('I', '').replace('1', '')

        max_attempts = 100
        for _ in range(max_attempts):
            code = ''.join(secrets.choice(alphabet) for _ in range(longueur))
            if not Session.objects.filter(code_acces=code).exists():
                return code

        # Si on n'a pas trouvé de code unique après 100 tentatives,
        # on rallonge le code
        return Session.generer_code(longueur=longueur + 1)

    def save(self, *args, **kwargs):
        """Override save pour générer le code automatiquement"""
        if not self.code_acces:
            code_length = settings.POSTE_PUBLIC.get('CODE_LENGTH', 6)
            self.code_acces = self.generer_code(longueur=code_length)

        # Si c'est une nouvelle session, initialiser temps_restant
        if not self.pk and not self.temps_restant:
            self.temps_restant = self.duree_initiale

        super().save(*args, **kwargs)

    @property
    def duree_totale(self):
        """Durée totale = initiale + ajoutée"""
        return self.duree_initiale + self.temps_ajoute

    @property
    def temps_ecoule(self):
        """Temps écoulé depuis le début de la session"""
        if self.debut_session:
            delta = timezone.now() - self.debut_session
            return int(delta.total_seconds())
        return 0

    @property
    def est_expiree(self):
        """Vérifie si la session est expirée"""
        return self.temps_restant <= 0

    @property
    def pourcentage_utilise(self):
        """Pourcentage de temps utilisé"""
        if self.duree_totale > 0:
            return int((self.temps_ecoule / self.duree_totale) * 100)
        return 0

    @property
    def minutes_restantes(self):
        """Temps restant en minutes"""
        return self.temps_restant // 60

    def ajouter_temps(self, secondes, operateur):
        """
        Ajoute du temps à la session

        Args:
            secondes: Nombre de secondes à ajouter
            operateur: Nom de l'opérateur effectuant l'action
        """
        self.temps_restant += secondes
        self.temps_ajoute += secondes
        self.save(update_fields=['temps_restant', 'temps_ajoute', 'updated_at'])

        # Créer un log
        from apps.logs.models import Log
        Log.objects.create(
            session=self,
            action='ajout_temps',
            operateur=operateur,
            details=f"{secondes // 60} minutes ajoutées à la session {self.code_acces}"
        )

    def demarrer(self):
        """Démarre la session"""
        self.statut = 'active'
        self.debut_session = timezone.now()
        self.save(update_fields=['statut', 'debut_session', 'updated_at'])

        # Marquer le poste comme occupé
        self.poste.marquer_occupe()

        # Mettre à jour les stats de l'utilisateur
        self.utilisateur.nombre_sessions_total += 1
        self.utilisateur.derniere_session = timezone.now()
        self.utilisateur.save(update_fields=['nombre_sessions_total', 'derniere_session', 'updated_at'])

        # Mettre à jour les stats du poste
        self.poste.nombre_sessions_total += 1
        self.poste.save(update_fields=['nombre_sessions_total', 'updated_at'])

        # Log
        from apps.logs.models import Log
        Log.objects.create(
            session=self,
            action='demarrage_session',
            operateur=self.operateur,
            details=f"Session {self.code_acces} démarrée sur {self.poste.nom}"
        )

    def terminer(self, operateur, raison='fermeture_normale'):
        """
        Termine la session

        Args:
            operateur: Nom de l'opérateur effectuant l'action
            raison: Raison de la fermeture (fermeture_normale, expiration, fermeture_forcee)
        """
        self.statut = 'terminee'
        self.fin_session = timezone.now()
        self.temps_restant = 0
        self.save(update_fields=['statut', 'fin_session', 'temps_restant', 'updated_at'])

        # Libérer le poste
        self.poste.marquer_disponible()

        # Log
        from apps.logs.models import Log
        Log.objects.create(
            session=self,
            action='fermeture',
            operateur=operateur,
            details=f"Session {self.code_acces} terminée - Raison: {raison}"
        )

    def suspendre(self, operateur):
        """Suspend la session"""
        self.statut = 'suspendue'
        self.save(update_fields=['statut', 'updated_at'])

        from apps.logs.models import Log
        Log.objects.create(
            session=self,
            action='suspension',
            operateur=operateur,
            details=f"Session {self.code_acces} suspendue"
        )

    def reprendre(self, operateur):
        """Reprend une session suspendue"""
        if self.statut == 'suspendue':
            self.statut = 'active'
            self.save(update_fields=['statut', 'updated_at'])

            from apps.logs.models import Log
            Log.objects.create(
                session=self,
                action='reprise',
                operateur=operateur,
                details=f"Session {self.code_acces} reprise"
            )

    def decremente_temps(self, secondes=1):
        """
        Décrémente le temps restant
        Utilisé par les tâches Celery
        """
        if self.temps_restant > 0:
            self.temps_restant -= secondes
            if self.temps_restant <= 0:
                self.temps_restant = 0
                self.statut = 'expiree'
                self.fin_session = timezone.now()
                self.poste.marquer_disponible()

                from apps.logs.models import Log
                Log.objects.create(
                    session=self,
                    action='expiration',
                    operateur='system',
                    details=f"Session {self.code_acces} expirée automatiquement"
                )

            self.save(update_fields=['temps_restant', 'statut', 'fin_session', 'updated_at'])
