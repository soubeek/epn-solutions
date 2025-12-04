"""
ViewSets pour l'app Postes
"""

import secrets
from datetime import timedelta

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from .models import Poste
from .serializers import (
    PosteSerializer,
    PosteListSerializer,
    PosteStatsSerializer,
    PosteHeartbeatSerializer
)
from .certificate_manager import get_certificate_manager


class PosteViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les postes

    Endpoints:
    - GET /api/postes/ - Liste des postes
    - POST /api/postes/ - Créer un poste
    - GET /api/postes/{id}/ - Détail d'un poste
    - PUT /api/postes/{id}/ - Modifier un poste
    - PATCH /api/postes/{id}/ - Modifier partiellement
    - DELETE /api/postes/{id}/ - Supprimer un poste
    - GET /api/postes/disponibles/ - Postes disponibles
    - POST /api/postes/{id}/heartbeat/ - Heartbeat du client
    - POST /api/postes/{id}/marquer_disponible/ - Marquer disponible
    - POST /api/postes/{id}/marquer_maintenance/ - Marquer en maintenance
    """

    queryset = Poste.objects.all()
    serializer_class = PosteSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # Filtres
    filterset_fields = ['statut', 'emplacement']
    search_fields = ['nom', 'ip_address', 'mac_address', 'emplacement']
    ordering_fields = ['nom', 'statut', 'derniere_connexion', 'nombre_sessions_total']
    ordering = ['nom']

    def get_serializer_class(self):
        """Retourne le serializer approprié selon l'action"""
        if self.action == 'list':
            return PosteListSerializer
        elif self.action == 'stats':
            return PosteStatsSerializer
        return PosteSerializer

    @action(detail=False, methods=['get'])
    def disponibles(self, request):
        """
        Retourne la liste des postes disponibles

        GET /api/postes/disponibles/
        """
        postes = Poste.objects.filter(statut='disponible')
        serializer = PosteListSerializer(postes, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Retourne les statistiques globales des postes

        GET /api/postes/stats/
        """
        from django.db.models import Count

        total = Poste.objects.count()
        stats_par_statut = Poste.objects.values('statut').annotate(count=Count('id'))

        # Postes en ligne
        en_ligne = sum(1 for p in Poste.objects.all() if p.est_en_ligne)

        return Response({
            'total': total,
            'en_ligne': en_ligne,
            'hors_ligne': total - en_ligne,
            'par_statut': {item['statut']: item['count'] for item in stats_par_statut}
        })

    @action(detail=True, methods=['post'])
    def heartbeat(self, request, pk=None):
        """
        Endpoint pour le heartbeat des clients
        Le client envoie régulièrement un signal pour indiquer qu'il est en ligne

        POST /api/postes/{id}/heartbeat/
        Body: {
            "ip_address": "192.168.1.100",
            "version_client": "1.0.0",
            "mac_address": "AA:BB:CC:DD:EE:FF"  (optionnel)
        }
        """
        poste = self.get_object()
        serializer = PosteHeartbeatSerializer(data=request.data)

        if serializer.is_valid():
            # Mettre à jour la dernière connexion
            version = serializer.validated_data.get('version_client')
            mac = serializer.validated_data.get('mac_address')

            poste.mettre_a_jour_connexion(version_client=version)

            # Mettre à jour la MAC si fournie et différente
            if mac and poste.mac_address != mac:
                poste.mac_address = mac
                poste.save(update_fields=['mac_address'])

            return Response({
                'status': 'ok',
                'poste': poste.nom,
                'est_en_ligne': poste.est_en_ligne,
                'session_active': poste.session_active.code_acces if poste.session_active else None
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def marquer_disponible(self, request, pk=None):
        """
        Marque le poste comme disponible

        POST /api/postes/{id}/marquer_disponible/
        """
        poste = self.get_object()

        # Vérifier qu'il n'y a pas de session active
        if poste.session_active:
            return Response(
                {'error': f"Le poste a une session active: {poste.session_active.code_acces}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        poste.marquer_disponible()

        return Response({
            'message': f"Poste {poste.nom} marqué comme disponible",
            'statut': poste.statut
        })

    @action(detail=True, methods=['post'])
    def marquer_maintenance(self, request, pk=None):
        """
        Marque le poste en maintenance

        POST /api/postes/{id}/marquer_maintenance/
        """
        poste = self.get_object()

        # Vérifier qu'il n'y a pas de session active
        if poste.session_active:
            return Response(
                {'error': f"Le poste a une session active: {poste.session_active.code_acces}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        poste.statut = 'maintenance'
        poste.save(update_fields=['statut'])

        return Response({
            'message': f"Poste {poste.nom} marqué en maintenance",
            'statut': poste.statut
        })

    @action(detail=True, methods=['post'])
    def marquer_hors_ligne(self, request, pk=None):
        """
        Marque le poste comme hors ligne

        POST /api/postes/{id}/marquer_hors_ligne/
        """
        poste = self.get_object()
        poste.marquer_hors_ligne()

        return Response({
            'message': f"Poste {poste.nom} marqué hors ligne",
            'statut': poste.statut
        })

    @action(detail=True, methods=['get'])
    def session_active(self, request, pk=None):
        """
        Retourne les détails de la session active du poste

        GET /api/postes/{id}/session_active/
        """
        poste = self.get_object()
        session = poste.session_active

        if not session:
            return Response(
                {'message': 'Aucune session active sur ce poste'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Import ici pour éviter les imports circulaires
        from apps.sessions.serializers import SessionActiveSerializer
        serializer = SessionActiveSerializer(session)

        return Response(serializer.data)

    # ============== Endpoints pour l'enregistrement mTLS ==============

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def generate_registration_token(self, request, pk=None):
        """
        Génère un token d'enregistrement pour un poste (admin uniquement).
        Le token est valide 24 heures et permet au client de s'enregistrer.

        POST /api/postes/{id}/generate_registration_token/

        Response:
        {
            "token": "xxx...",
            "expires_at": "2025-12-05T10:00:00Z",
            "message": "..."
        }
        """
        poste = self.get_object()

        # Vérifier si déjà enregistré
        if poste.is_registered:
            return Response(
                {'error': 'Ce poste a déjà un certificat valide. Révoquez-le d\'abord si vous voulez le ré-enregistrer.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Génère un token aléatoire sécurisé
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=24)

        poste.registration_token = token
        poste.registration_token_expires = expires_at
        poste.save(update_fields=['registration_token', 'registration_token_expires'])

        return Response({
            'token': token,
            'expires_at': expires_at.isoformat(),
            'poste_id': poste.id,
            'poste_nom': poste.nom,
            'message': f'Token généré pour {poste.nom}. Saisissez ce token sur le client pour l\'enregistrer. Valide 24h.'
        })

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register_client(self, request):
        """
        Enregistre un client et délivre un certificat TLS.
        Cet endpoint est appelé par le client Rust lors de sa première configuration.

        POST /api/postes/register_client/
        Body: {
            "token": "xxx...",
            "hostname": "PC-01",
            "mac_address": "00:11:22:33:44:55"
        }

        Response:
        {
            "client_cert": "-----BEGIN CERTIFICATE-----...",
            "client_key": "-----BEGIN PRIVATE KEY-----...",
            "ca_cert": "-----BEGIN CERTIFICATE-----...",
            "poste_id": 1,
            "poste_nom": "PC-01",
            "expires_at": "2026-12-04T10:00:00Z"
        }
        """
        token = request.data.get('token')
        hostname = request.data.get('hostname')
        mac_address = request.data.get('mac_address')

        if not token:
            return Response(
                {'error': 'Token requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Trouve le poste avec ce token valide
        try:
            poste = Poste.objects.get(
                registration_token=token,
                registration_token_expires__gt=timezone.now()
            )
        except Poste.DoesNotExist:
            return Response(
                {'error': 'Token invalide ou expiré'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Génère le certificat
        cert_manager = get_certificate_manager()
        try:
            cert_data = cert_manager.generate_client_certificate(poste)
        except Exception as e:
            return Response(
                {'error': f'Erreur lors de la génération du certificat: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Met à jour le poste
        poste.certificate_cn = cert_data['cn']
        poste.certificate_fingerprint = cert_data['fingerprint']
        poste.certificate_issued_at = timezone.now()
        poste.certificate_expires_at = cert_data['expires_at']
        poste.is_certificate_revoked = False
        poste.registration_token = None  # Invalide le token (usage unique)
        poste.registration_token_expires = None

        if mac_address:
            poste.mac_address = mac_address

        poste.save()

        # Log l'enregistrement
        from apps.logs.models import Log
        Log.log_action(
            action='client_registered',
            details=f"Client {poste.nom} enregistré avec certificat {cert_data['cn']}",
            operateur=request.user.username if request.user.is_authenticated else 'system',
            metadata={
                'poste_id': poste.id,
                'certificate_cn': cert_data['cn'],
                'fingerprint': cert_data['fingerprint'],
                'hostname': hostname,
                'mac_address': mac_address,
            }
        )

        return Response({
            'client_cert': cert_data['client_cert'],
            'client_key': cert_data['client_key'],
            'ca_cert': cert_data['ca_cert'],
            'poste_id': poste.id,
            'poste_nom': poste.nom,
            'certificate_cn': cert_data['cn'],
            'expires_at': cert_data['expires_at'].isoformat()
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def revoke_certificate(self, request, pk=None):
        """
        Révoque le certificat d'un poste.
        Le client ne pourra plus se connecter avec ce certificat.

        POST /api/postes/{id}/revoke_certificate/
        """
        poste = self.get_object()

        if not poste.certificate_cn:
            return Response(
                {'error': 'Ce poste n\'a pas de certificat'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if poste.is_certificate_revoked:
            return Response(
                {'error': 'Le certificat est déjà révoqué'},
                status=status.HTTP_400_BAD_REQUEST
            )

        poste.revoke_certificate()

        # Log la révocation
        from apps.logs.models import Log
        Log.log_action(
            action='certificate_revoked',
            details=f"Certificat du poste {poste.nom} révoqué",
            operateur=request.user.username if request.user.is_authenticated else 'admin',
            metadata={
                'poste_id': poste.id,
                'certificate_cn': poste.certificate_cn,
            }
        )

        return Response({
            'message': f'Certificat du poste {poste.nom} révoqué',
            'poste_id': poste.id
        })

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def certificate_status(self, request, pk=None):
        """
        Retourne le statut du certificat d'un poste.

        GET /api/postes/{id}/certificate_status/
        """
        poste = self.get_object()

        return Response({
            'poste_id': poste.id,
            'poste_nom': poste.nom,
            'is_registered': poste.is_registered,
            'has_pending_registration': poste.has_pending_registration,
            'certificate_cn': poste.certificate_cn,
            'certificate_fingerprint': poste.certificate_fingerprint,
            'certificate_issued_at': poste.certificate_issued_at.isoformat() if poste.certificate_issued_at else None,
            'certificate_expires_at': poste.certificate_expires_at.isoformat() if poste.certificate_expires_at else None,
            'is_certificate_revoked': poste.is_certificate_revoked,
            'registration_token_expires': poste.registration_token_expires.isoformat() if poste.registration_token_expires else None,
        })

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def ca_certificate(self, request):
        """
        Retourne le certificat CA public.
        Utile pour que les clients puissent vérifier le serveur.

        GET /api/postes/ca_certificate/
        """
        cert_manager = get_certificate_manager()
        try:
            ca_cert = cert_manager.get_ca_certificate()
            return Response({
                'ca_cert': ca_cert
            })
        except Exception as e:
            return Response(
                {'error': f'CA non disponible: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
