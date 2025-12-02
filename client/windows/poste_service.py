"""
Service Windows pour le Client Poste Public
Basé sur pywin32

Installation :
    python poste_service.py install
    python poste_service.py start

Désinstallation :
    python poste_service.py stop
    python poste_service.py remove
"""

import sys
import os
import time
import logging
import threading

# Ajouter le répertoire parent au path pour importer les modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
except ImportError:
    print("ERROR: pywin32 requis. Installez: pip install pywin32")
    sys.exit(1)

import config
from poste_client import PosteClient


class PostePublicService(win32serviceutil.ServiceFramework):
    """
    Service Windows pour le client Poste Public
    """
    _svc_name_ = "PostePublicClient"
    _svc_display_name_ = "Client Poste Public"
    _svc_description_ = "Gestion des sessions sur les postes publics pour la mairie"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.running = False
        self.client = None

        # Configuration logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(config.LOG_FILE),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('PosteService')

    def SvcStop(self):
        """Arrêt du service"""
        self.logger.info("Arrêt du service demandé")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self.running = False

    def SvcDoRun(self):
        """Exécution du service"""
        self.logger.info("Démarrage du service Poste Public Client")

        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )

        self.running = True
        self.main()

    def main(self):
        """Boucle principale du service"""
        self.logger.info("Service Poste Public Client démarré")
        self.logger.info(f"Serveur: {config.SERVER_URL}")

        try:
            # Créer le client
            self.client = PosteClient()

            # Mode service : attendre les connexions
            # En mode service, on pourrait :
            # 1. Écouter sur un port local pour recevoir des codes
            # 2. Scanner des QR codes
            # 3. Attendre des cartes NFC
            # Pour l'instant, on utilise le mode interactif dans un thread

            client_thread = threading.Thread(target=self.run_client)
            client_thread.daemon = True
            client_thread.start()

            # Attendre l'événement d'arrêt
            while self.running:
                # Vérifier toutes les secondes si on doit s'arrêter
                rc = win32event.WaitForSingleObject(self.stop_event, 1000)
                if rc == win32event.WAIT_OBJECT_0:
                    break

        except Exception as e:
            self.logger.error(f"Erreur dans le service: {e}")
            servicemanager.LogErrorMsg(f"Erreur: {e}")
        finally:
            self.logger.info("Service arrêté")
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STOPPED,
                (self._svc_name_, '')
            )

    def run_client(self):
        """Exécute le client dans un thread"""
        try:
            self.logger.info("Client thread démarré")

            # En mode service, on pourrait implémenter différentes stratégies:
            # - Écouter sur un port TCP local pour recevoir des codes
            # - Interface avec lecteur de badges
            # - Détection automatique d'utilisateurs

            # Pour l'instant, mode simple avec rechargement automatique
            while self.running:
                try:
                    # Attendre une connexion ou un code
                    # TODO: Implémenter l'interface appropriée
                    time.sleep(5)

                except Exception as e:
                    self.logger.error(f"Erreur client: {e}")
                    time.sleep(10)

        except Exception as e:
            self.logger.error(f"Erreur fatale dans client thread: {e}")


def main():
    """Point d'entrée pour l'installation/désinstallation du service"""
    if len(sys.argv) == 1:
        # Lancer le service via le gestionnaire de services Windows
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(PostePublicService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # Installation/désinstallation en ligne de commande
        win32serviceutil.HandleCommandLine(PostePublicService)


if __name__ == '__main__':
    main()
