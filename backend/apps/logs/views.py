"""
ViewSets pour l'app Logs
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from .models import Log
from .serializers import (
    LogSerializer,
    LogListSerializer,
    LogStatsSerializer,
    LogFilterSerializer
)


class LogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour les logs (lecture seule)

    Endpoints:
    - GET /api/logs/ - Liste des logs
    - GET /api/logs/{id}/ - Détail d'un log
    - GET /api/logs/stats/ - Statistiques des logs
    - GET /api/logs/recent/ - Logs récents
    - POST /api/logs/search/ - Recherche avancée
    """

    queryset = Log.objects.all()
    serializer_class = LogSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # Filtres
    filterset_fields = ['action', 'operateur', 'session']
    search_fields = ['details', 'operateur', 'ip_address']
    ordering_fields = ['created_at', 'action']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Retourne le serializer approprié selon l'action"""
        if self.action == 'list':
            return LogListSerializer
        return LogSerializer

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Retourne les statistiques des logs

        GET /api/logs/stats/
        """
        # Statistiques par action
        stats_par_action = Log.objects.values('action').annotate(
            count=Count('id')
        ).order_by('-count')

        # Ajouter le display name
        action_stats = []
        for item in stats_par_action:
            action_code = item['action']
            action_display = dict(Log.ACTION_CHOICES).get(action_code, action_code)

            # Dernière occurrence
            last_log = Log.objects.filter(action=action_code).first()

            action_stats.append({
                'action': action_code,
                'action_display': action_display,
                'count': item['count'],
                'last_occurrence': last_log.created_at if last_log else None
            })

        # Total
        total = Log.objects.count()

        # Logs aujourd'hui
        today = timezone.now().date()
        logs_today = Log.objects.filter(created_at__date=today).count()

        # Logs cette semaine
        week_ago = timezone.now() - timedelta(days=7)
        logs_week = Log.objects.filter(created_at__gte=week_ago).count()

        return Response({
            'total': total,
            'logs_aujourdhui': logs_today,
            'logs_cette_semaine': logs_week,
            'par_action': action_stats
        })

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """
        Retourne les logs récents (dernières 24h)

        GET /api/logs/recent/
        Params:
            - hours: nombre d'heures (défaut: 24)
            - limit: nombre max de résultats (défaut: 100)
        """
        hours = int(request.query_params.get('hours', 24))
        limit = int(request.query_params.get('limit', 100))

        cutoff = timezone.now() - timedelta(hours=hours)
        logs = Log.objects.filter(created_at__gte=cutoff)[:limit]

        serializer = LogListSerializer(logs, many=True)
        return Response({
            'count': logs.count(),
            'hours': hours,
            'logs': serializer.data
        })

    @action(detail=False, methods=['post'])
    def search(self, request):
        """
        Recherche avancée de logs avec filtres multiples

        POST /api/logs/search/
        Body: {
            "action": "demarrage_session",
            "operateur": "admin",
            "session_id": 123,
            "date_debut": "2025-01-01T00:00:00Z",
            "date_fin": "2025-01-31T23:59:59Z",
            "ip_address": "192.168.1.100"
        }
        """
        serializer = LogFilterSerializer(data=request.data)

        if serializer.is_valid():
            filters = {}

            # Appliquer les filtres
            if 'action' in serializer.validated_data:
                filters['action'] = serializer.validated_data['action']

            if 'operateur' in serializer.validated_data:
                filters['operateur__icontains'] = serializer.validated_data['operateur']

            if 'session_id' in serializer.validated_data:
                filters['session_id'] = serializer.validated_data['session_id']

            if 'ip_address' in serializer.validated_data:
                filters['ip_address'] = serializer.validated_data['ip_address']

            # Filtres de date
            queryset = Log.objects.filter(**filters)

            if 'date_debut' in serializer.validated_data:
                queryset = queryset.filter(created_at__gte=serializer.validated_data['date_debut'])

            if 'date_fin' in serializer.validated_data:
                queryset = queryset.filter(created_at__lte=serializer.validated_data['date_fin'])

            # Limiter les résultats
            limit = int(request.query_params.get('limit', 1000))
            queryset = queryset[:limit]

            result_serializer = LogListSerializer(queryset, many=True)

            return Response({
                'count': queryset.count(),
                'filters_applied': serializer.validated_data,
                'logs': result_serializer.data
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def by_session(self, request):
        """
        Retourne tous les logs d'une session

        GET /api/logs/by_session/?session_id=123
        """
        session_id = request.query_params.get('session_id')

        if not session_id:
            return Response(
                {'error': 'Le paramètre session_id est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        logs = Log.objects.filter(session_id=session_id)
        serializer = LogListSerializer(logs, many=True)

        return Response({
            'session_id': session_id,
            'count': logs.count(),
            'logs': serializer.data
        })

    @action(detail=False, methods=['get'])
    def errors(self, request):
        """
        Retourne les logs d'erreurs

        GET /api/logs/errors/
        Params:
            - hours: nombre d'heures (défaut: 24)
        """
        hours = int(request.query_params.get('hours', 24))
        cutoff = timezone.now() - timedelta(hours=hours)

        logs = Log.objects.filter(
            action__in=['erreur', 'warning'],
            created_at__gte=cutoff
        )

        serializer = LogListSerializer(logs, many=True)

        return Response({
            'count': logs.count(),
            'hours': hours,
            'logs': serializer.data
        })
