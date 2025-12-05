"""
ViewSets pour l'app Sessions
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from .models import Session
from .serializers import (
    SessionSerializer,
    SessionListSerializer,
    SessionCreateSerializer,
    SessionValidateCodeSerializer,
    SessionAddTimeSerializer,
    SessionTerminateSerializer,
    SessionStatsSerializer,
    SessionActiveSerializer,
    GuestSessionCreateSerializer,
    ExtensionRequestSerializer,
    ExtensionRequestCreateSerializer,
    ExtensionRequestResponseSerializer
)
from .models import ExtensionRequest
from .websocket_utils import send_time_added, send_session_terminated, send_time_update


class SessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les sessions

    Endpoints:
    - GET /api/sessions/ - Liste des sessions
    - POST /api/sessions/ - Créer une session
    - GET /api/sessions/{id}/ - Détail d'une session
    - PUT /api/sessions/{id}/ - Modifier une session
    - DELETE /api/sessions/{id}/ - Supprimer une session
    - GET /api/sessions/actives/ - Sessions actives
    - POST /api/sessions/validate_code/ - Valider un code d'accès
    - POST /api/sessions/{id}/start/ - Démarrer une session
    - POST /api/sessions/{id}/add_time/ - Ajouter du temps
    - POST /api/sessions/{id}/terminate/ - Terminer une session
    - POST /api/sessions/{id}/suspend/ - Suspendre une session
    - POST /api/sessions/{id}/resume/ - Reprendre une session
    - POST /api/sessions/create_guest/ - Créer une session invité
    """

    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # Filtres
    filterset_fields = ['statut', 'utilisateur', 'poste']
    search_fields = ['code_acces', 'utilisateur__nom', 'utilisateur__prenom', 'poste__nom']
    ordering_fields = ['created_at', 'debut_session', 'temps_restant']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Retourne le serializer approprié selon l'action"""
        if self.action == 'list':
            return SessionListSerializer
        elif self.action == 'create':
            return SessionCreateSerializer
        elif self.action == 'create_guest':
            return GuestSessionCreateSerializer
        elif self.action == 'validate_code':
            return SessionValidateCodeSerializer
        elif self.action == 'add_time':
            return SessionAddTimeSerializer
        elif self.action == 'terminate':
            return SessionTerminateSerializer
        elif self.action == 'actives':
            return SessionActiveSerializer
        return SessionSerializer

    @action(detail=False, methods=['post'])
    def create_guest(self, request):
        """
        Crée une session pour un utilisateur invité anonyme

        POST /api/sessions/create_guest/
        Body: {
            "poste": 1,
            "duree_minutes": 60,
            "notes": "Notes optionnelles"
        }

        Returns:
            {
                "session": {...},
                "guest_identifier": "GUEST-ABC123",
                "code_acces": "XYZ789"
            }
        """
        serializer = GuestSessionCreateSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            session = serializer.save()

            return Response({
                'session': SessionSerializer(session).data,
                'guest_identifier': session.utilisateur.nom,
                'code_acces': session.code_acces,
                'message': 'Session invité créée avec succès'
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def actives(self, request):
        """
        Retourne la liste des sessions actives

        GET /api/sessions/actives/
        """
        sessions = Session.objects.filter(statut='active')
        serializer = SessionActiveSerializer(sessions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Retourne les statistiques globales des sessions

        GET /api/sessions/stats/
        """
        from django.db.models import Count, Avg, Sum

        total = Session.objects.count()
        stats_par_statut = Session.objects.values('statut').annotate(count=Count('id'))

        # Sessions aujourd'hui
        today = timezone.now().date()
        sessions_today = Session.objects.filter(created_at__date=today).count()

        # Durée moyenne
        avg_duration = Session.objects.filter(
            statut__in=['terminee', 'expiree']
        ).aggregate(Avg('duree_initiale'))['duree_initiale__avg'] or 0

        return Response({
            'total': total,
            'sessions_aujourdhui': sessions_today,
            'duree_moyenne_secondes': int(avg_duration),
            'duree_moyenne_minutes': int(avg_duration / 60),
            'par_statut': {item['statut']: item['count'] for item in stats_par_statut}
        })

    @method_decorator(ratelimit(key='ip', rate='10/m', method='POST', block=True))
    @action(detail=False, methods=['post'])
    def validate_code(self, request):
        """
        Valide un code d'accès et retourne les infos de la session

        POST /api/sessions/validate_code/
        Body: {
            "code_acces": "ABC123",
            "ip_address": "192.168.1.100"
        }

        Returns:
            {
                "valid": true,
                "session": {...},
                "message": "Code valide"
            }

        Rate Limited: 10 requests per minute per IP
        """
        serializer = SessionValidateCodeSerializer(data=request.data)

        if serializer.is_valid():
            code = serializer.validated_data['code_acces'].upper().strip()
            ip_address = serializer.validated_data['ip_address']

            try:
                session = Session.objects.get(code_acces=code)

                # Vérifier l'IP correspond au poste
                if session.poste.ip_address != ip_address:
                    return Response({
                        'valid': False,
                        'message': f"Ce code est associé au poste {session.poste.nom} ({session.poste.ip_address})"
                    }, status=status.HTTP_403_FORBIDDEN)

                # Retourner les infos de la session
                session_data = SessionSerializer(session).data

                return Response({
                    'valid': True,
                    'session': session_data,
                    'message': 'Code valide'
                })

            except Session.DoesNotExist:
                return Response({
                    'valid': False,
                    'message': 'Code invalide'
                }, status=status.HTTP_404_NOT_FOUND)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """
        Démarre une session

        POST /api/sessions/{id}/start/
        """
        session = self.get_object()

        # Vérifier que la session est en attente
        if session.statut != 'en_attente':
            return Response(
                {'error': f"La session ne peut pas être démarrée (statut: {session.get_statut_display()})"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier que le poste est disponible
        if not session.poste.est_disponible:
            return Response(
                {'error': f"Le poste {session.poste.nom} n'est pas disponible"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Démarrer la session
        session.demarrer()

        return Response({
            'message': 'Session démarrée',
            'session': SessionSerializer(session).data
        })

    @action(detail=True, methods=['post'])
    def add_time(self, request, pk=None):
        """
        Ajoute du temps à une session

        POST /api/sessions/{id}/add_time/
        Body: {
            "minutes": 15
        }
        """
        session = self.get_object()
        serializer = SessionAddTimeSerializer(data=request.data)

        if serializer.is_valid():
            minutes = serializer.validated_data['minutes']
            # Récupérer l'opérateur depuis request.user
            operateur = request.user.username if request.user.is_authenticated else 'anonymous'
            secondes = minutes * 60

            # Vérifier que la session est active, suspendue ou en attente
            if session.statut not in ['active', 'suspendue', 'en_attente']:
                return Response(
                    {'error': f"Impossible d'ajouter du temps (statut: {session.get_statut_display()})"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Ajouter le temps
            session.ajouter_temps(secondes, operateur)

            # Notifier via WebSocket
            send_time_added(session, secondes, operateur)

            return Response({
                'message': f"{minutes} minutes ajoutées",
                'temps_restant': session.temps_restant,
                'temps_restant_minutes': session.temps_restant // 60
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def terminate(self, request, pk=None):
        """
        Termine une session

        POST /api/sessions/{id}/terminate/
        Body: {
            "raison": "fermeture_normale"
        }
        """
        session = self.get_object()
        serializer = SessionTerminateSerializer(data=request.data)

        if serializer.is_valid():
            # Récupérer l'opérateur depuis request.user
            operateur = request.user.username if request.user.is_authenticated else 'anonymous'
            raison = serializer.validated_data['raison']

            # Vérifier que la session peut être terminée
            if session.statut in ['terminee', 'expiree']:
                return Response(
                    {'error': f"La session est déjà terminée (statut: {session.get_statut_display()})"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Terminer la session
            session.terminer(operateur=operateur, raison=raison)

            # Notifier via WebSocket
            send_session_terminated(session, raison=raison, message='Session terminée')

            return Response({
                'message': 'Session terminée',
                'session': SessionSerializer(session).data
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        """
        Suspend une session

        POST /api/sessions/{id}/suspend/
        """
        session = self.get_object()
        # Récupérer l'opérateur depuis request.user
        operateur = request.user.username if request.user.is_authenticated else 'anonymous'

        if session.statut != 'active':
            return Response(
                {'error': f"Seules les sessions actives peuvent être suspendues (statut: {session.get_statut_display()})"},
                status=status.HTTP_400_BAD_REQUEST
            )

        session.suspendre(operateur=operateur)

        return Response({
            'message': 'Session suspendue',
            'session': SessionSerializer(session).data
        })

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """
        Reprend une session suspendue

        POST /api/sessions/{id}/resume/
        """
        session = self.get_object()
        # Récupérer l'opérateur depuis request.user
        operateur = request.user.username if request.user.is_authenticated else 'anonymous'

        if session.statut != 'suspendue':
            return Response(
                {'error': f"Seules les sessions suspendues peuvent être reprises (statut: {session.get_statut_display()})"},
                status=status.HTTP_400_BAD_REQUEST
            )

        session.reprendre(operateur=operateur)

        return Response({
            'message': 'Session reprise',
            'session': SessionSerializer(session).data
        })

    @action(detail=True, methods=['get'])
    def time_remaining(self, request, pk=None):
        """
        Retourne le temps restant de la session (temps réel)

        GET /api/sessions/{id}/time_remaining/
        """
        session = self.get_object()

        return Response({
            'session_id': session.id,
            'code_acces': session.code_acces,
            'temps_restant': session.temps_restant,
            'temps_restant_minutes': session.temps_restant // 60,
            'temps_restant_secondes': session.temps_restant % 60,
            'pourcentage_utilise': session.pourcentage_utilise,
            'est_expiree': session.est_expiree,
            'statut': session.statut
        })

    # ==================== Endpoints pour les demandes de prolongation ====================

    @action(detail=True, methods=['post'])
    def request_extension(self, request, pk=None):
        """
        Demande une prolongation pour une session.
        Appelé par le client Rust.

        POST /api/sessions/{id}/request_extension/
        Body: {
            "minutes": 15
        }
        """
        session = self.get_object()

        # Vérifier que la session est active
        if session.statut not in ['active', 'suspendue']:
            return Response(
                {'error': f"Impossible de demander une prolongation (statut: {session.get_statut_display()})"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier s'il y a déjà une demande en attente
        pending = ExtensionRequest.objects.filter(session=session, statut='pending').exists()
        if pending:
            return Response(
                {'error': 'Une demande de prolongation est déjà en attente'},
                status=status.HTTP_400_BAD_REQUEST
            )

        minutes = request.data.get('minutes', 15)
        if minutes < 5 or minutes > 60:
            return Response(
                {'error': 'La durée demandée doit être entre 5 et 60 minutes'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Créer la demande
        extension_request = ExtensionRequest.objects.create(
            session=session,
            minutes_requested=minutes
        )

        # Log
        from apps.logs.models import Log
        Log.objects.create(
            session=session,
            action='extension_requested',
            operateur='client',
            details=f"Demande de prolongation de {minutes} min pour {session.code_acces}"
        )

        # Notifier les admins via WebSocket (optionnel)
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'admin_notifications',
            {
                'type': 'extension_request',
                'extension_id': extension_request.id,
                'session_code': session.code_acces,
                'utilisateur': session.utilisateur.get_full_name(),
                'poste': session.poste.nom,
                'minutes': minutes
            }
        )

        return Response({
            'message': 'Demande de prolongation envoyée',
            'extension_id': extension_request.id,
            'minutes_requested': minutes
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def pending_extensions(self, request):
        """
        Liste les demandes de prolongation en attente.

        GET /api/sessions/pending_extensions/
        """
        extensions = ExtensionRequest.objects.filter(statut='pending').select_related(
            'session', 'session__utilisateur', 'session__poste'
        ).order_by('-created_at')

        serializer = ExtensionRequestSerializer(extensions, many=True)
        return Response(serializer.data)


class ExtensionRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les demandes de prolongation

    Endpoints:
    - GET /api/extension-requests/ - Liste des demandes
    - GET /api/extension-requests/{id}/ - Détail d'une demande
    - POST /api/extension-requests/{id}/respond/ - Répondre à une demande
    """

    queryset = ExtensionRequest.objects.all()
    serializer_class = ExtensionRequestSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['statut', 'session']
    ordering_fields = ['created_at', 'responded_at']
    ordering = ['-created_at']

    @action(detail=True, methods=['post'])
    def respond(self, request, pk=None):
        """
        Répond à une demande de prolongation (approuver ou refuser).

        POST /api/extension-requests/{id}/respond/
        Body: {
            "approve": true,
            "message": "Prolongation accordée"
        }
        """
        extension_request = self.get_object()
        serializer = ExtensionRequestResponseSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        admin_username = request.user.username if request.user.is_authenticated else 'admin'
        approve = serializer.validated_data['approve']
        message = serializer.validated_data.get('message')

        try:
            if approve:
                extension_request.approve(admin_username, message)
                action_msg = 'approuvée'

                # Notifier le client via WebSocket
                from asgiref.sync import async_to_sync
                from channels.layers import get_channel_layer
                channel_layer = get_channel_layer()
                group_name = f'poste_{extension_request.session.poste.id}'

                async_to_sync(channel_layer.group_send)(
                    group_name,
                    {
                        'type': 'extension_response',
                        'approved': True,
                        'minutes': extension_request.minutes_requested,
                        'new_remaining': extension_request.session.temps_restant,
                        'message': message or f"Prolongation de {extension_request.minutes_requested} minutes accordée"
                    }
                )

                # Aussi envoyer une mise à jour du temps
                send_time_added(
                    extension_request.session,
                    extension_request.seconds_requested,
                    admin_username
                )
            else:
                extension_request.deny(admin_username, message)
                action_msg = 'refusée'

                # Notifier le client via WebSocket
                from asgiref.sync import async_to_sync
                from channels.layers import get_channel_layer
                channel_layer = get_channel_layer()
                group_name = f'poste_{extension_request.session.poste.id}'

                async_to_sync(channel_layer.group_send)(
                    group_name,
                    {
                        'type': 'extension_response',
                        'approved': False,
                        'minutes': 0,
                        'message': message or "Demande de prolongation refusée"
                    }
                )

            return Response({
                'message': f'Demande de prolongation {action_msg}',
                'extension': ExtensionRequestSerializer(extension_request).data
            })

        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
