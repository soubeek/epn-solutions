// EPN System - Intégration système multi-plateforme
//!
//! Cette bibliothèque fournit l'intégration avec le système d'exploitation:
//! - Verrouillage d'écran (Linux/Windows)
//! - Déconnexion utilisateur (Linux/Windows)
//! - Notifications desktop (Linux/Windows)

pub mod notifications;
pub mod screen_lock;
pub mod logout;

pub use notifications::{Notifier, Urgency};
pub use screen_lock::ScreenLocker;
pub use logout::Logout;

/// Obtenir l'implémentation du verrouillage d'écran pour la plateforme actuelle
pub fn get_screen_locker() -> Box<dyn ScreenLocker> {
    #[cfg(target_os = "linux")]
    {
        Box::new(screen_lock::LinuxScreenLocker)
    }

    #[cfg(target_os = "windows")]
    {
        Box::new(screen_lock::WindowsScreenLocker)
    }

    #[cfg(not(any(target_os = "linux", target_os = "windows")))]
    {
        compile_error!("Platform not supported");
    }
}

/// Obtenir l'implémentation de la déconnexion pour la plateforme actuelle
pub fn get_logout() -> Box<dyn Logout> {
    #[cfg(target_os = "linux")]
    {
        Box::new(logout::LinuxLogout)
    }

    #[cfg(target_os = "windows")]
    {
        Box::new(logout::WindowsLogout)
    }

    #[cfg(not(any(target_os = "linux", target_os = "windows")))]
    {
        compile_error!("Platform not supported");
    }
}

/// Obtenir l'implémentation des notifications pour la plateforme actuelle
pub fn get_notifier() -> Box<dyn Notifier> {
    #[cfg(target_os = "linux")]
    {
        Box::new(notifications::LinuxNotifier)
    }

    #[cfg(target_os = "windows")]
    {
        Box::new(notifications::WindowsNotifier)
    }

    #[cfg(not(any(target_os = "linux", target_os = "windows")))]
    {
        compile_error!("Platform not supported");
    }
}
