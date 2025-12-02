# 💻 Client Poste Public - Windows

Guide d'installation et d'utilisation pour Windows 10/11

---

## 📋 Prérequis

- **Windows** : 10 ou 11 (64-bit recommandé)
- **Python** : >= 3.8 ([Télécharger](https://www.python.org/downloads/))
- **Permissions** : Administrateur pour l'installation du service

---

## 🚀 Installation Rapide

### Méthode 1 : Installation Automatique (Recommandée)

1. **Télécharger les fichiers** :
   - Copier le dossier `client` sur le poste Windows

2. **Ouvrir PowerShell en Administrateur** :
   - Touche Windows + X
   - Sélectionner "Windows PowerShell (Admin)" ou "Terminal (Admin)"

3. **Aller dans le répertoire** :
   ```powershell
   cd C:\Chemin\vers\client\windows
   ```

4. **Lancer l'installation** :
   ```powershell
   .\install.bat
   ```

   Ou directement avec PowerShell :
   ```powershell
   .\install.ps1
   ```

5. **Suivre les instructions** :
   - Entrer l'URL du serveur (ex: `http://192.168.1.10:8001`)
   - Choisir si vous voulez démarrer le service maintenant

6. **C'est prêt !** 🎉

### Méthode 2 : Installation Manuelle

```powershell
# 1. Créer les répertoires
New-Item -ItemType Directory -Force -Path "C:\Program Files\PostePublic"
New-Item -ItemType Directory -Force -Path "C:\ProgramData\PostePublic\logs"

# 2. Copier les fichiers
Copy-Item *.py "C:\Program Files\PostePublic\"
Copy-Item requirements.txt "C:\Program Files\PostePublic\"

# 3. Installer les dépendances
cd "C:\Program Files\PostePublic"
python -m pip install -r requirements.txt
python -m pip install pywin32 win10toast

# 4. Installer le service
python poste_service.py install

# 5. Configurer et démarrer
Set-Service -Name PostePublicClient -StartupType Automatic
Start-Service -Name PostePublicClient
```

---

## ⚙️ Configuration

### Fichier de Configuration

Après installation, le fichier de configuration est dans :
```
C:\ProgramData\PostePublic\config.env
```

Contenu :
```ini
POSTE_SERVER_URL=http://192.168.1.10:8001
POSTE_WS_URL=ws://192.168.1.10:8001
LOG_LEVEL=INFO
DEBUG=False
```

### Modifier la Configuration

1. **Éditer le fichier** :
   ```powershell
   notepad C:\ProgramData\PostePublic\config.env
   ```

2. **Redémarrer le service** :
   ```powershell
   Restart-Service PostePublicClient
   ```

---

## 🎮 Utilisation

### Service Windows

**Démarrer le service** :
```powershell
net start PostePublicClient
# ou
Start-Service PostePublicClient
```

**Arrêter le service** :
```powershell
net stop PostePublicClient
# ou
Stop-Service PostePublicClient
```

**Vérifier le statut** :
```powershell
sc query PostePublicClient
# ou
Get-Service PostePublicClient
```

**Voir les logs** :
```powershell
Get-Content C:\ProgramData\PostePublic\logs\client.log -Tail 50
# ou en temps réel
Get-Content C:\ProgramData\PostePublic\logs\client.log -Wait
```

### Mode Manuel (sans service)

Pour tester ou utilisation ponctuelle :

```powershell
cd "C:\Program Files\PostePublic"
python poste_client.py --interactive
```

Avec un code direct :
```powershell
python poste_client.py --code ABC123 --server http://192.168.1.10:8001
```

Mode debug :
```powershell
python poste_client.py --interactive --debug
```

---

## 🔔 Notifications Windows

Le client supporte plusieurs méthodes de notification (essayées dans l'ordre) :

1. **Toast Notifications** (Windows 10/11) 🎉
   - Notifications modernes dans le coin
   - Nécessite `win10toast` (installé automatiquement)

2. **MessageBox** (Toutes versions)
   - Fenêtre popup modale
   - Utilise `ctypes.windll.user32.MessageBoxW`

3. **msg.exe** (Réseau)
   - Message envoyé à tous les utilisateurs
   - Utile pour les terminaux distants

4. **PowerShell Balloon** (Fallback)
   - Notification ballon dans la zone de notification

### Tester les Notifications

```powershell
cd "C:\Program Files\PostePublic"
python -c "from session_manager import SessionManager; sm = SessionManager(); sm.show_warning('Test', 'Ceci est un test')"
```

---

## 🔒 Verrouillage & Déconnexion

### Verrouillage d'Écran

Le client utilise l'API Windows `LockWorkStation()` via `ctypes` :

```python
import ctypes
ctypes.windll.user32.LockWorkStation()
```

**Tester le verrouillage** :
```powershell
python -c "from session_manager import SessionManager; sm = SessionManager(); sm.lock_screen()"
```

### Déconnexion Utilisateur

Utilise la commande `shutdown /l` :

```powershell
shutdown /l
```

**Configuration** :

Dans `config.py` :
```python
ENABLE_SCREEN_LOCK = True    # Activer le verrouillage
LOCK_ON_EXPIRE = True        # Verrouiller à l'expiration
LOGOUT_ON_EXPIRE = True      # Déconnecter à l'expiration
```

---

## 📊 Logs

### Emplacement

- **Fichier log** : `C:\ProgramData\PostePublic\logs\client.log`
- **Event Viewer** : Applications et services > PostePublicClient

### Consulter les Logs

**PowerShell** :
```powershell
# Dernières 50 lignes
Get-Content C:\ProgramData\PostePublic\logs\client.log -Tail 50

# Temps réel
Get-Content C:\ProgramData\PostePublic\logs\client.log -Wait

# Filtrer par niveau
Select-String -Path C:\ProgramData\PostePublic\logs\client.log -Pattern "ERROR"
```

**Event Viewer** :
1. Ouvrir Event Viewer (eventvwr.msc)
2. Windows Logs > Application
3. Filtrer par Source : "PostePublicClient"

### Niveaux de Log

- `DEBUG` : Détails complets (développement)
- `INFO` : Informations importantes (par défaut)
- `WARNING` : Avertissements
- `ERROR` : Erreurs

Modifier dans `config.env` :
```ini
LOG_LEVEL=DEBUG
```

---

## 🔧 Gestion du Service

### Commandes de Base

```powershell
# Installer le service
python "C:\Program Files\PostePublic\poste_service.py" install

# Démarrer
python "C:\Program Files\PostePublic\poste_service.py" start
# ou
net start PostePublicClient

# Arrêter
python "C:\Program Files\PostePublic\poste_service.py" stop
# ou
net stop PostePublicClient

# Redémarrer
python "C:\Program Files\PostePublic\poste_service.py" restart
# ou
Restart-Service PostePublicClient

# Désinstaller
python "C:\Program Files\PostePublic\poste_service.py" remove

# Débugger (mode console)
python "C:\Program Files\PostePublic\poste_service.py" debug
```

### Configuration du Service

**Démarrage automatique** :
```powershell
Set-Service -Name PostePublicClient -StartupType Automatic
```

**Démarrage manuel** :
```powershell
Set-Service -Name PostePublicClient -StartupType Manual
```

**Désactiver** :
```powershell
Set-Service -Name PostePublicClient -StartupType Disabled
```

---

## 🐛 Dépannage

### Le service ne démarre pas

**Vérifier l'état** :
```powershell
Get-Service PostePublicClient
Get-EventLog -LogName Application -Source PostePublicClient -Newest 10
```

**Solutions** :
1. Vérifier que Python est dans le PATH
2. Vérifier les dépendances :
   ```powershell
   python -c "import win32serviceutil; print('OK')"
   ```
3. Réinstaller les dépendances :
   ```powershell
   python -m pip install --force-reinstall pywin32
   python -m pywin32_postinstall.py -install
   ```

### Erreur "Module win32serviceutil not found"

**Solution** :
```powershell
python -m pip install --upgrade pywin32
python "C:\Python39\Scripts\pywin32_postinstall.py" -install
```

Adapter le chemin selon votre version de Python.

### Le serveur est inaccessible

**Tester la connexion** :
```powershell
# Test HTTP
Invoke-WebRequest -Uri "http://192.168.1.10:8001/api/" -UseBasicParsing

# Test ping
Test-Connection -ComputerName 192.168.1.10 -Count 2
```

**Vérifier le pare-feu** :
```powershell
# Autoriser le client à se connecter
New-NetFirewallRule -DisplayName "Client Poste Public" `
    -Direction Outbound -Action Allow `
    -RemoteAddress 192.168.1.10 -RemotePort 8001
```

### Notifications ne s'affichent pas

**Vérifier les notifications Windows** :
1. Paramètres Windows > Système > Notifications
2. Activer les notifications pour Python

**Tester manuellement** :
```powershell
# Toast (si installé)
python -c "from win10toast import ToastNotifier; ToastNotifier().show_toast('Test', 'Message', duration=5)"

# MessageBox
python -c "import ctypes; ctypes.windll.user32.MessageBoxW(0, 'Message', 'Titre', 0)"
```

### Permissions refusées

**Exécuter PowerShell en Administrateur** :
1. Touche Windows + X
2. "Windows PowerShell (Admin)"

**Vérifier les permissions sur les fichiers** :
```powershell
icacls "C:\Program Files\PostePublic"
icacls "C:\ProgramData\PostePublic"
```

---

## 🔐 Sécurité

### Bonnes Pratiques

1. **Service sous compte dédié** :
   - Créer un compte de service Windows
   - Configurer le service pour utiliser ce compte

2. **Pare-feu** :
   - Autoriser uniquement le serveur spécifique
   - Bloquer tout autre trafic sortant

3. **Chiffrement** :
   - Utiliser HTTPS/WSS en production :
     ```ini
     POSTE_SERVER_URL=https://poste-public.mairie.re
     POSTE_WS_URL=wss://poste-public.mairie.re
     ```

4. **Logs** :
   - Configurer la rotation des logs
   - Limiter la taille du fichier de log

### Windows Defender

Si Windows Defender bloque le client :

```powershell
# Ajouter une exclusion
Add-MpPreference -ExclusionPath "C:\Program Files\PostePublic"
```

---

## 🚀 Déploiement en Masse

### Avec Group Policy (Active Directory)

1. **Créer un package MSI** (à venir)

2. **Déployer via GPO** :
   - Computer Configuration > Policies > Software Settings
   - Software installation > New > Package

### Avec PowerShell DSC

```powershell
Configuration PostePublicClient {
    Node "poste-*" {
        Script InstallClient {
            GetScript = { @{ Result = (Test-Path "C:\Program Files\PostePublic") } }
            TestScript = { Test-Path "C:\Program Files\PostePublic\poste_client.py" }
            SetScript = {
                # Télécharger et installer
                Invoke-WebRequest -Uri "http://server/client-installer.zip" -OutFile "C:\Temp\client.zip"
                Expand-Archive "C:\Temp\client.zip" -DestinationPath "C:\Temp\client"
                & "C:\Temp\client\windows\install.ps1"
            }
        }
    }
}
```

### Script de Déploiement Réseau

```powershell
# deploy.ps1 - À exécuter depuis le serveur
$postes = @("POSTE-01", "POSTE-02", "POSTE-03")
$source = "\\serveur\partage\client"

foreach ($poste in $postes) {
    Write-Host "Déploiement sur $poste..."

    # Copier les fichiers
    Copy-Item -Path $source -Destination "\\$poste\C$\Temp\client" -Recurse -Force

    # Exécuter l'installation à distance
    Invoke-Command -ComputerName $poste -ScriptBlock {
        & "C:\Temp\client\windows\install.ps1" -ServerUrl "http://192.168.1.10:8001"
    }
}
```

---

## 📚 Références

- **Python Windows** : https://www.python.org/downloads/windows/
- **pywin32** : https://github.com/mhammond/pywin32
- **Windows Services** : https://docs.microsoft.com/en-us/windows/win32/services/services
- **PowerShell** : https://docs.microsoft.com/en-us/powershell/

---

## ✅ Checklist Installation

- [ ] Python >= 3.8 installé
- [ ] Fichiers copiés dans `C:\Program Files\PostePublic`
- [ ] Dépendances Python installées
- [ ] Service Windows installé
- [ ] Configuration serveur définie
- [ ] Service démarré et actif
- [ ] Test avec un code de session
- [ ] Notifications fonctionnent
- [ ] Verrouillage d'écran fonctionne

---

## 🆘 Support

**Logs** :
- `C:\ProgramData\PostePublic\logs\client.log`
- Event Viewer > Application > PostePublicClient

**Documentation** :
- `README.md` - Documentation générale
- `PHASE4_CLIENT_COMPLETE.md` - Architecture complète

**Contact** :
- Support technique mairie

---

**Développé pour la Mairie de La Réunion**
**Client Poste Public v1.0.0 - Windows Edition**
