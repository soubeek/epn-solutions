//! Module de nettoyage en fin de session
//!
//! Ce module gère le nettoyage des données utilisateur après une session,
//! incluant les navigateurs, bureautique, documents et launchers de jeux.

use std::fs;
use std::path::{Path, PathBuf};
use tracing::{info, warn, debug};

/// Type de poste (détermine les éléments à nettoyer)
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PosteType {
    Bureautique,
    Gaming,
}

impl Default for PosteType {
    fn default() -> Self {
        PosteType::Bureautique
    }
}

impl From<&str> for PosteType {
    fn from(s: &str) -> Self {
        match s.to_lowercase().as_str() {
            "gaming" => PosteType::Gaming,
            _ => PosteType::Bureautique,
        }
    }
}

/// Configuration du nettoyage
#[derive(Debug, Clone)]
pub struct CleanupConfig {
    /// Type de poste
    pub poste_type: PosteType,
    /// Nettoyer Firefox
    pub clean_firefox: bool,
    /// Nettoyer LibreOffice
    pub clean_libreoffice: bool,
    /// Nettoyer les documents utilisateur
    pub clean_user_documents: bool,
    /// Nettoyer l'historique système
    pub clean_system_history: bool,
    /// Nettoyer les launchers gaming (Steam, Epic, etc.)
    pub clean_gaming_launchers: bool,
    /// Dossiers personnalisés à nettoyer
    pub custom_paths: Vec<PathBuf>,
    /// Patterns à exclure du nettoyage
    pub exclude_patterns: Vec<String>,
}

impl Default for CleanupConfig {
    fn default() -> Self {
        Self {
            poste_type: PosteType::Bureautique,
            clean_firefox: true,
            clean_libreoffice: true,
            clean_user_documents: true,
            clean_system_history: true,
            clean_gaming_launchers: false,
            custom_paths: Vec::new(),
            exclude_patterns: Vec::new(),
        }
    }
}

impl CleanupConfig {
    /// Configuration pour poste bureautique
    pub fn bureautique() -> Self {
        Self {
            poste_type: PosteType::Bureautique,
            clean_firefox: true,
            clean_libreoffice: true,
            clean_user_documents: true,
            clean_system_history: true,
            clean_gaming_launchers: false,
            ..Default::default()
        }
    }

    /// Configuration pour poste gaming
    pub fn gaming() -> Self {
        Self {
            poste_type: PosteType::Gaming,
            clean_firefox: true,
            clean_libreoffice: false,
            clean_user_documents: true,
            clean_system_history: true,
            clean_gaming_launchers: true,
            ..Default::default()
        }
    }
}

/// Résultat du nettoyage
#[derive(Debug, Default)]
pub struct CleanupResult {
    /// Nombre de fichiers supprimés
    pub files_deleted: u64,
    /// Nombre de dossiers supprimés
    pub dirs_deleted: u64,
    /// Espace libéré (octets)
    pub bytes_freed: u64,
    /// Erreurs rencontrées
    pub errors: Vec<String>,
}

impl CleanupResult {
    fn add_error(&mut self, msg: impl Into<String>) {
        self.errors.push(msg.into());
    }
}

/// Gestionnaire de nettoyage
pub struct CleanupManager {
    config: CleanupConfig,
    home_dir: PathBuf,
}

impl CleanupManager {
    /// Créer un nouveau gestionnaire de nettoyage
    pub fn new(config: CleanupConfig) -> Self {
        let home_dir = dirs::home_dir().unwrap_or_else(|| PathBuf::from("/tmp"));
        Self { config, home_dir }
    }

    /// Exécuter le nettoyage complet
    pub fn run_cleanup(&self) -> CleanupResult {
        let mut result = CleanupResult::default();

        info!("=== Début du nettoyage ({:?}) ===", self.config.poste_type);

        // Nettoyage bureautique
        if self.config.clean_firefox {
            self.clean_firefox(&mut result);
        }

        if self.config.clean_libreoffice {
            self.clean_libreoffice(&mut result);
        }

        if self.config.clean_user_documents {
            self.clean_user_documents(&mut result);
        }

        if self.config.clean_system_history {
            self.clean_system_history(&mut result);
        }

        // Nettoyage gaming (Windows)
        if self.config.clean_gaming_launchers {
            self.clean_gaming_launchers(&mut result);
        }

        // Dossiers personnalisés
        for path in &self.config.custom_paths {
            self.clean_directory(path, &mut result);
        }

        info!(
            "=== Nettoyage terminé: {} fichiers, {} dossiers, {} octets libérés, {} erreurs ===",
            result.files_deleted, result.dirs_deleted, result.bytes_freed, result.errors.len()
        );

        result
    }

    /// Nettoyer Firefox (suppression complète + restauration template)
    fn clean_firefox(&self, result: &mut CleanupResult) {
        info!("Nettoyage Firefox...");

        #[cfg(target_os = "linux")]
        {
            // 1. Tuer Firefox
            info!("Arrêt de Firefox...");
            let _ = std::process::Command::new("pkill")
                .arg("-9")
                .arg("firefox")
                .output();

            // Attendre que Firefox se ferme
            std::thread::sleep(std::time::Duration::from_millis(500));

            let firefox_dir = self.home_dir.join(".mozilla/firefox");
            let cache_dir = self.home_dir.join(".cache/mozilla/firefox");
            let template_dir = PathBuf::from("/usr/share/epn/firefox-template");

            // 2. Supprimer le profil actuel complet
            if firefox_dir.exists() {
                info!("Suppression du profil Firefox...");
                self.clean_directory(&firefox_dir, result);
            }

            // 3. Supprimer le cache Firefox
            if cache_dir.exists() {
                info!("Suppression du cache Firefox...");
                self.clean_directory(&cache_dir, result);
            }

            // 4. Restaurer le template si existe
            if template_dir.exists() {
                info!("Restauration du profil Firefox template...");
                if let Err(e) = fs::create_dir_all(&firefox_dir) {
                    warn!("Impossible de créer {:?}: {}", firefox_dir, e);
                    result.add_error(format!("Création {:?}: {}", firefox_dir, e));
                } else if let Err(e) = self.copy_dir_recursive(&template_dir, &firefox_dir) {
                    warn!("Impossible de restaurer le template Firefox: {}", e);
                    result.add_error(format!("Restauration template Firefox: {}", e));
                } else {
                    info!("Profil Firefox restauré depuis le template");
                }
            } else {
                debug!("Pas de template Firefox trouvé dans {:?}", template_dir);
            }
        }

        #[cfg(target_os = "windows")]
        {
            if let Some(appdata) = dirs::data_local_dir() {
                let firefox_dir = appdata.join("Mozilla/Firefox/Profiles");
                if firefox_dir.exists() {
                    if let Ok(entries) = fs::read_dir(&firefox_dir) {
                        for entry in entries.flatten() {
                            let path = entry.path();
                            if path.is_dir() {
                                self.clean_directory(&path.join("cache2"), result);
                                self.delete_file(&path.join("cookies.sqlite"), result);
                                self.delete_file(&path.join("places.sqlite"), result);
                                self.clean_directory(&path.join("sessionstore-backups"), result);
                                self.delete_file(&path.join("formhistory.sqlite"), result);
                            }
                        }
                    }
                }
            }
        }
    }

    /// Copier récursivement un dossier
    fn copy_dir_recursive(&self, src: &Path, dst: &Path) -> std::io::Result<()> {
        if !dst.exists() {
            fs::create_dir_all(dst)?;
        }

        for entry in fs::read_dir(src)? {
            let entry = entry?;
            let src_path = entry.path();
            let dst_path = dst.join(entry.file_name());

            if src_path.is_dir() {
                self.copy_dir_recursive(&src_path, &dst_path)?;
            } else {
                fs::copy(&src_path, &dst_path)?;
            }
        }

        Ok(())
    }

    /// Nettoyer LibreOffice
    fn clean_libreoffice(&self, result: &mut CleanupResult) {
        info!("Nettoyage LibreOffice...");

        #[cfg(target_os = "linux")]
        {
            let libreoffice_dir = self.home_dir.join(".config/libreoffice/4/user");
            if libreoffice_dir.exists() {
                // Backups
                self.clean_directory(&libreoffice_dir.join("backup"), result);
                // Fichiers récents
                self.delete_file(&libreoffice_dir.join("registrymodifications.xcu"), result);
            }
        }

        #[cfg(target_os = "windows")]
        {
            if let Some(appdata) = dirs::config_dir() {
                let libreoffice_dir = appdata.join("LibreOffice/4/user");
                if libreoffice_dir.exists() {
                    self.clean_directory(&libreoffice_dir.join("backup"), result);
                }
            }
        }
    }

    /// Nettoyer les documents utilisateur
    fn clean_user_documents(&self, result: &mut CleanupResult) {
        info!("Nettoyage des documents utilisateur...");

        let user_dirs = [
            dirs::document_dir(),
            dirs::download_dir(),
            dirs::desktop_dir(),
            dirs::picture_dir(),
            dirs::video_dir(),
        ];

        for dir in user_dirs.iter().flatten() {
            self.clean_directory_contents(dir, result);
        }

        // Dossier temporaire utilisateur
        #[cfg(target_os = "linux")]
        {
            self.clean_directory(&self.home_dir.join(".cache"), result);
        }

        #[cfg(target_os = "windows")]
        {
            if let Some(temp_dir) = dirs::cache_dir() {
                self.clean_directory(&temp_dir, result);
            }
        }
    }

    /// Nettoyer l'historique système
    fn clean_system_history(&self, result: &mut CleanupResult) {
        info!("Nettoyage de l'historique système...");

        #[cfg(target_os = "linux")]
        {
            // Historique bash
            self.delete_file(&self.home_dir.join(".bash_history"), result);
            // Historique zsh
            self.delete_file(&self.home_dir.join(".zsh_history"), result);
            // Fichiers récents (GNOME/GTK)
            self.delete_file(&self.home_dir.join(".local/share/recently-used.xbel"), result);
            // Corbeille
            self.clean_directory(&self.home_dir.join(".local/share/Trash/files"), result);
            self.clean_directory(&self.home_dir.join(".local/share/Trash/info"), result);
        }

        #[cfg(target_os = "windows")]
        {
            // Windows Recent
            if let Some(appdata) = dirs::data_dir() {
                self.clean_directory(&appdata.join("Microsoft/Windows/Recent"), result);
            }
        }
    }

    /// Nettoyer les launchers gaming (Windows principalement)
    fn clean_gaming_launchers(&self, result: &mut CleanupResult) {
        info!("Nettoyage des launchers gaming...");

        #[cfg(target_os = "windows")]
        {
            // Steam
            self.clean_steam(result);
            // Epic Games
            self.clean_epic_games(result);
            // GOG Galaxy
            self.clean_gog_galaxy(result);
            // Ubisoft Connect
            self.clean_ubisoft_connect(result);
            // EA App
            self.clean_ea_app(result);
        }

        #[cfg(target_os = "linux")]
        {
            // Steam sur Linux
            let steam_dir = self.home_dir.join(".steam/steam");
            if steam_dir.exists() {
                // Déconnecter les utilisateurs
                self.clean_directory(&steam_dir.join("userdata"), result);
                self.delete_file(&steam_dir.join("config/loginusers.vdf"), result);
            }
        }
    }

    #[cfg(target_os = "windows")]
    fn clean_steam(&self, result: &mut CleanupResult) {
        info!("  - Steam");

        // Chemin Steam standard
        let steam_paths = [
            PathBuf::from("C:/Program Files (x86)/Steam"),
            PathBuf::from("C:/Program Files/Steam"),
        ];

        for steam_dir in &steam_paths {
            if steam_dir.exists() {
                // Profils utilisateur (ne supprime pas les jeux)
                self.clean_directory(&steam_dir.join("userdata"), result);
                // Fichier de connexion
                self.delete_file(&steam_dir.join("config/loginusers.vdf"), result);
                // Cache HTML
                if let Some(local_app) = dirs::data_local_dir() {
                    self.clean_directory(&local_app.join("Steam/htmlcache"), result);
                }
                break;
            }
        }
    }

    #[cfg(target_os = "windows")]
    fn clean_epic_games(&self, result: &mut CleanupResult) {
        info!("  - Epic Games");

        if let Some(local_app) = dirs::data_local_dir() {
            let epic_dir = local_app.join("EpicGamesLauncher/Saved");
            if epic_dir.exists() {
                self.clean_directory(&epic_dir.join("Config"), result);
                self.clean_directory(&epic_dir.join("Logs"), result);
                self.clean_directory(&epic_dir.join("webcache"), result);
            }
        }
    }

    #[cfg(target_os = "windows")]
    fn clean_gog_galaxy(&self, result: &mut CleanupResult) {
        info!("  - GOG Galaxy");

        if let Some(local_app) = dirs::data_local_dir() {
            self.clean_directory(&local_app.join("GOG.com/Galaxy/webcache"), result);
            self.clean_directory(&local_app.join("GOG.com/Galaxy/logs"), result);
        }

        if let Some(program_data) = dirs::data_dir() {
            self.clean_directory(&program_data.join("GOG.com/Galaxy/logs"), result);
        }
    }

    #[cfg(target_os = "windows")]
    fn clean_ubisoft_connect(&self, result: &mut CleanupResult) {
        info!("  - Ubisoft Connect");

        if let Some(local_app) = dirs::data_local_dir() {
            let ubi_dir = local_app.join("Ubisoft Game Launcher");
            if ubi_dir.exists() {
                self.clean_directory(&ubi_dir.join("cache"), result);
                self.clean_directory(&ubi_dir.join("logs"), result);
            }
        }
    }

    #[cfg(target_os = "windows")]
    fn clean_ea_app(&self, result: &mut CleanupResult) {
        info!("  - EA App");

        if let Some(local_app) = dirs::data_local_dir() {
            let ea_dir = local_app.join("Electronic Arts/EA Desktop");
            if ea_dir.exists() {
                self.clean_directory(&ea_dir.join("cache"), result);
                self.clean_directory(&ea_dir.join("logs"), result);
            }
        }
    }

    /// Supprimer un fichier
    fn delete_file(&self, path: &Path, result: &mut CleanupResult) {
        if !path.exists() {
            return;
        }

        // Vérifier les exclusions
        if self.is_excluded(path) {
            debug!("Fichier exclu: {:?}", path);
            return;
        }

        match fs::metadata(path) {
            Ok(meta) => {
                let size = meta.len();
                match fs::remove_file(path) {
                    Ok(_) => {
                        debug!("Supprimé: {:?}", path);
                        result.files_deleted += 1;
                        result.bytes_freed += size;
                    }
                    Err(e) => {
                        warn!("Impossible de supprimer {:?}: {}", path, e);
                        result.add_error(format!("Fichier {:?}: {}", path, e));
                    }
                }
            }
            Err(e) => {
                warn!("Impossible de lire {:?}: {}", path, e);
            }
        }
    }

    /// Supprimer un dossier et son contenu
    fn clean_directory(&self, path: &Path, result: &mut CleanupResult) {
        if !path.exists() {
            return;
        }

        if self.is_excluded(path) {
            debug!("Dossier exclu: {:?}", path);
            return;
        }

        debug!("Nettoyage du dossier: {:?}", path);

        match fs::remove_dir_all(path) {
            Ok(_) => {
                result.dirs_deleted += 1;
                info!("Dossier supprimé: {:?}", path);
            }
            Err(e) => {
                warn!("Impossible de supprimer le dossier {:?}: {}", path, e);
                result.add_error(format!("Dossier {:?}: {}", path, e));
            }
        }
    }

    /// Supprimer le contenu d'un dossier (mais garder le dossier)
    fn clean_directory_contents(&self, path: &Path, result: &mut CleanupResult) {
        if !path.exists() {
            return;
        }

        if self.is_excluded(path) {
            debug!("Dossier exclu: {:?}", path);
            return;
        }

        debug!("Nettoyage du contenu de: {:?}", path);

        if let Ok(entries) = fs::read_dir(path) {
            for entry in entries.flatten() {
                let entry_path = entry.path();

                if self.is_excluded(&entry_path) {
                    continue;
                }

                if entry_path.is_dir() {
                    self.clean_directory(&entry_path, result);
                } else {
                    self.delete_file(&entry_path, result);
                }
            }
        }
    }

    /// Vérifier si un chemin est exclu du nettoyage
    fn is_excluded(&self, path: &Path) -> bool {
        let path_str = path.to_string_lossy();

        for pattern in &self.config.exclude_patterns {
            if path_str.contains(pattern) {
                return true;
            }
        }

        false
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cleanup_config_defaults() {
        let config = CleanupConfig::default();
        assert!(config.clean_firefox);
        assert!(config.clean_libreoffice);
        assert!(!config.clean_gaming_launchers);
    }

    #[test]
    fn test_cleanup_config_gaming() {
        let config = CleanupConfig::gaming();
        assert!(config.clean_gaming_launchers);
        assert!(!config.clean_libreoffice);
    }

    #[test]
    fn test_poste_type_from_str() {
        assert_eq!(PosteType::from("gaming"), PosteType::Gaming);
        assert_eq!(PosteType::from("Gaming"), PosteType::Gaming);
        assert_eq!(PosteType::from("bureautique"), PosteType::Bureautique);
        assert_eq!(PosteType::from("unknown"), PosteType::Bureautique);
    }
}
