// Notifications desktop multi-plateforme
use std::process::Command;

pub type Result<T> = std::result::Result<T, Box<dyn std::error::Error + Send + Sync>>;

/// Niveau d'urgence de la notification
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Urgency {
    Low,
    Normal,
    Critical,
}

/// Trait pour les notifications desktop
pub trait Notifier: Send + Sync {
    /// Afficher une notification
    fn show(&self, title: &str, message: &str, urgency: Urgency) -> Result<()>;
}

// ============================================================================
// LINUX IMPLEMENTATION
// ============================================================================

#[cfg(target_os = "linux")]
pub struct LinuxNotifier;

#[cfg(target_os = "linux")]
impl Notifier for LinuxNotifier {
    fn show(&self, title: &str, message: &str, urgency: Urgency) -> Result<()> {
        // Méthode 1: notify-rust (bibliothèque)
        if let Ok(_) = self.show_with_notify_rust(title, message, urgency) {
            return Ok(());
        }

        // Méthode 2: notify-send (commande)
        if let Ok(_) = self.show_with_notify_send(title, message, urgency) {
            return Ok(());
        }

        // Méthode 3: zenity (fallback)
        if let Ok(_) = self.show_with_zenity(title, message) {
            return Ok(());
        }

        // Méthode 4: kdialog (KDE)
        if let Ok(_) = self.show_with_kdialog(title, message) {
            return Ok(());
        }

        Err("Aucune méthode de notification n'a fonctionné".into())
    }
}

#[cfg(target_os = "linux")]
impl LinuxNotifier {
    fn show_with_notify_rust(&self, title: &str, message: &str, urgency: Urgency) -> Result<()> {
        use notify_rust::{Notification, Timeout};

        let urgency_level = match urgency {
            Urgency::Low => notify_rust::Urgency::Low,
            Urgency::Normal => notify_rust::Urgency::Normal,
            Urgency::Critical => notify_rust::Urgency::Critical,
        };

        Notification::new()
            .summary(title)
            .body(message)
            .urgency(urgency_level)
            .timeout(Timeout::Milliseconds(5000))
            .show()?;

        tracing::debug!("✓ Notification affichée (notify-rust)");
        Ok(())
    }

    fn show_with_notify_send(&self, title: &str, message: &str, urgency: Urgency) -> Result<()> {
        let urgency_str = match urgency {
            Urgency::Low => "low",
            Urgency::Normal => "normal",
            Urgency::Critical => "critical",
        };

        let output = Command::new("notify-send")
            .args(&[
                "-u", urgency_str,
                "-t", "5000",
                title,
                message,
            ])
            .output()?;

        if output.status.success() {
            tracing::debug!("✓ Notification affichée (notify-send)");
            Ok(())
        } else {
            Err("notify-send a échoué".into())
        }
    }

    fn show_with_zenity(&self, title: &str, message: &str) -> Result<()> {
        let full_message = format!("{}\n\n{}", title, message);

        Command::new("zenity")
            .args(&[
                "--info",
                "--title", title,
                "--text", &full_message,
                "--timeout", "5",
            ])
            .spawn()?;

        tracing::debug!("✓ Notification affichée (zenity)");
        Ok(())
    }

    fn show_with_kdialog(&self, title: &str, message: &str) -> Result<()> {
        let full_message = format!("{}\n\n{}", title, message);

        Command::new("kdialog")
            .args(&[
                "--passivepopup", &full_message, "5",
                "--title", title,
            ])
            .spawn()?;

        tracing::debug!("✓ Notification affichée (kdialog)");
        Ok(())
    }
}

// ============================================================================
// WINDOWS IMPLEMENTATION
// ============================================================================

#[cfg(target_os = "windows")]
pub struct WindowsNotifier;

#[cfg(target_os = "windows")]
impl Notifier for WindowsNotifier {
    fn show(&self, title: &str, message: &str, urgency: Urgency) -> Result<()> {
        // Méthode 1: MessageBox (simple et toujours disponible)
        if let Ok(_) = self.show_with_messagebox(title, message, urgency) {
            return Ok(());
        }

        // Méthode 2: Toast notification (Windows 10/11)
        // Note: Nécessiterait winrt-notification ou windows-notification
        // Pour l'instant, on utilise MessageBox comme fallback

        Err("Impossible d'afficher la notification".into())
    }
}

#[cfg(target_os = "windows")]
impl WindowsNotifier {
    fn show_with_messagebox(&self, title: &str, message: &str, urgency: Urgency) -> Result<()> {
        use windows::Win32::UI::WindowsAndMessaging::{
            MessageBoxW, MB_OK, MB_ICONINFORMATION, MB_ICONWARNING, MB_ICONERROR, MB_TOPMOST,
        };
        use windows::core::PCWSTR;

        let icon = match urgency {
            Urgency::Low => MB_ICONINFORMATION,
            Urgency::Normal => MB_ICONWARNING,
            Urgency::Critical => MB_ICONERROR,
        };

        // Convertir en UTF-16 pour Windows
        let title_wide: Vec<u16> = title.encode_utf16().chain(std::iter::once(0)).collect();
        let message_wide: Vec<u16> = message.encode_utf16().chain(std::iter::once(0)).collect();

        unsafe {
            MessageBoxW(
                None,
                PCWSTR(message_wide.as_ptr()),
                PCWSTR(title_wide.as_ptr()),
                MB_OK | icon | MB_TOPMOST,
            );
        }

        tracing::debug!("✓ Notification affichée (MessageBox)");
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_urgency() {
        assert_eq!(Urgency::Low, Urgency::Low);
        assert_ne!(Urgency::Low, Urgency::Critical);
    }

    #[test]
    fn test_notifier_creation() {
        #[cfg(target_os = "linux")]
        {
            let notifier = LinuxNotifier;
            assert!(std::mem::size_of_val(&notifier) == 0);
        }

        #[cfg(target_os = "windows")]
        {
            let notifier = WindowsNotifier;
            assert!(std::mem::size_of_val(&notifier) == 0);
        }
    }
}
