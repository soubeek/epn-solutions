//! Gestion de la whitelist d'applications
//!
//! Permet de restreindre les applications accessibles aux utilisateurs.

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::path::PathBuf;
use tracing::{info, warn, debug};

/// Restriction d'application
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppRestriction {
    /// Identifiant de l'application (nom du .desktop ou chemin)
    pub app_id: String,
    /// Nom affiche
    pub display_name: String,
    /// Autorisee ou bloquee
    pub allowed: bool,
    /// Categorie (bureautique, multimedia, gaming, etc.)
    pub category: Option<String>,
}

/// Whitelist d'applications
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct AppWhitelist {
    /// Applications autorisees
    apps: HashSet<String>,
    /// Mode strict (bloquer tout ce qui n'est pas dans la liste)
    strict_mode: bool,
}

impl AppWhitelist {
    /// Cree une nouvelle whitelist vide
    pub fn new() -> Self {
        Self {
            apps: HashSet::new(),
            strict_mode: true,
        }
    }

    /// Cree une whitelist avec des applications par defaut
    pub fn with_defaults() -> Self {
        let mut whitelist = Self::new();
        whitelist.add("firefox");
        whitelist.add("libreoffice-writer");
        whitelist.add("libreoffice-calc");
        whitelist.add("libreoffice-impress");
        whitelist
    }

    /// Ajoute une application a la whitelist
    pub fn add(&mut self, app_id: &str) {
        self.apps.insert(app_id.to_lowercase());
    }

    /// Retire une application de la whitelist
    pub fn remove(&mut self, app_id: &str) {
        self.apps.remove(&app_id.to_lowercase());
    }

    /// Verifie si une application est autorisee
    pub fn is_allowed(&self, app_id: &str) -> bool {
        if !self.strict_mode {
            return true;
        }
        self.apps.contains(&app_id.to_lowercase())
    }

    /// Retourne la liste des applications autorisees
    pub fn allowed_apps(&self) -> Vec<&String> {
        self.apps.iter().collect()
    }

    /// Active/desactive le mode strict
    pub fn set_strict_mode(&mut self, strict: bool) {
        self.strict_mode = strict;
    }
}

/// Gestionnaire d'applications pour Linux
#[cfg(target_os = "linux")]
pub struct LinuxAppManager {
    /// Dossiers contenant les fichiers .desktop
    desktop_dirs: Vec<PathBuf>,
    /// Whitelist active
    whitelist: AppWhitelist,
}

#[cfg(target_os = "linux")]
impl LinuxAppManager {
    /// Cree un nouveau gestionnaire
    pub fn new(whitelist: AppWhitelist) -> Self {
        let desktop_dirs = vec![
            PathBuf::from("/usr/share/applications"),
            PathBuf::from("/usr/local/share/applications"),
            dirs::data_dir()
                .map(|p| p.join("applications"))
                .unwrap_or_else(|| PathBuf::from("~/.local/share/applications")),
        ];

        Self {
            desktop_dirs,
            whitelist,
        }
    }

    /// Applique la whitelist en modifiant les fichiers .desktop
    pub fn apply_whitelist(&self) -> Result<()> {
        info!("Application de la whitelist d'applications...");

        let hidden_dir = dirs::data_dir()
            .map(|p| p.join("applications"))
            .unwrap_or_else(|| PathBuf::from("~/.local/share/applications"));

        std::fs::create_dir_all(&hidden_dir)
            .context("Impossible de creer le dossier applications")?;

        for dir in &self.desktop_dirs {
            if !dir.exists() {
                continue;
            }

            if let Ok(entries) = std::fs::read_dir(dir) {
                for entry in entries.flatten() {
                    let path = entry.path();
                    if path.extension().map(|e| e == "desktop").unwrap_or(false) {
                        self.process_desktop_file(&path, &hidden_dir)?;
                    }
                }
            }
        }

        info!("Whitelist appliquee");
        Ok(())
    }

    /// Traite un fichier .desktop
    fn process_desktop_file(&self, path: &PathBuf, hidden_dir: &PathBuf) -> Result<()> {
        let filename = path.file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("");

        // Extraire l'identifiant de l'application
        let app_id = filename.trim_end_matches(".desktop");

        if !self.whitelist.is_allowed(app_id) {
            // Creer un fichier .desktop qui cache l'application
            let hidden_path = hidden_dir.join(filename);
            let content = format!(r#"[Desktop Entry]
Name={}
NoDisplay=true
Hidden=true
"#, app_id);

            std::fs::write(&hidden_path, content)
                .context(format!("Impossible de cacher {}", app_id))?;

            debug!("Application cachee: {}", app_id);
        }

        Ok(())
    }

    /// Retire la whitelist (restaure toutes les applications)
    pub fn remove_whitelist(&self) -> Result<()> {
        info!("Retrait de la whitelist d'applications...");

        let hidden_dir = dirs::data_dir()
            .map(|p| p.join("applications"))
            .unwrap_or_else(|| PathBuf::from("~/.local/share/applications"));

        if hidden_dir.exists() {
            if let Ok(entries) = std::fs::read_dir(&hidden_dir) {
                for entry in entries.flatten() {
                    let path = entry.path();
                    // Supprimer les fichiers .desktop qui cachent des apps
                    if path.extension().map(|e| e == "desktop").unwrap_or(false) {
                        if let Ok(content) = std::fs::read_to_string(&path) {
                            if content.contains("NoDisplay=true") && content.contains("Hidden=true") {
                                std::fs::remove_file(&path)?;
                                debug!("Fichier de masquage supprime: {:?}", path);
                            }
                        }
                    }
                }
            }
        }

        // Rafraichir le cache des applications
        let _ = std::process::Command::new("update-desktop-database")
            .arg(&hidden_dir)
            .output();

        info!("Whitelist retiree");
        Ok(())
    }

    /// Liste les applications disponibles
    pub fn list_available_apps(&self) -> Result<Vec<String>> {
        let mut apps = Vec::new();

        for dir in &self.desktop_dirs {
            if !dir.exists() {
                continue;
            }

            if let Ok(entries) = std::fs::read_dir(dir) {
                for entry in entries.flatten() {
                    let path = entry.path();
                    if path.extension().map(|e| e == "desktop").unwrap_or(false) {
                        if let Some(filename) = path.file_name().and_then(|n| n.to_str()) {
                            let app_id = filename.trim_end_matches(".desktop").to_string();
                            if !apps.contains(&app_id) {
                                apps.push(app_id);
                            }
                        }
                    }
                }
            }
        }

        apps.sort();
        Ok(apps)
    }
}

/// Gestionnaire d'applications pour Windows
#[cfg(target_os = "windows")]
pub struct WindowsAppManager {
    whitelist: AppWhitelist,
}

#[cfg(target_os = "windows")]
impl WindowsAppManager {
    pub fn new(whitelist: AppWhitelist) -> Self {
        Self { whitelist }
    }

    /// Applique la whitelist via AppLocker ou Software Restriction Policies
    pub fn apply_whitelist(&self) -> Result<()> {
        info!("Application de la whitelist Windows...");
        warn!("La whitelist Windows via AppLocker necessite Windows Enterprise/Education");
        // Implementation AppLocker ou SRP a completer
        Ok(())
    }

    pub fn remove_whitelist(&self) -> Result<()> {
        info!("Retrait de la whitelist Windows...");
        Ok(())
    }
}

/// Applications predefinies par categorie
pub mod presets {
    use super::AppWhitelist;

    /// Applications bureautique
    pub fn office_apps() -> AppWhitelist {
        let mut whitelist = AppWhitelist::new();
        whitelist.add("firefox");
        whitelist.add("libreoffice-writer");
        whitelist.add("libreoffice-calc");
        whitelist.add("libreoffice-impress");
        whitelist.add("libreoffice-draw");
        whitelist.add("evince");  // Lecteur PDF
        whitelist.add("eog");     // Visionneuse images
        whitelist
    }

    /// Applications gaming
    pub fn gaming_apps() -> AppWhitelist {
        let mut whitelist = AppWhitelist::new();
        whitelist.add("firefox");
        whitelist.add("steam");
        whitelist.add("com.heroicgameslauncher.hgl");
        whitelist.add("lutris");
        whitelist.add("discord");
        whitelist
    }

    /// Applications multimedia
    pub fn multimedia_apps() -> AppWhitelist {
        let mut whitelist = AppWhitelist::new();
        whitelist.add("firefox");
        whitelist.add("vlc");
        whitelist.add("gimp");
        whitelist.add("inkscape");
        whitelist.add("audacity");
        whitelist.add("kdenlive");
        whitelist
    }

    /// Applications minimales (navigation uniquement)
    pub fn minimal_apps() -> AppWhitelist {
        let mut whitelist = AppWhitelist::new();
        whitelist.add("firefox");
        whitelist
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_whitelist_basic() {
        let mut whitelist = AppWhitelist::new();
        whitelist.add("firefox");

        assert!(whitelist.is_allowed("firefox"));
        assert!(whitelist.is_allowed("Firefox")); // Case insensitive
        assert!(!whitelist.is_allowed("chrome"));
    }

    #[test]
    fn test_whitelist_non_strict() {
        let mut whitelist = AppWhitelist::new();
        whitelist.set_strict_mode(false);

        assert!(whitelist.is_allowed("any-app"));
    }

    #[test]
    fn test_presets() {
        let office = presets::office_apps();
        assert!(office.is_allowed("libreoffice-writer"));
        assert!(!office.is_allowed("steam"));

        let gaming = presets::gaming_apps();
        assert!(gaming.is_allowed("steam"));
    }
}
