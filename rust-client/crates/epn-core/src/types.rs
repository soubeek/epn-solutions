// Types de données pour le client EPN
use serde::{Deserialize, Serialize};
use std::fmt;

/// Informations sur une session utilisateur (format code_valid)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionInfo {
    pub id: u64,
    #[serde(rename = "code_acces")]
    pub code: String,
    #[serde(rename = "utilisateur")]
    pub user_name: String,
    #[serde(rename = "poste")]
    pub workstation: String,
    #[serde(rename = "duree_initiale")]
    pub total_duration: u64,      // Durée totale en secondes
    #[serde(rename = "temps_restant")]
    pub remaining_time: u64,      // Temps restant en secondes
    #[serde(rename = "statut")]
    pub status: SessionStatus,
}

/// Informations de session démarrée (format session_started)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StartedSessionInfo {
    pub id: u64,
    #[serde(rename = "code_acces")]
    pub code: String,
    #[serde(rename = "temps_restant")]
    pub remaining_time: u64,
    #[serde(rename = "statut")]
    pub status: SessionStatus,
    #[serde(rename = "debut_session")]
    pub start_time: String,
}

/// Statut d'une session
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum SessionStatus {
    #[serde(rename = "en_attente")]
    Pending,
    #[serde(rename = "active")]
    Active,
    #[serde(rename = "expiree")]
    Expired,
    #[serde(rename = "terminee")]
    Terminated,
}

impl fmt::Display for SessionStatus {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            SessionStatus::Pending => write!(f, "En attente"),
            SessionStatus::Active => write!(f, "Active"),
            SessionStatus::Expired => write!(f, "Expirée"),
            SessionStatus::Terminated => write!(f, "Terminée"),
        }
    }
}

/// Messages envoyés par le client au serveur
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ClientMessage {
    /// Valider un code d'accès
    ValidateCode {
        code: String,
        ip_address: String,
        mac_address: String,
    },
    /// Démarrer une session
    StartSession {
        session_id: u64,
    },
    /// Demander le temps restant
    GetTime {
        session_id: u64,
    },
    /// Heartbeat pour maintenir la connexion
    Heartbeat,
}

/// Messages reçus du serveur
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ServerMessage {
    /// Connexion établie (envoyé à la connexion WebSocket)
    ConnectionEstablished {
        #[serde(default)]
        message: Option<String>,
        #[serde(default)]
        poste_id: Option<u64>,
        #[serde(default)]
        poste_nom: Option<String>,
    },
    /// Réponse au heartbeat
    HeartbeatAck,
    /// Code valide avec informations de session
    CodeValid {
        session: SessionInfo,
    },
    /// Code invalide
    CodeInvalid {
        message: String,
    },
    /// Session démarrée
    SessionStarted {
        session: StartedSessionInfo,
    },
    /// Mise à jour du temps
    TimeUpdate {
        #[serde(default)]
        session_id: Option<u64>,
        #[serde(rename = "temps_restant")]
        remaining: u64,
        #[serde(rename = "temps_restant_minutes", default)]
        remaining_minutes: Option<u64>,
        #[serde(rename = "pourcentage_utilise", default)]
        percentage: Option<f32>,
        #[serde(rename = "statut", default)]
        status: Option<SessionStatus>,
    },
    /// Session terminée
    SessionTerminated {
        #[serde(default)]
        reason: Option<String>,
        #[serde(default)]
        message: Option<String>,
        #[serde(default)]
        session_id: Option<u64>,
        #[serde(default)]
        raison: Option<String>,
    },
    /// Avertissement de temps
    Warning {
        level: WarningLevel,
        message: String,
        remaining: u64,
    },
    /// Erreur
    Error {
        message: String,
    },
}

/// Niveau d'avertissement
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum WarningLevel {
    Info,
    Warning,
    Critical,
}

impl fmt::Display for WarningLevel {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            WarningLevel::Info => write!(f, "Info"),
            WarningLevel::Warning => write!(f, "Avertissement"),
            WarningLevel::Critical => write!(f, "Critique"),
        }
    }
}

/// Erreurs du client
#[derive(Debug, thiserror::Error)]
pub enum ClientError {
    #[error("Erreur WebSocket: {0}")]
    WebSocket(String),

    #[error("Erreur de connexion: {0}")]
    Connection(String),

    #[error("Erreur de sérialisation: {0}")]
    Serialization(#[from] serde_json::Error),

    #[error("Code invalide: {0}")]
    InvalidCode(String),

    #[error("Session non trouvée")]
    SessionNotFound,

    #[error("Session expirée")]
    SessionExpired,

    #[error("Configuration invalide: {0}")]
    InvalidConfig(String),

    #[error("Erreur IO: {0}")]
    Io(#[from] std::io::Error),

    #[error("Erreur: {0}")]
    Other(String),
}

pub type Result<T> = std::result::Result<T, ClientError>;
