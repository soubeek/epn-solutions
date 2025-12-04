"""
WebSocket Consumer pour les clients (postes) avec authentification mTLS.

Ce consumer gère les connexions des clients Rust qui s'authentifient
via leur certificat TLS client.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class ClientConsumer(AsyncWebsocketConsumer):
    """
    Consumer WebSocket pour les clients (postes) authentifiés par certificat.

    L'authentification se fait via le certificat TLS client, pas via
    l'authentification Django standard.

    Messages du client → serveur :
    - heartbeat: Signal que le client est actif
    - validate_code: Valider un code d'accès session
    - start_session: Démarrer une session
    - get_time: Obtenir le temps restant
    - end_session: Terminer une session (par le client)

    Messages du serveur → client :
    - connection_established: Connexion acceptée
    - code_valid / code_invalid: Résultat validation code
    - session_started: Session démarrée
    - time_update: Mise à jour du temps
    - session_terminated: Session terminée
    - warning: Avertissement temps
    - error: Erreur
    """

    async def connect(self):
        """Connexion WebSocket avec vérification du certificat"""
        # Vérifier l'authentification par certificat
        cert_valid = self.scope.get("cert_valid")
        poste = self.scope.get("poste")

        # Mode développement : accepter sans certificat si DEBUG
        from django.conf import settings
        if settings.DEBUG and cert_valid is None:
            # En dev, on accepte les connexions sans certificat
            # mais on les marque comme non-authentifiées
            self.poste = None
            self.poste_cn = None
            self.authenticated = False
            await self.accept()
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': 'Connecté (mode développement - pas de certificat)',
                'authenticated': False
            }))
            return

        # En production : certificat requis
        if cert_valid is False:
            error = self.scope.get("cert_error", "Certificat invalide")
            await self.close(code=4403)
            return

        if cert_valid is None or poste is None:
            await self.close(code=4401)
            return

        # Certificat valide
        self.poste = poste
        self.poste_cn = self.scope.get("poste_cn")
        self.authenticated = True
        self.current_session = None

        # Groupe pour ce poste (pour recevoir les notifications)
        self.poste_group_name = f'poste_{poste.id}'
        await self.channel_layer.group_add(
            self.poste_group_name,
            self.channel_name
        )

        # Mettre à jour la dernière connexion
        await self._update_poste_connection()

        await self.accept()
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connecté avec certificat valide',
            'authenticated': True,
            'poste_id': poste.id,
            'poste_nom': poste.nom,
            'poste_cn': self.poste_cn
        }))

    async def disconnect(self, close_code):
        """Déconnexion"""
        if hasattr(self, 'poste_group_name'):
            await self.channel_layer.group_discard(
                self.poste_group_name,
                self.channel_name
            )

        if hasattr(self, 'session_group_name'):
            await self.channel_layer.group_discard(
                self.session_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """Réception d'un message du client"""
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

            elif message_type == 'end_session':
                await self.handle_end_session(data)

            else:
                await self.send_error(f"Type de message inconnu: {message_type}")

        except json.JSONDecodeError:
            await self.send_error("Format JSON invalide")
        except Exception as e:
            await self.send_error(f"Erreur: {str(e)}")

    async def handle_heartbeat(self, data):
        """Heartbeat du client"""
        if self.poste:
            await self._update_poste_connection()

        await self.send(text_data=json.dumps({
            'type': 'heartbeat_ack',
            'timestamp': timezone.now().isoformat()
        }))

    async def handle_validate_code(self, data):
        """Valide un code d'accès"""
        code = data.get('code')

        if not code:
            await self.send_error("Code d'accès requis")
            return

        # Valider le code
        session_data = await self._validate_session_code(code)

        if session_data:
            # Rejoindre le groupe de la session
            self.session_group_name = f'session_{session_data["id"]}'
            await self.channel_layer.group_add(
                self.session_group_name,
                self.channel_name
            )
            self.current_session_id = session_data["id"]

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
        """Démarre une session"""
        session_id = data.get('session_id') or getattr(self, 'current_session_id', None)

        if not session_id:
            await self.send_error("ID de session requis")
            return

        result = await self._start_session(session_id)

        if result['success']:
            await self.send(text_data=json.dumps({
                'type': 'session_started',
                'session': result['session']
            }))
        else:
            await self.send_error(result['error'])

    async def handle_get_time(self, data):
        """Retourne le temps restant"""
        session_id = data.get('session_id') or getattr(self, 'current_session_id', None)

        if not session_id:
            await self.send_error("ID de session requis")
            return

        time_data = await self._get_session_time(session_id)

        if time_data:
            await self.send(text_data=json.dumps({
                'type': 'time_update',
                **time_data
            }))
        else:
            await self.send_error("Session introuvable")

    async def handle_end_session(self, data):
        """Termine une session (demandé par le client)"""
        session_id = data.get('session_id') or getattr(self, 'current_session_id', None)
        raison = data.get('raison', 'client_request')

        if not session_id:
            await self.send_error("ID de session requis")
            return

        result = await self._end_session(session_id, raison)

        if result['success']:
            await self.send(text_data=json.dumps({
                'type': 'session_ended',
                'session_id': session_id,
                'raison': raison
            }))
        else:
            await self.send_error(result['error'])

    # Handlers pour les messages de groupe (notifications serveur)

    async def time_update(self, event):
        """Notification de mise à jour du temps"""
        await self.send(text_data=json.dumps({
            'type': 'time_update',
            'temps_restant': event['temps_restant'],
            'temps_restant_minutes': event.get('temps_restant_minutes'),
            'pourcentage_utilise': event.get('pourcentage_utilise'),
            'statut': event.get('statut')
        }))

    async def time_added(self, event):
        """Notification temps ajouté"""
        await self.send(text_data=json.dumps({
            'type': 'time_added',
            'secondes_ajoutees': event['secondes'],
            'temps_restant': event['temps_restant'],
            'operateur': event.get('operateur')
        }))

    async def session_terminated(self, event):
        """Notification session terminée"""
        await self.send(text_data=json.dumps({
            'type': 'session_terminated',
            'raison': event.get('raison', 'fermeture_normale'),
            'message': event.get('message', 'Session terminée')
        }))

    async def session_warning(self, event):
        """Avertissement"""
        await self.send(text_data=json.dumps({
            'type': 'warning',
            'level': event.get('level', 'info'),
            'message': event['message'],
            'temps_restant': event.get('temps_restant')
        }))

    # Méthodes utilitaires

    async def send_error(self, message):
        """Envoie un message d'erreur"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))

    @database_sync_to_async
    def _update_poste_connection(self):
        """Met à jour la dernière connexion du poste"""
        if self.poste:
            self.poste.mettre_a_jour_connexion()

    @database_sync_to_async
    def _validate_session_code(self, code):
        """Valide un code d'accès"""
        from apps.sessions.models import Session

        try:
            code = code.upper().strip()
            session = Session.objects.get(code_acces=code)

            if session.statut != 'en_attente':
                return None

            # Vérifier que la session est pour ce poste (si authentifié)
            if self.poste and session.poste_id != self.poste.id:
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
    def _start_session(self, session_id):
        """Démarre une session"""
        from apps.sessions.models import Session

        try:
            session = Session.objects.get(id=session_id)

            if session.statut != 'en_attente':
                return {
                    'success': False,
                    'error': f"Session ne peut pas être démarrée (statut: {session.get_statut_display()})"
                }

            # Vérifier que c'est le bon poste
            if self.poste and session.poste_id != self.poste.id:
                return {
                    'success': False,
                    'error': "Cette session n'est pas assignée à ce poste"
                }

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
    def _get_session_time(self, session_id):
        """Récupère le temps restant"""
        from apps.sessions.models import Session

        try:
            session = Session.objects.get(id=session_id)

            return {
                'session_id': session.id,
                'temps_restant': session.temps_restant,
                'temps_restant_minutes': session.temps_restant // 60,
                'temps_restant_secondes': session.temps_restant % 60,
                'pourcentage_utilise': session.pourcentage_utilise,
                'temps_ecoule': session.temps_ecoule,
                'est_expiree': session.est_expiree,
                'statut': session.statut
            }
        except Session.DoesNotExist:
            return None

    @database_sync_to_async
    def _end_session(self, session_id, raison):
        """Termine une session"""
        from apps.sessions.models import Session

        try:
            session = Session.objects.get(id=session_id)

            if session.statut not in ['active', 'suspendue']:
                return {
                    'success': False,
                    'error': f"Session ne peut pas être terminée (statut: {session.get_statut_display()})"
                }

            session.terminer(raison=raison)

            return {'success': True}
        except Session.DoesNotExist:
            return {
                'success': False,
                'error': 'Session introuvable'
            }
