//! Implementation du verrouillage systeme pour Linux (GNOME)
//!
//! Utilise dconf pour appliquer les restrictions sur le bureau GNOME.

use anyhow::{Context, Result, bail};
use std::process::Command;
use tracing::{info, warn, debug};

use super::{SystemLockdown, LockdownProfile};

/// Implementation Linux du verrouillage systeme
pub struct LinuxLockdown {
    /// Chemin vers la commande dconf
    dconf_path: String,
    /// Chemin vers la commande gsettings
    gsettings_path: String,
}

impl LinuxLockdown {
    /// Cree une nouvelle instance
    pub fn new() -> Self {
        Self {
            dconf_path: "dconf".to_string(),
            gsettings_path: "gsettings".to_string(),
        }
    }

    /// Verifie si dconf est disponible
    fn check_dconf_available(&self) -> Result<bool> {
        let output = Command::new("which")
            .arg(&self.dconf_path)
            .output()
            .context("Impossible de verifier la presence de dconf")?;
        Ok(output.status.success())
    }

    /// Execute une commande dconf write
    fn dconf_write(&self, key: &str, value: &str) -> Result<()> {
        debug!("dconf write {} {}", key, value);
        let output = Command::new(&self.dconf_path)
            .args(["write", key, value])
            .output()
            .context(format!("Erreur dconf write {} {}", key, value))?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            bail!("dconf write echoue: {}", stderr);
        }
        Ok(())
    }

    /// Execute une commande dconf reset
    fn dconf_reset(&self, key: &str) -> Result<()> {
        debug!("dconf reset {}", key);
        let output = Command::new(&self.dconf_path)
            .args(["reset", key])
            .output()
            .context(format!("Erreur dconf reset {}", key))?;

        if !output.status.success() {
            warn!("dconf reset {} n'a pas fonctionne (peut-etre deja reset)", key);
        }
        Ok(())
    }

    /// Lit une valeur dconf
    fn dconf_read(&self, key: &str) -> Result<Option<String>> {
        let output = Command::new(&self.dconf_path)
            .args(["read", key])
            .output()
            .context(format!("Erreur dconf read {}", key))?;

        if output.status.success() && !output.stdout.is_empty() {
            Ok(Some(String::from_utf8_lossy(&output.stdout).trim().to_string()))
        } else {
            Ok(None)
        }
    }

    /// Applique les restrictions du bureau GNOME
    fn apply_desktop_restrictions(&self, profile: &LockdownProfile) -> Result<()> {
        let restrictions = &profile.desktop_restrictions;

        info!("Application des restrictions bureau GNOME...");

        // Restrictions lockdown GNOME
        if restrictions.disable_system_shortcuts {
            // Desactiver la touche Super (overlay)
            self.dconf_write("/org/gnome/mutter/overlay-key", "''")?;
            // Desactiver Alt+F2 (commande)
            self.dconf_write("/org/gnome/desktop/wm/keybindings/panel-run-dialog", "['']")?;
        }

        if restrictions.disable_main_menu {
            // Desactiver le hot corner Activities
            self.dconf_write("/org/gnome/desktop/interface/enable-hot-corners", "false")?;
        }

        if restrictions.disable_notifications {
            self.dconf_write("/org/gnome/desktop/notifications/show-banners", "false")?;
            self.dconf_write("/org/gnome/desktop/notifications/show-in-lock-screen", "false")?;
        }

        if restrictions.hide_desktop_icons {
            self.dconf_write("/org/gnome/desktop/background/show-desktop-icons", "false")?;
        }

        if restrictions.lock_wallpaper {
            if let Some(ref path) = restrictions.wallpaper_path {
                self.dconf_write("/org/gnome/desktop/background/picture-uri", &format!("'file://{}'", path))?;
                self.dconf_write("/org/gnome/desktop/background/picture-uri-dark", &format!("'file://{}'", path))?;
            }
        }

        Ok(())
    }

    /// Applique les restrictions systeme
    fn apply_system_restrictions(&self, profile: &LockdownProfile) -> Result<()> {
        let restrictions = &profile.system_restrictions;

        info!("Application des restrictions systeme...");

        // GNOME lockdown schema
        if restrictions.disable_terminal {
            self.dconf_write("/org/gnome/desktop/lockdown/disable-command-line", "true")?;
        }

        if restrictions.disable_user_switching {
            self.dconf_write("/org/gnome/desktop/lockdown/disable-user-switching", "true")?;
        }

        if restrictions.disable_logout {
            self.dconf_write("/org/gnome/desktop/lockdown/disable-log-out", "true")?;
        }

        if restrictions.disable_print_setup {
            self.dconf_write("/org/gnome/desktop/lockdown/disable-print-setup", "true")?;
        }

        if restrictions.disable_settings {
            self.dconf_write("/org/gnome/desktop/lockdown/disable-lock-screen", "false")?;
        }

        // Bloquer USB storage via udev
        if restrictions.block_usb_storage {
            self.setup_usb_block()?;
        }

        Ok(())
    }

    /// Configure le blocage USB via udev
    fn setup_usb_block(&self) -> Result<()> {
        let udev_rule = r#"# EPN Solutions - Bloquer les peripheriques USB de stockage
ACTION=="add", SUBSYSTEMS=="usb", DRIVERS=="usb-storage", ATTR{authorized}="0"
"#;

        let rule_path = "/etc/udev/rules.d/99-epn-block-usb-storage.rules";

        // Verifier si on a les droits root
        if !nix::unistd::Uid::effective().is_root() {
            warn!("Droits root requis pour bloquer USB. Ignoré.");
            return Ok(());
        }

        std::fs::write(rule_path, udev_rule)
            .context("Impossible d'ecrire la regle udev")?;

        // Recharger udev
        Command::new("udevadm")
            .args(["control", "--reload-rules"])
            .output()
            .context("Impossible de recharger les regles udev")?;

        info!("Blocage USB configure: {}", rule_path);
        Ok(())
    }

    /// Retire le blocage USB
    fn remove_usb_block(&self) -> Result<()> {
        let rule_path = "/etc/udev/rules.d/99-epn-block-usb-storage.rules";

        if std::path::Path::new(rule_path).exists() {
            if nix::unistd::Uid::effective().is_root() {
                std::fs::remove_file(rule_path)
                    .context("Impossible de supprimer la regle udev")?;

                Command::new("udevadm")
                    .args(["control", "--reload-rules"])
                    .output()
                    .context("Impossible de recharger les regles udev")?;

                info!("Blocage USB retire");
            } else {
                warn!("Droits root requis pour retirer le blocage USB");
            }
        }
        Ok(())
    }

    /// Retire les restrictions bureau
    fn remove_desktop_restrictions(&self) -> Result<()> {
        info!("Retrait des restrictions bureau...");

        // Restaurer les valeurs par defaut
        self.dconf_reset("/org/gnome/mutter/overlay-key")?;
        self.dconf_reset("/org/gnome/desktop/wm/keybindings/panel-run-dialog")?;
        self.dconf_reset("/org/gnome/desktop/interface/enable-hot-corners")?;
        self.dconf_reset("/org/gnome/desktop/notifications/show-banners")?;
        self.dconf_reset("/org/gnome/desktop/notifications/show-in-lock-screen")?;
        self.dconf_reset("/org/gnome/desktop/background/show-desktop-icons")?;

        Ok(())
    }

    /// Retire les restrictions systeme
    fn remove_system_restrictions(&self) -> Result<()> {
        info!("Retrait des restrictions systeme...");

        self.dconf_reset("/org/gnome/desktop/lockdown/disable-command-line")?;
        self.dconf_reset("/org/gnome/desktop/lockdown/disable-user-switching")?;
        self.dconf_reset("/org/gnome/desktop/lockdown/disable-log-out")?;
        self.dconf_reset("/org/gnome/desktop/lockdown/disable-print-setup")?;
        self.dconf_reset("/org/gnome/desktop/lockdown/disable-lock-screen")?;

        self.remove_usb_block()?;

        Ok(())
    }
}

impl Default for LinuxLockdown {
    fn default() -> Self {
        Self::new()
    }
}

impl SystemLockdown for LinuxLockdown {
    fn apply(&self, profile: &LockdownProfile) -> Result<()> {
        info!("Application du profil de verrouillage: {:?}", profile.profile_type);

        // Verifier que dconf est disponible
        if !self.check_dconf_available()? {
            bail!("dconf n'est pas installe. Installez-le avec: sudo apt install dconf-cli");
        }

        // Appliquer les restrictions
        self.apply_desktop_restrictions(profile)?;
        self.apply_system_restrictions(profile)?;

        info!("Profil de verrouillage applique avec succes");
        Ok(())
    }

    fn remove(&self) -> Result<()> {
        info!("Retrait du verrouillage systeme...");

        self.remove_desktop_restrictions()?;
        self.remove_system_restrictions()?;

        info!("Verrouillage systeme retire");
        Ok(())
    }

    fn is_locked(&self) -> Result<bool> {
        // Verifier si au moins une restriction est active
        if let Some(value) = self.dconf_read("/org/gnome/desktop/lockdown/disable-command-line")? {
            if value == "true" {
                return Ok(true);
            }
        }
        Ok(false)
    }

    fn get_current_restrictions(&self) -> Result<Vec<String>> {
        let mut restrictions = Vec::new();

        let checks = [
            ("/org/gnome/desktop/lockdown/disable-command-line", "Terminal desactive"),
            ("/org/gnome/desktop/lockdown/disable-user-switching", "Changement utilisateur desactive"),
            ("/org/gnome/desktop/lockdown/disable-log-out", "Deconnexion desactivee"),
            ("/org/gnome/mutter/overlay-key", "Touche Super desactivee"),
        ];

        for (key, description) in checks {
            if let Some(value) = self.dconf_read(key)? {
                if value == "true" || value == "''" {
                    restrictions.push(description.to_string());
                }
            }
        }

        Ok(restrictions)
    }
}

/// Configure l'auto-login pour l'utilisateur specifie
pub fn configure_autologin(username: &str) -> Result<()> {
    info!("Configuration auto-login pour: {}", username);

    // GDM custom.conf
    let gdm_config = format!(r#"[daemon]
AutomaticLoginEnable=true
AutomaticLogin={}

[security]

[xdmcp]

[chooser]

[debug]
"#, username);

    let gdm_path = "/etc/gdm3/custom.conf";

    if !nix::unistd::Uid::effective().is_root() {
        bail!("Droits root requis pour configurer l'auto-login");
    }

    // Backup de l'ancien fichier
    if std::path::Path::new(gdm_path).exists() {
        std::fs::copy(gdm_path, format!("{}.bak", gdm_path))
            .context("Impossible de sauvegarder la config GDM")?;
    }

    std::fs::write(gdm_path, gdm_config)
        .context("Impossible d'ecrire la config GDM")?;

    info!("Auto-login configure pour {} dans {}", username, gdm_path);
    Ok(())
}

/// Cree le fichier autostart pour le client EPN
pub fn configure_autostart(client_path: &str) -> Result<()> {
    let autostart_dir = dirs::config_dir()
        .map(|p| p.join("autostart"))
        .unwrap_or_else(|| std::path::PathBuf::from("~/.config/autostart"));

    std::fs::create_dir_all(&autostart_dir)
        .context("Impossible de creer le dossier autostart")?;

    let desktop_entry = format!(r#"[Desktop Entry]
Type=Application
Name=EPN Client
Comment=Client EPN Solutions
Exec={}
Terminal=false
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=2
"#, client_path);

    let autostart_path = autostart_dir.join("epn-client.desktop");
    std::fs::write(&autostart_path, desktop_entry)
        .context("Impossible de creer le fichier autostart")?;

    info!("Autostart configure: {:?}", autostart_path);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::lockdown::ProfileType;

    #[test]
    fn test_lockdown_new() {
        let lockdown = LinuxLockdown::new();
        assert_eq!(lockdown.dconf_path, "dconf");
    }

    #[test]
    fn test_default_profile() {
        let profile = LockdownProfile::from_type(ProfileType::Standard);
        assert!(profile.system_restrictions.disable_terminal);
    }
}
