// Types de données pour le client EPN
use serde::{Deserialize, Serialize};
use std::fmt;

/// Informations sur une session utilisateur
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionInfo {
    pub id: u64,
    pub code: String,
    pub user_name: String,
    pub workstation: String,
    pub total_duration: u64,      // Durée totale en secondes
    pub remaining_time: u64,      // Temps restant en secondes
    pub status: SessionStatus,
}

/// Statut d'une session
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum SessionStatus {
    Pending,
    Active,
    Expired,
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
        session: SessionInfo,
    },
    /// Mise à jour du temps
    TimeUpdate {
        remaining: u64,
        percentage: f32,
    },
    /// Session terminée
    SessionTerminated {
        reason: String,
        message: String,
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
