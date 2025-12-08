//! Profils de restriction predefinis

use serde::{Deserialize, Serialize};

/// Types de profils de restriction predefinis
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "lowercase")]
pub enum ProfileType {
    /// Mode strict: Firefox uniquement
    Strict,
    /// Mode standard: Firefox + LibreOffice
    #[default]
    Standard,
    /// Mode permissif: Applications selectionnees
    Permissive,
    /// Mode gaming: Firefox + Steam + Epic + autres launchers
    Gaming,
    /// Mode personnalise: Configuration manuelle
    Custom,
}

impl ProfileType {
    /// Retourne la liste des applications par defaut pour ce profil
    pub fn default_apps(&self) -> Vec<&'static str> {
        match self {
            ProfileType::Strict => vec!["firefox"],
            ProfileType::Standard => vec![
                "firefox",
                "libreoffice-writer",
                "libreoffice-calc",
                "libreoffice-impress",
            ],
            ProfileType::Permissive => vec![
                "firefox",
                "libreoffice-writer",
                "libreoffice-calc",
                "libreoffice-impress",
                "libreoffice-draw",
                "gimp",
                "inkscape",
                "vlc",
            ],
            ProfileType::Gaming => vec![
                "firefox",
                "steam",
                "com.heroicgameslauncher.hgl",
                "lutris",
            ],
            ProfileType::Custom => vec![],
        }
    }

    /// Retourne la description du profil
    pub fn description(&self) -> &'static str {
        match self {
            ProfileType::Strict => "Mode strict - Navigation web uniquement",
            ProfileType::Standard => "Mode standard - Navigation et bureautique",
            ProfileType::Permissive => "Mode permissif - Applications multimedia",
            ProfileType::Gaming => "Mode gaming - Jeux video autorises",
            ProfileType::Custom => "Mode personnalise - Configuration manuelle",
        }
    }
}

/// Profil de verrouillage complet
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LockdownProfile {
    /// Type de profil
    pub profile_type: ProfileType,

    /// Nom personnalise du profil
    pub name: String,

    /// Description
    pub description: String,

    /// Liste des applications autorisees (identifiants .desktop ou chemins)
    pub allowed_apps: Vec<String>,

    /// Restrictions bureau
    pub desktop_restrictions: DesktopRestrictions,

    /// Restrictions systeme
    pub system_restrictions: SystemRestrictions,
}

impl LockdownProfile {
    /// Cree un profil a partir d'un type predefini
    pub fn from_type(profile_type: ProfileType) -> Self {
        Self {
            profile_type,
            name: format!("{:?}", profile_type),
            description: profile_type.description().to_string(),
            allowed_apps: profile_type.default_apps().iter().map(|s| s.to_string()).collect(),
            desktop_restrictions: DesktopRestrictions::default_for(profile_type),
            system_restrictions: SystemRestrictions::default_for(profile_type),
        }
    }

    /// Cree un profil personnalise
    pub fn custom(name: &str, allowed_apps: Vec<String>) -> Self {
        Self {
            profile_type: ProfileType::Custom,
            name: name.to_string(),
            description: format!("Profil personnalise: {}", name),
            allowed_apps,
            desktop_restrictions: DesktopRestrictions::default(),
            system_restrictions: SystemRestrictions::default(),
        }
    }
}

impl Default for LockdownProfile {
    fn default() -> Self {
        Self::from_type(ProfileType::Standard)
    }
}

/// Restrictions du bureau (GNOME/KDE/Windows)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DesktopRestrictions {
    /// Desactiver le clic droit sur le bureau
    pub disable_desktop_context_menu: bool,

    /// Cacher les icones du bureau
    pub hide_desktop_icons: bool,

    /// Desactiver le menu principal (Activities/Start)
    pub disable_main_menu: bool,

    /// Desactiver la barre des taches/dock
    pub disable_taskbar: bool,

    /// Desactiver les raccourcis systeme (Super, Alt+F2, etc.)
    pub disable_system_shortcuts: bool,

    /// Desactiver les notifications
    pub disable_notifications: bool,

    /// Verrouiller le fond d'ecran
    pub lock_wallpaper: bool,

    /// Chemin du fond d'ecran a utiliser
    pub wallpaper_path: Option<String>,
}

impl DesktopRestrictions {
    /// Restrictions par defaut selon le type de profil
    pub fn default_for(profile_type: ProfileType) -> Self {
        match profile_type {
            ProfileType::Strict => Self {
                disable_desktop_context_menu: true,
                hide_desktop_icons: true,
                disable_main_menu: true,
                disable_taskbar: false, // Garder pour voir les apps
                disable_system_shortcuts: true,
                disable_notifications: true,
                lock_wallpaper: true,
                wallpaper_path: None,
            },
            ProfileType::Standard | ProfileType::Permissive => Self {
                disable_desktop_context_menu: true,
                hide_desktop_icons: true,
                disable_main_menu: true,
                disable_taskbar: false,
                disable_system_shortcuts: true,
                disable_notifications: false,
                lock_wallpaper: true,
                wallpaper_path: None,
            },
            ProfileType::Gaming => Self {
                disable_desktop_context_menu: true,
                hide_desktop_icons: false, // Peut avoir des raccourcis jeux
                disable_main_menu: true,
                disable_taskbar: false,
                disable_system_shortcuts: true,
                disable_notifications: false,
                lock_wallpaper: false,
                wallpaper_path: None,
            },
            ProfileType::Custom => Self::default(),
        }
    }
}

impl Default for DesktopRestrictions {
    fn default() -> Self {
        Self {
            disable_desktop_context_menu: true,
            hide_desktop_icons: true,
            disable_main_menu: true,
            disable_taskbar: false,
            disable_system_shortcuts: true,
            disable_notifications: false,
            lock_wallpaper: true,
            wallpaper_path: None,
        }
    }
}

/// Restrictions systeme (acces fichiers, terminal, etc.)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemRestrictions {
    /// Desactiver l'acces au terminal
    pub disable_terminal: bool,

    /// Desactiver le gestionnaire de fichiers
    pub disable_file_manager: bool,

    /// Desactiver l'acces aux parametres systeme
    pub disable_settings: bool,

    /// Desactiver le changement d'utilisateur
    pub disable_user_switching: bool,

    /// Desactiver la deconnexion
    pub disable_logout: bool,

    /// Desactiver l'arret/redemarrage
    pub disable_shutdown: bool,

    /// Desactiver l'impression (config)
    pub disable_print_setup: bool,

    /// Bloquer les peripheriques USB de stockage
    pub block_usb_storage: bool,

    /// Dossiers autorises en lecture/ecriture
    pub allowed_directories: Vec<String>,
}

impl SystemRestrictions {
    /// Restrictions par defaut selon le type de profil
    pub fn default_for(profile_type: ProfileType) -> Self {
        match profile_type {
            ProfileType::Strict => Self {
                disable_terminal: true,
                disable_file_manager: true,
                disable_settings: true,
                disable_user_switching: true,
                disable_logout: true,
                disable_shutdown: true,
                disable_print_setup: true,
                block_usb_storage: true,
                allowed_directories: vec![
                    "/tmp".to_string(),
                    "~/Downloads".to_string(),
                ],
            },
            ProfileType::Standard => Self {
                disable_terminal: true,
                disable_file_manager: true,
                disable_settings: true,
                disable_user_switching: true,
                disable_logout: true,
                disable_shutdown: true,
                disable_print_setup: false,
                block_usb_storage: true,
                allowed_directories: vec![
                    "/tmp".to_string(),
                    "~/Downloads".to_string(),
                    "~/Documents".to_string(),
                ],
            },
            ProfileType::Permissive | ProfileType::Gaming => Self {
                disable_terminal: true,
                disable_file_manager: false, // Peut avoir besoin d'acceder aux fichiers
                disable_settings: true,
                disable_user_switching: true,
                disable_logout: true,
                disable_shutdown: true,
                disable_print_setup: false,
                block_usb_storage: false,
                allowed_directories: vec![
                    "/tmp".to_string(),
                    "~/Downloads".to_string(),
                    "~/Documents".to_string(),
                    "~/.local/share/Steam".to_string(),
                ],
            },
            ProfileType::Custom => Self::default(),
        }
    }
}

impl Default for SystemRestrictions {
    fn default() -> Self {
        Self {
            disable_terminal: true,
            disable_file_manager: true,
            disable_settings: true,
            disable_user_switching: true,
            disable_logout: true,
            disable_shutdown: true,
            disable_print_setup: false,
            block_usb_storage: true,
            allowed_directories: vec![
                "/tmp".to_string(),
                "~/Downloads".to_string(),
            ],
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_profile_types() {
        assert!(!ProfileType::Strict.default_apps().is_empty());
        assert!(ProfileType::Standard.default_apps().len() > 1);
        assert!(ProfileType::Gaming.default_apps().contains(&"steam"));
    }

    #[test]
    fn test_profile_from_type() {
        let profile = LockdownProfile::from_type(ProfileType::Strict);
        assert_eq!(profile.allowed_apps, vec!["firefox"]);
        assert!(profile.desktop_restrictions.disable_main_menu);
    }

    #[test]
    fn test_custom_profile() {
        let apps = vec!["app1".to_string(), "app2".to_string()];
        let profile = LockdownProfile::custom("Test", apps.clone());
        assert_eq!(profile.allowed_apps, apps);
        assert!(matches!(profile.profile_type, ProfileType::Custom));
    }
}
