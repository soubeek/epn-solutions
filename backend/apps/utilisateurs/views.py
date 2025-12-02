"""
ViewSets pour l'app Utilisateurs
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Utilisateur
from .serializers import (
    UtilisateurSerializer,
    UtilisateurListSerializer,
    UtilisateurStatsSerializer
)


class UtilisateurViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les utilisateurs

    Endpoints:
    - GET /api/utilisateurs/ - Liste des utilisateurs
    - POST /api/utilisateurs/ - Créer un utilisateur
    - GET /api/utilisateurs/{id}/ - Détail d'un utilisateur
    - PUT /api/utilisateurs/{id}/ - Modifier un utilisateur
    - PATCH /api/utilisateurs/{id}/ - Modifier partiellement
    - DELETE /api/utilisateurs/{id}/ - Supprimer un utilisateur
    - GET /api/utilisateurs/stats/ - Statistiques globales
    - GET /api/utilisateurs/{id}/sessions/ - Sessions de l'utilisateur
    """

    queryset = Utilisateur.objects.all()
    serializer_class = UtilisateurSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # Filtres
    filterset_fields = ['consentement_rgpd']
    search_fields = ['nom', 'prenom', 'email', 'telephone', 'carte_identite']
    ordering_fields = ['nom', 'prenom', 'created_at', 'derniere_session']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Retourne le serializer approprié selon l'action"""
        if self.action == 'list':
            return UtilisateurListSerializer
        elif self.action == 'stats':
            return UtilisateurStatsSerializer
        return UtilisateurSerializer

    def perform_create(self, serializer):
        """Ajoute l'opérateur lors de la création"""
        # Récupérer l'opérateur depuis request.user
        username = self.request.user.username if self.request.user.is_authenticated else 'anonymous'
        serializer.save(created_by=username)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Retourne les statistiques globales des utilisateurs

        GET /api/utilisateurs/stats/
        """
        total = Utilisateur.objects.count()
        avec_consentement = Utilisateur.objects.filter(consentement_rgpd=True).count()
        sans_consentement = total - avec_consentement

        # Utilisateurs actifs (ayant eu une session dans les 30 derniers jours)
        from django.utils import timezone
        from datetime import timedelta
        date_limite = timezone.now() - timedelta(days=30)
        actifs = Utilisateur.objects.filter(derniere_session__gte=date_limite).count()

        return Response({
            'total': total,
            'avec_consentement_rgpd': avec_consentement,
            'sans_consentement_rgpd': sans_consentement,
            'actifs_30_jours': actifs
        })

    @action(detail=True, methods=['get'])
    def sessions(self, request, pk=None):
        """
        Retourne les sessions d'un utilisateur

        GET /api/utilisateurs/{id}/sessions/
        """
        utilisateur = self.get_object()
        sessions = utilisateur.sessions.all()

        # Import ici pour éviter les imports circulaires
        from apps.sessions.serializers import SessionListSerializer
        serializer = SessionListSerializer(sessions, many=True)

        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def can_create_session(self, request, pk=None):
        """
        Vérifie si l'utilisateur peut créer une session aujourd'hui

        GET /api/utilisateurs/{id}/can_create_session/

        Returns:
            {
                "can_create": true/false,
                "sessions_today": 2,
                "max_sessions": 3,
                "remaining": 1
            }
        """
        from django.conf import settings

        utilisateur = self.get_object()
        can_create = utilisateur.can_create_session_today()
        sessions_today = utilisateur.sessions_today
        max_sessions = settings.POSTE_PUBLIC.get('MAX_SESSIONS_PER_USER_PER_DAY', 3)

        return Response({
            'can_create': can_create,
            'sessions_today': sessions_today,
            'max_sessions': max_sessions,
            'remaining': max(0, max_sessions - sessions_today)
        })

    @action(detail=True, methods=['post'])
    def revoke_consent(self, request, pk=None):
        """
        Révoquer le consentement RGPD d'un utilisateur

        POST /api/utilisateurs/{id}/revoke_consent/
        """
        utilisateur = self.get_object()

        # Vérifier s'il n'a pas de sessions actives
        if utilisateur.sessions.filter(statut='active').exists():
            return Response(
                {'error': "Impossible de révoquer le consentement avec des sessions actives"},
                status=status.HTTP_400_BAD_REQUEST
            )

        utilisateur.consentement_rgpd = False
        utilisateur.date_consentement = None
        utilisateur.save()

        return Response({
            'message': 'Consentement RGPD révoqué',
            'utilisateur_id': utilisateur.id
        })
