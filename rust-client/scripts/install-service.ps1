# Script d'installation du service EPN Client sur Windows
# A executer en tant qu'Administrateur

param(
    [string]$ServerUrl = "http://192.168.1.25:8001",
    [string]$DiscoveryToken = "",
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"

# Chemins d'installation
$InstallDir = "C:\Program Files\EPNClient"
$DataDir = "C:\ProgramData\EPNClient"
$ServiceName = "EPNClient"
$ServiceDisplayName = "EPN Client Service"
$ServiceDescription = "Service de gestion des postes publics EPN"

# Couleurs pour les messages
function Write-Success { param($msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Info { param($msg) Write-Host "  [..] $msg" -ForegroundColor Cyan }
function Write-Warn { param($msg) Write-Host "  [!] $msg" -ForegroundColor Yellow }
function Write-Err { param($msg) Write-Host "  [X] $msg" -ForegroundColor Red }

# Verifier les droits administrateur
function Test-Administrator {
    $currentUser = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentUser.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Administrator)) {
    Write-Err "Ce script doit etre execute en tant qu'Administrateur"
    Write-Host "Cliquez droit sur PowerShell et selectionnez 'Executer en tant qu'administrateur'"
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Installation EPN Client pour Windows" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Desinstallation
if ($Uninstall) {
    Write-Host "=== Desinstallation ===" -ForegroundColor Yellow

    # Arreter et supprimer le service
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($service) {
        Write-Info "Arret du service..."
        Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
        Write-Info "Suppression du service..."
        sc.exe delete $ServiceName | Out-Null
        Write-Success "Service supprime"
    }

    # Supprimer les fichiers
    if (Test-Path $InstallDir) {
        Write-Info "Suppression de $InstallDir..."
        Remove-Item -Path $InstallDir -Recurse -Force
        Write-Success "Dossier programme supprime"
    }

    # Garder les donnees (config, templates) sauf si demande
    Write-Warn "Les donnees dans $DataDir ont ete conservees"
    Write-Host ""
    Write-Success "Desinstallation terminee"
    exit 0
}

# Installation
Write-Host "=== Creation des dossiers ===" -ForegroundColor Yellow

# Creer les dossiers
$folders = @(
    $InstallDir,
    $DataDir,
    "$DataDir\logs",
    "$DataDir\firefox-template"
)

foreach ($folder in $folders) {
    if (-not (Test-Path $folder)) {
        New-Item -ItemType Directory -Path $folder -Force | Out-Null
        Write-Success "Cree: $folder"
    } else {
        Write-Info "Existe: $folder"
    }
}

Write-Host ""
Write-Host "=== Copie des binaires ===" -ForegroundColor Yellow

# Chercher les binaires dans le dossier courant ou target/release
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir

$guiBinary = $null
$serviceBinary = $null

# Chemins possibles pour les binaires
$guiPaths = @(
    "$projectDir\target\release\epn-gui.exe",
    "$scriptDir\epn-gui.exe",
    ".\epn-gui.exe"
)

$servicePaths = @(
    "$projectDir\target\release\epn-service.exe",
    "$scriptDir\epn-service.exe",
    ".\epn-service.exe"
)

foreach ($path in $guiPaths) {
    if (Test-Path $path) {
        $guiBinary = $path
        break
    }
}

foreach ($path in $servicePaths) {
    if (Test-Path $path) {
        $serviceBinary = $path
        break
    }
}

if (-not $guiBinary) {
    Write-Err "epn-gui.exe non trouve"
    Write-Host "Compilez d'abord avec: cargo build --release"
    exit 1
}

if (-not $serviceBinary) {
    Write-Err "epn-service.exe non trouve"
    Write-Host "Compilez d'abord avec: cargo build --release"
    exit 1
}

Copy-Item -Path $guiBinary -Destination "$InstallDir\epn-gui.exe" -Force
Write-Success "epn-gui.exe copie"

Copy-Item -Path $serviceBinary -Destination "$InstallDir\epn-service.exe" -Force
Write-Success "epn-service.exe copie"

Write-Host ""
Write-Host "=== Configuration ===" -ForegroundColor Yellow

# Creer le fichier de configuration
$configPath = "$DataDir\config.yaml"
if (-not (Test-Path $configPath)) {
    $configContent = @"
# Configuration EPN Client Windows
# Genere par install-service.ps1

# ============== Connexion au serveur ==============
server_url: $ServerUrl
ws_url: ws://$($ServerUrl -replace 'http://', '' -replace 'https://', '')

# ============== Token de decouverte ==============
discovery_token: $DiscoveryToken

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

# ============== Mode kiosque ==============
kiosk_mode: true
# kiosk_admin_password: "votre-mot-de-passe"
"@
    Set-Content -Path $configPath -Value $configContent -Encoding UTF8
    Write-Success "Configuration creee: $configPath"
} else {
    Write-Info "Configuration existante conservee"
}

Write-Host ""
Write-Host "=== Installation du service ===" -ForegroundColor Yellow

# Arreter l'ancien service s'il existe
$existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existingService) {
    Write-Info "Arret de l'ancien service..."
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    sc.exe delete $ServiceName | Out-Null
    Start-Sleep -Seconds 1
}

# Creer le nouveau service
Write-Info "Creation du service..."
$servicePath = "$InstallDir\epn-service.exe"
sc.exe create $ServiceName binPath= "`"$servicePath`"" start= auto DisplayName= "$ServiceDisplayName" | Out-Null

# Configurer la description
sc.exe description $ServiceName "$ServiceDescription" | Out-Null

# Configurer le redemarrage automatique en cas d'echec
sc.exe failure $ServiceName reset= 86400 actions= restart/5000/restart/10000/restart/30000 | Out-Null

Write-Success "Service cree"

# Demarrer le service
Write-Info "Demarrage du service..."
Start-Service -Name $ServiceName
Start-Sleep -Seconds 2

$service = Get-Service -Name $ServiceName
if ($service.Status -eq "Running") {
    Write-Success "Service demarre"
} else {
    Write-Warn "Le service n'a pas demarre. Verifiez les logs dans $DataDir\logs"
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Installation terminee!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Prochaines etapes:"
Write-Host "  1. Configurez le serveur dans: $configPath"
Write-Host "  2. Creez le template Firefox: .\save-firefox-template.ps1"
Write-Host "  3. Enregistrez le poste depuis l'interface admin"
Write-Host ""
Write-Host "Commandes utiles:"
Write-Host "  - Voir les logs:    Get-Content $DataDir\logs\service.log -Tail 50"
Write-Host "  - Statut service:   Get-Service $ServiceName"
Write-Host "  - Redemarrer:       Restart-Service $ServiceName"
Write-Host "  - Desinstaller:     .\install-service.ps1 -Uninstall"
Write-Host ""
