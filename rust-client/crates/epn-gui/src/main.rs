// EPN GUI - Application Tauri (Simplifié pour POC)
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use epn_core::{Config, SessionInfo, SessionManager};
use epn_system::{get_notifier, get_screen_locker, get_logout, Urgency};
use std::sync::Arc;
use tokio::sync::Mutex;
use tauri::{Manager, State};

/// État partagé de l'application
struct AppState {
    session_manager: Arc<Mutex<Option<SessionManager>>>,
    config: Arc<Config>,
}

/// Initialiser l'application
#[tauri::command]
async fn initialize(state: State<'_, AppState>) -> Result<String, String> {
    tracing::info!("Initialisation de l'application");

    let config = state.config.clone();
    match SessionManager::new((*config).clone()).await {
        Ok(manager) => {
            *state.session_manager.lock().await = Some(manager);
            Ok("Application initialisée".to_string())
        }
        Err(e) => {
            tracing::error!("Erreur d'initialisation: {}", e);
            Err(format!("Erreur d'initialisation: {}", e))
        }
    }
}

/// Valider un code d'accès
#[tauri::command]
async fn validate_code(
    code: String,
    state: State<'_, AppState>,
) -> Result<SessionInfo, String> {
    tracing::info!("Validation du code: {}", code);

    let mut manager_guard = state.session_manager.lock().await;
    match manager_guard.as_mut() {
        Some(manager) => {
            manager.validate_code(&code)
                .await
                .map_err(|e| e.to_string())
        }
        None => Err("Session manager non initialisé".to_string()),
    }
}

/// Démarrer une session
#[tauri::command]
async fn start_session(state: State<'_, AppState>) -> Result<SessionInfo, String> {
    tracing::info!("Démarrage de la session");

    let mut manager_guard = state.session_manager.lock().await;
    match manager_guard.as_mut() {
        Some(manager) => {
            manager.start_session()
                .await
                .map_err(|e| e.to_string())
        }
        None => Err("Session manager non initialisé".to_string()),
    }
}

/// Obtenir le temps restant
#[tauri::command]
async fn get_remaining_time(state: State<'_, AppState>) -> Result<u64, String> {
    let mut manager_guard = state.session_manager.lock().await;
    match manager_guard.as_mut() {
        Some(manager) => {
            manager.get_remaining_time()
                .await
                .map_err(|e| e.to_string())
        }
        None => Err("Session manager non initialisé".to_string()),
    }
}

/// Terminer la session et nettoyer
#[tauri::command]
async fn end_session(state: State<'_, AppState>) -> Result<(), String> {
    tracing::info!("Fin de session demandée");

    let manager_guard = state.session_manager.lock().await;
    match manager_guard.as_ref() {
        Some(manager) => {
            manager.handle_session_end("Session expirée").await;
            Ok(())
        }
        None => Err("Session manager non initialisé".to_string()),
    }
}

/// Verrouiller l'écran
#[tauri::command]
async fn lock_screen() -> Result<(), String> {
    tracing::info!("Verrouillage de l'écran");
    let locker = get_screen_locker();
    locker.lock().map_err(|e| e.to_string())
}

/// Déconnecter l'utilisateur
#[tauri::command]
async fn logout_user() -> Result<(), String> {
    tracing::info!("Déconnexion de l'utilisateur");
    let logout = get_logout();
    logout.logout().map_err(|e| e.to_string())
}

/// Afficher une notification
#[tauri::command]
async fn show_notification(title: String, message: String, urgency: String) -> Result<(), String> {
    tracing::info!("Affichage notification: {}", title);

    let urgency_level = match urgency.as_str() {
        "low" => Urgency::Low,
        "critical" => Urgency::Critical,
        _ => Urgency::Normal,
    };

    let notifier = get_notifier();
    notifier.show(&title, &message, urgency_level)
        .map_err(|e| e.to_string())
}

/// Obtenir la configuration
#[tauri::command]
fn get_config(state: State<'_, AppState>) -> Config {
    (*state.config).clone()
}

/// Vérifier le mot de passe admin pour déverrouiller le mode kiosque
#[tauri::command]
fn verify_admin_password(password: String, state: State<'_, AppState>) -> bool {
    let config = &state.config;

    match &config.kiosk_admin_password {
        Some(admin_password) => {
            let is_valid = password == *admin_password;
            if is_valid {
                tracing::info!("Mot de passe admin correct - déverrouillage du mode kiosque");
            } else {
                tracing::warn!("Tentative de déverrouillage avec mot de passe incorrect");
            }
            is_valid
        }
        None => {
            tracing::warn!("Tentative de déverrouillage mais aucun mot de passe admin configuré");
            false
        }
    }
}

#[tokio::main]
async fn main() {
    // Initialiser le logging
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::from_default_env()
                .add_directive(tracing::Level::INFO.into())
        )
        .init();

    tracing::info!("Démarrage de l'application EPN Client");

    // Charger la configuration
    let config = match Config::load() {
        Ok(cfg) => {
            tracing::info!("Configuration chargée");
            cfg
        }
        Err(e) => {
            tracing::warn!("Erreur de chargement de la config: {}. Utilisation de la config par défaut", e);
            Config::default()
        }
    };

    // Valider la configuration
    if let Err(e) = config.validate() {
        tracing::error!("Configuration invalide: {}", e);
        std::process::exit(1);
    }

    // Créer l'état de l'application
    let app_state = AppState {
        session_manager: Arc::new(Mutex::new(None)),
        config: Arc::new(config),
    };

    // Récupérer kiosk_mode avant de déplacer app_state
    let kiosk_mode = app_state.config.kiosk_mode;

    // Construire et lancer l'application Tauri
    tauri::Builder::default()
        .manage(app_state)
        .setup(move |app| {
            // Forcer le plein écran côté Rust (plus fiable que JavaScript)
            if kiosk_mode {
                if let Some(window) = app.get_webview_window("main") {
                    tracing::info!("Configuration mode kiosque (Rust-side)...");

                    // Désactiver les décorations d'abord
                    if let Err(e) = window.set_decorations(false) {
                        tracing::error!("Erreur set_decorations: {}", e);
                    }

                    // Toujours au premier plan
                    if let Err(e) = window.set_always_on_top(true) {
                        tracing::error!("Erreur set_always_on_top: {}", e);
                    }

                    // Maximiser d'abord (fonctionne mieux sur Wayland)
                    if let Err(e) = window.maximize() {
                        tracing::error!("Erreur maximize: {}", e);
                    }

                    // Puis forcer le plein écran
                    if let Err(e) = window.set_fullscreen(true) {
                        tracing::error!("Erreur set_fullscreen: {}", e);
                    }

                    // Focus sur la fenêtre
                    if let Err(e) = window.set_focus() {
                        tracing::error!("Erreur set_focus: {}", e);
                    }

                    tracing::info!("Mode kiosque configuré (Rust-side)");
                } else {
                    tracing::warn!("Fenêtre 'main' non trouvée pour le mode kiosque");
                }
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            initialize,
            validate_code,
            start_session,
            get_remaining_time,
            end_session,
            lock_screen,
            logout_user,
            show_notification,
            get_config,
            verify_admin_password,
        ])
        .run(tauri::generate_context!())
        .expect("Erreur lors du lancement de l'application Tauri");
}
