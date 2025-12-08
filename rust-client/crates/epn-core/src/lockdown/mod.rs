//! Module de verrouillage systeme (System Lockdown)
//!
//! Ce module gere les restrictions du systeme d'exploitation pour
//! transformer un poste en kiosque securise.
//!
//! Fonctionnalites:
//! - Restrictions bureau (GNOME/Windows)
//! - Whitelist d'applications
//! - Profils de restriction predefinis

mod profiles;

#[cfg(target_os = "linux")]
mod linux;

#[cfg(target_os = "windows")]
mod windows;

mod apps;

pub use profiles::{LockdownProfile, ProfileType};
pub use apps::{AppWhitelist, AppRestriction};

#[cfg(target_os = "linux")]
pub use linux::LinuxLockdown;

#[cfg(target_os = "windows")]
pub use windows::WindowsLockdown;

use anyhow::Result;

/// Trait commun pour le verrouillage systeme
pub trait SystemLockdown {
    /// Applique les restrictions systeme
    fn apply(&self, profile: &LockdownProfile) -> Result<()>;

    /// Retire les restrictions systeme
    fn remove(&self) -> Result<()>;

    /// Verifie si les restrictions sont actives
    fn is_locked(&self) -> Result<bool>;

    /// Retourne les restrictions actuellement actives
    fn get_current_restrictions(&self) -> Result<Vec<String>>;
}

/// Cree une instance du lockdown pour la plateforme courante
pub fn create_lockdown() -> Box<dyn SystemLockdown> {
    #[cfg(target_os = "linux")]
    {
        Box::new(LinuxLockdown::new())
    }

    #[cfg(target_os = "windows")]
    {
        Box::new(WindowsLockdown::new())
    }

    #[cfg(not(any(target_os = "linux", target_os = "windows")))]
    {
        compile_error!("Plateforme non supportee pour le lockdown systeme")
    }
}

/// Configuration du lockdown depuis le fichier YAML
#[derive(Debug, Clone, serde::Deserialize, serde::Serialize)]
pub struct LockdownConfig {
    /// Activer le lockdown systeme
    #[serde(default)]
    pub enabled: bool,

    /// Type de profil a utiliser
    #[serde(default)]
    pub profile: ProfileType,

    /// Applications autorisees (whitelist)
    #[serde(default)]
    pub allowed_apps: Vec<String>,

    /// Activer l'auto-login
    #[serde(default)]
    pub auto_login: bool,

    /// Utilisateur pour l'auto-login
    #[serde(default)]
    pub auto_login_user: Option<String>,

    /// Bloquer les peripheriques USB de stockage
    #[serde(default)]
    pub block_usb_storage: bool,
}

impl Default for LockdownConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            profile: ProfileType::Standard,
            allowed_apps: vec![
                "firefox".to_string(),
                "libreoffice".to_string(),
            ],
            auto_login: false,
            auto_login_user: None,
            block_usb_storage: false,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = LockdownConfig::default();
        assert!(!config.enabled);
        assert!(matches!(config.profile, ProfileType::Standard));
        assert!(!config.allowed_apps.is_empty());
    }
}
