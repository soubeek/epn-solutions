//! Service Windows EPN Client
//!
//! Ce service gère le cycle de vie de l'application EPN Client sur Windows:
//! - Démarre automatiquement au boot
//! - Lance epn-gui.exe quand un utilisateur se connecte
//! - Surveille et relance l'application si elle se ferme
//! - Gère les événements système (shutdown, session change)

#[cfg(windows)]
mod service;

#[cfg(windows)]
fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialiser le logging vers fichier
    let log_dir = std::path::PathBuf::from("C:/ProgramData/EPNClient/logs");
    std::fs::create_dir_all(&log_dir).ok();

    let log_file = std::fs::File::create(log_dir.join("service.log"))?;

    tracing_subscriber::fmt()
        .with_writer(log_file)
        .with_ansi(false)
        .init();

    tracing::info!("Démarrage du service EPN...");

    // Lancer le service Windows
    service::run()
}

#[cfg(not(windows))]
fn main() {
    eprintln!("epn-service est uniquement disponible sur Windows.");
    eprintln!("Sur Linux, utilisez l'autostart GNOME ou systemd.");
    std::process::exit(1);
}

// ============================================================================
// Module service (Windows uniquement)
// ============================================================================

#[cfg(windows)]
mod service {
    use std::ffi::OsString;
    use std::path::PathBuf;
    use std::process::{Child, Command};
    use std::sync::atomic::{AtomicBool, Ordering};
    use std::sync::Arc;
    use std::time::Duration;

    use tracing::{info, warn, error};
    use windows_service::{
        define_windows_service,
        service::{
            ServiceControl, ServiceControlAccept, ServiceExitCode, ServiceState,
            ServiceStatus, ServiceType,
        },
        service_control_handler::{self, ServiceControlHandlerResult},
        service_dispatcher,
    };

    const SERVICE_NAME: &str = "EPNClient";
    const SERVICE_TYPE: ServiceType = ServiceType::OWN_PROCESS;

    /// Point d'entrée du service
    pub fn run() -> Result<(), Box<dyn std::error::Error>> {
        // Dispatcher vers le service Windows
        service_dispatcher::start(SERVICE_NAME, ffi_service_main)?;
        Ok(())
    }

    // Macro pour définir le point d'entrée FFI du service
    define_windows_service!(ffi_service_main, service_main);

    /// Fonction principale du service
    fn service_main(_arguments: Vec<OsString>) {
        if let Err(e) = run_service() {
            error!("Erreur du service: {}", e);
        }
    }

    /// Logique principale du service
    fn run_service() -> Result<(), Box<dyn std::error::Error>> {
        let running = Arc::new(AtomicBool::new(true));
        let running_clone = running.clone();

        // Handler pour les commandes du service (Stop, Shutdown, etc.)
        let event_handler = move |control_event| -> ServiceControlHandlerResult {
            match control_event {
                ServiceControl::Stop | ServiceControl::Shutdown => {
                    info!("Arrêt du service demandé");
                    running_clone.store(false, Ordering::SeqCst);
                    ServiceControlHandlerResult::NoError
                }
                ServiceControl::Interrogate => ServiceControlHandlerResult::NoError,
                ServiceControl::SessionChange(session_event) => {
                    info!("Événement de session: {:?}", session_event);
                    ServiceControlHandlerResult::NoError
                }
                _ => ServiceControlHandlerResult::NotImplemented,
            }
        };

        // Enregistrer le handler
        let status_handle = service_control_handler::register(SERVICE_NAME, event_handler)?;

        // Signaler que le service démarre
        status_handle.set_service_status(ServiceStatus {
            service_type: SERVICE_TYPE,
            current_state: ServiceState::StartPending,
            controls_accepted: ServiceControlAccept::empty(),
            exit_code: ServiceExitCode::Win32(0),
            checkpoint: 0,
            wait_hint: Duration::from_secs(10),
            process_id: None,
        })?;

        // Signaler que le service est en cours d'exécution
        status_handle.set_service_status(ServiceStatus {
            service_type: SERVICE_TYPE,
            current_state: ServiceState::Running,
            controls_accepted: ServiceControlAccept::STOP | ServiceControlAccept::SHUTDOWN,
            exit_code: ServiceExitCode::Win32(0),
            checkpoint: 0,
            wait_hint: Duration::default(),
            process_id: None,
        })?;

        info!("Service EPN démarré");

        // Chemin vers l'application GUI
        let gui_path = PathBuf::from("C:/Program Files/EPNClient/epn-gui.exe");
        let mut child_process: Option<Child> = None;

        // Boucle principale du service
        while running.load(Ordering::SeqCst) {
            // Vérifier si l'application GUI tourne
            let gui_running = match &mut child_process {
                Some(child) => {
                    match child.try_wait() {
                        Ok(Some(status)) => {
                            info!("epn-gui s'est terminé avec le code: {:?}", status);
                            false
                        }
                        Ok(None) => true, // Toujours en cours
                        Err(e) => {
                            warn!("Erreur lors de la vérification de epn-gui: {}", e);
                            false
                        }
                    }
                }
                None => false,
            };

            // Relancer si nécessaire
            if !gui_running && gui_path.exists() {
                info!("Lancement de epn-gui...");
                match Command::new(&gui_path).spawn() {
                    Ok(child) => {
                        info!("epn-gui lancé (PID: {})", child.id());
                        child_process = Some(child);
                    }
                    Err(e) => {
                        error!("Impossible de lancer epn-gui: {}", e);
                    }
                }
            }

            // Attendre avant la prochaine vérification
            std::thread::sleep(Duration::from_secs(5));
        }

        // Arrêter l'application GUI si elle tourne
        if let Some(mut child) = child_process {
            info!("Arrêt de epn-gui...");
            let _ = child.kill();
        }

        // Signaler que le service s'arrête
        status_handle.set_service_status(ServiceStatus {
            service_type: SERVICE_TYPE,
            current_state: ServiceState::Stopped,
            controls_accepted: ServiceControlAccept::empty(),
            exit_code: ServiceExitCode::Win32(0),
            checkpoint: 0,
            wait_hint: Duration::default(),
            process_id: None,
        })?;

        info!("Service EPN arrêté");
        Ok(())
    }
}
