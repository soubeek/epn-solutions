// EPN Core - Bibliothèque principale du client EPN
//!
//! Cette bibliothèque fournit la logique métier pour le client de gestion
//! des postes publics, incluant:
//! - Communication WebSocket avec le serveur Django
//! - Gestion des sessions utilisateur
//! - Configuration
//! - Types de données

pub mod config;
pub mod session;
pub mod types;
pub mod websocket;

// Réexporter les types principaux pour faciliter l'utilisation
pub use config::Config;
pub use session::SessionManager;
pub use types::{
    ClientError, ClientMessage, Result, ServerMessage, SessionInfo, SessionStatus, WarningLevel,
};
pub use websocket::WsClient;
