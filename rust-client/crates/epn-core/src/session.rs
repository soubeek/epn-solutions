// Gestionnaire de session
use crate::certificate::CertificateStore;
use crate::config::Config;
use crate::types::{ClientError, ClientMessage, Result, ServerMessage, SessionInfo, WarningLevel};
use crate::websocket::{TlsConfig, WsClient};
use tokio::time::{sleep, Duration};

/// Gestionnaire de session
pub struct SessionManager {
    ws_client: WsClient,
    current_session: Option<SessionInfo>,
    config: Config,
    mac_address: String,
    ip_address: String,
    is_registered: bool,
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

        Ok(Self {
            ws_client,
            current_session: None,
            config,
            mac_address,
            ip_address,
            is_registered,
        })
    }

    /// Vérifie si le client est enregistré auprès du serveur
    pub fn is_registered(&self) -> bool {
        self.is_registered
    }

    /// Valider un code d'accès
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
            Some(ServerMessage::CodeValid { session }) => {
                tracing::info!("✓ Code valide: session {}", session.id);
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
            Some(ServerMessage::SessionStarted { session: started }) => {
                tracing::info!("✓ Session démarrée: {}", started.id);
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

        loop {
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

                        // Si le temps est écoulé, terminer
                        if remaining == 0 {
                            tracing::info!("Session expirée");
                            break;
                        }
                    }
                }
                Err(ClientError::SessionExpired) => {
                    tracing::info!("Session terminée");
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
                        let r = reason.or(raison).unwrap_or_default();
                        let m = message.unwrap_or_default();
                        tracing::info!("Session terminée: {} - {}", r, m);
                        self.current_session = None;
                        return Ok(());
                    }
                    ServerMessage::TimeUpdate { remaining, .. } => {
                        if let Some(session) = &mut self.current_session {
                            session.remaining_time = remaining;
                        }
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
}
