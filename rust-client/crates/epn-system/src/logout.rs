// Déconnexion utilisateur multi-plateforme
use std::process::Command;

pub type Result<T> = std::result::Result<T, Box<dyn std::error::Error + Send + Sync>>;

/// Trait pour la déconnexion utilisateur
pub trait Logout: Send + Sync {
    /// Déconnecter l'utilisateur actuel
    fn logout(&self) -> Result<()>;
}

// ============================================================================
// LINUX IMPLEMENTATION
// ============================================================================

#[cfg(target_os = "linux")]
pub struct LinuxLogout;

#[cfg(target_os = "linux")]
impl Logout for LinuxLogout {
    fn logout(&self) -> Result<()> {
        // Liste des commandes à essayer (dans l'ordre)
        let commands: Vec<Vec<&str>> = vec![
            // systemd
            vec!["loginctl", "terminate-user", ""],
            vec!["loginctl", "terminate-session", "self"],
            // GNOME
            vec!["gnome-session-quit", "--logout", "--no-prompt"],
            vec!["gnome-session-quit", "--force"],
            // KDE
            vec!["qdbus", "org.kde.ksmserver", "/KSMServer", "logout", "0", "0", "0"],
            // XFCE
            vec!["xfce4-session-logout", "--logout"],
            // Generic
            vec!["pkill", "-KILL", "-u", ""],
        ];

        // Obtenir le nom d'utilisateur pour certaines commandes
        let username = std::env::var("USER").unwrap_or_default();

        for mut cmd_args in commands {
            if cmd_args.is_empty() {
                continue;
            }

            // Remplacer les paramètres vides par le nom d'utilisateur
            for arg in &mut cmd_args {
                if arg.is_empty() {
                    *arg = &username;
                }
            }

            let cmd = &cmd_args[0];
            let args = &cmd_args[1..];

            tracing::debug!("Tentative de déconnexion avec: {} {:?}", cmd, args);

            match Command::new(cmd).args(args).spawn() {
                Ok(_) => {
                    tracing::info!("✓ Déconnexion initiée avec: {}", cmd);
                    return Ok(());
                }
                Err(e) => {
                    tracing::debug!("Commande {} échouée: {}", cmd, e);
                }
            }
        }

        Err("Aucune commande de déconnexion n'a fonctionné".into())
    }
}

// ============================================================================
// WINDOWS IMPLEMENTATION
// ============================================================================

#[cfg(target_os = "windows")]
pub struct WindowsLogout;

#[cfg(target_os = "windows")]
impl Logout for WindowsLogout {
    fn logout(&self) -> Result<()> {
        use windows::Win32::System::Shutdown::{ExitWindowsEx, EWX_LOGOFF, EWX_FORCE};

        unsafe {
            // Déconnecter l'utilisateur (force si nécessaire)
            if ExitWindowsEx(EWX_LOGOFF | EWX_FORCE, 0).as_bool() {
                tracing::info!("✓ Déconnexion initiée (ExitWindowsEx)");
                Ok(())
            } else {
                // Essayer avec la commande shutdown
                tracing::warn!("ExitWindowsEx a échoué, tentative avec shutdown.exe");
                match Command::new("shutdown").args(&["/l"]).spawn() {
                    Ok(_) => {
                        tracing::info!("✓ Déconnexion initiée (shutdown /l)");
                        Ok(())
                    }
                    Err(e) => {
                        Err(format!("Impossible de déconnecter: {}", e).into())
                    }
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_logout_creation() {
        #[cfg(target_os = "linux")]
        {
            let logout = LinuxLogout;
            assert!(std::mem::size_of_val(&logout) == 0);
        }

        #[cfg(target_os = "windows")]
        {
            let logout = WindowsLogout;
            assert!(std::mem::size_of_val(&logout) == 0);
        }
    }
}
