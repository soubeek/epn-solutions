"""
Serializers pour l'app Logs
"""

from rest_framework import serializers
from .models import Log


class LogSerializer(serializers.ModelSerializer):
    """
    Serializer pour le modèle Log
    Read-only - les logs ne peuvent être créés que par le système
    """

    # Relations avec détails
    session_code = serializers.CharField(
        source='session.code_acces',
        read_only=True
    )
    action_display = serializers.CharField(
        source='get_action_display',
        read_only=True
    )

    class Meta:
        model = Log
        fields = [
            'id',
            'session',
            'session_code',
            'action',
            'action_display',
            'operateur',
            'details',
            'ip_address',
            'metadata',
            'created_at'
        ]
        read_only_fields = '__all__'  # Tous les champs en lecture seule

    def create(self, validated_data):
        """Empêcher la création via l'API"""
        raise serializers.ValidationError(
            "Les logs ne peuvent être créés que par le système"
        )

    def update(self, instance, validated_data):
        """Empêcher la modification via l'API"""
        raise serializers.ValidationError(
            "Les logs ne peuvent pas être modifiés"
        )


class LogListSerializer(serializers.ModelSerializer):
    """
    Serializer simplifié pour les listes de logs
    """
    session_code = serializers.CharField(source='session.code_acces', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = Log
        fields = [
            'id',
            'action_display',
            'operateur',
            'details',
            'session_code',
            'created_at'
        ]


class LogStatsSerializer(serializers.Serializer):
    """
    Serializer pour les statistiques de logs
    Utilisé pour les agrégations
    """
    action = serializers.CharField()
    action_display = serializers.CharField()
    count = serializers.IntegerField()
    last_occurrence = serializers.DateTimeField()


class LogFilterSerializer(serializers.Serializer):
    """
    Serializer pour les filtres de recherche de logs
    """
    action = serializers.ChoiceField(
        choices=Log.ACTION_CHOICES,
        required=False,
        help_text="Filtrer par type d'action"
    )
    operateur = serializers.CharField(
        required=False,
        max_length=100,
        help_text="Filtrer par opérateur"
    )
    session_id = serializers.IntegerField(
        required=False,
        help_text="Filtrer par session"
    )
    date_debut = serializers.DateTimeField(
        required=False,
        help_text="Date de début (format ISO 8601)"
    )
    date_fin = serializers.DateTimeField(
        required=False,
        help_text="Date de fin (format ISO 8601)"
    )
    ip_address = serializers.IPAddressField(
        required=False,
        protocol='IPv4',
        help_text="Filtrer par adresse IP"
    )

    def validate(self, attrs):
        """Validation des dates"""
        date_debut = attrs.get('date_debut')
        date_fin = attrs.get('date_fin')

        if date_debut and date_fin:
            if date_debut > date_fin:
                raise serializers.ValidationError(
                    "La date de début doit être antérieure à la date de fin"
                )

        return attrs
