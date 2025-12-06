// EPN Client - Application JavaScript
// Tauri v2 API

// État de l'application
let currentSession = null;
let countdownInterval = null;
let invoke = null;
let kioskModeActive = false;
let appConfig = null;

// Initialisation au chargement
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Application EPN Client démarrée');

    // Vérifier que Tauri est disponible
    if (!window.__TAURI__) {
        console.error('Tauri API non disponible (window.__TAURI__ est undefined)');
        updateConnectionStatus(false);
        showError('Erreur: API Tauri non disponible');
        return;
    }

    if (!window.__TAURI__.core) {
        console.error('Tauri core non disponible');
        updateConnectionStatus(false);
        showError('Erreur: Tauri core non disponible');
        return;
    }

    invoke = window.__TAURI__.core.invoke;
    console.log('Tauri API chargée avec succès');

    // Initialiser l'application
    try {
        console.log('Appel de initialize()...');
        await invoke('initialize');
        console.log('initialize() réussi');
        updateConnectionStatus(true);

        // Charger la configuration
        appConfig = await invoke('get_config');
        document.getElementById('server-info').textContent =
            `Serveur: ${appConfig.server_url}`;

        // Activer le mode kiosque si configuré
        if (appConfig.kiosk_mode) {
            await setupKioskMode();
        }
    } catch (error) {
        console.error('Erreur d\'initialisation:', error);
        updateConnectionStatus(false);
        showError('Impossible de se connecter au serveur: ' + error);
    }

    // Gérer la touche Entrée sur le champ de code
    document.getElementById('code-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            validateCode();
        }
    });
});

// Mettre à jour le statut de connexion
function updateConnectionStatus(connected) {
    const statusBar = document.getElementById('connection-status');
    const statusText = document.getElementById('connection-text');

    if (connected) {
        statusBar.classList.add('connected');
        statusText.textContent = '✓ Connecté';
    } else {
        statusBar.classList.remove('connected');
        statusText.textContent = '⚠️ Non connecté';
    }
}

// Valider un code d'accès
async function validateCode() {
    const codeInput = document.getElementById('code-input');
    const code = codeInput.value.trim().toUpperCase();

    if (!code) {
        showError('Veuillez entrer un code');
        return;
    }

    const validateBtn = document.getElementById('validate-btn');
    validateBtn.disabled = true;
    validateBtn.textContent = 'Validation...';

    try {
        // Valider le code
        const session = await invoke('validate_code', { code });
        console.log('Code valide:', session);

        // Démarrer la session
        const startedSession = await invoke('start_session');
        console.log('Session démarrée:', startedSession);

        // Afficher l'écran de session
        currentSession = startedSession;
        showSessionScreen();

        // Démarrer la surveillance
        startSessionMonitoring();

    } catch (error) {
        console.error('Erreur de validation:', error);
        showError(error || 'Code invalide');
        validateBtn.disabled = false;
        validateBtn.textContent = 'Valider';
    }
}

// Afficher l'écran de session
function showSessionScreen() {
    document.getElementById('login-screen').classList.remove('active');
    document.getElementById('session-screen').classList.add('active');

    // Afficher les informations
    document.getElementById('user-name').textContent =
        currentSession.user_name;
    document.getElementById('workstation').textContent =
        currentSession.workstation;
    document.getElementById('total-duration').textContent =
        formatTime(currentSession.total_duration);

    // Initialiser le compteur
    updateCountdown(currentSession.remaining_time);
}

// Démarrer la surveillance de la session
function startSessionMonitoring() {
    // Mettre à jour toutes les secondes
    countdownInterval = setInterval(async () => {
        try {
            const remaining = await invoke('get_remaining_time');
            currentSession.remaining_time = remaining;
            updateCountdown(remaining);

            // Vérifier si la session est expirée
            if (remaining === 0) {
                sessionExpired();
            }
        } catch (error) {
            console.error('Erreur de surveillance:', error);
            // La session a peut-être été terminée
            sessionExpired();
        }
    }, 1000);
}

// Mettre à jour le compteur
function updateCountdown(remainingSeconds) {
    const minutes = Math.floor(remainingSeconds / 60);
    const seconds = remainingSeconds % 60;

    document.getElementById('minutes').textContent =
        String(minutes).padStart(2, '0');
    document.getElementById('seconds').textContent =
        String(seconds).padStart(2, '0');

    // Calculer le pourcentage
    const percentage = (remainingSeconds / currentSession.total_duration) * 100;
    const progressBar = document.getElementById('progress-bar');
    progressBar.style.width = `${percentage}%`;

    const countdownDisplay = document.getElementById('countdown-display');
    const warningBox = document.getElementById('warning-message');

    // Avertissements
    if (remainingSeconds <= 60) {
        // Critique (1 minute)
        countdownDisplay.querySelector('.countdown-time').className = 'countdown-time critical';
        progressBar.className = 'progress-bar critical';
        warningBox.style.display = 'flex';
        warningBox.className = 'warning-box critical';
        document.getElementById('warning-text').textContent =
            '⚠️ ATTENTION : Il vous reste moins d\'une minute !';

        // Notification système
        if (remainingSeconds === 60) {
            invoke('show_notification', {
                title: 'Session sur le point d\'expirer',
                message: 'Il vous reste 1 minute',
                urgency: 'critical'
            }).catch(console.error);
        }

    } else if (remainingSeconds <= 300) {
        // Avertissement (5 minutes)
        countdownDisplay.querySelector('.countdown-time').className = 'countdown-time warning';
        progressBar.className = 'progress-bar warning';
        warningBox.style.display = 'flex';
        warningBox.className = 'warning-box';
        document.getElementById('warning-text').textContent =
            `⚠️ Attention : Il vous reste ${minutes} minutes`;

        // Notification système
        if (remainingSeconds === 300) {
            invoke('show_notification', {
                title: 'Avertissement',
                message: 'Il vous reste 5 minutes',
                urgency: 'normal'
            }).catch(console.error);
        }

    } else {
        // Normal
        countdownDisplay.querySelector('.countdown-time').className = 'countdown-time';
        progressBar.className = 'progress-bar';
        warningBox.style.display = 'none';
    }
}

// Session expirée
async function sessionExpired() {
    // Arrêter la surveillance
    if (countdownInterval) {
        clearInterval(countdownInterval);
        countdownInterval = null;
    }

    // Afficher l'écran d'expiration
    document.getElementById('session-screen').classList.remove('active');
    document.getElementById('expired-screen').classList.add('active');

    // Notification
    try {
        await invoke('show_notification', {
            title: 'Session Expirée',
            message: 'Votre temps est écoulé',
            urgency: 'critical'
        });
    } catch (error) {
        console.error('Erreur de notification:', error);
    }

    // Verrouiller l'écran après 5 secondes
    setTimeout(async () => {
        try {
            await invoke('lock_screen');
        } catch (error) {
            console.error('Erreur de verrouillage:', error);
        }
    }, 5000);
}

// Retourner à l'écran de connexion
function returnToLogin() {
    currentSession = null;

    document.getElementById('expired-screen').classList.remove('active');
    document.getElementById('login-screen').classList.add('active');

    // Réinitialiser le formulaire
    document.getElementById('code-input').value = '';
    document.getElementById('validate-btn').disabled = false;
    document.getElementById('validate-btn').textContent = 'Valider';
    hideError();

    // Focus sur le champ de saisie
    document.getElementById('code-input').focus();
}

// Afficher une erreur
function showError(message) {
    const errorDiv = document.getElementById('login-error');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
}

// Masquer l'erreur
function hideError() {
    const errorDiv = document.getElementById('login-error');
    errorDiv.style.display = 'none';
}

// Formater le temps (secondes -> HH:MM:SS ou MM:SS)
function formatTime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hours > 0) {
        return `${hours}h ${String(minutes).padStart(2, '0')}m`;
    } else {
        return `${minutes}m ${String(secs).padStart(2, '0')}s`;
    }
}

// ==================== MODE KIOSQUE ====================

// Configurer le mode kiosque
async function setupKioskMode() {
    console.log('Activation du mode kiosque...');

    try {
        // Accéder à l'API Window de Tauri
        const { getCurrentWindow } = window.__TAURI__.window;
        const win = getCurrentWindow();

        // Configurer la fenêtre
        await win.setFullscreen(true);
        await win.setDecorations(false);
        await win.setAlwaysOnTop(true);
        await win.setClosable(false);

        // Bloquer la fermeture de la fenêtre
        await win.onCloseRequested((event) => {
            console.log('Tentative de fermeture bloquée (mode kiosque actif)');
            event.preventDefault();
        });

        kioskModeActive = true;
        console.log('Mode kiosque activé');
    } catch (error) {
        console.error('Erreur lors de l\'activation du mode kiosque:', error);
    }
}

// Désactiver le mode kiosque
async function exitKioskMode() {
    console.log('Désactivation du mode kiosque...');

    try {
        const { getCurrentWindow } = window.__TAURI__.window;
        const win = getCurrentWindow();

        await win.setFullscreen(false);
        await win.setDecorations(true);
        await win.setAlwaysOnTop(false);
        await win.setClosable(true);

        kioskModeActive = false;
        console.log('Mode kiosque désactivé');
    } catch (error) {
        console.error('Erreur lors de la désactivation du mode kiosque:', error);
    }
}

// Demander le mot de passe admin pour déverrouiller
async function promptAdminPassword() {
    const password = prompt('Mot de passe administrateur:');
    if (password) {
        try {
            const valid = await invoke('verify_admin_password', { password });
            if (valid) {
                await exitKioskMode();
                alert('Mode kiosque désactivé');
            } else {
                alert('Mot de passe incorrect');
            }
        } catch (error) {
            console.error('Erreur de vérification du mot de passe:', error);
            alert('Erreur: ' + error);
        }
    }
}

// Déverrouillage à distance (appelé via WebSocket)
async function handleRemoteUnlock(adminName) {
    console.log('Déverrouillage à distance par:', adminName);
    await exitKioskMode();
    await invoke('show_notification', {
        title: 'Mode kiosque désactivé',
        message: `Déverrouillé par ${adminName}`,
        urgency: 'normal'
    }).catch(console.error);
}

// ==================== GESTION DES TOUCHES ====================

// Bloquer les touches système en mode kiosque
document.addEventListener('keydown', (e) => {
    // Détecter Ctrl+Alt+Shift+K pour déverrouillage admin
    if (e.ctrlKey && e.altKey && e.shiftKey && (e.key === 'K' || e.key === 'k')) {
        e.preventDefault();
        if (kioskModeActive && appConfig && appConfig.kiosk_admin_password) {
            promptAdminPassword();
        }
        return false;
    }

    // Bloquer les touches de sortie en mode kiosque
    if (kioskModeActive) {
        // Bloquer Alt+F4
        if (e.altKey && e.key === 'F4') {
            e.preventDefault();
            return false;
        }
        // Bloquer Alt+Tab (ne fonctionne pas toujours au niveau navigateur)
        if (e.altKey && e.key === 'Tab') {
            e.preventDefault();
            return false;
        }
        // Bloquer F11 (fullscreen toggle)
        if (e.key === 'F11') {
            e.preventDefault();
            return false;
        }
        // Bloquer Escape
        if (e.key === 'Escape') {
            e.preventDefault();
            return false;
        }
    }
});

// ==================== GESTION DES ERREURS ====================

// Gérer les erreurs globales
window.addEventListener('error', (event) => {
    console.error('Erreur globale:', event.error);
});

// Gérer la fermeture de la fenêtre
window.addEventListener('beforeunload', () => {
    if (countdownInterval) {
        clearInterval(countdownInterval);
    }
});
