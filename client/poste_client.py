#!/usr/bin/env python3
"""
Client Poste Public - Gestion des sessions sur les postes publics
Compatible Linux et Windows

Usage:
    python poste_client.py --code ABC123
    python poste_client.py --interactive
"""

import sys
import time
import json
import socket
import logging
import argparse
import threading
from datetime import datetime, timedelta

try:
    import websocket
    import requests
except ImportError:
    print("ERROR: Modules requis manquants. Installez: pip install websocket-client requests")
    sys.exit(1)

import config
from session_manager import SessionManager


class PosteClient:
    """
    Client principal pour la gestion des postes publics
    """

    def __init__(self):
        self.session_id = None
        self.code_acces = None
        self.ws = None
        self.session_manager = SessionManager()
        self.temps_restant = 0
        self.session_active = False
        self.running = False

        # Détection automatique du poste
        self.mac_address = self.get_mac_address()
        self.ip_address = self.get_ip_address()

        # Configuration logging
        logging.basicConfig(
            level=getattr(logging, config.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(config.LOG_FILE) if self._can_write_log() else logging.NullHandler()
            ]
        )
        self.logger = logging.getLogger('PosteClient')

    def _can_write_log(self):
        """Vérifie si on peut écrire dans le fichier de log"""
        try:
            with open(config.LOG_FILE, 'a'):
                pass
            return True
        except:
            return False

    def get_mac_address(self):
        """Récupère l'adresse MAC de la carte réseau principale"""
        import uuid
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
                       for elements in range(0, 2*6, 2)][::-1])
        return mac.upper()

    def get_ip_address(self):
        """Récupère l'adresse IP locale"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return '127.0.0.1'

    def validate_code(self, code):
        """
        Valide un code d'accès via WebSocket
        """
        self.logger.info(f"Validation du code: {code}")
        self.code_acces = code.upper().strip()

        # Connexion WebSocket
        ws_url = f"{config.SERVER_WS_URL}/ws/sessions/"
        self.logger.info(f"Connexion à: {ws_url}")

        try:
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_open=self.on_ws_open,
                on_message=self.on_ws_message,
                on_error=self.on_ws_error,
                on_close=self.on_ws_close
            )

            # Lancer WebSocket dans un thread séparé
            ws_thread = threading.Thread(target=self.ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()

            # Attendre la connexion
            time.sleep(2)

            return True

        except Exception as e:
            self.logger.error(f"Erreur connexion WebSocket: {e}")
            return False

    def on_ws_open(self, ws):
        """Callback: WebSocket ouvert"""
        self.logger.info("WebSocket connecté")

        # Envoyer la validation du code
        message = {
            'type': 'validate_code',
            'code': self.code_acces,
            'ip_address': self.ip_address
        }
        ws.send(json.dumps(message))

    def on_ws_message(self, ws, message):
        """Callback: Message WebSocket reçu"""
        try:
            data = json.dumps(message)
            self.logger.info(f"Message reçu: {data.get('type')}")

            if data['type'] == 'code_valid':
                self.handle_code_valid(data)
            elif data['type'] == 'code_invalid':
                self.handle_code_invalid(data)
            elif data['type'] == 'session_started':
                self.handle_session_started(data)
            elif data['type'] == 'time_update':
                self.handle_time_update(data)
            elif data['type'] == 'session_terminated':
                self.handle_session_terminated(data)
            elif data['type'] == 'warning':
                self.handle_warning(data)

        except json.JSONDecodeError:
            self.logger.error(f"Message JSON invalide: {message}")
        except Exception as e:
            self.logger.error(f"Erreur traitement message: {e}")

    def on_ws_error(self, ws, error):
        """Callback: Erreur WebSocket"""
        self.logger.error(f"Erreur WebSocket: {error}")

    def on_ws_close(self, ws, close_status_code, close_msg):
        """Callback: WebSocket fermé"""
        self.logger.info(f"WebSocket fermé: {close_status_code} - {close_msg}")
        self.session_active = False

    def handle_code_valid(self, data):
        """Code d'accès valide"""
        session = data['session']
        self.session_id = session['id']
        self.temps_restant = session['temps_restant']

        self.logger.info(f"✓ Code valide! Session ID: {self.session_id}")
        self.logger.info(f"  Utilisateur: {session['utilisateur']}")
        self.logger.info(f"  Poste: {session['poste']}")
        self.logger.info(f"  Durée: {session['duree_initiale'] // 60} minutes")

        print(f"\n{'='*60}")
        print(f"  CODE VALIDE !")
        print(f"{'='*60}")
        print(f"  Utilisateur : {session['utilisateur']}")
        print(f"  Poste       : {session['poste']}")
        print(f"  Durée       : {session['duree_initiale'] // 60} minutes")
        print(f"{'='*60}\n")

        # Démarrer la session
        self.start_session()

    def handle_code_invalid(self, data):
        """Code d'accès invalide"""
        self.logger.warning("✗ Code invalide")
        print(f"\n{'='*60}")
        print(f"  CODE INVALIDE !")
        print(f"{'='*60}")
        print(f"  {data.get('message', 'Code inconnu ou session déjà utilisée')}")
        print(f"{'='*60}\n")
        sys.exit(1)

    def start_session(self):
        """Démarre la session"""
        if not self.session_id:
            self.logger.error("Pas de session ID")
            return

        # Envoyer la demande de démarrage
        message = {
            'type': 'start_session',
            'session_id': self.session_id
        }
        self.ws.send(json.dumps(message))

    def handle_session_started(self, data):
        """Session démarrée"""
        session = data['session']
        self.session_active = True
        self.temps_restant = session['temps_restant']

        self.logger.info(f"✓ Session démarrée!")
        print(f"\n{'='*60}")
        print(f"  SESSION DÉMARRÉE !")
        print(f"{'='*60}")
        print(f"  Temps restant : {self.temps_restant // 60} min {self.temps_restant % 60} sec")
        print(f"{'='*60}\n")

        # Déverrouiller l'écran
        if config.ENABLE_SCREEN_LOCK:
            self.session_manager.unlock_screen()

        # Démarrer la boucle de surveillance
        self.running = True
        self.monitor_session()

    def handle_time_update(self, data):
        """Mise à jour du temps restant"""
        self.temps_restant = data['temps_restant']

        # Vérifier les seuils d'avertissement
        if self.temps_restant <= config.CRITICAL_TIME and self.temps_restant > 0:
            self.logger.warning(f"⚠ CRITIQUE: {self.temps_restant} secondes restantes!")
            self.session_manager.show_warning(
                "Temps critique !",
                f"Il vous reste {self.temps_restant} secondes"
            )
        elif self.temps_restant <= config.WARNING_TIME and self.temps_restant % 60 == 0:
            self.logger.info(f"⚠ ATTENTION: {self.temps_restant // 60} minutes restantes")
            self.session_manager.show_warning(
                "Attention",
                f"Il vous reste {self.temps_restant // 60} minutes"
            )

    def handle_session_terminated(self, data):
        """Session terminée"""
        self.logger.info(f"Session terminée: {data.get('raison')}")
        print(f"\n{'='*60}")
        print(f"  SESSION TERMINÉE")
        print(f"{'='*60}")
        print(f"  {data.get('message', 'Session expirée')}")
        print(f"{'='*60}\n")

        self.session_active = False
        self.running = False

        # Verrouiller l'écran
        if config.ENABLE_SCREEN_LOCK and config.LOCK_ON_EXPIRE:
            self.session_manager.lock_screen()

        # Déconnecter l'utilisateur
        if config.LOGOUT_ON_EXPIRE:
            self.session_manager.logout_user()

    def handle_warning(self, data):
        """Avertissement du serveur"""
        self.logger.warning(f"⚠ {data['message']}")
        self.session_manager.show_warning("Attention", data['message'])

    def monitor_session(self):
        """Surveille la session en cours"""
        self.logger.info("Surveillance de la session démarrée")

        while self.running and self.session_active:
            # Demander une mise à jour du temps
            if self.ws and self.ws.sock and self.ws.sock.connected:
                message = {
                    'type': 'get_time',
                    'session_id': self.session_id
                }
                try:
                    self.ws.send(json.dumps(message))
                except:
                    self.logger.error("Erreur envoi heartbeat")
                    break

            # Afficher le temps restant
            if self.temps_restant > 0:
                mins = self.temps_restant // 60
                secs = self.temps_restant % 60
                print(f"\rTemps restant: {mins:02d}:{secs:02d}", end='', flush=True)

            time.sleep(config.CHECK_INTERVAL)

        self.logger.info("Surveillance terminée")

    def interactive_mode(self):
        """Mode interactif pour saisir le code"""
        print(f"\n{'='*60}")
        print(f"  CLIENT POSTE PUBLIC")
        print(f"{'='*60}")
        print(f"  Poste : {self.ip_address} ({self.mac_address})")
        print(f"  Serveur : {config.SERVER_URL}")
        print(f"{'='*60}\n")

        while True:
            code = input("Entrez votre code d'accès (ou 'q' pour quitter): ").strip()

            if code.lower() == 'q':
                print("Au revoir!")
                sys.exit(0)

            if len(code) < 6:
                print("✗ Code trop court (minimum 6 caractères)\n")
                continue

            if self.validate_code(code):
                # Attendre que la session se termine
                while self.session_active:
                    time.sleep(1)
                break


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(description='Client Poste Public')
    parser.add_argument('--code', '-c', help='Code d\'accès direct')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Mode interactif')
    parser.add_argument('--server', '-s', help='URL du serveur')
    parser.add_argument('--debug', '-d', action='store_true',
                       help='Mode debug')

    args = parser.parse_args()

    # Configuration
    if args.server:
        config.SERVER_URL = args.server
        config.SERVER_WS_URL = args.server.replace('http', 'ws')

    if args.debug:
        config.DEBUG = True
        config.LOG_LEVEL = 'DEBUG'

    # Client
    client = PosteClient()

    try:
        if args.code:
            # Mode direct avec code
            if client.validate_code(args.code):
                while client.session_active:
                    time.sleep(1)
        else:
            # Mode interactif
            client.interactive_mode()

    except KeyboardInterrupt:
        print("\n\nInterruption utilisateur")
        sys.exit(0)
    except Exception as e:
        print(f"\nErreur fatale: {e}")
        logging.exception(e)
        sys.exit(1)


if __name__ == '__main__':
    main()
