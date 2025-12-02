// Verrouillage d'écran multi-plateforme
use std::process::Command;

pub type Result<T> = std::result::Result<T, Box<dyn std::error::Error + Send + Sync>>;

/// Trait pour le verrouillage d'écran
pub trait ScreenLocker: Send + Sync {
    /// Verrouiller l'écran
    fn lock(&self) -> Result<()>;

    /// Déverrouiller l'écran (si possible)
    fn unlock(&self) -> Result<()> {
        Err("Le déverrouillage n'est pas supporté".into())
    }

    /// Vérifier si l'écran est verrouillé
    fn is_locked(&self) -> Result<bool> {
        Err("La détection de verrouillage n'est pas supportée".into())
    }
}

// ============================================================================
// LINUX IMPLEMENTATION
// ============================================================================

#[cfg(target_os = "linux")]
pub struct LinuxScreenLocker;

#[cfg(target_os = "linux")]
impl ScreenLocker for LinuxScreenLocker {
    fn lock(&self) -> Result<()> {
        // Liste des commandes à essayer (dans l'ordre)
        let commands = vec![
            // systemd
            vec!["loginctl", "lock-session"],
            // GNOME
            vec!["gnome-screensaver-command", "--lock"],
            // KDE
            vec!["qdbus", "org.freedesktop.ScreenSaver", "/ScreenSaver", "Lock"],
            vec!["dbus-send", "--type=method_call", "--dest=org.freedesktop.ScreenSaver",
                 "/ScreenSaver", "org.freedesktop.ScreenSaver.Lock"],
            // XFCE
            vec!["xflock4"],
            // Cinnamon
            vec!["cinnamon-screensaver-command", "--lock"],
            // MATE
            vec!["mate-screensaver-command", "--lock"],
            // i3/sway
            vec!["i3lock"],
            vec!["swaylock"],
            // Générique X11
            vec!["xdg-screensaver", "lock"],
        ];

        for cmd_args in commands {
            if cmd_args.is_empty() {
                continue;
            }

            let cmd = &cmd_args[0];
            let args = &cmd_args[1..];

            tracing::debug!("Tentative de verrouillage avec: {} {:?}", cmd, args);

            match Command::new(cmd).args(args).output() {
                Ok(output) if output.status.success() => {
                    tracing::info!("✓ Écran verrouillé avec: {}", cmd);
                    return Ok(());
                }
                Ok(output) => {
                    tracing::debug!("Échec de {}: status={}", cmd, output.status);
                }
                Err(e) => {
                    tracing::debug!("Commande {} non trouvée: {}", cmd, e);
                }
            }
        }

        Err("Aucune commande de verrouillage n'a fonctionné".into())
    }

    fn is_locked(&self) -> Result<bool> {
        // Essayer avec gnome-screensaver
        if let Ok(output) = Command::new("gnome-screensaver-command")
            .arg("--query")
            .output()
        {
            if output.status.success() {
                let stdout = String::from_utf8_lossy(&output.stdout);
                return Ok(stdout.contains("is active"));
            }
        }

        // Essayer avec loginctl
        if let Ok(output) = Command::new("loginctl")
            .args(&["show-session", "self", "-p", "LockedHint"])
            .output()
        {
            if output.status.success() {
                let stdout = String::from_utf8_lossy(&output.stdout);
                return Ok(stdout.contains("LockedHint=yes"));
            }
        }

        // Pas supporté
        Err("Impossible de détecter le statut de verrouillage".into())
    }
}

// ============================================================================
// WINDOWS IMPLEMENTATION
// ============================================================================

#[cfg(target_os = "windows")]
pub struct WindowsScreenLocker;

#[cfg(target_os = "windows")]
impl ScreenLocker for WindowsScreenLocker {
    fn lock(&self) -> Result<()> {
        use windows::Win32::System::Power::LockWorkStation;

        unsafe {
            if LockWorkStation().as_bool() {
                tracing::info!("✓ Écran verrouillé (LockWorkStation)");
                Ok(())
            } else {
                Err("LockWorkStation a échoué".into())
            }
        }
    }

    fn is_locked(&self) -> Result<bool> {
        // Sur Windows, il n'y a pas d'API simple pour détecter le verrouillage
        // Cette fonctionnalité nécessiterait un hook plus complexe
        Err("La détection de verrouillage n'est pas supportée sur Windows".into())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_screen_locker_creation() {
        #[cfg(target_os = "linux")]
        {
            let locker = LinuxScreenLocker;
            // Le test ne peut pas vraiment verrouiller l'écran dans CI
            assert!(std::mem::size_of_val(&locker) == 0);
        }

        #[cfg(target_os = "windows")]
        {
            let locker = WindowsScreenLocker;
            assert!(std::mem::size_of_val(&locker) == 0);
        }
    }
}
