"""
Serializers pour l'app Utilisateurs
"""

from rest_framework import serializers
from .models import Utilisateur


class UtilisateurSerializer(serializers.ModelSerializer):
    """
    Serializer pour le modèle Utilisateur
    Gère la création et modification avec photo
    """

    # Champs calculés en lecture seule
    age = serializers.IntegerField(read_only=True)
    sessions_count = serializers.IntegerField(read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    can_create_session = serializers.SerializerMethodField()

    # Photo avec validation
    photo = serializers.ImageField(
        required=False,
        allow_null=True,
        help_text="Photo d'identité (max 5MB, formats: JPEG, PNG)"
    )

    class Meta:
        model = Utilisateur
        fields = [
            'id',
            'nom',
            'prenom',
            'full_name',
            'email',
            'telephone',
            'carte_identite',
            'adresse',
            'date_naissance',
            'age',
            'photo',
            'consentement_rgpd',
            'date_consentement',
            'created_by',
            'notes',
            'nombre_sessions_total',
            'sessions_count',
            'derniere_session',
            'can_create_session',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'full_name',
            'age',
            'sessions_count',
            'date_consentement',
            'nombre_sessions_total',
            'derniere_session',
            'can_create_session',
            'created_at',
            'updated_at'
        ]

    def get_can_create_session(self, obj):
        """Vérifie si l'utilisateur peut créer une session aujourd'hui"""
        return obj.can_create_session_today()

    def validate_telephone(self, value):
        """Validation personnalisée du téléphone"""
        if value:
            # Le validator du modèle fera la validation regex
            # On peut ajouter des validations supplémentaires ici
            if len(value) < 10:
                raise serializers.ValidationError(
                    "Le numéro de téléphone doit contenir au moins 10 chiffres"
                )
        return value

    def validate_photo(self, value):
        """Validation de la photo"""
        if value:
            # Vérifier la taille (5MB max)
            max_size = 5 * 1024 * 1024  # 5MB
            if value.size > max_size:
                raise serializers.ValidationError(
                    f"La photo ne doit pas dépasser 5MB (taille actuelle: {value.size // 1024 // 1024}MB)"
                )

            # Vérifier le format
            allowed_formats = ['JPEG', 'PNG', 'JPG']
            file_ext = value.name.split('.')[-1].upper()
            if file_ext not in allowed_formats:
                raise serializers.ValidationError(
                    f"Format non autorisé. Formats acceptés: {', '.join(allowed_formats)}"
                )

        return value

    def validate_consentement_rgpd(self, value):
        """Le consentement RGPD doit être True"""
        if not value:
            raise serializers.ValidationError(
                "Le consentement RGPD est obligatoire pour créer un utilisateur"
            )
        return value

    def validate(self, attrs):
        """Validation globale"""
        # Vérifier qu'au moins un moyen de contact est fourni
        if not attrs.get('email') and not attrs.get('telephone'):
            raise serializers.ValidationError(
                "Au moins un moyen de contact (email ou téléphone) est requis"
            )
        return attrs


class UtilisateurListSerializer(serializers.ModelSerializer):
    """
    Serializer simplifié pour les listes d'utilisateurs
    """
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    sessions_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Utilisateur
        fields = [
            'id',
            'nom',
            'prenom',
            'full_name',
            'email',
            'telephone',
            'sessions_count',
            'derniere_session',
            'created_at'
        ]


class UtilisateurStatsSerializer(serializers.ModelSerializer):
    """
    Serializer pour les statistiques utilisateur
    """
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    age = serializers.IntegerField(read_only=True)
    sessions_actives = serializers.SerializerMethodField()
    sessions_total = serializers.IntegerField(source='nombre_sessions_total', read_only=True)

    class Meta:
        model = Utilisateur
        fields = [
            'id',
            'full_name',
            'age',
            'sessions_actives',
            'sessions_total',
            'derniere_session'
        ]

    def get_sessions_actives(self, obj):
        """Compte les sessions actives de l'utilisateur"""
        return obj.sessions.filter(statut='active').count()
