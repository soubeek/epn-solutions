@echo off
REM Installation du Client Poste Public - Windows
REM Lance le script PowerShell d'installation

echo ====================================================================
echo   Installation Client Poste Public - Windows
echo ====================================================================
echo.

REM Vérifier les permissions administrateur
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo   [ERREUR] Ce script doit etre execute en tant qu'Administrateur
    echo.
    echo   Faites un clic droit sur install.bat et selectionnez
    echo   "Executer en tant qu'administrateur"
    echo.
    pause
    exit /b 1
)

echo   Lancement de l'installation PowerShell...
echo.

REM Lancer le script PowerShell
powershell.exe -ExecutionPolicy Bypass -File "%~dp0install.ps1"

if %errorLevel% neq 0 (
    echo.
    echo   [ERREUR] L'installation a echoue
    pause
    exit /b 1
)

echo.
echo   Installation terminee !
pause
