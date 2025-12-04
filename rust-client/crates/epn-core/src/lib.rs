// EPN Core - Bibliothèque principale du client EPN
//!
//! Cette bibliothèque fournit la logique métier pour le client de gestion
//! des postes publics, incluant:
//! - Communication WebSocket avec le serveur Django
//! - Gestion des sessions utilisateur
//! - Configuration
//! - Types de données
//! - Gestion des certificats mTLS
//! - Enregistrement du client

pub mod certificate;
pub mod config;
pub mod registration;
pub mod session;
pub mod types;
pub mod websocket;

// Réexporter les types principaux pour faciliter l'utilisation
pub use certificate::{CertificateStore, ClientCertificates};
pub use config::Config;
pub use registration::{RegistrationClient, RegistrationStatus};
pub use session::SessionManager;
pub use types::{
    ClientError, ClientMessage, Result, ServerMessage, SessionInfo, SessionStatus, WarningLevel,
};
pub use websocket::{TlsConfig, WsClient};
