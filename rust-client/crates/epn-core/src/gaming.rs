// Module de gestion des launchers gaming
//
// Ce module gère le démarrage et l'arrêt des launchers de jeux
// pour les postes de type "gaming".

use std::path::PathBuf;
use std::process::Command;
use tracing::{debug, error, info, warn};

/// Launchers de jeux supportés
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GameLauncher {
    Steam,
    EpicGames,
    GOGGalaxy,
    UbisoftConnect,
    EAApp,
}

impl GameLauncher {
    /// Nom d'affichage du launcher
    pub fn display_name(&self) -> &'static str {
        match self {
            GameLauncher::Steam => "Steam",
            GameLauncher::EpicGames => "Epic Games",
            GameLauncher::GOGGalaxy => "GOG Galaxy",
            GameLauncher::UbisoftConnect => "Ubisoft Connect",
            GameLauncher::EAApp => "EA App",
        }
    }

    /// Nom du processus (pour la détection)
    pub fn process_name(&self) -> &'static str {
        match self {
            GameLauncher::Steam => {
                #[cfg(target_os = "windows")]
                { "steam.exe" }
                #[cfg(not(target_os = "windows"))]
                { "steam" }
            }
            GameLauncher::EpicGames => "EpicGamesLauncher.exe",
            GameLauncher::GOGGalaxy => "GalaxyClient.exe",
            GameLauncher::UbisoftConnect => "upc.exe",
            GameLauncher::EAApp => "EADesktop.exe",
        }
    }

    /// Tous les launchers disponibles
    pub fn all() -> Vec<GameLauncher> {
        vec![
            GameLauncher::Steam,
            GameLauncher::EpicGames,
            GameLauncher::GOGGalaxy,
            GameLauncher::UbisoftConnect,
            GameLauncher::EAApp,
        ]
    }

    /// Parse depuis une string
    pub fn from_str(s: &str) -> Option<GameLauncher> {
        match s.to_lowercase().as_str() {
            "steam" => Some(GameLauncher::Steam),
            "epic" | "epicgames" | "epic_games" => Some(GameLauncher::EpicGames),
            "gog" | "goggalaxy" | "gog_galaxy" => Some(GameLauncher::GOGGalaxy),
            "ubisoft" | "uplay" | "ubisoftconnect" | "ubisoft_connect" => Some(GameLauncher::UbisoftConnect),
            "ea" | "eaapp" | "ea_app" | "origin" => Some(GameLauncher::EAApp),
            _ => None,
        }
    }
}

/// Configuration gaming
#[derive(Debug, Clone)]
pub struct GamingConfig {
    /// Launchers à démarrer automatiquement au début de session
    pub auto_start_launchers: Vec<GameLauncher>,
    /// Fermer les launchers en fin de session
    pub close_launchers_on_end: bool,
    /// Fermer tous les jeux en cours en fin de session
    pub close_games_on_end: bool,
    /// Démarrer Steam en mode Big Picture
    pub steam_big_picture: bool,
    /// Chemin personnalisé vers Steam (optionnel)
    pub steam_path: Option<PathBuf>,
    /// Chemin personnalisé vers Epic Games (optionnel)
    pub epic_path: Option<PathBuf>,
    /// Chemin personnalisé vers GOG Galaxy (optionnel)
    pub gog_path: Option<PathBuf>,
}

impl Default for GamingConfig {
    fn default() -> Self {
        Self {
            auto_start_launchers: vec![GameLauncher::Steam],
            close_launchers_on_end: true,
            close_games_on_end: true,
            steam_big_picture: false,
            steam_path: None,
            epic_path: None,
            gog_path: None,
        }
    }
}

/// Gestionnaire des launchers gaming
pub struct GamingManager {
    config: GamingConfig,
}

impl GamingManager {
    /// Créer un nouveau gestionnaire
    pub fn new(config: GamingConfig) -> Self {
        Self { config }
    }

    /// Démarrer les launchers configurés au début de session
    pub fn start_session_launchers(&self) {
        info!("Démarrage des launchers gaming pour la session");

        for launcher in &self.config.auto_start_launchers {
            if let Err(e) = self.start_launcher(*launcher) {
                warn!("Impossible de démarrer {}: {}", launcher.display_name(), e);
            }
        }
    }

    /// Arrêter les launchers et jeux en fin de session
    pub fn end_session_launchers(&self) {
        info!("Arrêt des launchers gaming en fin de session");

        if self.config.close_games_on_end {
            self.close_all_games();
        }

        if self.config.close_launchers_on_end {
            for launcher in GameLauncher::all() {
                if let Err(e) = self.stop_launcher(launcher) {
                    debug!("Erreur arrêt {}: {}", launcher.display_name(), e);
                }
            }
        }
    }

    /// Démarrer un launcher spécifique
    pub fn start_launcher(&self, launcher: GameLauncher) -> Result<(), String> {
        let path = self.get_launcher_path(launcher)?;

        info!("Démarrage de {} depuis {:?}", launcher.display_name(), path);

        let mut cmd = Command::new(&path);

        // Arguments spéciaux pour Steam
        if launcher == GameLauncher::Steam && self.config.steam_big_picture {
            cmd.arg("-bigpicture");
        }

        #[cfg(target_os = "windows")]
        {
            use std::os::windows::process::CommandExt;
            // CREATE_NO_WINDOW pour ne pas afficher de console
            cmd.creation_flags(0x08000000);
        }

        match cmd.spawn() {
            Ok(_) => {
                info!("{} démarré avec succès", launcher.display_name());
                Ok(())
            }
            Err(e) => {
                error!("Erreur démarrage {}: {}", launcher.display_name(), e);
                Err(format!("Erreur démarrage: {}", e))
            }
        }
    }

    /// Arrêter un launcher spécifique
    pub fn stop_launcher(&self, launcher: GameLauncher) -> Result<(), String> {
        let process_name = launcher.process_name();
        info!("Arrêt de {} ({})", launcher.display_name(), process_name);

        #[cfg(target_os = "windows")]
        {
            let output = Command::new("taskkill")
                .args(["/F", "/IM", process_name])
                .output();

            match output {
                Ok(out) => {
                    if out.status.success() {
                        info!("{} arrêté", launcher.display_name());
                        Ok(())
                    } else {
                        // Pas d'erreur si le processus n'existe pas
                        debug!("{} n'était pas en cours d'exécution", launcher.display_name());
                        Ok(())
                    }
                }
                Err(e) => Err(format!("Erreur taskkill: {}", e)),
            }
        }

        #[cfg(not(target_os = "windows"))]
        {
            let output = Command::new("pkill")
                .args(["-f", process_name])
                .output();

            match output {
                Ok(_) => {
                    debug!("{} arrêté (ou n'était pas lancé)", launcher.display_name());
                    Ok(())
                }
                Err(e) => Err(format!("Erreur pkill: {}", e)),
            }
        }
    }

    /// Fermer tous les jeux en cours
    fn close_all_games(&self) {
        info!("Fermeture de tous les jeux en cours");

        // Liste des processus de jeux courants à fermer
        // On utilise des patterns génériques pour attraper la plupart des jeux
        #[cfg(target_os = "windows")]
        {
            // Fermer les jeux Steam
            let _ = Command::new("taskkill")
                .args(["/F", "/FI", "WINDOWTITLE eq *Steam*"])
                .output();

            // Fermer les processus dans les dossiers de jeux courants
            // Note: On évite de tuer des processus système importants
            let game_processes = [
                // Jeux populaires
                "witcher3.exe",
                "cyberpunk2077.exe",
                "eldenring.exe",
                "GTA5.exe",
                "RDR2.exe",
                "Minecraft.exe",
                "javaw.exe", // Minecraft Java
                "FortniteClient-Win64-Shipping.exe",
                "VALORANT.exe",
                "csgo.exe",
                "cs2.exe",
                "dota2.exe",
                "hl2.exe",
                "portal2.exe",
                // Emulateurs
                "retroarch.exe",
                "dolphin.exe",
                "rpcs3.exe",
                "yuzu.exe",
            ];

            for process in game_processes {
                let _ = Command::new("taskkill")
                    .args(["/F", "/IM", process])
                    .output();
            }
        }

        #[cfg(not(target_os = "windows"))]
        {
            // Sur Linux, les jeux Steam sont souvent des processus avec "game" ou le nom du jeu
            // On utilise des patterns génériques
            let patterns = [
                "proton",
                "wine",
                "Celeste",
                "HollowKnight",
                "factorio",
                "minecraft",
                "java", // Minecraft Java (attention aux faux positifs)
            ];

            for pattern in patterns {
                let _ = Command::new("pkill")
                    .args(["-f", pattern])
                    .output();
            }
        }
    }

    /// Vérifier si un launcher est installé
    pub fn is_launcher_installed(&self, launcher: GameLauncher) -> bool {
        self.get_launcher_path(launcher).is_ok()
    }

    /// Vérifier si un launcher est en cours d'exécution
    pub fn is_launcher_running(&self, launcher: GameLauncher) -> bool {
        let process_name = launcher.process_name();

        #[cfg(target_os = "windows")]
        {
            let output = Command::new("tasklist")
                .args(["/FI", &format!("IMAGENAME eq {}", process_name)])
                .output();

            match output {
                Ok(out) => {
                    let stdout = String::from_utf8_lossy(&out.stdout);
                    stdout.contains(process_name)
                }
                Err(_) => false,
            }
        }

        #[cfg(not(target_os = "windows"))]
        {
            let output = Command::new("pgrep")
                .args(["-f", process_name])
                .output();

            match output {
                Ok(out) => out.status.success(),
                Err(_) => false,
            }
        }
    }

    /// Obtenir la liste des launchers installés
    pub fn get_installed_launchers(&self) -> Vec<GameLauncher> {
        GameLauncher::all()
            .into_iter()
            .filter(|l| self.is_launcher_installed(*l))
            .collect()
    }

    /// Obtenir le chemin vers un launcher
    fn get_launcher_path(&self, launcher: GameLauncher) -> Result<PathBuf, String> {
        // Vérifier d'abord les chemins personnalisés
        match launcher {
            GameLauncher::Steam => {
                if let Some(ref path) = self.config.steam_path {
                    if path.exists() {
                        return Ok(path.clone());
                    }
                }
            }
            GameLauncher::EpicGames => {
                if let Some(ref path) = self.config.epic_path {
                    if path.exists() {
                        return Ok(path.clone());
                    }
                }
            }
            GameLauncher::GOGGalaxy => {
                if let Some(ref path) = self.config.gog_path {
                    if path.exists() {
                        return Ok(path.clone());
                    }
                }
            }
            _ => {}
        }

        // Chemins par défaut
        #[cfg(target_os = "windows")]
        {
            let paths = match launcher {
                GameLauncher::Steam => vec![
                    PathBuf::from(r"C:\Program Files (x86)\Steam\steam.exe"),
                    PathBuf::from(r"C:\Program Files\Steam\steam.exe"),
                ],
                GameLauncher::EpicGames => vec![
                    PathBuf::from(r"C:\Program Files (x86)\Epic Games\Launcher\Portal\Binaries\Win32\EpicGamesLauncher.exe"),
                    PathBuf::from(r"C:\Program Files (x86)\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe"),
                ],
                GameLauncher::GOGGalaxy => vec![
                    PathBuf::from(r"C:\Program Files (x86)\GOG Galaxy\GalaxyClient.exe"),
                ],
                GameLauncher::UbisoftConnect => vec![
                    PathBuf::from(r"C:\Program Files (x86)\Ubisoft\Ubisoft Game Launcher\upc.exe"),
                ],
                GameLauncher::EAApp => vec![
                    PathBuf::from(r"C:\Program Files\Electronic Arts\EA Desktop\EA Desktop\EADesktop.exe"),
                ],
            };

            for path in paths {
                if path.exists() {
                    return Ok(path);
                }
            }
        }

        #[cfg(target_os = "linux")]
        {
            let paths = match launcher {
                GameLauncher::Steam => vec![
                    PathBuf::from("/usr/bin/steam"),
                    PathBuf::from("/usr/games/steam"),
                    PathBuf::from(format!("{}/.steam/steam/steam.sh", std::env::var("HOME").unwrap_or_default())),
                ],
                // Les autres launchers ne sont généralement pas disponibles nativement sur Linux
                _ => vec![],
            };

            for path in paths {
                if path.exists() {
                    return Ok(path);
                }
            }
        }

        Err(format!("{} non trouvé", launcher.display_name()))
    }

    /// Déconnecter l'utilisateur des launchers (pour le nettoyage)
    pub fn logout_all_launchers(&self) {
        info!("Déconnexion des comptes sur tous les launchers");

        // Steam: supprimer le fichier loginusers.vdf pour déconnecter
        #[cfg(target_os = "windows")]
        {
            let steam_config = PathBuf::from(r"C:\Program Files (x86)\Steam\config\loginusers.vdf");
            if steam_config.exists() {
                if let Err(e) = std::fs::remove_file(&steam_config) {
                    warn!("Impossible de supprimer loginusers.vdf: {}", e);
                } else {
                    info!("Steam: utilisateur déconnecté");
                }
            }

            // Epic Games: supprimer le fichier de configuration des comptes
            if let Ok(local_app_data) = std::env::var("LOCALAPPDATA") {
                let epic_config = PathBuf::from(&local_app_data)
                    .join("EpicGamesLauncher")
                    .join("Saved")
                    .join("Config")
                    .join("Windows")
                    .join("GameUserSettings.ini");

                if epic_config.exists() {
                    if let Err(e) = std::fs::remove_file(&epic_config) {
                        warn!("Impossible de supprimer config Epic: {}", e);
                    } else {
                        info!("Epic Games: utilisateur déconnecté");
                    }
                }
            }

            // GOG Galaxy: supprimer le fichier de connexion
            if let Ok(local_app_data) = std::env::var("LOCALAPPDATA") {
                let gog_config = PathBuf::from(&local_app_data)
                    .join("GOG.com")
                    .join("Galaxy")
                    .join("Configuration")
                    .join("config.json");

                if gog_config.exists() {
                    if let Err(e) = std::fs::remove_file(&gog_config) {
                        warn!("Impossible de supprimer config GOG: {}", e);
                    } else {
                        info!("GOG Galaxy: utilisateur déconnecté");
                    }
                }
            }
        }

        #[cfg(target_os = "linux")]
        {
            if let Ok(home) = std::env::var("HOME") {
                // Steam sur Linux
                let steam_config = PathBuf::from(&home)
                    .join(".steam")
                    .join("steam")
                    .join("config")
                    .join("loginusers.vdf");

                if steam_config.exists() {
                    if let Err(e) = std::fs::remove_file(&steam_config) {
                        warn!("Impossible de supprimer loginusers.vdf: {}", e);
                    } else {
                        info!("Steam: utilisateur déconnecté");
                    }
                }
            }
        }
    }
}

/// Statistiques de jeu (pour le monitoring optionnel)
#[derive(Debug, Clone, Default)]
pub struct GamingStats {
    /// Launcher actif
    pub active_launcher: Option<GameLauncher>,
    /// Jeu en cours
    pub current_game: Option<String>,
    /// Temps de jeu pendant la session (secondes)
    pub play_time_secs: u64,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_launcher_from_str() {
        assert_eq!(GameLauncher::from_str("steam"), Some(GameLauncher::Steam));
        assert_eq!(GameLauncher::from_str("STEAM"), Some(GameLauncher::Steam));
        assert_eq!(GameLauncher::from_str("epic"), Some(GameLauncher::EpicGames));
        assert_eq!(GameLauncher::from_str("gog"), Some(GameLauncher::GOGGalaxy));
        assert_eq!(GameLauncher::from_str("unknown"), None);
    }

    #[test]
    fn test_default_config() {
        let config = GamingConfig::default();
        assert!(config.close_launchers_on_end);
        assert!(config.close_games_on_end);
        assert!(!config.steam_big_picture);
    }
}
