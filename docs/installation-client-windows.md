# Installation du Client EPN sur Windows

## Prerequis

- Windows 10/11 (64-bit)
- Connexion reseau au serveur EPN
- Droits administrateur
- Visual C++ Redistributable 2019+

## Installation rapide

```powershell
# En tant qu'Administrateur
cd rust-client\scripts
.\install-service.ps1 -ServerUrl "http://192.168.1.25:8001" -DiscoveryToken "votre-token"
```

## Installation manuelle

### 1. Compilation

```powershell
# Installer Rust si necessaire
winget install Rustlang.Rust.MSVC

# Compiler
cd rust-client
cargo build --release
```

### 2. Installation des binaires

```powershell
# Creer les dossiers
New-Item -ItemType Directory -Path "C:\Program Files\EPNClient" -Force
New-Item -ItemType Directory -Path "C:\ProgramData\EPNClient" -Force
New-Item -ItemType Directory -Path "C:\ProgramData\EPNClient\logs" -Force
New-Item -ItemType Directory -Path "C:\ProgramData\EPNClient\firefox-template" -Force

# Copier les binaires
Copy-Item "target\release\epn-gui.exe" "C:\Program Files\EPNClient\"
Copy-Item "target\release\epn-service.exe" "C:\Program Files\EPNClient\"
```

### 3. Configuration

Creer `C:\ProgramData\EPNClient\config.yaml` :

```yaml
# ============== Connexion au serveur ==============
server_url: http://192.168.1.25:8001
ws_url: ws://192.168.1.25:8001

# ============== Token de decouverte ==============
discovery_token: votre-token-ici

# ============== Comportement fin de session ==============
lock_on_expire: true
logout_on_expire: false
lock_delay_secs: 5

# ============== Nettoyage automatique ==============
enable_cleanup: true
cleanup_firefox: true
cleanup_libreoffice: true
cleanup_user_documents: true
cleanup_system_history: true

# ============== Surveillance d'inactivite ==============
inactivity_enabled: true
inactivity_warning_secs: 300
inactivity_timeout_secs: 600

# ============== Type de poste ==============
poste_type: bureautique
# poste_type: gaming

# ============== Mode kiosque ==============
kiosk_mode: true
# kiosk_admin_password: "votre-mot-de-passe"
```

### 4. Installation du service

```powershell
# Creer le service
sc.exe create EPNClient binPath= "C:\Program Files\EPNClient\epn-service.exe" start= auto DisplayName= "EPN Client Service"

# Configurer la description
sc.exe description EPNClient "Service de gestion des postes publics EPN"

# Configurer le redemarrage automatique
sc.exe failure EPNClient reset= 86400 actions= restart/5000/restart/10000/restart/30000

# Demarrer le service
Start-Service EPNClient
```

### 5. Configuration auto-login (optionnel)

Pour un poste kiosque, configurer l'auto-login Windows :

```powershell
# Via registre (remplacer USERNAME et PASSWORD)
$regPath = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
Set-ItemProperty -Path $regPath -Name "AutoAdminLogon" -Value "1"
Set-ItemProperty -Path $regPath -Name "DefaultUserName" -Value "epn"
Set-ItemProperty -Path $regPath -Name "DefaultPassword" -Value "votre-mot-de-passe"
```

> **Attention** : Le mot de passe est stocke en clair dans le registre.

## Enregistrement du poste

### Flux d'enregistrement

```
CLIENT                              SERVEUR
   |                                   |
   |  1. Connexion avec token          |
   | --------------------------------->|
   |     (MAC, hostname, IP)           |
   |                                   |
   |  2. Poste cree "En attente"       |
   | <---------------------------------|
   |                                   |
   |      +---------------------+      |
   |      |  ADMIN VALIDE LE    |      |
   |      |  POSTE DANS L'UI    |      |
   |      +---------------------+      |
   |                                   |
   |  3. Certificat mTLS envoye        |
   | <---------------------------------|
   |                                   |
   |  4. Client pret                   |
   | ==================================|
```

### Etapes

1. **Lancer le service** : Le service demarre automatiquement au boot
2. **Verifier cote serveur** : Aller sur `http://serveur:3001` -> Postes -> "En attente"
3. **Valider le poste** : Cliquer "Valider" sur le nouveau poste
4. **Client pret** : Le client recoit son certificat et passe en mode operationnel

## Configuration du template Firefox

Le nettoyage Firefox supprime entierement le profil et le restaure depuis un template.

### Creer le template Firefox

1. **Configurer Firefox** :
   - Lancer Firefox
   - Installer les extensions necessaires
   - Configurer la page d'accueil
   - Ajuster les parametres
   - Fermer Firefox

2. **Sauvegarder le template** :
```powershell
# En tant qu'Administrateur
.\scripts\save-firefox-template.ps1
```

Le template est sauvegarde dans `C:\ProgramData\EPNClient\firefox-template\`.

## Arborescence des fichiers

```
C:\Program Files\EPNClient\
+-- epn-gui.exe                # Application GUI
+-- epn-service.exe            # Service Windows

C:\ProgramData\EPNClient\
+-- config.yaml                # Configuration
+-- logs\
|   +-- service.log            # Logs du service
+-- firefox-template\          # Template Firefox
    +-- Profiles\
        +-- xxxxxxxx.default\

%LOCALAPPDATA%\epn-client\
+-- client.crt                 # Certificat client (mTLS)
+-- client.key                 # Cle privee
+-- ca.crt                     # Certificat CA serveur
```

## Depannage

### Voir les logs du service

```powershell
Get-Content "C:\ProgramData\EPNClient\logs\service.log" -Tail 50 -Wait
```

### Verifier le statut du service

```powershell
Get-Service EPNClient
```

### Tester la connexion au serveur

```powershell
Invoke-WebRequest -Uri "http://192.168.1.25:8001/api/health/"
```

### Reinitialiser l'enregistrement

```powershell
Remove-Item "$env:LOCALAPPDATA\epn-client" -Recurse -Force
Restart-Service EPNClient
```

### Lancer manuellement en mode debug

```powershell
$env:RUST_LOG = "debug"
& "C:\Program Files\EPNClient\epn-gui.exe"
```

### Problemes courants

| Probleme | Solution |
|----------|----------|
| Service ne demarre pas | Verifier les logs, droits admin |
| Pas de connexion serveur | Verifier firewall, URL serveur |
| Firefox pas nettoye | Verifier le template existe |
| Mode kiosque ne fonctionne pas | Verifier config.yaml |

## Configuration Gaming

Pour un poste gaming, modifier `C:\ProgramData\EPNClient\config.yaml` :

```yaml
poste_type: gaming
gaming_enabled: true
gaming_auto_start_launchers:
  - steam
gaming_close_on_end: true
gaming_close_games_on_end: true
gaming_steam_big_picture: false
```

## Mode Kiosque

### Fonctionnalites

- **Plein ecran force** : L'application s'affiche en plein ecran
- **Pas de decorations** : Pas de barre de titre
- **Toujours au premier plan** : L'application reste devant
- **Fermeture bloquee** : Alt+F4 desactive

### Deverrouillage

**Local (raccourci clavier)** : `Ctrl+Alt+Shift+K` + mot de passe

**A distance (interface admin)** : Postes -> Commandes -> Deverrouiller kiosque

## Desinstallation

```powershell
# Arreter et supprimer le service
Stop-Service EPNClient
sc.exe delete EPNClient

# Supprimer les fichiers
Remove-Item "C:\Program Files\EPNClient" -Recurse -Force

# Optionnel : supprimer les donnees
Remove-Item "C:\ProgramData\EPNClient" -Recurse -Force
Remove-Item "$env:LOCALAPPDATA\epn-client" -Recurse -Force
```

Ou utiliser le script :

```powershell
.\scripts\install-service.ps1 -Uninstall
```
