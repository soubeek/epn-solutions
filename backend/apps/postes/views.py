"""
ViewSets pour l'app Postes
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import Poste
from .serializers import (
    PosteSerializer,
    PosteListSerializer,
    PosteStatsSerializer,
    PosteHeartbeatSerializer
)


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
