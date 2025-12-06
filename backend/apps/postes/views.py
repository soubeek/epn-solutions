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
from django.conf import settings
from .serializers import (
    PosteSerializer,
    PosteListSerializer,
    PosteStatsSerializer,
    PosteHeartbeatSerializer,
    DiscoveryRequestSerializer,
    DiscoveryStatusRequestSerializer,
    PendingPosteSerializer,
    ValidateDiscoverySerializer
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

    # ============== Endpoints pour la découverte automatique ==============

    def _get_client_ip(self, request):
        """Extrait l'adresse IP du client depuis la requête"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    def _validate_discovery_token(self, token):
        """Vérifie si le token de découverte est valide"""
        valid_tokens = []
        if settings.DISCOVERY_TOKEN:
            valid_tokens.append(settings.DISCOVERY_TOKEN)
        if settings.DISCOVERY_TOKEN_PREVIOUS:
            valid_tokens.append(settings.DISCOVERY_TOKEN_PREVIOUS)
        return token in valid_tokens

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def discover(self, request):
        """
        Endpoint de découverte client.
        Crée un poste en attente de validation si il n'existe pas.

        POST /api/postes/discover/
        Body: {
            "discovery_token": "xxx...",
            "hostname": "PC-01",
            "mac_address": "00:11:22:33:44:55",
            "ip_address": "192.168.1.100"  (optionnel)
        }

        Response:
        {
            "status": "pending_validation" | "validated" | "registered",
            "poste_id": 123,
            "message": "..."
        }
        """
        serializer = DiscoveryRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        discovery_token = data['discovery_token']
        hostname = data['hostname']
        mac_address = data['mac_address']
        ip_address = data.get('ip_address') or self._get_client_ip(request)

        # Vérifier le token de découverte
        if not self._validate_discovery_token(discovery_token):
            return Response(
                {'error': 'Token de découverte invalide'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Chercher un poste existant avec cette MAC
        try:
            poste = Poste.objects.get(mac_address=mac_address)

            # Poste déjà enregistré avec certificat
            if poste.is_registered:
                return Response({
                    'status': 'registered',
                    'poste_id': poste.id,
                    'poste_nom': poste.nom,
                    'message': 'Client déjà enregistré avec certificat valide'
                })

            # Poste en attente de validation
            if poste.is_pending_validation:
                return Response({
                    'status': 'pending_validation',
                    'poste_id': poste.id,
                    'poste_nom': poste.nom,
                    'message': 'En attente de validation par un administrateur'
                })

            # Poste validé mais pas encore enregistré
            return Response({
                'status': 'validated',
                'poste_id': poste.id,
                'poste_nom': poste.nom,
                'has_registration_token': poste.has_pending_registration,
                'message': 'Poste validé, en attente du token d\'enregistrement'
            })

        except Poste.DoesNotExist:
            # Créer un nouveau poste en attente de validation
            # Générer un nom automatique basé sur la MAC
            auto_nom = f"AUTO-{mac_address[-8:].replace(':', '')}"

            # Vérifier que le nom n'existe pas déjà
            counter = 1
            base_nom = auto_nom
            while Poste.objects.filter(nom=auto_nom).exists():
                auto_nom = f"{base_nom}-{counter}"
                counter += 1

            poste = Poste.objects.create(
                nom=auto_nom,
                mac_address=mac_address,
                ip_address=ip_address,
                statut='en_attente_validation',
                discovered_at=timezone.now(),
                discovered_hostname=hostname
            )

            # Log la découverte
            from apps.logs.models import Log
            Log.log_action(
                action='client_discovered',
                details=f"Nouveau client découvert: {auto_nom} ({mac_address})",
                operateur='system',
                metadata={
                    'poste_id': poste.id,
                    'mac_address': mac_address,
                    'ip_address': ip_address,
                    'hostname': hostname,
                }
            )

            return Response({
                'status': 'pending_validation',
                'poste_id': poste.id,
                'poste_nom': poste.nom,
                'message': 'Poste découvert, en attente de validation par un administrateur'
            }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def check_discovery_status(self, request):
        """
        Vérifie le statut d'un client découvert.
        Le client peut polluer cet endpoint pour savoir s'il a été validé.

        POST /api/postes/check_discovery_status/
        Body: {
            "mac_address": "00:11:22:33:44:55"
        }

        Response:
        {
            "status": "pending_validation" | "validated" | "registered" | "unknown",
            "poste_id": 123,
            "poste_nom": "PC-01",
            "has_registration_token": true/false,
            "registration_token": "xxx..."  (seulement si validé et token généré)
        }
        """
        serializer = DiscoveryStatusRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        mac_address = serializer.validated_data['mac_address']

        try:
            poste = Poste.objects.get(mac_address=mac_address)

            # Poste déjà enregistré
            if poste.is_registered:
                return Response({
                    'status': 'registered',
                    'poste_id': poste.id,
                    'poste_nom': poste.nom,
                    'message': 'Client enregistré'
                })

            # Poste en attente de validation
            if poste.is_pending_validation:
                return Response({
                    'status': 'pending_validation',
                    'poste_id': poste.id,
                    'poste_nom': poste.nom,
                    'message': 'En attente de validation'
                })

            # Poste validé - vérifier s'il a un token
            response_data = {
                'status': 'validated',
                'poste_id': poste.id,
                'poste_nom': poste.nom,
                'has_registration_token': poste.has_pending_registration,
            }

            # Si le poste a un token valide, le retourner
            if poste.has_pending_registration:
                response_data['registration_token'] = poste.registration_token
                response_data['message'] = 'Token d\'enregistrement disponible'
            else:
                response_data['message'] = 'Validé, en attente du token d\'enregistrement'

            return Response(response_data)

        except Poste.DoesNotExist:
            return Response({
                'status': 'unknown',
                'message': 'Aucun poste trouvé avec cette adresse MAC'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def pending_validation(self, request):
        """
        Liste les postes en attente de validation.

        GET /api/postes/pending_validation/
        """
        postes = Poste.objects.filter(statut='en_attente_validation').order_by('-discovered_at')
        serializer = PendingPosteSerializer(postes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def validate_discovery(self, request, pk=None):
        """
        Valide un poste découvert automatiquement.

        POST /api/postes/{id}/validate_discovery/
        Body: {
            "nom": "PC-Salle-01"  (optionnel: pour renommer)
        }

        Response:
        {
            "message": "Poste validé",
            "poste_id": 123,
            "poste_nom": "PC-Salle-01"
        }
        """
        poste = self.get_object()

        if not poste.is_pending_validation:
            return Response(
                {'error': f'Ce poste n\'est pas en attente de validation (statut: {poste.statut})'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ValidateDiscoverySerializer(
            data=request.data,
            context={'instance': poste}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Renommer si demandé
        new_nom = serializer.validated_data.get('nom')
        if new_nom:
            poste.nom = new_nom

        # Valider le poste
        username = request.user.username if request.user.is_authenticated else 'admin'
        poste.validate_discovery(username)

        # Log la validation
        from apps.logs.models import Log
        Log.log_action(
            action='client_validated',
            details=f"Poste {poste.nom} validé par {username}",
            operateur=username,
            metadata={
                'poste_id': poste.id,
                'mac_address': poste.mac_address,
                'discovered_hostname': poste.discovered_hostname,
            }
        )

        return Response({
            'message': f'Poste {poste.nom} validé avec succès',
            'poste_id': poste.id,
            'poste_nom': poste.nom
        })

    # ============== Endpoints pour les commandes à distance ==============

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def remote_command(self, request, pk=None):
        """
        Envoie une commande à distance à un poste.

        POST /api/postes/{id}/remote_command/
        Body: {
            "command": "lock" | "message" | "shutdown" | "restart",
            "payload": "..."  (optionnel, requis pour 'message')
        }

        Response:
        {
            "message": "Commande envoyée",
            "command": "lock",
            "poste_id": 123
        }
        """
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        poste = self.get_object()

        command = request.data.get('command')
        payload = request.data.get('payload')

        valid_commands = ['lock', 'message', 'shutdown', 'restart']
        if command not in valid_commands:
            return Response(
                {'error': f'Commande invalide. Commandes valides: {valid_commands}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if command == 'message' and not payload:
            return Response(
                {'error': 'Le champ "payload" est requis pour la commande "message"'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier que le poste est en ligne
        if not poste.est_en_ligne:
            return Response(
                {'error': f'Le poste {poste.nom} n\'est pas en ligne'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Envoyer la commande via WebSocket
        channel_layer = get_channel_layer()
        group_name = f'poste_{poste.id}'

        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'remote_command',
                'command': command,
                'payload': payload,
            }
        )

        # Log la commande
        from apps.logs.models import Log
        Log.log_action(
            action='remote_command',
            details=f"Commande '{command}' envoyée au poste {poste.nom}",
            operateur=request.user.username if request.user.is_authenticated else 'admin',
            metadata={
                'poste_id': poste.id,
                'command': command,
                'payload': payload,
            }
        )

        return Response({
            'message': f'Commande "{command}" envoyée au poste {poste.nom}',
            'command': command,
            'poste_id': poste.id
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def unlock_kiosk(self, request, pk=None):
        """
        Déverrouille le mode kiosque d'un poste à distance.

        POST /api/postes/{id}/unlock_kiosk/

        Response:
        {
            "message": "Mode kiosque déverrouillé",
            "poste_id": 123,
            "admin": "username"
        }
        """
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        poste = self.get_object()
        admin_username = request.user.username if request.user.is_authenticated else 'admin'

        # Vérifier que le poste est en ligne
        if not poste.est_en_ligne:
            return Response(
                {'error': f'Le poste {poste.nom} n\'est pas en ligne'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Envoyer la commande via WebSocket
        channel_layer = get_channel_layer()
        group_name = f'poste_{poste.id}'

        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'unlock_kiosk',
                'admin': admin_username,
                'message': f'Mode kiosque désactivé par {admin_username}'
            }
        )

        # Log l'action
        from apps.logs.models import Log
        Log.log_action(
            action='unlock_kiosk',
            details=f"Mode kiosque déverrouillé sur {poste.nom} par {admin_username}",
            operateur=admin_username,
            metadata={
                'poste_id': poste.id,
            }
        )

        return Response({
            'message': f'Mode kiosque déverrouillé sur {poste.nom}',
            'poste_id': poste.id,
            'admin': admin_username
        })
