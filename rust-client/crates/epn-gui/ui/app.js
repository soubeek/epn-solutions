// EPN Client - Application JavaScript
// Tauri v2 API

// État de l'application
let currentSession = null;
let countdownInterval = null;
let invoke = null;
let kioskModeActive = false;
let widgetModeActive = false;
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
async function showSessionScreen() {
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

    // En mode kiosque, basculer vers le widget après connexion
    if (appConfig && appConfig.kiosk_mode) {
        // Petit délai pour que l'utilisateur voie la confirmation
        setTimeout(async () => {
            await switchToWidgetMode();
        }, 1500);
    }
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
    const minsStr = String(minutes).padStart(2, '0');
    const secsStr = String(seconds).padStart(2, '0');

    // Timer principal (écran session)
    document.getElementById('minutes').textContent = minsStr;
    document.getElementById('seconds').textContent = secsStr;

    // Timer widget
    const widgetMins = document.getElementById('widget-minutes');
    const widgetSecs = document.getElementById('widget-seconds');
    if (widgetMins) widgetMins.textContent = minsStr;
    if (widgetSecs) widgetSecs.textContent = secsStr;

    // Calculer le pourcentage
    const percentage = (remainingSeconds / currentSession.total_duration) * 100;

    // Barre de progression principale
    const progressBar = document.getElementById('progress-bar');
    progressBar.style.width = `${percentage}%`;

    // Barre de progression widget
    const widgetProgressBar = document.getElementById('widget-progress-bar');
    if (widgetProgressBar) widgetProgressBar.style.width = `${percentage}%`;

    const countdownDisplay = document.getElementById('countdown-display');
    const warningBox = document.getElementById('warning-message');
    const widgetTimer = document.getElementById('widget-timer');

    // Avertissements
    if (remainingSeconds <= 60) {
        // Critique (1 minute)
        countdownDisplay.querySelector('.countdown-time').className = 'countdown-time critical';
        progressBar.className = 'progress-bar critical';
        if (widgetTimer) widgetTimer.className = 'widget-timer critical';
        if (widgetProgressBar) widgetProgressBar.className = 'warning';
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
        if (widgetTimer) widgetTimer.className = 'widget-timer warning';
        if (widgetProgressBar) widgetProgressBar.className = 'warning';
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
        if (widgetTimer) widgetTimer.className = 'widget-timer';
        if (widgetProgressBar) widgetProgressBar.className = '';
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

    // Afficher l'écran d'expiration (masquer tous les autres écrans)
    document.getElementById('session-screen').classList.remove('active');
    document.getElementById('widget-screen').classList.remove('active');
    document.getElementById('login-screen').classList.remove('active');
    document.getElementById('expired-screen').classList.add('active');

    // Notification
    try {
        await invoke('show_notification', {
            title: 'Session Expirée',
            message: 'Votre temps est écoulé. L\'application va redémarrer.',
            urgency: 'critical'
        });
    } catch (error) {
        console.error('Erreur de notification:', error);
    }

    // Terminer et nettoyer la session côté Rust
    try {
        console.log('Nettoyage de la session...');
        await invoke('end_session');
        console.log('Session nettoyée');
    } catch (error) {
        console.error('Erreur lors du nettoyage de la session:', error);
    }

    // Redémarrer l'application après 3 secondes (systemd la relancera)
    setTimeout(async () => {
        console.log('Redémarrage de l\'application...');
        try {
            await invoke('restart_app');
        } catch (error) {
            console.error('Erreur lors du redémarrage:', error);
        }
    }, 3000);
}

// Retourner à l'écran de connexion
async function returnToLogin() {
    currentSession = null;

    document.getElementById('expired-screen').classList.remove('active');
    document.getElementById('login-screen').classList.add('active');

    // Réinitialiser le formulaire
    document.getElementById('code-input').value = '';
    document.getElementById('validate-btn').disabled = false;
    document.getElementById('validate-btn').textContent = 'Valider';
    hideError();

    // S'assurer que le mode kiosque/fullscreen est actif
    if (appConfig && appConfig.kiosk_mode) {
        try {
            const { getCurrentWindow, LogicalSize, LogicalPosition } = window.__TAURI__.window;
            const win = getCurrentWindow();

            // 1. Remettre position et taille normale
            const monitor = await win.currentMonitor();
            if (monitor) {
                await win.setPosition(new LogicalPosition(0, 0));
                await win.setSize(new LogicalSize(monitor.size.width, monitor.size.height));
            }

            // Attendre que les changements prennent effet
            await new Promise(resolve => setTimeout(resolve, 200));

            // 2. Configurer le mode kiosque
            await win.setDecorations(false);
            await win.setAlwaysOnTop(true);

            // 3. Maximiser puis fullscreen
            await win.maximize();
            await new Promise(resolve => setTimeout(resolve, 100));
            await ensureFullscreen(win);
        } catch (error) {
            console.error('Erreur lors de la réactivation du fullscreen:', error);
        }
    }

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

        // Attendre que la fenêtre soit prête (important pour Wayland/X11)
        await new Promise(resolve => setTimeout(resolve, 300));

        // Configurer la fenêtre
        await win.setDecorations(false);
        await win.setAlwaysOnTop(true);
        await win.setClosable(false);

        // Assurer le plein écran avec retry
        await ensureFullscreen(win);

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

// Assurer le plein écran avec vérification et retry
async function ensureFullscreen(win) {
    const maxRetries = 5;
    const retryDelay = 500;

    for (let i = 0; i < maxRetries; i++) {
        try {
            // Vérifier si déjà en plein écran
            const isFullscreen = await win.isFullscreen();
            if (isFullscreen) {
                console.log(`Plein écran confirmé (tentative ${i + 1})`);
                return true;
            }

            console.log(`Tentative plein écran ${i + 1}/${maxRetries}...`);
            await win.setFullscreen(true);

            // Attendre avant de vérifier
            await new Promise(resolve => setTimeout(resolve, retryDelay));
        } catch (e) {
            console.error(`Erreur tentative ${i + 1}:`, e);
        }
    }

    console.warn('Impossible de confirmer le plein écran après toutes les tentatives');
    return false;
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

// ==================== MODE WIDGET (SESSION ACTIVE) ====================

// Basculer vers le mode widget (petite fenêtre flottante)
async function switchToWidgetMode() {
    console.log('Activation du mode widget...');

    try {
        const { getCurrentWindow, LogicalSize, LogicalPosition } = window.__TAURI__.window;
        const win = getCurrentWindow();

        // Sortir du plein écran
        await win.setFullscreen(false);

        // Attendre un peu pour que le changement de mode prenne effet
        await new Promise(resolve => setTimeout(resolve, 100));

        // Définir la taille du widget
        await win.setSize(new LogicalSize(320, 80));

        // Positionner en bas à droite
        const monitor = await win.currentMonitor();
        if (monitor) {
            const x = monitor.size.width - 340;
            const y = monitor.size.height - 120;
            await win.setPosition(new LogicalPosition(x, y));
        }

        // Garder au premier plan
        await win.setAlwaysOnTop(true);

        // Permettre le déplacement
        await win.setDecorations(false);

        // Afficher le widget au lieu de l'écran session
        document.getElementById('session-screen').classList.remove('active');
        document.getElementById('widget-screen').classList.add('active');
        document.body.classList.add('widget-active');

        // Configurer le drag
        setupWidgetDrag();

        widgetModeActive = true;
        console.log('Mode widget activé');
    } catch (error) {
        console.error('Erreur lors de l\'activation du mode widget:', error);
    }
}

// Revenir en mode plein écran
async function switchToFullscreenMode() {
    console.log('Retour en mode plein écran...');

    try {
        const { getCurrentWindow, LogicalSize, LogicalPosition } = window.__TAURI__.window;
        const win = getCurrentWindow();

        // Masquer le widget
        document.getElementById('widget-screen').classList.remove('active');
        document.body.classList.remove('widget-active');

        // 1. D'abord sortir du mode widget - remettre position et taille normale
        const monitor = await win.currentMonitor();
        if (monitor) {
            // Position en haut à gauche
            await win.setPosition(new LogicalPosition(0, 0));
            // Taille du moniteur
            await win.setSize(new LogicalSize(monitor.size.width, monitor.size.height));
        }

        // Attendre que les changements prennent effet
        await new Promise(resolve => setTimeout(resolve, 200));

        // 2. Configurer le mode kiosque
        await win.setDecorations(false);
        await win.setAlwaysOnTop(true);

        // 3. Maximiser d'abord (important pour Wayland)
        await win.maximize();
        await new Promise(resolve => setTimeout(resolve, 100));

        // 4. Puis forcer le plein écran avec retry
        await ensureFullscreen(win);

        widgetModeActive = false;
        console.log('Mode plein écran activé');
    } catch (error) {
        console.error('Erreur lors du retour en mode plein écran:', error);
    }
}

// Configurer le déplacement du widget par drag
function setupWidgetDrag() {
    const widget = document.getElementById('widget-screen');

    widget.addEventListener('mousedown', async (e) => {
        // Ne pas drag si on clique sur un bouton
        if (e.target.tagName === 'BUTTON') return;

        try {
            const { getCurrentWindow } = window.__TAURI__.window;
            const win = getCurrentWindow();
            await win.startDragging();
        } catch (error) {
            console.error('Erreur de drag:', error);
        }
    });
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
