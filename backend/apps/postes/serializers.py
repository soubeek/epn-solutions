"""
Serializers pour l'app Postes
"""

from rest_framework import serializers
from .models import Poste


class PosteSerializer(serializers.ModelSerializer):
    """
    Serializer pour le modèle Poste
    Gère la création et modification des postes informatiques
    """

    # Champs calculés en lecture seule
    est_en_ligne = serializers.BooleanField(read_only=True)
    est_disponible = serializers.BooleanField(read_only=True)
    session_active_info = serializers.SerializerMethodField()

    class Meta:
        model = Poste
        fields = [
            'id',
            'nom',
            'ip_address',
            'mac_address',
            'statut',
            'derniere_connexion',
            'version_client',
            'emplacement',
            'notes',
            'nombre_sessions_total',
            'est_en_ligne',
            'est_disponible',
            'session_active_info',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'derniere_connexion',
            'version_client',
            'nombre_sessions_total',
            'est_en_ligne',
            'est_disponible',
            'session_active_info',
            'created_at',
            'updated_at'
        ]

    def get_session_active_info(self, obj):
        """Retourne les infos de la session active si elle existe"""
        session = obj.session_active
        if session:
            return {
                'id': session.id,
                'code_acces': session.code_acces,
                'utilisateur': session.utilisateur.get_full_name(),
                'temps_restant': session.temps_restant,
                'statut': session.statut
            }
        return None

    def validate_ip_address(self, value):
        """Validation de l'adresse IP"""
        # Vérifier que l'IP n'est pas déjà utilisée (sauf si mise à jour du même poste)
        instance_id = self.instance.id if self.instance else None
        existing = Poste.objects.filter(ip_address=value).exclude(id=instance_id)

        if existing.exists():
            raise serializers.ValidationError(
                f"L'adresse IP {value} est déjà utilisée par le poste '{existing.first().nom}'"
            )

        return value

    def validate_mac_address(self, value):
        """Validation de l'adresse MAC"""
        if value:
            # Vérifier le format AA:BB:CC:DD:EE:FF
            import re
            mac_pattern = r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$'
            if not re.match(mac_pattern, value):
                raise serializers.ValidationError(
                    "Format d'adresse MAC invalide. Format attendu: AA:BB:CC:DD:EE:FF"
                )

            # Normaliser en majuscules
            value = value.upper()

            # Vérifier que la MAC n'est pas déjà utilisée (sauf si mise à jour du même poste)
            instance_id = self.instance.id if self.instance else None
            existing = Poste.objects.filter(mac_address=value).exclude(id=instance_id)

            if existing.exists():
                raise serializers.ValidationError(
                    f"L'adresse MAC {value} est déjà utilisée par le poste '{existing.first().nom}'"
                )

        return value

    def validate_nom(self, value):
        """Validation du nom du poste"""
        # Vérifier que le nom n'est pas déjà utilisé (sauf si mise à jour du même poste)
        instance_id = self.instance.id if self.instance else None
        existing = Poste.objects.filter(nom=value).exclude(id=instance_id)

        if existing.exists():
            raise serializers.ValidationError(
                f"Un poste avec le nom '{value}' existe déjà"
            )

        return value


class PosteListSerializer(serializers.ModelSerializer):
    """
    Serializer simplifié pour les listes de postes
    """
    est_en_ligne = serializers.BooleanField(read_only=True)
    est_disponible = serializers.BooleanField(read_only=True)
    session_active_code = serializers.SerializerMethodField()

    class Meta:
        model = Poste
        fields = [
            'id',
            'nom',
            'ip_address',
            'statut',
            'emplacement',
            'est_en_ligne',
            'est_disponible',
            'session_active_code',
            'derniere_connexion'
        ]

    def get_session_active_code(self, obj):
        """Retourne le code de la session active si elle existe"""
        session = obj.session_active
        return session.code_acces if session else None


class PosteStatsSerializer(serializers.ModelSerializer):
    """
    Serializer pour les statistiques de poste
    """
    est_en_ligne = serializers.BooleanField(read_only=True)
    taux_utilisation = serializers.SerializerMethodField()
    sessions_actives = serializers.SerializerMethodField()

    class Meta:
        model = Poste
        fields = [
            'id',
            'nom',
            'statut',
            'est_en_ligne',
            'nombre_sessions_total',
            'taux_utilisation',
            'sessions_actives',
            'derniere_connexion'
        ]

    def get_taux_utilisation(self, obj):
        """
        Calcule le taux d'utilisation du poste sur les 7 derniers jours
        Basé sur le temps d'utilisation réel par rapport au temps disponible
        """
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Sum

        # Période d'analyse: 7 derniers jours
        now = timezone.now()
        start_date = now - timedelta(days=7)

        # Temps total disponible (en supposant 12h/jour d'ouverture)
        heures_ouverture_par_jour = 12
        temps_disponible_secondes = 7 * heures_ouverture_par_jour * 3600

        # Temps total utilisé (sessions terminées ou actives)
        sessions = obj.sessions.filter(
            created_at__gte=start_date,
            statut__in=['active', 'terminee', 'expiree']
        )

        # Calculer le temps utilisé
        temps_utilise = 0
        for session in sessions:
            if session.debut_session:
                if session.fin_session:
                    # Session terminée: durée réelle
                    duree = (session.fin_session - session.debut_session).total_seconds()
                else:
                    # Session active: temps écoulé jusqu'à maintenant
                    duree = (now - session.debut_session).total_seconds()
                temps_utilise += duree

        if temps_disponible_secondes > 0:
            taux = (temps_utilise / temps_disponible_secondes) * 100
            return round(min(taux, 100), 1)  # Plafonné à 100%
        return 0.0

    def get_sessions_actives(self, obj):
        """Compte les sessions actives du poste"""
        return obj.sessions.filter(statut='active').count()


class PosteHeartbeatSerializer(serializers.Serializer):
    """
    Serializer pour les heartbeat des postes
    Utilisé par le client pour signaler qu'il est en ligne
    """
    ip_address = serializers.IPAddressField(protocol='IPv4')
    version_client = serializers.CharField(max_length=50, required=False, allow_blank=True)
    mac_address = serializers.CharField(max_length=17, required=False, allow_blank=True)

    def validate_mac_address(self, value):
        """Validation du format MAC"""
        if value:
            import re
            mac_pattern = r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$'
            if not re.match(mac_pattern, value):
                raise serializers.ValidationError(
                    "Format d'adresse MAC invalide. Format attendu: AA:BB:CC:DD:EE:FF"
                )
            return value.upper()
        return value
