// Configuration du client EPN
use crate::cleanup::{CleanupConfig, PosteType};
use crate::gaming::{GameLauncher, GamingConfig};
use crate::inactivity::InactivityConfig;
use crate::types::{ClientError, Result};
use serde::{Deserialize, Serialize};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

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

    /// Délai avant verrouillage (secondes) - permet à l'utilisateur de lire la notification
    #[serde(default = "default_lock_delay")]
    pub lock_delay_secs: u64,

    /// Scripts à exécuter en fin de session (nettoyage)
    #[serde(default)]
    pub cleanup_scripts: Vec<String>,

    /// Mode debug
    #[serde(default = "default_false")]
    pub debug: bool,

    /// Niveau de log
    #[serde(default = "default_log_level")]
    pub log_level: String,

    /// Token de découverte (pour l'auto-enregistrement)
    #[serde(default)]
    pub discovery_token: Option<String>,

    /// Intervalle de polling pour vérifier la validation (secondes)
    #[serde(default = "default_discovery_poll_interval")]
    pub discovery_poll_interval: u64,

    /// Temps maximum d'attente de validation (secondes) - 24h par défaut
    #[serde(default = "default_discovery_max_wait")]
    pub discovery_max_wait: u64,

    /// Type de poste (bureautique ou gaming)
    #[serde(default = "default_poste_type")]
    pub poste_type: String,

    /// Activer le nettoyage automatique en fin de session
    #[serde(default = "default_true")]
    pub enable_cleanup: bool,

    /// Nettoyer Firefox en fin de session
    #[serde(default = "default_true")]
    pub cleanup_firefox: bool,

    /// Nettoyer LibreOffice en fin de session
    #[serde(default = "default_true")]
    pub cleanup_libreoffice: bool,

    /// Nettoyer les documents utilisateur en fin de session
    #[serde(default = "default_true")]
    pub cleanup_user_documents: bool,

    /// Nettoyer l'historique système en fin de session
    #[serde(default = "default_true")]
    pub cleanup_system_history: bool,

    /// Nettoyer les launchers gaming (Steam, Epic, etc.) en fin de session
    #[serde(default = "default_false")]
    pub cleanup_gaming_launchers: bool,

    /// Chemins personnalisés à nettoyer
    #[serde(default)]
    pub cleanup_custom_paths: Vec<String>,

    /// Patterns à exclure du nettoyage
    #[serde(default)]
    pub cleanup_exclude_patterns: Vec<String>,

    /// Activer la surveillance d'inactivité
    #[serde(default = "default_true")]
    pub inactivity_enabled: bool,

    /// Temps avant avertissement d'inactivité (secondes)
    #[serde(default = "default_inactivity_warning")]
    pub inactivity_warning_secs: u64,

    /// Temps avant fin de session pour inactivité (secondes)
    #[serde(default = "default_inactivity_timeout")]
    pub inactivity_timeout_secs: u64,

    // ==================== Configuration Gaming ====================

    /// Activer les fonctionnalités gaming (pour postes type "gaming")
    #[serde(default = "default_false")]
    pub gaming_enabled: bool,

    /// Launchers à démarrer automatiquement (ex: ["steam", "epic"])
    #[serde(default)]
    pub gaming_auto_start_launchers: Vec<String>,

    /// Fermer les launchers en fin de session
    #[serde(default = "default_true")]
    pub gaming_close_on_end: bool,

    /// Fermer tous les jeux en cours en fin de session
    #[serde(default = "default_true")]
    pub gaming_close_games_on_end: bool,

    /// Démarrer Steam en mode Big Picture
    #[serde(default = "default_false")]
    pub gaming_steam_big_picture: bool,

    /// Chemin personnalisé vers Steam
    #[serde(default)]
    pub gaming_steam_path: Option<String>,

    /// Chemin personnalisé vers Epic Games
    #[serde(default)]
    pub gaming_epic_path: Option<String>,

    /// Chemin personnalisé vers GOG Galaxy
    #[serde(default)]
    pub gaming_gog_path: Option<String>,

    // ==================== Configuration Mode Kiosque ====================

    /// Activer le mode kiosque (plein écran, pas de fermeture possible)
    #[serde(default = "default_true")]
    pub kiosk_mode: bool,

    /// Mot de passe admin pour déverrouiller le mode kiosque (Ctrl+Alt+Shift+K)
    #[serde(default)]
    pub kiosk_admin_password: Option<String>,
}

// Valeurs par défaut
fn default_check_interval() -> u64 { 5 }
fn default_warning_time() -> u64 { 300 }
fn default_critical_time() -> u64 { 60 }
fn default_true() -> bool { true }
fn default_false() -> bool { false }
fn default_log_level() -> String { "info".to_string() }
fn default_discovery_poll_interval() -> u64 { 30 }  // 30 secondes
fn default_discovery_max_wait() -> u64 { 86400 }    // 24 heures
fn default_lock_delay() -> u64 { 5 }                 // 5 secondes avant verrouillage
fn default_poste_type() -> String { "bureautique".to_string() }
fn default_inactivity_warning() -> u64 { 300 }       // 5 minutes avant avertissement
fn default_inactivity_timeout() -> u64 { 600 }       // 10 minutes avant fin de session

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
            lock_delay_secs: default_lock_delay(),
            cleanup_scripts: Vec::new(),
            debug: default_false(),
            log_level: default_log_level(),
            discovery_token: None,
            discovery_poll_interval: default_discovery_poll_interval(),
            discovery_max_wait: default_discovery_max_wait(),
            poste_type: default_poste_type(),
            enable_cleanup: default_true(),
            cleanup_firefox: default_true(),
            cleanup_libreoffice: default_true(),
            cleanup_user_documents: default_true(),
            cleanup_system_history: default_true(),
            cleanup_gaming_launchers: default_false(),
            cleanup_custom_paths: Vec::new(),
            cleanup_exclude_patterns: Vec::new(),
            inactivity_enabled: default_true(),
            inactivity_warning_secs: default_inactivity_warning(),
            inactivity_timeout_secs: default_inactivity_timeout(),
            // Gaming
            gaming_enabled: default_false(),
            gaming_auto_start_launchers: Vec::new(),
            gaming_close_on_end: default_true(),
            gaming_close_games_on_end: default_true(),
            gaming_steam_big_picture: default_false(),
            gaming_steam_path: None,
            gaming_epic_path: None,
            gaming_gog_path: None,
            // Kiosk
            kiosk_mode: default_true(),
            kiosk_admin_password: None,
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

        let lock_delay_secs = env::var("EPN_LOCK_DELAY")
            .ok()
            .and_then(|s| s.parse().ok())
            .unwrap_or(default_lock_delay());

        let cleanup_scripts = env::var("EPN_CLEANUP_SCRIPTS")
            .ok()
            .map(|s| s.split(':').map(|p| p.to_string()).collect())
            .unwrap_or_default();

        let debug = env::var("EPN_DEBUG")
            .ok()
            .map(|s| s.to_lowercase() == "true")
            .unwrap_or(false);

        let log_level = env::var("EPN_LOG_LEVEL")
            .unwrap_or_else(|_| default_log_level());

        let discovery_token = env::var("EPN_DISCOVERY_TOKEN").ok();

        let discovery_poll_interval = env::var("EPN_DISCOVERY_POLL_INTERVAL")
            .ok()
            .and_then(|s| s.parse().ok())
            .unwrap_or(default_discovery_poll_interval());

        let discovery_max_wait = env::var("EPN_DISCOVERY_MAX_WAIT")
            .ok()
            .and_then(|s| s.parse().ok())
            .unwrap_or(default_discovery_max_wait());

        let poste_type = env::var("EPN_POSTE_TYPE")
            .unwrap_or_else(|_| default_poste_type());

        let enable_cleanup = env::var("EPN_ENABLE_CLEANUP")
            .ok()
            .map(|s| s.to_lowercase() == "true")
            .unwrap_or(true);

        let cleanup_firefox = env::var("EPN_CLEANUP_FIREFOX")
            .ok()
            .map(|s| s.to_lowercase() == "true")
            .unwrap_or(true);

        let cleanup_libreoffice = env::var("EPN_CLEANUP_LIBREOFFICE")
            .ok()
            .map(|s| s.to_lowercase() == "true")
            .unwrap_or(true);

        let cleanup_user_documents = env::var("EPN_CLEANUP_USER_DOCUMENTS")
            .ok()
            .map(|s| s.to_lowercase() == "true")
            .unwrap_or(true);

        let cleanup_system_history = env::var("EPN_CLEANUP_SYSTEM_HISTORY")
            .ok()
            .map(|s| s.to_lowercase() == "true")
            .unwrap_or(true);

        let cleanup_gaming_launchers = env::var("EPN_CLEANUP_GAMING_LAUNCHERS")
            .ok()
            .map(|s| s.to_lowercase() == "true")
            .unwrap_or(false);

        let cleanup_custom_paths = env::var("EPN_CLEANUP_CUSTOM_PATHS")
            .ok()
            .map(|s| s.split(':').map(|p| p.to_string()).collect())
            .unwrap_or_default();

        let cleanup_exclude_patterns = env::var("EPN_CLEANUP_EXCLUDE_PATTERNS")
            .ok()
            .map(|s| s.split(':').map(|p| p.to_string()).collect())
            .unwrap_or_default();

        let inactivity_enabled = env::var("EPN_INACTIVITY_ENABLED")
            .ok()
            .map(|s| s.to_lowercase() == "true")
            .unwrap_or(true);

        let inactivity_warning_secs = env::var("EPN_INACTIVITY_WARNING_SECS")
            .ok()
            .and_then(|s| s.parse().ok())
            .unwrap_or(default_inactivity_warning());

        let inactivity_timeout_secs = env::var("EPN_INACTIVITY_TIMEOUT_SECS")
            .ok()
            .and_then(|s| s.parse().ok())
            .unwrap_or(default_inactivity_timeout());

        // Gaming
        let gaming_enabled = env::var("EPN_GAMING_ENABLED")
            .ok()
            .map(|s| s.to_lowercase() == "true")
            .unwrap_or(false);

        let gaming_auto_start_launchers = env::var("EPN_GAMING_AUTO_START_LAUNCHERS")
            .ok()
            .map(|s| s.split(',').map(|p| p.trim().to_string()).collect())
            .unwrap_or_default();

        let gaming_close_on_end = env::var("EPN_GAMING_CLOSE_ON_END")
            .ok()
            .map(|s| s.to_lowercase() == "true")
            .unwrap_or(true);

        let gaming_close_games_on_end = env::var("EPN_GAMING_CLOSE_GAMES_ON_END")
            .ok()
            .map(|s| s.to_lowercase() == "true")
            .unwrap_or(true);

        let gaming_steam_big_picture = env::var("EPN_GAMING_STEAM_BIG_PICTURE")
            .ok()
            .map(|s| s.to_lowercase() == "true")
            .unwrap_or(false);

        let gaming_steam_path = env::var("EPN_GAMING_STEAM_PATH").ok();
        let gaming_epic_path = env::var("EPN_GAMING_EPIC_PATH").ok();
        let gaming_gog_path = env::var("EPN_GAMING_GOG_PATH").ok();

        // Kiosk
        let kiosk_mode = env::var("EPN_KIOSK_MODE")
            .ok()
            .map(|s| s.to_lowercase() == "true")
            .unwrap_or(true);

        let kiosk_admin_password = env::var("EPN_KIOSK_ADMIN_PASSWORD").ok();

        Ok(Self {
            server_url,
            ws_url,
            check_interval,
            warning_time,
            critical_time,
            enable_screen_lock,
            lock_on_expire,
            logout_on_expire,
            lock_delay_secs,
            cleanup_scripts,
            debug,
            log_level,
            discovery_token,
            discovery_poll_interval,
            discovery_max_wait,
            poste_type,
            enable_cleanup,
            cleanup_firefox,
            cleanup_libreoffice,
            cleanup_user_documents,
            cleanup_system_history,
            cleanup_gaming_launchers,
            cleanup_custom_paths,
            cleanup_exclude_patterns,
            inactivity_enabled,
            inactivity_warning_secs,
            inactivity_timeout_secs,
            // Gaming
            gaming_enabled,
            gaming_auto_start_launchers,
            gaming_close_on_end,
            gaming_close_games_on_end,
            gaming_steam_big_picture,
            gaming_steam_path,
            gaming_epic_path,
            gaming_gog_path,
            // Kiosk
            kiosk_mode,
            kiosk_admin_password,
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

    /// Créer une configuration de nettoyage à partir de la configuration générale
    pub fn cleanup_config(&self) -> CleanupConfig {
        CleanupConfig {
            poste_type: PosteType::from(self.poste_type.as_str()),
            clean_firefox: self.cleanup_firefox,
            clean_libreoffice: self.cleanup_libreoffice,
            clean_user_documents: self.cleanup_user_documents,
            clean_system_history: self.cleanup_system_history,
            clean_gaming_launchers: self.cleanup_gaming_launchers,
            custom_paths: self.cleanup_custom_paths.iter().map(PathBuf::from).collect(),
            exclude_patterns: self.cleanup_exclude_patterns.clone(),
        }
    }

    /// Créer une configuration d'inactivité à partir de la configuration générale
    pub fn inactivity_config(&self) -> InactivityConfig {
        InactivityConfig {
            enabled: self.inactivity_enabled,
            warning_secs: self.inactivity_warning_secs,
            timeout_secs: self.inactivity_timeout_secs,
        }
    }

    /// Créer une configuration gaming à partir de la configuration générale
    pub fn gaming_config(&self) -> GamingConfig {
        let auto_start_launchers: Vec<GameLauncher> = self
            .gaming_auto_start_launchers
            .iter()
            .filter_map(|s| GameLauncher::from_str(s))
            .collect();

        GamingConfig {
            auto_start_launchers,
            close_launchers_on_end: self.gaming_close_on_end,
            close_games_on_end: self.gaming_close_games_on_end,
            steam_big_picture: self.gaming_steam_big_picture,
            steam_path: self.gaming_steam_path.as_ref().map(PathBuf::from),
            epic_path: self.gaming_epic_path.as_ref().map(PathBuf::from),
            gog_path: self.gaming_gog_path.as_ref().map(PathBuf::from),
        }
    }

    /// Vérifie si le poste est de type gaming
    pub fn is_gaming_poste(&self) -> bool {
        self.poste_type == "gaming" || self.gaming_enabled
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
