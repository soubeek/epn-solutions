# Script pour sauvegarder le profil Firefox actuel comme template
# A executer en tant qu'Administrateur apres avoir configure Firefox

param(
    [string]$SourceUser = $env:USERNAME
)

$ErrorActionPreference = "Stop"

# Chemins
$TemplateDir = "C:\ProgramData\EPNClient\firefox-template"
$SourceDir = "$env:APPDATA\Mozilla\Firefox"

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
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Sauvegarde du template Firefox" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Utilisateur source: $SourceUser"
Write-Host "Dossier source: $SourceDir"
Write-Host "Dossier template: $TemplateDir"
Write-Host ""

# Verifier que le dossier Firefox existe
if (-not (Test-Path $SourceDir)) {
    Write-Err "Dossier Firefox non trouve: $SourceDir"
    Write-Host "Lancez Firefox une fois pour creer le profil"
    exit 1
}

# Verifier que Firefox n'est pas en cours d'execution
$firefoxProcess = Get-Process -Name "firefox" -ErrorAction SilentlyContinue
if ($firefoxProcess) {
    Write-Err "Firefox est en cours d'execution"
    Write-Host "Fermez Firefox avant de sauvegarder le template"
    exit 1
}

Write-Host "=== Preparation ===" -ForegroundColor Yellow

# Creer le dossier template
if (Test-Path $TemplateDir) {
    Write-Info "Suppression de l'ancien template..."
    Remove-Item -Path $TemplateDir -Recurse -Force
}

New-Item -ItemType Directory -Path $TemplateDir -Force | Out-Null
Write-Success "Dossier template cree"

Write-Host ""
Write-Host "=== Copie du profil Firefox ===" -ForegroundColor Yellow

# Copier le profil Firefox
Write-Info "Copie en cours..."
Copy-Item -Path "$SourceDir\*" -Destination $TemplateDir -Recurse -Force
Write-Success "Profil copie"

Write-Host ""
Write-Host "=== Nettoyage des donnees de session ===" -ForegroundColor Yellow

# Fichiers a supprimer du template (donnees de session)
$filesToDelete = @(
    "*.sqlite-wal",
    "*.sqlite-shm",
    "cookies.sqlite",
    "places.sqlite",
    "formhistory.sqlite",
    "sessionstore*",
    "webappsstore.sqlite",
    "permissions.sqlite",
    "content-prefs.sqlite",
    "logins.json",
    "key4.db",
    "signons.sqlite"
)

# Dossiers a supprimer
$foldersToDelete = @(
    "cache2",
    "storage",
    "crashes",
    "saved-telemetry-pings",
    "datareporting",
    "security_state"
)

# Parcourir tous les profils
$profiles = Get-ChildItem -Path $TemplateDir -Directory -ErrorAction SilentlyContinue
foreach ($profile in $profiles) {
    if ($profile.Name -like "*.default*" -or $profile.Name -like "*.default-release*") {
        Write-Info "Nettoyage du profil: $($profile.Name)"

        # Supprimer les fichiers
        foreach ($pattern in $filesToDelete) {
            $files = Get-ChildItem -Path $profile.FullName -Filter $pattern -Recurse -ErrorAction SilentlyContinue
            foreach ($file in $files) {
                Remove-Item -Path $file.FullName -Force -ErrorAction SilentlyContinue
            }
        }

        # Supprimer les dossiers
        foreach ($folder in $foldersToDelete) {
            $folderPath = Join-Path $profile.FullName $folder
            if (Test-Path $folderPath) {
                Remove-Item -Path $folderPath -Recurse -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

Write-Success "Donnees de session supprimees"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Template Firefox sauvegarde!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Le profil Firefox sera restaure a chaque fin de session EPN."
Write-Host ""
Write-Host "Contenu du template:"
Get-ChildItem -Path $TemplateDir | Format-Table Name, LastWriteTime -AutoSize
