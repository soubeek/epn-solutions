"""
Configuration du client Poste Public
"""

import os
import platform

# Configuration serveur
SERVER_URL = os.getenv('POSTE_SERVER_URL', 'http://localhost:8001')
SERVER_WS_URL = os.getenv('POSTE_WS_URL', 'ws://localhost:8001')

# Configuration poste
POSTE_MAC = None  # Sera détecté automatiquement
POSTE_IP = None   # Sera détecté automatiquement

# Configuration session
CHECK_INTERVAL = 5  # Vérifier le temps restant toutes les 5 secondes
WARNING_TIME = 300  # Avertissement à 5 minutes
CRITICAL_TIME = 60  # Critique à 1 minute

# Configuration écran
ENABLE_SCREEN_LOCK = True
LOCK_ON_EXPIRE = True
LOGOUT_ON_EXPIRE = True

# Système
OS_TYPE = platform.system()  # 'Linux', 'Windows', 'Darwin'
IS_LINUX = OS_TYPE == 'Linux'
IS_WINDOWS = OS_TYPE == 'Windows'

# Logs
LOG_FILE = '/var/log/poste-client.log' if IS_LINUX else 'C:\\ProgramData\\PostePublic\\client.log'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Mode debug
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
