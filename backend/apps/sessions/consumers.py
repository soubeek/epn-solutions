"""
WebSocket Consumers pour les sessions
Gère la communication temps réel avec les clients
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Session


class SessionConsumer(AsyncWebsocketConsumer):
    """
    Consumer WebSocket pour gérer les sessions en temps réel

    Messages du client → serveur :
    - heartbeat: Signal que le client est toujours actif
    - validate_code: Valider un code d'accès
    - start_session: Démarrer une session
    - get_time: Obtenir le temps restant

    Messages du serveur → client :
    - time_update: Mise à jour du temps restant
    - session_started: Session démarrée avec succès
    - session_terminated: Session terminée
    - time_added: Temps ajouté à la session
    - warning: Avertissement (temps bientôt écoulé)
    - error: Erreur
    """

    async def connect(self):
        """Connexion WebSocket établie"""
        # Vérifier l'authentification
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            # Rejeter la connexion si non authentifié
            await self.close(code=4401)
            return

        # Récupérer l'ID de session depuis l'URL
        self.session_id = self.scope['url_route']['kwargs'].get('session_id')
        self.user = user

        if self.session_id:
            # Nom du groupe pour cette session
            self.session_group_name = f'session_{self.session_id}'

            # Rejoindre le groupe de la session
            await self.channel_layer.group_add(
                self.session_group_name,
                self.channel_name
            )

        # Accepter la connexion
        await self.accept()

        # Envoyer un message de confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connecté au serveur WebSocket',
            'session_id': self.session_id,
            'user': user.username
        }))

    async def disconnect(self, close_code):
        """Déconnexion WebSocket"""
        if hasattr(self, 'session_group_name'):
            # Quitter le groupe de la session
            await self.channel_layer.group_discard(
                self.session_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """
        Réception d'un message du client
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'heartbeat':
                await self.handle_heartbeat(data)

            elif message_type == 'validate_code':
                await self.handle_validate_code(data)

            elif message_type == 'start_session':
                await self.handle_start_session(data)

            elif message_type == 'get_time':
                await self.handle_get_time(data)

            else:
                await self.send_error(f"Type de message inconnu: {message_type}")

        except json.JSONDecodeError:
            await self.send_error("Format JSON invalide")
        except Exception as e:
            await self.send_error(f"Erreur: {str(e)}")

    async def handle_heartbeat(self, data):
        """
        Gestion du heartbeat du client
        Le client envoie régulièrement un signal pour indiquer qu'il est actif
        """
        await self.send(text_data=json.dumps({
            'type': 'heartbeat_ack',
            'timestamp': timezone.now().isoformat()
        }))

    async def handle_validate_code(self, data):
        """
        Valide un code d'accès
        """
        code = data.get('code')
        ip_address = data.get('ip_address')

        if not code:
            await self.send_error("Code d'accès requis")
            return

        # Valider le code (appel synchrone à la BDD)
        session_data = await self.validate_session_code(code, ip_address)

        if session_data:
            await self.send(text_data=json.dumps({
                'type': 'code_valid',
                'session': session_data
            }))
        else:
            await self.send(text_data=json.dumps({
                'type': 'code_invalid',
                'message': 'Code invalide ou session déjà utilisée'
            }))

    async def handle_start_session(self, data):
        """
        Démarre une session
        """
        session_id = data.get('session_id') or self.session_id

        if not session_id:
            await self.send_error("ID de session requis")
            return

        # Démarrer la session
        result = await self.start_session(session_id)

        if result['success']:
            await self.send(text_data=json.dumps({
                'type': 'session_started',
                'session': result['session']
            }))
        else:
            await self.send_error(result['error'])

    async def handle_get_time(self, data):
        """
        Retourne le temps restant de la session
        """
        session_id = data.get('session_id') or self.session_id

        if not session_id:
            await self.send_error("ID de session requis")
            return

        # Récupérer le temps restant
        time_data = await self.get_session_time(session_id)

        if time_data:
            await self.send(text_data=json.dumps({
                'type': 'time_update',
                **time_data
            }))
        else:
            await self.send_error("Session introuvable")

    # Messages envoyés par le serveur (via channel layer)

    async def time_update(self, event):
        """
        Envoi d'une mise à jour du temps restant au client
        Appelé depuis l'extérieur (tâche Celery, viewset, etc.)
        """
        await self.send(text_data=json.dumps({
            'type': 'time_update',
            'temps_restant': event['temps_restant'],
            'temps_restant_minutes': event.get('temps_restant_minutes'),
            'pourcentage_utilise': event.get('pourcentage_utilise'),
            'statut': event.get('statut')
        }))

    async def time_added(self, event):
        """
        Notification que du temps a été ajouté à la session
        """
        await self.send(text_data=json.dumps({
            'type': 'time_added',
            'secondes_ajoutees': event['secondes'],
            'temps_restant': event['temps_restant'],
            'operateur': event.get('operateur')
        }))

    async def session_terminated(self, event):
        """
        Notification que la session a été terminée
        """
        await self.send(text_data=json.dumps({
            'type': 'session_terminated',
            'raison': event.get('raison', 'fermeture_normale'),
            'message': event.get('message', 'Session terminée')
        }))

    async def session_warning(self, event):
        """
        Avertissement (ex: temps bientôt écoulé)
        """
        await self.send(text_data=json.dumps({
            'type': 'warning',
            'level': event.get('level', 'info'),
            'message': event['message'],
            'temps_restant': event.get('temps_restant')
        }))

    # Méthodes utilitaires (accès BDD)

    @database_sync_to_async
    def validate_session_code(self, code, ip_address=None):
        """
        Valide un code d'accès et retourne les données de la session
        """
        try:
            code = code.upper().strip()
            session = Session.objects.get(code_acces=code)

            # Vérifier le statut
            if session.statut != 'en_attente':
                return None

            # Vérifier l'IP si fournie
            if ip_address and session.poste.ip_address != ip_address:
                return None

            return {
                'id': session.id,
                'code_acces': session.code_acces,
                'utilisateur': session.utilisateur.get_full_name(),
                'poste': session.poste.nom,
                'duree_initiale': session.duree_initiale,
                'temps_restant': session.temps_restant,
                'statut': session.statut
            }
        except Session.DoesNotExist:
            return None

    @database_sync_to_async
    def start_session(self, session_id):
        """
        Démarre une session
        """
        try:
            session = Session.objects.get(id=session_id)

            if session.statut != 'en_attente':
                return {
                    'success': False,
                    'error': f"La session ne peut pas être démarrée (statut: {session.get_statut_display()})"
                }

            if not session.poste.est_disponible:
                return {
                    'success': False,
                    'error': f"Le poste {session.poste.nom} n'est pas disponible"
                }

            # Démarrer la session
            session.demarrer()

            return {
                'success': True,
                'session': {
                    'id': session.id,
                    'code_acces': session.code_acces,
                    'statut': session.statut,
                    'temps_restant': session.temps_restant,
                    'debut_session': session.debut_session.isoformat()
                }
            }
        except Session.DoesNotExist:
            return {
                'success': False,
                'error': 'Session introuvable'
            }

    @database_sync_to_async
    def get_session_time(self, session_id):
        """
        Récupère le temps restant d'une session
        """
        try:
            session = Session.objects.get(id=session_id)

            return {
                'session_id': session.id,
                'temps_restant': session.temps_restant,
                'temps_restant_minutes': session.temps_restant // 60,
                'temps_restant_secondes': session.temps_restant % 60,
                'pourcentage_utilise': session.pourcentage_utilise,
                'est_expiree': session.est_expiree,
                'statut': session.statut
            }
        except Session.DoesNotExist:
            return None

    async def send_error(self, message):
        """
        Envoie un message d'erreur au client
        """
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))
