//! Implementation du verrouillage systeme pour Windows
//!
//! Utilise le registre Windows pour appliquer les restrictions.

use anyhow::{Context, Result, bail};
use tracing::{info, warn, debug};

use super::{SystemLockdown, LockdownProfile};

#[cfg(target_os = "windows")]
use winreg::enums::*;
#[cfg(target_os = "windows")]
use winreg::RegKey;

/// Implementation Windows du verrouillage systeme
pub struct WindowsLockdown {
    /// Indique si on a les droits admin
    has_admin: bool,
}

impl WindowsLockdown {
    /// Cree une nouvelle instance
    pub fn new() -> Self {
        Self {
            has_admin: Self::check_admin(),
        }
    }

    /// Verifie si on a les droits administrateur
    #[cfg(target_os = "windows")]
    fn check_admin() -> bool {
        use std::ptr;
        use windows_sys::Win32::Security::{
            AllocateAndInitializeSid, CheckTokenMembership, FreeSid,
            SECURITY_BUILTIN_DOMAIN_RID, DOMAIN_ALIAS_RID_ADMINS,
            SECURITY_NT_AUTHORITY, SID_IDENTIFIER_AUTHORITY,
        };

        unsafe {
            let mut nt_authority = SID_IDENTIFIER_AUTHORITY {
                Value: SECURITY_NT_AUTHORITY,
            };
            let mut admin_group = ptr::null_mut();

            if AllocateAndInitializeSid(
                &mut nt_authority,
                2,
                SECURITY_BUILTIN_DOMAIN_RID,
                DOMAIN_ALIAS_RID_ADMINS,
                0, 0, 0, 0, 0, 0,
                &mut admin_group,
            ) != 0
            {
                let mut is_member = 0;
                if CheckTokenMembership(ptr::null_mut(), admin_group, &mut is_member) != 0 {
                    FreeSid(admin_group);
                    return is_member != 0;
                }
                FreeSid(admin_group);
            }
        }
        false
    }

    #[cfg(not(target_os = "windows"))]
    fn check_admin() -> bool {
        false
    }

    /// Ecrit une valeur DWORD dans le registre
    #[cfg(target_os = "windows")]
    fn write_reg_dword(&self, hkey: RegKey, subkey: &str, value_name: &str, value: u32) -> Result<()> {
        let (key, _) = hkey
            .create_subkey(subkey)
            .context(format!("Impossible de creer la cle {}", subkey))?;

        key.set_value(value_name, &value)
            .context(format!("Impossible d'ecrire {} = {}", value_name, value))?;

        debug!("Registry: {}\\{} = {}", subkey, value_name, value);
        Ok(())
    }

    /// Supprime une valeur du registre
    #[cfg(target_os = "windows")]
    fn delete_reg_value(&self, hkey: RegKey, subkey: &str, value_name: &str) -> Result<()> {
        if let Ok(key) = hkey.open_subkey_with_flags(subkey, KEY_WRITE) {
            let _ = key.delete_value(value_name);
            debug!("Registry deleted: {}\\{}", subkey, value_name);
        }
        Ok(())
    }

    /// Lit une valeur DWORD du registre
    #[cfg(target_os = "windows")]
    fn read_reg_dword(&self, hkey: &RegKey, subkey: &str, value_name: &str) -> Result<Option<u32>> {
        if let Ok(key) = hkey.open_subkey(subkey) {
            if let Ok(value) = key.get_value::<u32, _>(value_name) {
                return Ok(Some(value));
            }
        }
        Ok(None)
    }

    /// Applique les restrictions via le registre
    #[cfg(target_os = "windows")]
    fn apply_registry_restrictions(&self, profile: &LockdownProfile) -> Result<()> {
        let hkcu = RegKey::predef(HKEY_CURRENT_USER);
        let restrictions = &profile.system_restrictions;
        let desktop = &profile.desktop_restrictions;

        info!("Application des restrictions registre Windows...");

        // Cle Explorer policies
        let explorer_policies = r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer";

        // Desactiver le menu demarrer complet
        if desktop.disable_main_menu {
            self.write_reg_dword(hkcu.clone(), explorer_policies, "NoStartMenuMFUprogramsList", 1)?;
            self.write_reg_dword(hkcu.clone(), explorer_policies, "NoStartMenuMorePrograms", 1)?;
        }

        // Cacher les icones du bureau
        if desktop.hide_desktop_icons {
            self.write_reg_dword(hkcu.clone(), explorer_policies, "NoDesktop", 1)?;
        }

        // Desactiver le clic droit
        if desktop.disable_desktop_context_menu {
            self.write_reg_dword(hkcu.clone(), explorer_policies, "NoViewContextMenu", 1)?;
        }

        // Desactiver Run (Win+R)
        if desktop.disable_system_shortcuts {
            self.write_reg_dword(hkcu.clone(), explorer_policies, "NoRun", 1)?;
            // Desactiver Win+E (Explorer)
            self.write_reg_dword(hkcu.clone(), explorer_policies, "NoWinKeys", 1)?;
        }

        // Cle System policies
        let system_policies = r"Software\Microsoft\Windows\CurrentVersion\Policies\System";

        // Desactiver le gestionnaire de taches
        if restrictions.disable_terminal {
            self.write_reg_dword(hkcu.clone(), system_policies, "DisableTaskMgr", 1)?;
        }

        // Desactiver le panneau de configuration
        if restrictions.disable_settings {
            self.write_reg_dword(hkcu.clone(), explorer_policies, "NoControlPanel", 1)?;
        }

        // Desactiver le changement de mot de passe
        if restrictions.disable_user_switching {
            self.write_reg_dword(hkcu.clone(), system_policies, "DisableChangePassword", 1)?;
            self.write_reg_dword(hkcu.clone(), system_policies, "HideFastUserSwitching", 1)?;
        }

        // Desactiver l'arret
        if restrictions.disable_shutdown {
            self.write_reg_dword(hkcu.clone(), explorer_policies, "NoClose", 1)?;
        }

        Ok(())
    }

    /// Retire les restrictions du registre
    #[cfg(target_os = "windows")]
    fn remove_registry_restrictions(&self) -> Result<()> {
        let hkcu = RegKey::predef(HKEY_CURRENT_USER);

        info!("Retrait des restrictions registre Windows...");

        let explorer_policies = r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer";
        let system_policies = r"Software\Microsoft\Windows\CurrentVersion\Policies\System";

        // Explorer policies
        let explorer_values = [
            "NoStartMenuMFUprogramsList",
            "NoStartMenuMorePrograms",
            "NoDesktop",
            "NoViewContextMenu",
            "NoRun",
            "NoWinKeys",
            "NoControlPanel",
            "NoClose",
        ];

        for value in explorer_values {
            self.delete_reg_value(hkcu.clone(), explorer_policies, value)?;
        }

        // System policies
        let system_values = [
            "DisableTaskMgr",
            "DisableChangePassword",
            "HideFastUserSwitching",
        ];

        for value in system_values {
            self.delete_reg_value(hkcu.clone(), system_policies, value)?;
        }

        Ok(())
    }

    #[cfg(not(target_os = "windows"))]
    fn apply_registry_restrictions(&self, _profile: &LockdownProfile) -> Result<()> {
        warn!("Windows registry non disponible sur cette plateforme");
        Ok(())
    }

    #[cfg(not(target_os = "windows"))]
    fn remove_registry_restrictions(&self) -> Result<()> {
        Ok(())
    }
}

impl Default for WindowsLockdown {
    fn default() -> Self {
        Self::new()
    }
}

impl SystemLockdown for WindowsLockdown {
    fn apply(&self, profile: &LockdownProfile) -> Result<()> {
        info!("Application du profil de verrouillage Windows: {:?}", profile.profile_type);

        if !self.has_admin {
            warn!("Execution sans droits admin - certaines restrictions peuvent ne pas s'appliquer");
        }

        self.apply_registry_restrictions(profile)?;

        info!("Profil de verrouillage applique avec succes");
        Ok(())
    }

    fn remove(&self) -> Result<()> {
        info!("Retrait du verrouillage systeme Windows...");

        self.remove_registry_restrictions()?;

        info!("Verrouillage systeme retire");
        Ok(())
    }

    #[cfg(target_os = "windows")]
    fn is_locked(&self) -> Result<bool> {
        let hkcu = RegKey::predef(HKEY_CURRENT_USER);
        let system_policies = r"Software\Microsoft\Windows\CurrentVersion\Policies\System";

        if let Some(value) = self.read_reg_dword(&hkcu, system_policies, "DisableTaskMgr")? {
            if value == 1 {
                return Ok(true);
            }
        }
        Ok(false)
    }

    #[cfg(not(target_os = "windows"))]
    fn is_locked(&self) -> Result<bool> {
        Ok(false)
    }

    #[cfg(target_os = "windows")]
    fn get_current_restrictions(&self) -> Result<Vec<String>> {
        let mut restrictions = Vec::new();
        let hkcu = RegKey::predef(HKEY_CURRENT_USER);

        let checks = [
            (r"Software\Microsoft\Windows\CurrentVersion\Policies\System", "DisableTaskMgr", "Gestionnaire de taches desactive"),
            (r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer", "NoRun", "Win+R desactive"),
            (r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer", "NoDesktop", "Bureau cache"),
            (r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer", "NoControlPanel", "Panneau de configuration desactive"),
        ];

        for (subkey, value_name, description) in checks {
            if let Some(value) = self.read_reg_dword(&hkcu, subkey, value_name)? {
                if value == 1 {
                    restrictions.push(description.to_string());
                }
            }
        }

        Ok(restrictions)
    }

    #[cfg(not(target_os = "windows"))]
    fn get_current_restrictions(&self) -> Result<Vec<String>> {
        Ok(Vec::new())
    }
}

/// Configure l'auto-login Windows
#[cfg(target_os = "windows")]
pub fn configure_autologin(username: &str, password: &str) -> Result<()> {
    use winreg::enums::*;
    use winreg::RegKey;

    info!("Configuration auto-login Windows pour: {}", username);

    let hklm = RegKey::predef(HKEY_LOCAL_MACHINE);
    let winlogon_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon";

    let (key, _) = hklm
        .create_subkey(winlogon_path)
        .context("Impossible d'ouvrir la cle Winlogon")?;

    key.set_value("AutoAdminLogon", &"1")
        .context("Impossible de configurer AutoAdminLogon")?;

    key.set_value("DefaultUserName", &username)
        .context("Impossible de configurer DefaultUserName")?;

    key.set_value("DefaultPassword", &password)
        .context("Impossible de configurer DefaultPassword")?;

    // Optionnel: domaine
    key.set_value("DefaultDomainName", &".")
        .context("Impossible de configurer DefaultDomainName")?;

    info!("Auto-login Windows configure pour {}", username);
    Ok(())
}

#[cfg(not(target_os = "windows"))]
pub fn configure_autologin(_username: &str, _password: &str) -> Result<()> {
    bail!("Auto-login Windows non disponible sur cette plateforme")
}

/// Configure l'autostart Windows
#[cfg(target_os = "windows")]
pub fn configure_autostart(client_path: &str) -> Result<()> {
    use winreg::enums::*;
    use winreg::RegKey;

    info!("Configuration autostart Windows...");

    let hkcu = RegKey::predef(HKEY_CURRENT_USER);
    let run_path = r"Software\Microsoft\Windows\CurrentVersion\Run";

    let (key, _) = hkcu
        .create_subkey(run_path)
        .context("Impossible d'ouvrir la cle Run")?;

    key.set_value("EPNClient", &client_path)
        .context("Impossible de configurer l'autostart")?;

    info!("Autostart Windows configure: {}", client_path);
    Ok(())
}

#[cfg(not(target_os = "windows"))]
pub fn configure_autostart(_client_path: &str) -> Result<()> {
    bail!("Autostart Windows non disponible sur cette plateforme")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_lockdown_new() {
        let lockdown = WindowsLockdown::new();
        // Le test d'admin depend de l'environnement
        let _ = lockdown.has_admin;
    }
}
