"""
WebSocket Consumers pour les mises à jour temps réel
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class DashboardConsumer(AsyncWebsocketConsumer):
    """
    Consumer pour le dashboard - envoie les statistiques en temps réel
    """

    async def connect(self):
        """Connexion au WebSocket"""
        from django.conf import settings

        user = self.scope.get('user')

        # En mode DEBUG, permettre les connexions non authentifiées
        if not settings.DEBUG:
            if not user or not user.is_authenticated:
                await self.close(code=4401)
                return

        self.room_group_name = 'dashboard'
        self.user = user if user and user.is_authenticated else None

        # Rejoindre le groupe dashboard
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Envoyer les stats initiales
        stats = await self.get_dashboard_stats()
        await self.send(text_data=json.dumps({
            'type': 'stats_update',
            'data': stats
        }))

    async def disconnect(self, close_code):
        """Déconnexion du WebSocket"""
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """Réception de message du client"""
        data = json.loads(text_data)

        if data.get('type') == 'get_stats':
            stats = await self.get_dashboard_stats()
            await self.send(text_data=json.dumps({
                'type': 'stats_update',
                'data': stats
            }))

    async def stats_update(self, event):
        """Envoi de mise à jour des stats au client"""
        await self.send(text_data=json.dumps({
            'type': 'stats_update',
            'data': event['data']
        }))

    @database_sync_to_async
    def get_dashboard_stats(self):
        """Récupère les statistiques du dashboard"""
        from apps.utilisateurs.models import Utilisateur
        from apps.sessions.models import Session
        from apps.postes.models import Poste

        return {
            'utilisateurs': {
                'total': Utilisateur.objects.count(),
                'actifs': Utilisateur.objects.count(),  # Tous les utilisateurs sont considérés actifs
                'nouveaux_mois': Utilisateur.objects.filter(
                    created_at__month=timezone.now().month
                ).count()
            },
            'sessions': {
                'total': Session.objects.count(),
                'actives': Session.objects.filter(statut='active').count(),
                'en_attente': Session.objects.filter(statut='en_attente').count(),
                'terminees_aujourd_hui': Session.objects.filter(
                    fin_session__date=timezone.now().date()
                ).count()
            },
            'postes': {
                'total': Poste.objects.count(),
                'disponibles': Poste.objects.filter(statut='disponible').count(),
                'occupes': Poste.objects.filter(statut='occupe').count(),
                'hors_ligne': Poste.objects.filter(statut='hors_ligne').count()
            },
            'timestamp': timezone.now().isoformat()
        }


class SessionConsumer(AsyncWebsocketConsumer):
    """
    Consumer pour les sessions - mises à jour temps réel des sessions
    """

    async def connect(self):
        """Connexion au WebSocket"""
        # Vérifier l'authentification
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            # Rejeter la connexion si non authentifié
            await self.close(code=4401)
            return

        self.room_group_name = 'sessions'
        self.user = user

        # Rejoindre le groupe sessions
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Envoyer les sessions initiales
        sessions = await self.get_active_sessions()
        await self.send(text_data=json.dumps({
            'type': 'sessions_update',
            'data': sessions
        }))

    async def disconnect(self, close_code):
        """Déconnexion du WebSocket"""
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """Réception de message du client"""
        data = json.loads(text_data)

        if data.get('type') == 'get_sessions':
            sessions = await self.get_active_sessions()
            await self.send(text_data=json.dumps({
                'type': 'sessions_update',
                'data': sessions
            }))

    async def session_update(self, event):
        """Envoi de mise à jour de session au client"""
        await self.send(text_data=json.dumps({
            'type': 'session_update',
            'data': event['data']
        }))

    async def session_created(self, event):
        """Envoi notification de création de session"""
        await self.send(text_data=json.dumps({
            'type': 'session_created',
            'data': event['data']
        }))

    async def session_ended(self, event):
        """Envoi notification de fin de session"""
        await self.send(text_data=json.dumps({
            'type': 'session_ended',
            'data': event['data']
        }))

    @database_sync_to_async
    def get_active_sessions(self):
        """Récupère les sessions actives"""
        from apps.sessions.models import Session

        sessions = Session.objects.filter(
            statut__in=['active', 'en_attente']
        ).select_related('utilisateur', 'poste')

        return [{
            'id': s.id,
            'code_acces': s.code_acces,
            'utilisateur': s.utilisateur.get_full_name(),
            'poste': s.poste.nom if s.poste else None,
            'temps_restant': s.temps_restant,
            'statut': s.statut,
            'debut_session': s.debut_session.isoformat() if s.debut_session else None
        } for s in sessions]
