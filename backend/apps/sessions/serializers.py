"""
Serializers pour l'app Sessions
"""

from rest_framework import serializers
from django.utils import timezone
from .models import Session, ExtensionRequest
from apps.postes.models import Poste


class SessionSerializer(serializers.ModelSerializer):
    """
    Serializer pour le modèle Session
    Gère la création et modification des sessions
    """

    # Champs calculés en lecture seule
    duree_totale = serializers.IntegerField(read_only=True)
    temps_ecoule = serializers.IntegerField(read_only=True)
    est_expiree = serializers.BooleanField(read_only=True)
    pourcentage_utilise = serializers.IntegerField(read_only=True)
    minutes_restantes = serializers.IntegerField(read_only=True)
    is_guest_session = serializers.BooleanField(read_only=True)

    # Relations avec détails
    utilisateur_nom = serializers.CharField(
        source='utilisateur.get_full_name',
        read_only=True
    )
    poste_nom = serializers.CharField(
        source='poste.nom',
        read_only=True
    )

    class Meta:
        model = Session
        fields = [
            'id',
            'code_acces',
            'utilisateur',
            'utilisateur_nom',
            'poste',
            'poste_nom',
            'duree_initiale',
            'temps_restant',
            'temps_ajoute',
            'duree_totale',
            'temps_ecoule',
            'debut_session',
            'fin_session',
            'statut',
            'est_expiree',
            'pourcentage_utilise',
            'minutes_restantes',
            'is_guest_session',
            'operateur',
            'notes',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'code_acces',
            'temps_restant',
            'temps_ajoute',
            'duree_totale',
            'temps_ecoule',
            'debut_session',
            'fin_session',
            'est_expiree',
            'pourcentage_utilise',
            'minutes_restantes',
            'is_guest_session',
            'created_at',
            'updated_at'
        ]

    def validate_duree_initiale(self, value):
        """Validation de la durée initiale"""
        if value < 60:
            raise serializers.ValidationError(
                "La durée minimale est de 60 secondes (1 minute)"
            )

        # Vérifier la durée maximale (ex: 4 heures = 14400 secondes)
        max_duration = 14400  # 4 heures
        if value > max_duration:
            raise serializers.ValidationError(
                f"La durée maximale est de {max_duration // 3600} heures"
            )

        return value

    def validate(self, attrs):
        """Validation globale"""
        # Si c'est une nouvelle session
        if not self.instance:
            utilisateur = attrs.get('utilisateur')
            poste = attrs.get('poste')

            # Vérifier que l'utilisateur peut créer une session aujourd'hui
            if utilisateur and not utilisateur.can_create_session_today():
                max_sessions = 3  # Pourrait venir de settings
                raise serializers.ValidationError(
                    f"L'utilisateur a atteint la limite de {max_sessions} sessions par jour"
                )

            # Vérifier que le poste est disponible
            if poste and not poste.est_disponible:
                if poste.session_active:
                    raise serializers.ValidationError(
                        f"Le poste {poste.nom} est déjà occupé par la session {poste.session_active.code_acces}"
                    )
                else:
                    raise serializers.ValidationError(
                        f"Le poste {poste.nom} n'est pas disponible (statut: {poste.get_statut_display()})"
                    )

            # Initialiser temps_restant si pas défini
            if 'temps_restant' not in attrs:
                attrs['temps_restant'] = attrs.get('duree_initiale')

        return attrs


class SessionListSerializer(serializers.ModelSerializer):
    """
    Serializer simplifié pour les listes de sessions
    """
    utilisateur_nom = serializers.CharField(source='utilisateur.get_full_name', read_only=True)
    poste_nom = serializers.CharField(source='poste.nom', read_only=True)
    minutes_restantes = serializers.IntegerField(read_only=True)
    temps_ecoule = serializers.IntegerField(read_only=True)
    pourcentage_utilise = serializers.IntegerField(read_only=True)
    is_guest = serializers.BooleanField(source='utilisateur.is_guest', read_only=True)

    class Meta:
        model = Session
        fields = [
            'id',
            'code_acces',
            'utilisateur_nom',
            'poste_nom',
            'statut',
            'temps_restant',
            'temps_ecoule',
            'minutes_restantes',
            'pourcentage_utilise',
            'is_guest',
            'debut_session',
            'created_at'
        ]


class SessionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la création de sessions
    Simplifié pour l'opérateur
    """
    duree_minutes = serializers.IntegerField(
        write_only=True,
        min_value=1,
        max_value=240,
        help_text="Durée en minutes (1-240)"
    )

    class Meta:
        model = Session
        fields = [
            'utilisateur',
            'poste',
            'duree_minutes',
            'operateur',
            'notes'
        ]

    def validate_duree_minutes(self, value):
        """Validation de la durée en minutes"""
        if value < 1:
            raise serializers.ValidationError("La durée minimale est de 1 minute")
        if value > 240:
            raise serializers.ValidationError("La durée maximale est de 240 minutes (4 heures)")
        return value

    def create(self, validated_data):
        """Création avec conversion minutes → secondes"""
        duree_minutes = validated_data.pop('duree_minutes')
        validated_data['duree_initiale'] = duree_minutes * 60
        validated_data['temps_restant'] = validated_data['duree_initiale']

        return super().create(validated_data)


class SessionValidateCodeSerializer(serializers.Serializer):
    """
    Serializer pour la validation d'un code d'accès
    Utilisé par le client pour démarrer une session
    """
    code_acces = serializers.CharField(
        max_length=10,
        help_text="Code d'accès de la session"
    )
    ip_address = serializers.IPAddressField(
        protocol='IPv4',
        help_text="Adresse IP du poste"
    )

    def validate_code_acces(self, value):
        """Validation du code d'accès"""
        # Normaliser en majuscules
        value = value.upper().strip()

        # Vérifier que le code existe
        try:
            session = Session.objects.get(code_acces=value)
        except Session.DoesNotExist:
            raise serializers.ValidationError("Code d'accès invalide")

        # Vérifier que la session est en attente
        if session.statut != 'en_attente':
            raise serializers.ValidationError(
                f"Cette session ne peut pas être démarrée (statut: {session.get_statut_display()})"
            )

        return value


class SessionAddTimeSerializer(serializers.Serializer):
    """
    Serializer pour ajouter du temps à une session
    L'opérateur est récupéré automatiquement depuis request.user
    """
    minutes = serializers.IntegerField(
        min_value=1,
        max_value=120,
        help_text="Nombre de minutes à ajouter (1-120)"
    )


class SessionTerminateSerializer(serializers.Serializer):
    """
    Serializer pour terminer une session
    L'opérateur est récupéré automatiquement depuis request.user
    """
    raison = serializers.ChoiceField(
        choices=[
            ('fermeture_normale', 'Fermeture normale'),
            ('fermeture_forcee', 'Fermeture forcée'),
            ('expiration', 'Expiration'),
        ],
        default='fermeture_normale'
    )


class SessionStatsSerializer(serializers.ModelSerializer):
    """
    Serializer pour les statistiques de session
    """
    utilisateur_nom = serializers.CharField(source='utilisateur.get_full_name', read_only=True)
    poste_nom = serializers.CharField(source='poste.nom', read_only=True)
    duree_totale = serializers.IntegerField(read_only=True)
    temps_ecoule = serializers.IntegerField(read_only=True)
    pourcentage_utilise = serializers.IntegerField(read_only=True)

    class Meta:
        model = Session
        fields = [
            'id',
            'code_acces',
            'utilisateur_nom',
            'poste_nom',
            'duree_totale',
            'temps_ecoule',
            'pourcentage_utilise',
            'debut_session',
            'fin_session',
            'statut'
        ]


class SessionActiveSerializer(serializers.ModelSerializer):
    """
    Serializer pour les sessions actives (temps réel)
    Optimisé pour les mises à jour fréquentes via WebSocket
    """
    utilisateur_nom = serializers.CharField(source='utilisateur.get_full_name', read_only=True)
    poste_nom = serializers.CharField(source='poste.nom', read_only=True)
    temps_restant_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = [
            'id',
            'code_acces',
            'utilisateur_nom',
            'poste_nom',
            'temps_restant',
            'temps_restant_minutes',
            'pourcentage_utilise',
            'statut'
        ]

    def get_temps_restant_minutes(self, obj):
        """Temps restant formaté en minutes:secondes"""
        minutes = obj.temps_restant // 60
        secondes = obj.temps_restant % 60
        return f"{minutes:02d}:{secondes:02d}"


class GuestSessionCreateSerializer(serializers.Serializer):
    """
    Serializer pour la création de sessions invité
    Ne nécessite pas d'utilisateur existant - crée un guest automatiquement
    """
    poste = serializers.PrimaryKeyRelatedField(
        queryset=Poste.objects.all(),
        help_text="ID du poste"
    )
    duree_minutes = serializers.IntegerField(
        min_value=1,
        max_value=240,
        help_text="Durée en minutes (1-240)"
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Notes optionnelles"
    )

    def validate_poste(self, value):
        """Vérifier que le poste est disponible"""
        if not value.est_disponible:
            if value.session_active:
                raise serializers.ValidationError(
                    f"Le poste {value.nom} est déjà occupé par la session {value.session_active.code_acces}"
                )
            else:
                raise serializers.ValidationError(
                    f"Le poste {value.nom} n'est pas disponible (statut: {value.get_statut_display()})"
                )
        return value

    def create(self, validated_data):
        """Création de la session invité avec utilisateur auto-généré"""
        from apps.utilisateurs.models import Utilisateur
        from apps.logs.models import Log

        poste = validated_data['poste']
        duree_minutes = validated_data['duree_minutes']
        notes = validated_data.get('notes', '')
        operateur = self.context['request'].user.username if self.context['request'].user.is_authenticated else 'anonymous'

        # Créer l'utilisateur guest anonyme
        guest_user = Utilisateur.create_guest(created_by=operateur)

        # Créer la session
        session = Session.objects.create(
            utilisateur=guest_user,
            poste=poste,
            duree_initiale=duree_minutes * 60,
            temps_restant=duree_minutes * 60,
            operateur=operateur,
            notes=f"[INVITÉ] {notes}".strip() if notes else "[INVITÉ]"
        )

        # Log la création de session invité
        Log.log_action(
            action='generation_code',
            details=f"Session invité {session.code_acces} créée pour {guest_user.nom} sur {poste.nom}",
            operateur=operateur,
            session=session,
            metadata={
                'is_guest': True,
                'guest_identifier': guest_user.nom,
                'poste': poste.nom,
                'duree_minutes': duree_minutes
            }
        )

        return session


# ==================== Serializers pour les demandes de prolongation ====================

class ExtensionRequestSerializer(serializers.ModelSerializer):
    """
    Serializer pour les demandes de prolongation
    """
    session_code = serializers.CharField(source='session.code_acces', read_only=True)
    utilisateur_nom = serializers.CharField(source='session.utilisateur.get_full_name', read_only=True)
    poste_nom = serializers.CharField(source='session.poste.nom', read_only=True)
    temps_restant = serializers.IntegerField(source='session.temps_restant', read_only=True)

    class Meta:
        model = ExtensionRequest
        fields = [
            'id',
            'session',
            'session_code',
            'utilisateur_nom',
            'poste_nom',
            'temps_restant',
            'minutes_requested',
            'statut',
            'responded_by',
            'responded_at',
            'response_message',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'session',
            'statut',
            'responded_by',
            'responded_at',
            'response_message',
            'created_at',
            'updated_at'
        ]


class ExtensionRequestCreateSerializer(serializers.Serializer):
    """
    Serializer pour créer une demande de prolongation depuis le client
    """
    session_id = serializers.IntegerField(help_text="ID de la session")
    minutes = serializers.IntegerField(
        min_value=5,
        max_value=60,
        default=15,
        help_text="Nombre de minutes demandées (5-60)"
    )

    def validate_session_id(self, value):
        """Vérifier que la session existe et est active"""
        try:
            session = Session.objects.get(id=value)
        except Session.DoesNotExist:
            raise serializers.ValidationError("Session introuvable")

        if session.statut not in ['active', 'suspendue']:
            raise serializers.ValidationError(
                f"La session n'est plus active (statut: {session.get_statut_display()})"
            )

        return value

    def validate(self, attrs):
        """Vérifier qu'il n'y a pas déjà une demande en attente"""
        session_id = attrs['session_id']

        # Vérifier s'il y a une demande en attente pour cette session
        pending_request = ExtensionRequest.objects.filter(
            session_id=session_id,
            statut='pending'
        ).exists()

        if pending_request:
            raise serializers.ValidationError(
                "Une demande de prolongation est déjà en attente pour cette session"
            )

        return attrs

    def create(self, validated_data):
        """Créer la demande de prolongation"""
        session = Session.objects.get(id=validated_data['session_id'])

        extension_request = ExtensionRequest.objects.create(
            session=session,
            minutes_requested=validated_data['minutes']
        )

        # Log
        from apps.logs.models import Log
        Log.objects.create(
            session=session,
            action='extension_requested',
            operateur='client',
            details=f"Demande de prolongation de {validated_data['minutes']} min pour {session.code_acces}"
        )

        return extension_request


class ExtensionRequestResponseSerializer(serializers.Serializer):
    """
    Serializer pour répondre à une demande de prolongation (admin)
    """
    approve = serializers.BooleanField(help_text="True pour approuver, False pour refuser")
    message = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
        help_text="Message optionnel"
    )
