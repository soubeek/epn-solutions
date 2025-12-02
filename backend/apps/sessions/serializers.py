"""
Serializers pour l'app Sessions
"""

from rest_framework import serializers
from django.utils import timezone
from .models import Session


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

    class Meta:
        model = Session
        fields = [
            'id',
            'code_acces',
            'utilisateur_nom',
            'poste_nom',
            'statut',
            'minutes_restantes',
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
