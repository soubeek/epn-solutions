# Installation du Client Poste Public - Windows
# Nécessite : PowerShell en mode Administrateur
# Usage : .\install.ps1

#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"

# Couleurs
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

Write-Host "====================================================================" -ForegroundColor Green
Write-Host "  Installation du Client Poste Public - Windows" -ForegroundColor Green
Write-Host "====================================================================" -ForegroundColor Green
Write-Host ""

# Configuration
$INSTALL_DIR = "C:\Program Files\PostePublic"
$DATA_DIR = "C:\ProgramData\PostePublic"
$CERT_DIR = "C:\ProgramData\PostePublic\certs"
$SERVICE_NAME = "PostePublicClient"
$PYTHON_MIN_VERSION = "3.8"

Write-Host "[1/9] Vérification des permissions..." -ForegroundColor Yellow

if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "  x Ce script doit être exécuté en tant qu'Administrateur" -ForegroundColor Red
    Exit 1
}

Write-Host "  √ Permissions OK" -ForegroundColor Green

Write-Host ""
Write-Host "[2/9] Vérification de Python..." -ForegroundColor Yellow

# Vérifier Python
try {
    $pythonVersion = & python --version 2>&1
    Write-Host "  √ Python trouvé: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  x Python non trouvé. Veuillez installer Python >= $PYTHON_MIN_VERSION depuis python.org" -ForegroundColor Red
    Write-Host "  URL: https://www.python.org/downloads/" -ForegroundColor Yellow
    Exit 1
}

# Vérifier la version de Python
$pythonVersionNumber = (python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if ([version]$pythonVersionNumber -lt [version]$PYTHON_MIN_VERSION) {
    Write-Host "  x Python $pythonVersionNumber trouvé, mais >= $PYTHON_MIN_VERSION requis" -ForegroundColor Red
    Exit 1
}

Write-Host ""
Write-Host "[3/9] Création des répertoires..." -ForegroundColor Yellow

# Créer les répertoires
New-Item -ItemType Directory -Force -Path $INSTALL_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $DATA_DIR | Out-Null
New-Item -ItemType Directory -Force -Path "$DATA_DIR\logs" | Out-Null
New-Item -ItemType Directory -Force -Path $CERT_DIR | Out-Null

Write-Host "  √ Répertoires créés" -ForegroundColor Green
Write-Host "    - $INSTALL_DIR" -ForegroundColor Gray
Write-Host "    - $DATA_DIR" -ForegroundColor Gray
Write-Host "    - $CERT_DIR" -ForegroundColor Gray

Write-Host ""
Write-Host "[4/9] Copie des fichiers..." -ForegroundColor Yellow

# Copier les fichiers
$sourceDir = Split-Path -Parent $PSScriptRoot
Copy-Item "$sourceDir\poste_client.py" $INSTALL_DIR -Force
Copy-Item "$sourceDir\session_manager.py" $INSTALL_DIR -Force
Copy-Item "$sourceDir\config.py" $INSTALL_DIR -Force
Copy-Item "$sourceDir\requirements.txt" $INSTALL_DIR -Force
Copy-Item "$PSScriptRoot\poste_service.py" $INSTALL_DIR -Force

Write-Host "  √ Fichiers copiés" -ForegroundColor Green

Write-Host ""
Write-Host "[5/9] Installation du certificat SSL..." -ForegroundColor Yellow

# Chercher le certificat
$certPath = "$sourceDir\..\deployment\ssl\poste-public.crt"
if (-not (Test-Path $certPath)) {
    # Essayer un autre emplacement
    $certPath = "$PSScriptRoot\..\..\deployment\ssl\poste-public.crt"
}

if (Test-Path $certPath) {
    # Copier le certificat
    Copy-Item $certPath "$CERT_DIR\server.crt" -Force

    # Importer dans le store de certificats Windows
    try {
        $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($certPath)
        $store = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root", "LocalMachine")
        $store.Open("ReadWrite")
        $store.Add($cert)
        $store.Close()
        Write-Host "  √ Certificat SSL installé dans le store Windows" -ForegroundColor Green
    } catch {
        Write-Host "  ! Impossible d'importer le certificat dans le store Windows" -ForegroundColor Yellow
        Write-Host "    Le certificat sera utilisé directement par l'application" -ForegroundColor Gray
    }
} else {
    Write-Host "  ! Certificat SSL non trouvé" -ForegroundColor Yellow
    Write-Host "    Chemin recherché: $certPath" -ForegroundColor Gray
    Write-Host "    Vous devrez copier manuellement le certificat dans $CERT_DIR" -ForegroundColor Gray
}

Write-Host ""
Write-Host "[6/9] Installation des dépendances Python..." -ForegroundColor Yellow

# Installer les dépendances
try {
    & python -m pip install --upgrade pip
    & python -m pip install -r "$INSTALL_DIR\requirements.txt"
    & python -m pip install pywin32 win10toast
    Write-Host "  √ Dépendances Python installées" -ForegroundColor Green
} catch {
    Write-Host "  ! Erreur lors de l'installation des dépendances" -ForegroundColor Yellow
    Write-Host "  Détails: $_" -ForegroundColor Gray
}

Write-Host ""
Write-Host "[7/9] Configuration..." -ForegroundColor Yellow

# Demander l'IP du serveur
Write-Host ""
$serverIP = Read-Host "Adresse IP du serveur EPN (ex: 192.168.1.10)"
if ([string]::IsNullOrWhiteSpace($serverIP)) {
    $serverIP = "192.168.1.10"
}

# Utiliser HTTPS par défaut
$serverUrl = "https://$serverIP"
$wsUrl = "wss://$serverIP/ws/sessions/"

# Créer le fichier de configuration YAML
$configContent = @"
# Configuration Client Poste Public - Windows
# Généré automatiquement le $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

# Serveur EPN (HTTPS)
server_url: $serverUrl
ws_url: $wsUrl

# Paramètres de session
check_interval: 5
warning_time: 300
critical_time: 60

# Actions à l'expiration
enable_screen_lock: true
lock_on_expire: true
logout_on_expire: false

# Logging
debug: false
log_level: INFO
log_file: C:\ProgramData\PostePublic\logs\client.log

# SSL (certificat self-signed)
ssl_cert_path: $CERT_DIR\server.crt
ssl_verify: true
"@

$configContent | Out-File -FilePath "$DATA_DIR\config.yaml" -Encoding UTF8 -Force

# Créer aussi un fichier .env pour compatibilité
$envContent = @"
POSTE_SERVER_URL=$serverUrl
POSTE_WS_URL=$wsUrl
LOG_LEVEL=INFO
DEBUG=False
SSL_CERT_PATH=$CERT_DIR\server.crt
"@
$envContent | Out-File -FilePath "$DATA_DIR\config.env" -Encoding UTF8 -Force

Write-Host "  √ Configuration sauvegardée" -ForegroundColor Green
Write-Host "    - Serveur: $serverUrl" -ForegroundColor Gray
Write-Host "    - WebSocket: $wsUrl" -ForegroundColor Gray
Write-Host "    - Config: $DATA_DIR\config.yaml" -ForegroundColor Gray

Write-Host ""
Write-Host "[8/9] Installation du service Windows..." -ForegroundColor Yellow

# Installer le service avec pywin32
try {
    Push-Location $INSTALL_DIR
    & python poste_service.py install
    Pop-Location
    Write-Host "  √ Service Windows installé" -ForegroundColor Green
} catch {
    Write-Host "  ! Erreur lors de l'installation du service" -ForegroundColor Yellow
    Write-Host "  Détails: $_" -ForegroundColor Gray
}

Write-Host ""
Write-Host "[9/9] Configuration finale..." -ForegroundColor Yellow

# Configurer le service pour démarrage automatique
try {
    Set-Service -Name $SERVICE_NAME -StartupType Automatic
    Write-Host "  √ Service configuré pour démarrage automatique" -ForegroundColor Green
} catch {
    Write-Host "  ! Impossible de configurer le démarrage automatique" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "====================================================================" -ForegroundColor Green
Write-Host "  Installation terminée avec succès !" -ForegroundColor Green
Write-Host "====================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Commandes utiles:" -ForegroundColor White
Write-Host "  Démarrer    : net start $SERVICE_NAME" -ForegroundColor Yellow
Write-Host "  Arrêter     : net stop $SERVICE_NAME" -ForegroundColor Yellow
Write-Host "  Statut      : sc query $SERVICE_NAME" -ForegroundColor Yellow
Write-Host "  Logs        : Get-Content $DATA_DIR\logs\client.log -Tail 50" -ForegroundColor Yellow
Write-Host "  Désinstaller: python '$INSTALL_DIR\poste_service.py' remove" -ForegroundColor Yellow
Write-Host ""
Write-Host "Mode manuel:" -ForegroundColor White
Write-Host "  cd '$INSTALL_DIR'" -ForegroundColor Yellow
Write-Host "  python poste_client.py --interactive" -ForegroundColor Yellow
Write-Host ""

# Proposer de démarrer le service
$startNow = Read-Host "Démarrer le service maintenant ? (O/N)"
if ($startNow -eq "O" -or $startNow -eq "o") {
    Write-Host ""
    try {
        Start-Service -Name $SERVICE_NAME
        Write-Host "  √ Service démarré" -ForegroundColor Green
        Start-Sleep -Seconds 2
        $serviceStatus = Get-Service -Name $SERVICE_NAME
        Write-Host ""
        Write-Host "Statut du service:" -ForegroundColor White
        Write-Host "  Nom    : $($serviceStatus.Name)" -ForegroundColor Gray
        Write-Host "  Statut : $($serviceStatus.Status)" -ForegroundColor Gray
        Write-Host "  Démarrage: $($serviceStatus.StartType)" -ForegroundColor Gray
    } catch {
        Write-Host "  x Erreur lors du démarrage du service" -ForegroundColor Red
        Write-Host "  Détails: $_" -ForegroundColor Gray
        Write-Host ""
        Write-Host "  Pour démarrer manuellement:" -ForegroundColor Yellow
        Write-Host "    net start $SERVICE_NAME" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Installation complète !" -ForegroundColor Green
