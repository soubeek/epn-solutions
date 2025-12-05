// Gestionnaire de session
use crate::certificate::CertificateStore;
use crate::cleanup::CleanupManager;
use crate::config::Config;
use crate::gaming::GamingManager;
use crate::inactivity::{InactivityMonitor, InactivityState};
use crate::types::{ClientError, ClientMessage, RemoteCommandType, Result, ServerMessage, SessionInfo, WarningLevel};
use crate::websocket::{TlsConfig, WsClient};
use epn_system::{get_screen_locker, get_logout, get_notifier, Urgency};
use std::process::Command;
use tokio::time::{sleep, Duration};

/// Gestionnaire de session
pub struct SessionManager {
    ws_client: WsClient,
    current_session: Option<SessionInfo>,
    config: Config,
    mac_address: String,
    ip_address: String,
    is_registered: bool,
    inactivity_monitor: InactivityMonitor,
    gaming_manager: Option<GamingManager>,
}

impl SessionManager {
    /// Créer un nouveau gestionnaire de session
    pub async fn new(config: Config) -> Result<Self> {
        // Obtenir l'adresse MAC
        let mac_address = mac_address::get_mac_address()
            .map_err(|e| ClientError::Other(format!("Impossible d'obtenir l'adresse MAC: {}", e)))?
            .map(|addr| addr.to_string())
            .unwrap_or_else(|| "00:00:00:00:00:00".to_string());

        // Obtenir l'adresse IP
        let ip_address = local_ip_address::local_ip()
            .map(|ip| ip.to_string())
            .unwrap_or_else(|_| "127.0.0.1".to_string());

        tracing::info!("Adresse MAC: {}, IP: {}", mac_address, ip_address);

        // Vérifier si le client est enregistré (a des certificats)
        let cert_store = CertificateStore::new()?;
        let is_registered = cert_store.is_registered();

        // Construire l'URL WebSocket pour les clients
        let ws_url = format!("{}/ws/client/", config.ws_url);
        tracing::info!("Connexion WebSocket: {}", ws_url);

        // Connecter au serveur WebSocket
        let mut ws_client = if is_registered {
            // Utiliser mTLS si enregistré
            tracing::info!("Client enregistré, utilisation de mTLS");
            let tls_config = TlsConfig::from_store(&cert_store)?;
            WsClient::connect_with_tls(&ws_url, tls_config).await?
        } else {
            // Mode développement sans certificat
            tracing::warn!("Client non enregistré, connexion sans authentification");
            WsClient::connect(&ws_url).await?
        };

        // Consommer le message de connexion initial
        match ws_client.recv_timeout(Duration::from_secs(5)).await {
            Some(ServerMessage::ConnectionEstablished { message, poste_id, poste_nom }) => {
                tracing::info!(
                    "✓ Connexion établie: {:?}, poste_id: {:?}, poste_nom: {:?}",
                    message, poste_id, poste_nom
                );
            }
            Some(other) => {
                tracing::warn!("Message inattendu à la connexion: {:?}", other);
            }
            None => {
                tracing::warn!("Pas de message de connexion reçu");
            }
        }

        // Créer le moniteur d'inactivité
        let inactivity_config = config.inactivity_config();
        let inactivity_monitor = InactivityMonitor::new(inactivity_config);

        // Créer le gestionnaire gaming si c'est un poste gaming
        let gaming_manager = if config.is_gaming_poste() {
            let gaming_config = config.gaming_config();
            tracing::info!("Poste gaming détecté, initialisation du gestionnaire gaming");
            Some(GamingManager::new(gaming_config))
        } else {
            None
        };

        Ok(Self {
            ws_client,
            current_session: None,
            config,
            mac_address,
            ip_address,
            is_registered,
            inactivity_monitor,
            gaming_manager,
        })
    }

    /// Vérifie si le client est enregistré auprès du serveur
    pub fn is_registered(&self) -> bool {
        self.is_registered
    }

    /// Valider un code d'accès
    /// Gère à la fois les nouvelles sessions et les reconnexions (sessions actives)
    pub async fn validate_code(&mut self, code: &str) -> Result<SessionInfo> {
        tracing::info!("Validation du code: {}", code);

        // Envoyer la demande de validation
        self.ws_client.send(ClientMessage::ValidateCode {
            code: code.to_string(),
            ip_address: self.ip_address.clone(),
            mac_address: self.mac_address.clone(),
        })?;

        // Attendre la réponse (timeout 10 secondes)
        match self.ws_client.recv_timeout(Duration::from_secs(10)).await {
            Some(ServerMessage::CodeValid { session, is_reconnection }) => {
                if is_reconnection {
                    tracing::info!("✓ Reconnexion à session existante: {} ({}s restantes)",
                        session.id, session.remaining_time);
                } else {
                    tracing::info!("✓ Code valide: nouvelle session {}", session.id);
                }
                self.current_session = Some(session.clone());
                Ok(session)
            }
            Some(ServerMessage::CodeInvalid { message }) => {
                tracing::warn!("✗ Code invalide: {}", message);
                Err(ClientError::InvalidCode(message))
            }
            Some(ServerMessage::Error { message }) => {
                tracing::error!("Erreur serveur: {}", message);
                Err(ClientError::Other(message))
            }
            Some(other) => {
                let err_msg = format!("Réponse inattendue: {:?}", other);
                tracing::error!("{}", err_msg);
                Err(ClientError::Other(err_msg))
            }
            None => {
                let err_msg = "Timeout lors de la validation du code".to_string();
                tracing::error!("{}", err_msg);
                Err(ClientError::Connection(err_msg))
            }
        }
    }

    /// Démarrer une session
    /// Gère à la fois le démarrage initial et la reprise (reconnexion)
    pub async fn start_session(&mut self) -> Result<SessionInfo> {
        let session_id = self.current_session
            .as_ref()
            .ok_or(ClientError::SessionNotFound)?
            .id;

        tracing::info!("Démarrage de la session {}", session_id);

        // Envoyer la demande de démarrage
        self.ws_client.send(ClientMessage::StartSession { session_id })?;

        // Attendre la confirmation
        match self.ws_client.recv_timeout(Duration::from_secs(10)).await {
            Some(ServerMessage::SessionStarted { session: started, reconnected }) => {
                if reconnected {
                    tracing::info!("✓ Session reprise: {} ({}s restantes)",
                        started.id, started.remaining_time);
                } else {
                    tracing::info!("✓ Session démarrée: {}", started.id);

                    // Démarrer les launchers gaming au début d'une nouvelle session
                    if let Some(ref gaming) = self.gaming_manager {
                        tracing::info!("Démarrage des launchers gaming...");
                        gaming.start_session_launchers();
                    }
                }
                // Mettre à jour la session existante avec les nouvelles infos
                if let Some(session) = &mut self.current_session {
                    session.remaining_time = started.remaining_time;
                    session.status = started.status;
                }
                Ok(self.current_session.clone().ok_or(ClientError::SessionNotFound)?)
            }
            Some(ServerMessage::Error { message }) => {
                tracing::error!("Erreur serveur: {}", message);
                Err(ClientError::Other(message))
            }
            Some(other) => {
                let err_msg = format!("Réponse inattendue: {:?}", other);
                tracing::error!("{}", err_msg);
                Err(ClientError::Other(err_msg))
            }
            None => {
                let err_msg = "Timeout lors du démarrage de la session".to_string();
                tracing::error!("{}", err_msg);
                Err(ClientError::Connection(err_msg))
            }
        }
    }

    /// Obtenir le temps restant
    pub async fn get_remaining_time(&mut self) -> Result<u64> {
        let session_id = self.current_session
            .as_ref()
            .ok_or(ClientError::SessionNotFound)?
            .id;

        // Envoyer la demande de temps
        self.ws_client.send(ClientMessage::GetTime { session_id })?;

        // Boucle pour attendre la réponse correcte (évite la récursion async)
        loop {
            match self.ws_client.recv_timeout(Duration::from_secs(5)).await {
                Some(ServerMessage::TimeUpdate { remaining, .. }) => {
                    // Mettre à jour la session
                    if let Some(session) = &mut self.current_session {
                        session.remaining_time = remaining;
                    }
                    return Ok(remaining);
                }
                Some(ServerMessage::SessionTerminated { reason, message, raison, .. }) => {
                    let r = reason.or(raison).unwrap_or_default();
                    let m = message.unwrap_or_default();
                    tracing::warn!("Session terminée: {} - {}", r, m);
                    self.current_session = None;
                    return Err(ClientError::SessionExpired);
                }
                Some(other) => {
                    // Ignorer les autres messages et attendre le prochain
                    tracing::debug!("Message ignoré en attente de TimeUpdate: {:?}", other);
                    continue;
                }
                None => {
                    return Err(ClientError::Connection("Timeout lors de la demande de temps".to_string()));
                }
            }
        }
    }

    /// Surveiller la session et appeler un callback pour chaque mise à jour
    pub async fn monitor_session<F>(&mut self, mut callback: F) -> Result<()>
    where
        F: FnMut(&SessionInfo, Option<WarningLevel>),
    {
        let check_interval = Duration::from_secs(self.config.check_interval);
        let notifier = get_notifier();

        loop {
            // Vérifier l'inactivité
            match self.inactivity_monitor.check() {
                InactivityState::Timeout => {
                    tracing::warn!("Session terminée pour inactivité");
                    self.handle_session_end("Inactivité prolongée").await;
                    break;
                }
                InactivityState::Warning => {
                    if !self.inactivity_monitor.is_warning_shown() {
                        let time_left = self.inactivity_monitor.time_until_timeout();
                        tracing::warn!("Avertissement d'inactivité: {}s restantes", time_left);

                        // Afficher une notification d'avertissement
                        let msg = format!(
                            "Êtes-vous toujours là ? Bougez la souris ou appuyez sur une touche. \
                            La session se terminera dans {}s.",
                            time_left
                        );
                        if let Err(e) = notifier.show("Inactivité détectée", &msg, epn_system::Urgency::Normal) {
                            tracing::warn!("Impossible d'afficher la notification d'inactivité: {}", e);
                        }
                        self.inactivity_monitor.mark_warning_shown();
                    }
                }
                InactivityState::Active => {
                    // Rien à faire, l'utilisateur est actif
                }
            }

            // Demander le temps restant
            match self.get_remaining_time().await {
                Ok(remaining) => {
                    if let Some(session) = &self.current_session {
                        // Déterminer le niveau d'avertissement
                        let warning_level = if remaining <= self.config.critical_time {
                            Some(WarningLevel::Critical)
                        } else if remaining <= self.config.warning_time {
                            Some(WarningLevel::Warning)
                        } else {
                            None
                        };

                        // Appeler le callback
                        callback(session, warning_level);

                        // Si le temps est écoulé, exécuter les actions de fin
                        if remaining == 0 {
                            tracing::info!("Session expirée");
                            self.handle_session_end("Temps écoulé").await;
                            break;
                        }
                    }
                }
                Err(ClientError::SessionExpired) => {
                    tracing::info!("Session terminée (expirée)");
                    self.handle_session_end("Session expirée").await;
                    break;
                }
                Err(e) => {
                    tracing::error!("Erreur lors de la surveillance: {}", e);
                    // Continuer malgré l'erreur
                }
            }

            // Vérifier les messages du serveur
            while let Some(msg) = self.ws_client.recv_timeout(Duration::from_millis(100)).await {
                match msg {
                    ServerMessage::Warning { level, message, remaining } => {
                        tracing::warn!("[{}] {} ({}s restantes)", level, message, remaining);
                        if let Some(session) = &mut self.current_session {
                            session.remaining_time = remaining;
                            callback(session, Some(level));
                        }
                    }
                    ServerMessage::SessionTerminated { reason, message, raison, .. } => {
                        let r = reason.or(raison).unwrap_or_else(|| "Fin de session".to_string());
                        let m = message.unwrap_or_default();
                        tracing::info!("Session terminée: {} - {}", r, m);
                        self.handle_session_end(&r).await;
                        self.current_session = None;
                        return Ok(());
                    }
                    ServerMessage::TimeUpdate { remaining, .. } => {
                        if let Some(session) = &mut self.current_session {
                            session.remaining_time = remaining;
                        }
                    }
                    ServerMessage::RemoteCommand { command, payload } => {
                        tracing::info!("Commande à distance reçue: {:?}", command);
                        self.handle_remote_command(command, payload).await;
                    }
                    ServerMessage::ExtensionResponse { approved, minutes, new_remaining, message } => {
                        self.handle_extension_response(approved, minutes, new_remaining, message).await;
                    }
                    _ => {}
                }
            }

            // Attendre avant la prochaine vérification
            sleep(check_interval).await;
        }

        Ok(())
    }

    /// Obtenir la session actuelle
    pub fn current_session(&self) -> Option<&SessionInfo> {
        self.current_session.as_ref()
    }

    /// Envoyer un heartbeat
    pub fn send_heartbeat(&mut self) -> Result<()> {
        self.ws_client.send(ClientMessage::Heartbeat)
    }

    /// Demander une prolongation de session
    pub fn request_extension(&mut self, minutes: u64) -> Result<()> {
        let session_id = self.current_session
            .as_ref()
            .ok_or(ClientError::SessionNotFound)?
            .id;

        tracing::info!("Demande de prolongation de {} minutes pour la session {}", minutes, session_id);

        self.ws_client.send(ClientMessage::RequestExtension {
            session_id,
            minutes,
        })
    }

    /// Gérer la réponse à une demande de prolongation
    async fn handle_extension_response(
        &mut self,
        approved: bool,
        minutes: u64,
        new_remaining: Option<u64>,
        message: Option<String>,
    ) {
        let notifier = get_notifier();

        if approved {
            tracing::info!("Prolongation approuvée: {} minutes", minutes);

            // Mettre à jour le temps restant si fourni
            if let Some(remaining) = new_remaining {
                if let Some(session) = &mut self.current_session {
                    session.remaining_time = remaining;
                }
            }

            // Réinitialiser le moniteur d'inactivité après une prolongation
            self.inactivity_monitor.reset();

            let msg = message.unwrap_or_else(|| format!("{} minutes ajoutées à votre session", minutes));
            let _ = notifier.show("Prolongation accordée", &msg, Urgency::Normal);
        } else {
            tracing::info!("Prolongation refusée");
            let msg = message.unwrap_or_else(|| "Votre demande de prolongation a été refusée".to_string());
            let _ = notifier.show("Prolongation refusée", &msg, Urgency::Normal);
        }
    }

    /// Gérer une commande à distance
    pub async fn handle_remote_command(&mut self, command: RemoteCommandType, payload: Option<String>) {
        let notifier = get_notifier();
        let command_name = format!("{:?}", command);
        let mut success = true;
        let mut error_msg: Option<String> = None;

        match command {
            RemoteCommandType::Lock => {
                tracing::info!("Commande à distance: Verrouillage de l'écran");
                let locker = get_screen_locker();
                if let Err(e) = locker.lock() {
                    tracing::error!("Impossible de verrouiller l'écran: {}", e);
                    success = false;
                    error_msg = Some(e.to_string());
                }
            }
            RemoteCommandType::Message => {
                if let Some(msg) = payload {
                    tracing::info!("Commande à distance: Message - {}", msg);
                    if let Err(e) = notifier.show("Message de l'administrateur", &msg, Urgency::Normal) {
                        tracing::warn!("Impossible d'afficher le message: {}", e);
                        success = false;
                        error_msg = Some(e.to_string());
                    }
                } else {
                    tracing::warn!("Commande Message sans payload");
                    success = false;
                    error_msg = Some("Aucun message fourni".to_string());
                }
            }
            RemoteCommandType::Shutdown => {
                tracing::info!("Commande à distance: Extinction du poste");
                // Notifier l'utilisateur
                let _ = notifier.show(
                    "Extinction imminente",
                    "L'administrateur a demandé l'extinction du poste. Le système va s'éteindre dans 30 secondes.",
                    Urgency::Critical
                );

                // Attendre un peu avant l'extinction
                sleep(Duration::from_secs(5)).await;

                #[cfg(target_os = "linux")]
                {
                    match Command::new("systemctl").arg("poweroff").output() {
                        Ok(_) => {}
                        Err(e) => {
                            tracing::error!("Impossible d'éteindre le système: {}", e);
                            success = false;
                            error_msg = Some(e.to_string());
                        }
                    }
                }

                #[cfg(target_os = "windows")]
                {
                    match Command::new("shutdown").args(["/s", "/t", "30", "/c", "Extinction demandée par l'administrateur"]).output() {
                        Ok(_) => {}
                        Err(e) => {
                            tracing::error!("Impossible d'éteindre le système: {}", e);
                            success = false;
                            error_msg = Some(e.to_string());
                        }
                    }
                }
            }
            RemoteCommandType::Restart => {
                tracing::info!("Commande à distance: Redémarrage du poste");
                // Notifier l'utilisateur
                let _ = notifier.show(
                    "Redémarrage imminent",
                    "L'administrateur a demandé le redémarrage du poste. Le système va redémarrer dans 30 secondes.",
                    Urgency::Critical
                );

                // Attendre un peu avant le redémarrage
                sleep(Duration::from_secs(5)).await;

                #[cfg(target_os = "linux")]
                {
                    match Command::new("systemctl").arg("reboot").output() {
                        Ok(_) => {}
                        Err(e) => {
                            tracing::error!("Impossible de redémarrer le système: {}", e);
                            success = false;
                            error_msg = Some(e.to_string());
                        }
                    }
                }

                #[cfg(target_os = "windows")]
                {
                    match Command::new("shutdown").args(["/r", "/t", "30", "/c", "Redémarrage demandé par l'administrateur"]).output() {
                        Ok(_) => {}
                        Err(e) => {
                            tracing::error!("Impossible de redémarrer le système: {}", e);
                            success = false;
                            error_msg = Some(e.to_string());
                        }
                    }
                }
            }
        }

        // Envoyer l'acquittement au serveur
        let _ = self.ws_client.send(ClientMessage::CommandAck {
            command: command_name,
            success,
            error: error_msg,
        });
    }

    /// Exécute les actions de fin de session
    ///
    /// 1. Affiche une notification critique
    /// 2. Exécute le nettoyage automatique (si configuré)
    /// 3. Exécute les scripts de nettoyage personnalisés
    /// 4. Attend le délai configuré (pour laisser le temps de lire)
    /// 5. Verrouille l'écran (si configuré)
    /// 6. Déconnecte l'utilisateur (si configuré)
    pub async fn handle_session_end(&self, reason: &str) {
        tracing::info!("=== Fin de session: {} ===", reason);

        // 1. Notification critique
        let notifier = get_notifier();
        let notification_msg = if self.config.lock_on_expire {
            format!("{}. L'écran va se verrouiller.", reason)
        } else {
            reason.to_string()
        };

        if let Err(e) = notifier.show("Session terminée", &notification_msg, Urgency::Critical) {
            tracing::warn!("Impossible d'afficher la notification: {}", e);
        }

        // 2. Arrêter les launchers gaming et fermer les jeux
        if let Some(ref gaming) = self.gaming_manager {
            tracing::info!("Arrêt des launchers gaming et des jeux...");
            gaming.end_session_launchers();

            // Déconnecter les utilisateurs des launchers
            tracing::info!("Déconnexion des comptes des launchers...");
            gaming.logout_all_launchers();
        }

        // 3. Nettoyage automatique (si activé)
        if self.config.enable_cleanup {
            tracing::info!("Exécution du nettoyage automatique...");
            let cleanup_config = self.config.cleanup_config();
            let cleanup_manager = CleanupManager::new(cleanup_config);
            let result = cleanup_manager.run_cleanup();

            tracing::info!(
                "Nettoyage terminé: {} fichiers, {} dossiers supprimés, {} octets libérés",
                result.files_deleted,
                result.dirs_deleted,
                result.bytes_freed
            );

            if !result.errors.is_empty() {
                tracing::warn!("Erreurs de nettoyage: {:?}", result.errors);
            }
        }

        // 4. Exécuter les scripts de nettoyage personnalisés
        for script in &self.config.cleanup_scripts {
            tracing::info!("Exécution du script de nettoyage: {}", script);
            match Command::new("sh")
                .arg("-c")
                .arg(script)
                .output()
            {
                Ok(output) => {
                    if output.status.success() {
                        tracing::info!("Script {} exécuté avec succès", script);
                    } else {
                        let stderr = String::from_utf8_lossy(&output.stderr);
                        tracing::warn!("Script {} a échoué: {}", script, stderr);
                    }
                }
                Err(e) => {
                    tracing::error!("Impossible d'exécuter le script {}: {}", script, e);
                }
            }
        }

        // 5. Attendre le délai configuré
        if self.config.lock_delay_secs > 0 {
            tracing::info!("Attente de {} secondes avant verrouillage...", self.config.lock_delay_secs);
            sleep(Duration::from_secs(self.config.lock_delay_secs)).await;
        }

        // 6. Verrouiller l'écran si configuré
        if self.config.lock_on_expire {
            tracing::info!("Verrouillage de l'écran...");
            let locker = get_screen_locker();
            if let Err(e) = locker.lock() {
                tracing::error!("Impossible de verrouiller l'écran: {}", e);
            }
        }

        // 7. Déconnecter l'utilisateur si configuré
        if self.config.logout_on_expire {
            tracing::info!("Déconnexion de l'utilisateur...");
            let logout = get_logout();
            if let Err(e) = logout.logout() {
                tracing::error!("Impossible de déconnecter l'utilisateur: {}", e);
            }
        }
    }
}
