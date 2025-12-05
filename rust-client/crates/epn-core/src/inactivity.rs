//! Module de surveillance d'inactivité
//!
//! Ce module détecte l'inactivité clavier/souris et avertit l'utilisateur
//! avant de terminer la session.

use std::time::Instant;
use tracing::{info, warn, debug};

/// Configuration de la surveillance d'inactivité
#[derive(Debug, Clone)]
pub struct InactivityConfig {
    /// Temps avant avertissement (secondes)
    pub warning_secs: u64,
    /// Temps avant fin de session (secondes)
    pub timeout_secs: u64,
    /// Activer la surveillance d'inactivité
    pub enabled: bool,
}

impl Default for InactivityConfig {
    fn default() -> Self {
        Self {
            warning_secs: 300,   // 5 minutes
            timeout_secs: 600,   // 10 minutes
            enabled: true,
        }
    }
}

/// État de l'inactivité
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum InactivityState {
    /// Utilisateur actif
    Active,
    /// Utilisateur inactif, avertissement affiché
    Warning,
    /// Temps d'inactivité dépassé
    Timeout,
}

/// Gestionnaire de surveillance d'inactivité
pub struct InactivityMonitor {
    config: InactivityConfig,
    last_activity: Instant,
    current_state: InactivityState,
    warning_shown: bool,
}

impl InactivityMonitor {
    /// Créer un nouveau moniteur d'inactivité
    pub fn new(config: InactivityConfig) -> Self {
        Self {
            config,
            last_activity: Instant::now(),
            current_state: InactivityState::Active,
            warning_shown: false,
        }
    }

    /// Vérifier l'état d'inactivité et retourner le nouvel état
    pub fn check(&mut self) -> InactivityState {
        if !self.config.enabled {
            return InactivityState::Active;
        }

        // Obtenir le temps d'inactivité du système
        let idle_secs = self.get_system_idle_time();

        debug!("Temps d'inactivité: {}s", idle_secs);

        // Déterminer l'état
        let new_state = if idle_secs >= self.config.timeout_secs {
            InactivityState::Timeout
        } else if idle_secs >= self.config.warning_secs {
            InactivityState::Warning
        } else {
            InactivityState::Active
        };

        // Log les changements d'état
        if new_state != self.current_state {
            match new_state {
                InactivityState::Active => {
                    info!("Activité détectée, réinitialisation du compteur");
                    self.warning_shown = false;
                }
                InactivityState::Warning => {
                    warn!("Inactivité détectée depuis {}s, avertissement", idle_secs);
                }
                InactivityState::Timeout => {
                    warn!("Timeout d'inactivité après {}s", idle_secs);
                }
            }
            self.current_state = new_state;
        }

        new_state
    }

    /// Réinitialiser le compteur d'inactivité (après interaction utilisateur)
    pub fn reset(&mut self) {
        self.last_activity = Instant::now();
        self.current_state = InactivityState::Active;
        self.warning_shown = false;
        info!("Compteur d'inactivité réinitialisé");
    }

    /// Marquer que l'avertissement a été affiché
    pub fn mark_warning_shown(&mut self) {
        self.warning_shown = true;
    }

    /// Vérifier si l'avertissement a déjà été affiché
    pub fn is_warning_shown(&self) -> bool {
        self.warning_shown
    }

    /// Obtenir le temps d'inactivité restant avant timeout (en secondes)
    pub fn time_until_timeout(&self) -> u64 {
        let idle_secs = self.get_system_idle_time();
        self.config.timeout_secs.saturating_sub(idle_secs)
    }

    /// Obtenir le temps d'inactivité du système
    fn get_system_idle_time(&self) -> u64 {
        #[cfg(target_os = "linux")]
        {
            self.get_linux_idle_time()
        }

        #[cfg(target_os = "windows")]
        {
            self.get_windows_idle_time()
        }

        #[cfg(not(any(target_os = "linux", target_os = "windows")))]
        {
            // Fallback: utiliser le temps depuis la dernière réinitialisation
            self.last_activity.elapsed().as_secs()
        }
    }

    /// Obtenir le temps d'inactivité sous Linux
    #[cfg(target_os = "linux")]
    fn get_linux_idle_time(&self) -> u64 {
        // Essayer plusieurs méthodes

        // 1. Essayer X11 via xprintidle (si disponible)
        if let Ok(output) = std::process::Command::new("xprintidle").output() {
            if output.status.success() {
                if let Ok(ms_str) = String::from_utf8(output.stdout) {
                    if let Ok(ms) = ms_str.trim().parse::<u64>() {
                        return ms / 1000; // Convertir ms en secondes
                    }
                }
            }
        }

        // 2. Essayer de lire /proc/interrupts pour estimer l'activité
        // (moins précis, mais ne nécessite pas X11)
        // Cette méthode est complexe et nécessite un état persistant

        // 3. Fallback: utiliser le temps depuis la dernière réinitialisation manuelle
        self.last_activity.elapsed().as_secs()
    }

    /// Obtenir le temps d'inactivité sous Windows
    #[cfg(target_os = "windows")]
    fn get_windows_idle_time(&self) -> u64 {
        use std::mem;

        #[repr(C)]
        struct LASTINPUTINFO {
            cb_size: u32,
            dw_time: u32,
        }

        #[link(name = "user32")]
        extern "system" {
            fn GetLastInputInfo(plii: *mut LASTINPUTINFO) -> i32;
            fn GetTickCount() -> u32;
        }

        unsafe {
            let mut lii = LASTINPUTINFO {
                cb_size: mem::size_of::<LASTINPUTINFO>() as u32,
                dw_time: 0,
            };

            if GetLastInputInfo(&mut lii) != 0 {
                let tick_count = GetTickCount();
                let idle_ms = tick_count.wrapping_sub(lii.dw_time);
                return (idle_ms / 1000) as u64;
            }
        }

        // Fallback
        self.last_activity.elapsed().as_secs()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_inactivity_config_default() {
        let config = InactivityConfig::default();
        assert_eq!(config.warning_secs, 300);
        assert_eq!(config.timeout_secs, 600);
        assert!(config.enabled);
    }

    #[test]
    fn test_inactivity_monitor_new() {
        let config = InactivityConfig::default();
        let monitor = InactivityMonitor::new(config);
        assert_eq!(monitor.current_state, InactivityState::Active);
        assert!(!monitor.warning_shown);
    }

    #[test]
    fn test_inactivity_monitor_reset() {
        let config = InactivityConfig::default();
        let mut monitor = InactivityMonitor::new(config);
        monitor.current_state = InactivityState::Warning;
        monitor.warning_shown = true;

        monitor.reset();

        assert_eq!(monitor.current_state, InactivityState::Active);
        assert!(!monitor.warning_shown);
    }

    #[test]
    fn test_inactivity_disabled() {
        let config = InactivityConfig {
            enabled: false,
            ..Default::default()
        };
        let mut monitor = InactivityMonitor::new(config);

        // Même après un long moment, devrait rester actif si désactivé
        assert_eq!(monitor.check(), InactivityState::Active);
    }
}
