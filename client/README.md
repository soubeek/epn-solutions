# 💻 Client Poste Public

Client Python pour la gestion des sessions sur les postes publics.
Compatible Linux et Windows.

---

## 📋 Fonctionnalités

- ✅ Validation de codes d'accès via WebSocket
- ✅ Gestion de session en temps réel
- ✅ Verrouillage/déverrouillage automatique de l'écran
- ✅ Déconnexion automatique à l'expiration
- ✅ Notifications visuelles (temps restant, avertissements)
- ✅ Support Linux (systemd service)
- ✅ Support Windows (service Windows) - À venir
- ✅ Reconnexion automatique en cas de perte de connexion

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Poste Public (Client)                    │
├──────────────────────────────────────────────────────────────┤
│  poste_client.py       - Client principal                    │
│  session_manager.py    - Gestion écran/session               │
│  config.py             - Configuration                        │
└────────────┬─────────────────────────────────────────────────┘
             │ WebSocket
             │ ws://server:8001/ws/sessions/
             ▼
┌──────────────────────────────────────────────────────────────┐
│                    Serveur Central (Django)                  │
├──────────────────────────────────────────────────────────────┤
│  WebSocket Consumer    - Validation, gestion sessions        │
│  PostgreSQL            - Base de données                     │
│  Redis                 - Channel layer                        │
└──────────────────────────────────────────────────────────────┘
```

---

## 📦 Installation

### Linux (Debian/Ubuntu)

```bash
# 1. Cloner ou copier les fichiers du client
cd /opt
sudo git clone <repo> poste-client
cd poste-client/client

# 2. Lancer le script d'installation
sudo ./install_linux.sh

# 3. Le script va :
#    - Installer Python 3 et pip3
#    - Créer l'utilisateur 'poste'
#    - Copier les fichiers dans /opt/poste-client
#    - Installer les dépendances Python
#    - Configurer le service systemd
#    - Demander l'URL du serveur
```

### Installation manuelle

```bash
# Installer les dépendances
pip3 install -r requirements.txt

# Configuration
export POSTE_SERVER_URL="http://192.168.1.10:8001"
export POSTE_WS_URL="ws://192.168.1.10:8001"

# Lancer le client
python3 poste_client.py --interactive
```

---

## 🚀 Usage

### Mode Interactif

Le mode par défaut pour les postes publics :

```bash
python3 poste_client.py --interactive
```

Affiche :
```
====================================================================
  CLIENT POSTE PUBLIC
====================================================================
  Poste : 192.168.1.101 (AA:BB:CC:DD:EE:01)
  Serveur : http://192.168.1.10:8001
====================================================================

Entrez votre code d'accès (ou 'q' pour quitter): _
```

### Mode Direct (avec code)

Pour tester ou scripts automatisés :

```bash
python3 poste_client.py --code ABC123
```

### Avec Service Systemd

```bash
# Démarrer le service
sudo systemctl start poste-client

# Arrêter le service
sudo systemctl stop poste-client

# Voir les logs en temps réel
sudo journalctl -u poste-client -f

# Activer au démarrage
sudo systemctl enable poste-client

# Statut
sudo systemctl status poste-client
```

---

## ⚙️ Configuration

### Variables d'Environnement

| Variable | Description | Défaut |
|----------|-------------|--------|
| `POSTE_SERVER_URL` | URL du serveur API | http://localhost:8001 |
| `POSTE_WS_URL` | URL WebSocket | ws://localhost:8001 |
| `LOG_LEVEL` | Niveau de log | INFO |
| `DEBUG` | Mode debug | False |

### Fichier config.py

```python
# Serveur
SERVER_URL = 'http://192.168.1.10:8001'
SERVER_WS_URL = 'ws://192.168.1.10:8001'

# Session
CHECK_INTERVAL = 5      # Vérifier toutes les 5 secondes
WARNING_TIME = 300      # Avertir à 5 minutes
CRITICAL_TIME = 60      # Critique à 1 minute

# Écran
ENABLE_SCREEN_LOCK = True
LOCK_ON_EXPIRE = True
LOGOUT_ON_EXPIRE = True

# Logs
LOG_FILE = '/var/log/poste-client.log'
LOG_LEVEL = 'INFO'
```

---

## 📡 Communication WebSocket

### Messages Client → Serveur

**Valider un code :**
```json
{
  "type": "validate_code",
  "code": "ABC123",
  "ip_address": "192.168.1.101"
}
```

**Démarrer une session :**
```json
{
  "type": "start_session",
  "session_id": 1
}
```

**Demander le temps restant :**
```json
{
  "type": "get_time",
  "session_id": 1
}
```

### Messages Serveur → Client

**Code valide :**
```json
{
  "type": "code_valid",
  "session": {
    "id": 1,
    "code_acces": "ABC123",
    "utilisateur": "Jean Dupont",
    "poste": "Poste-03",
    "duree_initiale": 7200,
    "temps_restant": 7200,
    "statut": "en_attente"
  }
}
```

**Code invalide :**
```json
{
  "type": "code_invalid",
  "message": "Code inconnu ou session déjà utilisée"
}
```

**Session démarrée :**
```json
{
  "type": "session_started",
  "session": {
    "id": 1,
    "statut": "active",
    "temps_restant": 7200,
    "debut_session": "2025-11-19T10:00:00Z"
  }
}
```

**Mise à jour temps :**
```json
{
  "type": "time_update",
  "temps_restant": 5340,
  "temps_restant_minutes": 89,
  "pourcentage_utilise": 26,
  "statut": "active"
}
```

**Session terminée :**
```json
{
  "type": "session_terminated",
  "raison": "temps_expire",
  "message": "Votre temps est écoulé"
}
```

**Avertissement :**
```json
{
  "type": "warning",
  "level": "critical",
  "message": "Il vous reste 1 minute",
  "temps_restant": 60
}
```

---

## 🔒 Gestion de Session

### Verrouillage d'Écran

Le client supporte automatiquement les principaux environnements Linux :

- **GNOME** / Unity : `gnome-screensaver-command -l`
- **KDE** Plasma : `qdbus org.freedesktop.ScreenSaver`
- **XFCE** : `xflock4`
- **Cinnamon** : `cinnamon-screensaver-command -l`
- **MATE** : `mate-screensaver-command -l`
- **systemd** : `loginctl lock-session`
- **Fallback** : `xdg-screensaver lock`, `slock`, `xtrlock`

### Déconnexion

À l'expiration, le client peut :
1. **Verrouiller l'écran** (si `LOCK_ON_EXPIRE=True`)
2. **Déconnecter l'utilisateur** (si `LOGOUT_ON_EXPIRE=True`)

Méthodes supportées :
- **systemd** : `loginctl terminate-user`
- **GNOME** : `gnome-session-quit --logout --no-prompt`
- **KDE** : `qdbus org.kde.ksmserver`
- **XFCE** : `xfce4-session-logout --logout`
- Et autres...

### Notifications

Affichage des avertissements avec :
- **notify-send** (le plus courant)
- **zenity**
- **kdialog**
- **xmessage** (fallback)

---

## 🐛 Dépannage

### Le client ne se connecte pas au serveur

**Problème** : `Erreur connexion WebSocket`

**Solutions** :
1. Vérifier que le serveur est accessible :
   ```bash
   curl http://192.168.1.10:8001/api/
   ```

2. Vérifier les variables d'environnement :
   ```bash
   echo $POSTE_SERVER_URL
   echo $POSTE_WS_URL
   ```

3. Tester avec mode debug :
   ```bash
   python3 poste_client.py --interactive --debug
   ```

### Code invalide alors qu'il est correct

**Problème** : Le code existe mais est rejeté

**Causes possibles** :
- Session déjà démarrée
- Poste incorrect (IP ne correspond pas)
- Session expirée

**Solution** :
- Vérifier dans l'admin Django : http://server:8001/admin/
- Vérifier les logs serveur : `sudo journalctl -u daphne -f`

### L'écran ne se verrouille pas

**Problème** : `Aucune commande de verrouillage n'a fonctionné`

**Solutions** :
1. Installer un screensaver :
   ```bash
   # GNOME
   sudo apt install gnome-screensaver

   # XFCE
   sudo apt install xfce4-screensaver

   # Fallback universel
   sudo apt install xtrlock
   ```

2. Désactiver le verrouillage :
   ```python
   # Dans config.py
   ENABLE_SCREEN_LOCK = False
   ```

### Permissions refusées

**Problème** : `Permission denied: /var/log/poste-client.log`

**Solution** :
```bash
sudo touch /var/log/poste-client.log
sudo chown poste:poste /var/log/poste-client.log
sudo chmod 644 /var/log/poste-client.log
```

---

## 📊 Logs

### Emplacement

- **Linux** : `/var/log/poste-client.log`
- **Console** : stdout (toujours actif)

### Niveaux de Log

- `DEBUG` : Tous les détails (développement)
- `INFO` : Informations importantes (par défaut)
- `WARNING` : Avertissements
- `ERROR` : Erreurs

### Consulter les logs

```bash
# Logs en direct
tail -f /var/log/poste-client.log

# Logs systemd
sudo journalctl -u poste-client -f

# Filtrer par niveau
sudo journalctl -u poste-client -p err
```

---

## 🧪 Tests

### Test manuel rapide

```bash
# Terminal 1 : Serveur (si pas déjà lancé)
cd backend
source venv/bin/activate
DJANGO_ENV=development daphne -b 0.0.0.0 -p 8001 config.asgi:application

# Terminal 2 : Client
cd client
python3 poste_client.py --interactive --debug

# Entrer un code de test (créer dans l'admin Django)
# Exemple : ABC123
```

### Test avec code fixe

```bash
# Créer une session dans l'admin Django avec code ABC123
# Puis :
python3 poste_client.py --code ABC123 --server http://localhost:8001
```

---

## 📚 Dépendances

- **Python** : >= 3.8
- **websocket-client** : 1.7.0
- **requests** : 2.31.0
- **python-dotenv** : 1.0.0

### Dépendances système (optionnelles)

Pour un meilleur support des fonctionnalités :

```bash
# Notifications
sudo apt install libnotify-bin  # notify-send

# Verrouillage d'écran
sudo apt install gnome-screensaver  # ou votre environnement
```

---

## 🔐 Sécurité

### Bonnes pratiques

1. **Utilisateur dédié** : Le service tourne sous l'utilisateur `poste` (non-root)
2. **Permissions restreintes** : Accès limité au système
3. **Pas de stockage de credentials** : Aucun mot de passe stocké
4. **Communication chiffrée** : Utiliser wss:// en production
5. **Logs sécurisés** : Pas de données sensibles dans les logs

### Production

Pour la production, utiliser HTTPS/WSS :

```bash
# config.py
SERVER_URL = 'https://poste-public.mairie.re'
SERVER_WS_URL = 'wss://poste-public.mairie.re'
```

---

## 🚀 Prochaines Améliorations

- [ ] Support Windows service
- [ ] Interface graphique Qt/GTK
- [ ] Mode kiosque (fullscreen navigateur)
- [ ] Statistiques d'utilisation locales
- [ ] Backup/sync offline
- [ ] Multi-écrans
- [ ] Accessibilité améliorée

---

## 📝 Licence

Ce projet est développé pour la Mairie de La Réunion.

---

## 💡 Support

**Problèmes** : Consulter les logs et la section Dépannage
**Documentation serveur** : Voir `../backend/README.md`
**Contact** : Support technique mairie

---

**Développé pour la Mairie de La Réunion**
**Client Poste Public v1.0.0**
