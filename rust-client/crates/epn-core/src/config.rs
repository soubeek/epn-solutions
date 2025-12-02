// Configuration du client EPN
use crate::types::{ClientError, Result};
use serde::{Deserialize, Serialize};
use std::env;
use std::fs;
use std::path::Path;

/// Configuration du client
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    /// URL du serveur API (ex: http://192.168.1.10:8001)
    pub server_url: String,

    /// URL WebSocket (ex: ws://192.168.1.10:8001)
    pub ws_url: String,

    /// Intervalle de vérification en secondes
    #[serde(default = "default_check_interval")]
    pub check_interval: u64,

    /// Temps d'avertissement en secondes (5 minutes)
    #[serde(default = "default_warning_time")]
    pub warning_time: u64,

    /// Temps critique en secondes (1 minute)
    #[serde(default = "default_critical_time")]
    pub critical_time: u64,

    /// Activer le verrouillage d'écran
    #[serde(default = "default_true")]
    pub enable_screen_lock: bool,

    /// Verrouiller à l'expiration
    #[serde(default = "default_true")]
    pub lock_on_expire: bool,

    /// Déconnecter à l'expiration
    #[serde(default = "default_false")]
    pub logout_on_expire: bool,

    /// Mode debug
    #[serde(default = "default_false")]
    pub debug: bool,

    /// Niveau de log
    #[serde(default = "default_log_level")]
    pub log_level: String,
}

// Valeurs par défaut
fn default_check_interval() -> u64 { 5 }
fn default_warning_time() -> u64 { 300 }
fn default_critical_time() -> u64 { 60 }
fn default_true() -> bool { true }
fn default_false() -> bool { false }
fn default_log_level() -> String { "info".to_string() }

impl Default for Config {
    fn default() -> Self {
        Self {
            server_url: "http://localhost:8001".to_string(),
            ws_url: "ws://localhost:8001".to_string(),
            check_interval: default_check_interval(),
            warning_time: default_warning_time(),
            critical_time: default_critical_time(),
            enable_screen_lock: default_true(),
            lock_on_expire: default_true(),
            logout_on_expire: default_false(),
            debug: default_false(),
            log_level: default_log_level(),
        }
    }
}

impl Config {
    /// Charger la configuration depuis les variables d'environnement
    pub fn from_env() -> Result<Self> {
        let server_url = env::var("EPN_SERVER_URL")
            .unwrap_or_else(|_| "http://localhost:8001".to_string());

        let ws_url = env::var("EPN_WS_URL")
            .unwrap_or_else(|_| server_url.replace("http", "ws"));

        let check_interval = env::var("EPN_CHECK_INTERVAL")
            .ok()
            .and_then(|s| s.parse().ok())
            .unwrap_or(default_check_interval());

        let warning_time = env::var("EPN_WARNING_TIME")
            .ok()
            .and_then(|s| s.parse().ok())
            .unwrap_or(default_warning_time());

        let critical_time = env::var("EPN_CRITICAL_TIME")
            .ok()
            .and_then(|s| s.parse().ok())
            .unwrap_or(default_critical_time());

        let enable_screen_lock = env::var("EPN_ENABLE_SCREEN_LOCK")
            .ok()
            .map(|s| s.to_lowercase() == "true")
            .unwrap_or(true);

        let lock_on_expire = env::var("EPN_LOCK_ON_EXPIRE")
            .ok()
            .map(|s| s.to_lowercase() == "true")
            .unwrap_or(true);

        let logout_on_expire = env::var("EPN_LOGOUT_ON_EXPIRE")
            .ok()
            .map(|s| s.to_lowercase() == "true")
            .unwrap_or(false);

        let debug = env::var("EPN_DEBUG")
            .ok()
            .map(|s| s.to_lowercase() == "true")
            .unwrap_or(false);

        let log_level = env::var("EPN_LOG_LEVEL")
            .unwrap_or_else(|_| default_log_level());

        Ok(Self {
            server_url,
            ws_url,
            check_interval,
            warning_time,
            critical_time,
            enable_screen_lock,
            lock_on_expire,
            logout_on_expire,
            debug,
            log_level,
        })
    }

    /// Charger la configuration depuis un fichier YAML
    pub fn from_file<P: AsRef<Path>>(path: P) -> Result<Self> {
        let contents = fs::read_to_string(path)
            .map_err(|e| ClientError::InvalidConfig(format!("Impossible de lire le fichier: {}", e)))?;

        serde_yaml::from_str(&contents)
            .map_err(|e| ClientError::InvalidConfig(format!("Format invalide: {}", e)))
    }

    /// Charger la configuration (fichier puis env)
    pub fn load() -> Result<Self> {
        // Essayer de charger depuis un fichier
        let config_paths = vec![
            "epn-config.yaml",
            "/etc/epn-client/config.yaml",
            #[cfg(target_os = "windows")]
            "C:\\ProgramData\\EPNClient\\config.yaml",
        ];

        for path in config_paths {
            if Path::new(path).exists() {
                tracing::info!("Chargement de la configuration depuis {}", path);
                return Self::from_file(path);
            }
        }

        // Sinon, charger depuis l'environnement
        tracing::info!("Chargement de la configuration depuis l'environnement");
        Self::from_env()
    }

    /// Obtenir l'URL WebSocket complète pour les sessions
    pub fn ws_sessions_url(&self) -> String {
        format!("{}/ws/sessions/", self.ws_url)
    }

    /// Valider la configuration
    pub fn validate(&self) -> Result<()> {
        if self.server_url.is_empty() {
            return Err(ClientError::InvalidConfig("server_url ne peut pas être vide".to_string()));
        }

        if self.ws_url.is_empty() {
            return Err(ClientError::InvalidConfig("ws_url ne peut pas être vide".to_string()));
        }

        if self.check_interval == 0 {
            return Err(ClientError::InvalidConfig("check_interval doit être > 0".to_string()));
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = Config::default();
        assert_eq!(config.server_url, "http://localhost:8001");
        assert_eq!(config.check_interval, 5);
        assert!(config.enable_screen_lock);
    }

    #[test]
    fn test_validate() {
        let config = Config::default();
        assert!(config.validate().is_ok());

        let mut invalid_config = Config::default();
        invalid_config.server_url = String::new();
        assert!(invalid_config.validate().is_err());
    }

    #[test]
    fn test_ws_sessions_url() {
        let config = Config::default();
        assert_eq!(config.ws_sessions_url(), "ws://localhost:8001/ws/sessions/");
    }
}
