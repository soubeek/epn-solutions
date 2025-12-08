<#
.SYNOPSIS
    EPN Solutions - Configuration du verrouillage systeme Windows

.DESCRIPTION
    Configure les restrictions systeme pour un poste kiosque Windows:
    - Restrictions via registre (Explorer, System policies)
    - Auto-login de l'utilisateur
    - Autostart du client EPN

.PARAMETER Action
    Action a effectuer: Apply, Remove, Status

.PARAMETER User
    Nom d'utilisateur kiosque (defaut: epn)

.PARAMETER Profile
    Profil de restriction: Strict, Standard, Permissive, Gaming

.PARAMETER ClientPath
    Chemin vers l'executable du client EPN

.EXAMPLE
    .\configure-lockdown.ps1 -Action Apply -User epn -Profile Standard

.EXAMPLE
    .\configure-lockdown.ps1 -Action Status

.EXAMPLE
    .\configure-lockdown.ps1 -Action Remove
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("Apply", "Remove", "Status")]
    [string]$Action,

    [Parameter()]
    [string]$User = "epn",

    [Parameter()]
    [ValidateSet("Strict", "Standard", "Permissive", "Gaming")]
    [string]$Profile = "Standard",

    [Parameter()]
    [string]$ClientPath = "C:\Program Files\EPN\epn-gui.exe"
)

# =============================================================================
# Configuration
# =============================================================================

$ErrorActionPreference = "Stop"

# Chemins registre
$ExplorerPolicies = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer"
$SystemPolicies = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Policies\System"
$WinlogonPath = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
$RunPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"

# =============================================================================
# Fonctions utilitaires
# =============================================================================

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] " -ForegroundColor Blue -NoNewline
    Write-Host $Message
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] " -ForegroundColor Green -NoNewline
    Write-Host $Message
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARN] " -ForegroundColor Yellow -NoNewline
    Write-Host $Message
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERREUR] " -ForegroundColor Red -NoNewline
    Write-Host $Message
}

function Test-Administrator {
    $currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Ensure-RegistryPath {
    param([string]$Path)
    if (!(Test-Path $Path)) {
        New-Item -Path $Path -Force | Out-Null
    }
}

function Set-RegistryValue {
    param(
        [string]$Path,
        [string]$Name,
        [int]$Value
    )
    Ensure-RegistryPath $Path
    Set-ItemProperty -Path $Path -Name $Name -Value $Value -Type DWord
    Write-Info "  Registre: $Name = $Value"
}

function Remove-RegistryValue {
    param(
        [string]$Path,
        [string]$Name
    )
    if (Test-Path $Path) {
        $item = Get-ItemProperty -Path $Path -Name $Name -ErrorAction SilentlyContinue
        if ($item) {
            Remove-ItemProperty -Path $Path -Name $Name -ErrorAction SilentlyContinue
            Write-Info "  Supprime: $Name"
        }
    }
}

function Get-RegistryValue {
    param(
        [string]$Path,
        [string]$Name
    )
    if (Test-Path $Path) {
        $item = Get-ItemProperty -Path $Path -Name $Name -ErrorAction SilentlyContinue
        if ($item) {
            return $item.$Name
        }
    }
    return $null
}

# =============================================================================
# Application des restrictions
# =============================================================================

function Apply-ExplorerRestrictions {
    Write-Info "Application des restrictions Explorer..."

    # NoDesktop - Cacher les icones du bureau
    Set-RegistryValue -Path $ExplorerPolicies -Name "NoDesktop" -Value 1

    # NoViewContextMenu - Desactiver clic droit
    Set-RegistryValue -Path $ExplorerPolicies -Name "NoViewContextMenu" -Value 1

    # NoRun - Desactiver Win+R
    Set-RegistryValue -Path $ExplorerPolicies -Name "NoRun" -Value 1

    # NoWinKeys - Desactiver les raccourcis Windows
    Set-RegistryValue -Path $ExplorerPolicies -Name "NoWinKeys" -Value 1

    # NoControlPanel - Desactiver panneau de configuration
    Set-RegistryValue -Path $ExplorerPolicies -Name "NoControlPanel" -Value 1

    # NoClose - Desactiver bouton arreter
    if ($Profile -eq "Strict") {
        Set-RegistryValue -Path $ExplorerPolicies -Name "NoClose" -Value 1
    }

    # Desactiver le menu demarrer complet
    Set-RegistryValue -Path $ExplorerPolicies -Name "NoStartMenuMFUprogramsList" -Value 1
    Set-RegistryValue -Path $ExplorerPolicies -Name "NoStartMenuMorePrograms" -Value 1

    Write-Success "Restrictions Explorer appliquees"
}

function Apply-SystemRestrictions {
    Write-Info "Application des restrictions systeme..."

    # DisableTaskMgr - Desactiver gestionnaire de taches
    Set-RegistryValue -Path $SystemPolicies -Name "DisableTaskMgr" -Value 1

    # DisableChangePassword - Desactiver changement mot de passe
    Set-RegistryValue -Path $SystemPolicies -Name "DisableChangePassword" -Value 1

    # HideFastUserSwitching - Cacher changement utilisateur
    Set-RegistryValue -Path $SystemPolicies -Name "HideFastUserSwitching" -Value 1

    Write-Success "Restrictions systeme appliquees"
}

function Remove-ExplorerRestrictions {
    Write-Info "Retrait des restrictions Explorer..."

    $values = @(
        "NoDesktop",
        "NoViewContextMenu",
        "NoRun",
        "NoWinKeys",
        "NoControlPanel",
        "NoClose",
        "NoStartMenuMFUprogramsList",
        "NoStartMenuMorePrograms"
    )

    foreach ($value in $values) {
        Remove-RegistryValue -Path $ExplorerPolicies -Name $value
    }

    Write-Success "Restrictions Explorer retirees"
}

function Remove-SystemRestrictions {
    Write-Info "Retrait des restrictions systeme..."

    $values = @(
        "DisableTaskMgr",
        "DisableChangePassword",
        "HideFastUserSwitching"
    )

    foreach ($value in $values) {
        Remove-RegistryValue -Path $SystemPolicies -Name $value
    }

    Write-Success "Restrictions systeme retirees"
}

# =============================================================================
# Auto-login
# =============================================================================

function Configure-AutoLogin {
    param([string]$Username)

    Write-Info "Configuration auto-login pour '$Username'..."

    if (!(Test-Administrator)) {
        Write-Warning "Droits admin requis pour configurer l'auto-login HKLM"
        return
    }

    Set-ItemProperty -Path $WinlogonPath -Name "AutoAdminLogon" -Value "1"
    Set-ItemProperty -Path $WinlogonPath -Name "DefaultUserName" -Value $Username
    Set-ItemProperty -Path $WinlogonPath -Name "DefaultDomainName" -Value "."

    Write-Warning "ATTENTION: Le mot de passe doit etre configure manuellement"
    Write-Warning "Utilisez: Set-ItemProperty -Path '$WinlogonPath' -Name 'DefaultPassword' -Value 'MOTDEPASSE'"

    Write-Success "Auto-login configure"
}

function Remove-AutoLogin {
    Write-Info "Retrait auto-login..."

    if (!(Test-Administrator)) {
        Write-Warning "Droits admin requis pour retirer l'auto-login"
        return
    }

    Set-ItemProperty -Path $WinlogonPath -Name "AutoAdminLogon" -Value "0" -ErrorAction SilentlyContinue
    Remove-ItemProperty -Path $WinlogonPath -Name "DefaultPassword" -ErrorAction SilentlyContinue

    Write-Success "Auto-login retire"
}

# =============================================================================
# Autostart
# =============================================================================

function Configure-Autostart {
    param([string]$ClientPath)

    Write-Info "Configuration autostart..."

    if (!(Test-Path $ClientPath)) {
        Write-Warning "Client non trouve: $ClientPath"
    }

    Set-ItemProperty -Path $RunPath -Name "EPNClient" -Value $ClientPath

    Write-Success "Autostart configure: $ClientPath"
}

function Remove-Autostart {
    Write-Info "Retrait autostart..."

    Remove-ItemProperty -Path $RunPath -Name "EPNClient" -ErrorAction SilentlyContinue

    Write-Success "Autostart retire"
}

# =============================================================================
# Statut
# =============================================================================

function Show-Status {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "  EPN Solutions - Statut verrouillage" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""

    # Admin
    if (Test-Administrator) {
        Write-Host "Droits admin:         " -NoNewline
        Write-Host "Oui" -ForegroundColor Green
    } else {
        Write-Host "Droits admin:         " -NoNewline
        Write-Host "Non" -ForegroundColor Yellow
    }

    # Auto-login
    $autoLogin = Get-ItemProperty -Path $WinlogonPath -Name "AutoAdminLogon" -ErrorAction SilentlyContinue
    if ($autoLogin -and $autoLogin.AutoAdminLogon -eq "1") {
        $defaultUser = (Get-ItemProperty -Path $WinlogonPath -Name "DefaultUserName" -ErrorAction SilentlyContinue).DefaultUserName
        Write-Host "Auto-login:           " -NoNewline
        Write-Host "Actif ($defaultUser)" -ForegroundColor Green
    } else {
        Write-Host "Auto-login:           " -NoNewline
        Write-Host "Inactif" -ForegroundColor Yellow
    }

    # Autostart
    $autostart = Get-ItemProperty -Path $RunPath -Name "EPNClient" -ErrorAction SilentlyContinue
    if ($autostart) {
        Write-Host "Autostart:            " -NoNewline
        Write-Host "Configure" -ForegroundColor Green
    } else {
        Write-Host "Autostart:            " -NoNewline
        Write-Host "Non configure" -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "Restrictions actives:" -ForegroundColor Cyan

    $checks = @(
        @{Path=$ExplorerPolicies; Name="NoDesktop"; Label="Bureau cache"},
        @{Path=$ExplorerPolicies; Name="NoRun"; Label="Win+R desactive"},
        @{Path=$ExplorerPolicies; Name="NoControlPanel"; Label="Panneau config desactive"},
        @{Path=$SystemPolicies; Name="DisableTaskMgr"; Label="Task Manager desactive"}
    )

    foreach ($check in $checks) {
        $value = Get-RegistryValue -Path $check.Path -Name $check.Name
        Write-Host "  $($check.Label): " -NoNewline
        if ($value -eq 1) {
            Write-Host "Oui" -ForegroundColor Green
        } else {
            Write-Host "Non" -ForegroundColor Yellow
        }
    }

    Write-Host ""
}

# =============================================================================
# Main
# =============================================================================

Write-Host ""
Write-Host "EPN Solutions - Configuration verrouillage Windows" -ForegroundColor Cyan
Write-Host ""

switch ($Action) {
    "Apply" {
        Write-Info "Application du profil '$Profile' pour l'utilisateur '$User'..."
        Write-Host ""

        Apply-ExplorerRestrictions
        Apply-SystemRestrictions
        Configure-AutoLogin -Username $User
        Configure-Autostart -ClientPath $ClientPath

        Write-Host ""
        Write-Success "Configuration terminee!"
        Write-Host ""
        Write-Host "Prochaines etapes:"
        Write-Host "  1. Configurer le mot de passe auto-login (voir warning ci-dessus)"
        Write-Host "  2. Redemarrer le systeme"
        Write-Host ""
        Write-Host "Pour retirer: .\configure-lockdown.ps1 -Action Remove"
    }

    "Remove" {
        Write-Info "Retrait de toutes les restrictions..."
        Write-Host ""

        Remove-ExplorerRestrictions
        Remove-SystemRestrictions
        Remove-AutoLogin
        Remove-Autostart

        Write-Host ""
        Write-Success "Toutes les restrictions ont ete retirees"
        Write-Host ""
        Write-Host "Note: Un redemarrage peut etre necessaire"
    }

    "Status" {
        Show-Status
    }
}
