//! EPN Client GUI - POC Iced
//!
//! Implementation alternative du client EPN utilisant Iced au lieu de Tauri.
//! Avantages: 100% Rust, pas de WebView, binaire plus leger.

use epn_core::{Config, SessionInfo, SessionManager};
use epn_system::{get_notifier, Urgency};
use iced::keyboard::{self, Key, Modifiers};
use iced::time::{self, Duration};
use iced::widget::{
    button, column, container, progress_bar, row, text, text_input, Space,
};
use iced::window;
use iced::{Center, Element, Fill, Size, Subscription, Task, Theme};
use std::sync::Arc;
use tokio::sync::Mutex;

// Constantes pour le mode widget
const WIDGET_WIDTH: f32 = 320.0;
const WIDGET_HEIGHT: f32 = 100.0;

/// Point d'entree de l'application
pub fn main() -> iced::Result {
    // Initialiser le logging
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::from_default_env()
                .add_directive(tracing::Level::INFO.into()),
        )
        .init();

    tracing::info!("Demarrage de l'application EPN Client (Iced)");

    // Charger la configuration
    let config = match Config::load() {
        Ok(cfg) => {
            tracing::info!("Configuration chargee");
            cfg
        }
        Err(e) => {
            tracing::warn!(
                "Erreur de chargement de la config: {}. Utilisation de la config par defaut",
                e
            );
            Config::default()
        }
    };

    // Valider la configuration
    if let Err(e) = config.validate() {
        tracing::error!("Configuration invalide: {}", e);
        std::process::exit(1);
    }

    let kiosk_mode = config.kiosk_mode;

    // Configuration de la fenetre
    let window_settings = if kiosk_mode {
        window::Settings {
            decorations: false,
            resizable: false,
            ..Default::default()
        }
    } else {
        window::Settings {
            size: Size::new(800.0, 600.0),
            position: window::Position::Centered,
            ..Default::default()
        }
    };

    iced::application("EPN Client", EpnApp::update, EpnApp::view)
        .subscription(EpnApp::subscription)
        .theme(EpnApp::theme)
        .window(window_settings)
        .run_with(move || EpnApp::new(config))
}

/// Ecrans de l'application
#[derive(Debug, Clone, PartialEq)]
enum Screen {
    Login,
    Session,
    Widget,
    Expired,
    AdminUnlock,
}

/// Etat de l'application
struct EpnApp {
    // Configuration
    config: Config,

    // Gestion de session
    session_manager: Arc<Mutex<Option<SessionManager>>>,

    // Ecran actuel
    screen: Screen,
    previous_screen: Option<Screen>,

    // Ecran Login
    code_input: String,
    error_message: Option<String>,
    is_validating: bool,

    // Ecran Session
    session_info: Option<SessionInfo>,
    remaining_time: u64,
    total_duration: u64,

    // Mode widget
    widget_mode: bool,

    // Dialogue Admin
    admin_password_input: String,
    admin_error: Option<String>,

    // Etat connexion
    is_connected: bool,
    is_initializing: bool,

    // Mode kiosque actif
    kiosk_active: bool,
}

/// Messages de l'application
#[derive(Debug, Clone)]
enum Message {
    // Initialisation
    Initialized(Result<(), String>),

    // Login
    CodeInputChanged(String),
    ValidateCode,
    CodeValidated(Result<SessionInfo, String>),
    SessionStarted(Result<SessionInfo, String>),

    // Session
    Tick,
    TimeUpdated(Result<u64, String>),
    EndSession,
    SessionEnded,

    // Widget mode
    SwitchToWidget,
    SwitchToFullscreen,
    WidgetModeSet,

    // Navigation
    ReturnToLogin,

    // Clavier
    KeyPressed(Key, Modifiers),

    // Fenetre
    RequestFullscreen,
    WindowResized,

    // Admin
    ShowAdminDialog,
    AdminPasswordChanged(String),
    ValidateAdminPassword,
    CancelAdminDialog,
    KioskUnlocked,
}

impl EpnApp {
    /// Creer une nouvelle instance de l'application
    fn new(config: Config) -> (Self, Task<Message>) {
        let session_manager = Arc::new(Mutex::new(None));
        let session_manager_clone = session_manager.clone();
        let config_clone = config.clone();
        let kiosk_mode = config.kiosk_mode;

        let app = Self {
            config,
            session_manager,
            screen: Screen::Login,
            previous_screen: None,
            code_input: String::new(),
            error_message: None,
            is_validating: false,
            session_info: None,
            remaining_time: 0,
            total_duration: 0,
            widget_mode: false,
            admin_password_input: String::new(),
            admin_error: None,
            is_connected: false,
            is_initializing: true,
            kiosk_active: kiosk_mode,
        };

        // Lancer l'initialisation en arriere-plan
        let init_task = Task::perform(
            async move {
                match SessionManager::new(config_clone).await {
                    Ok(manager) => {
                        *session_manager_clone.lock().await = Some(manager);
                        Ok(())
                    }
                    Err(e) => Err(e.to_string()),
                }
            },
            Message::Initialized,
        );

        (app, init_task)
    }

    /// Mettre a jour l'etat de l'application
    fn update(&mut self, message: Message) -> Task<Message> {
        match message {
            // Initialisation terminee
            Message::Initialized(result) => {
                self.is_initializing = false;
                match result {
                    Ok(()) => {
                        tracing::info!("Application initialisee");
                        self.is_connected = true;

                        // Activer le plein ecran si mode kiosque
                        if self.config.kiosk_mode {
                            return Task::done(Message::RequestFullscreen);
                        }
                    }
                    Err(e) => {
                        tracing::error!("Erreur d'initialisation: {}", e);
                        self.error_message = Some(format!("Erreur de connexion: {}", e));
                    }
                }
                Task::none()
            }

            // Saisie du code
            Message::CodeInputChanged(value) => {
                self.code_input = value.to_uppercase();
                self.error_message = None;
                Task::none()
            }

            // Validation du code
            Message::ValidateCode => {
                if self.code_input.is_empty() {
                    self.error_message = Some("Veuillez entrer un code".to_string());
                    return Task::none();
                }

                self.is_validating = true;
                self.error_message = None;

                let session_manager = self.session_manager.clone();
                let code = self.code_input.clone();

                Task::perform(
                    async move {
                        let mut guard = session_manager.lock().await;
                        match guard.as_mut() {
                            Some(manager) => manager
                                .validate_code(&code)
                                .await
                                .map_err(|e| e.to_string()),
                            None => Err("Session manager non initialise".to_string()),
                        }
                    },
                    Message::CodeValidated,
                )
            }

            // Code valide
            Message::CodeValidated(result) => {
                match result {
                    Ok(session) => {
                        tracing::info!("Code valide: {:?}", session);

                        // Demarrer la session
                        let session_manager = self.session_manager.clone();
                        return Task::perform(
                            async move {
                                let mut guard = session_manager.lock().await;
                                match guard.as_mut() {
                                    Some(manager) => manager
                                        .start_session()
                                        .await
                                        .map_err(|e| e.to_string()),
                                    None => Err("Session manager non initialise".to_string()),
                                }
                            },
                            Message::SessionStarted,
                        );
                    }
                    Err(e) => {
                        tracing::error!("Code invalide: {}", e);
                        self.is_validating = false;
                        self.error_message = Some(e);
                    }
                }
                Task::none()
            }

            // Session demarree
            Message::SessionStarted(result) => {
                self.is_validating = false;
                match result {
                    Ok(session) => {
                        tracing::info!("Session demarree: {:?}", session);
                        self.total_duration = session.total_duration;
                        self.remaining_time = session.remaining_time;
                        self.session_info = Some(session);
                        self.screen = Screen::Session;
                        self.code_input.clear();

                        // En mode kiosque, basculer vers le widget apres un court delai
                        if self.config.kiosk_mode {
                            return Task::perform(
                                async {
                                    tokio::time::sleep(std::time::Duration::from_millis(1500)).await;
                                },
                                |_| Message::SwitchToWidget,
                            );
                        }
                    }
                    Err(e) => {
                        tracing::error!("Erreur demarrage session: {}", e);
                        self.error_message = Some(e);
                    }
                }
                Task::none()
            }

            // Tick du timer (chaque seconde)
            Message::Tick => {
                if self.screen != Screen::Session && self.screen != Screen::Widget {
                    return Task::none();
                }

                let session_manager = self.session_manager.clone();
                Task::perform(
                    async move {
                        let mut guard = session_manager.lock().await;
                        match guard.as_mut() {
                            Some(manager) => manager
                                .get_remaining_time()
                                .await
                                .map_err(|e| e.to_string()),
                            None => Err("Session manager non initialise".to_string()),
                        }
                    },
                    Message::TimeUpdated,
                )
            }

            // Temps mis a jour
            Message::TimeUpdated(result) => {
                match result {
                    Ok(remaining) => {
                        let old_remaining = self.remaining_time;
                        self.remaining_time = remaining;

                        // Notifications d'avertissement
                        if remaining == 300 && old_remaining > 300 {
                            self.show_notification(
                                "Avertissement",
                                "Il vous reste 5 minutes",
                                Urgency::Normal,
                            );
                        } else if remaining == 60 && old_remaining > 60 {
                            self.show_notification(
                                "Session sur le point d'expirer",
                                "Il vous reste 1 minute",
                                Urgency::Critical,
                            );
                        }

                        // Session expiree
                        if remaining == 0 {
                            return Task::done(Message::EndSession);
                        }
                    }
                    Err(e) => {
                        tracing::error!("Erreur recuperation temps: {}", e);
                        // Session probablement terminee
                        return Task::done(Message::EndSession);
                    }
                }
                Task::none()
            }

            // Basculer vers le mode widget
            Message::SwitchToWidget => {
                tracing::info!("Basculement vers le mode widget");
                self.widget_mode = true;
                self.screen = Screen::Widget;

                // Redimensionner la fenetre en mode widget
                window::get_latest().and_then(|id| {
                    Task::batch([
                        window::change_mode(id, window::Mode::Windowed),
                        window::resize(id, Size::new(WIDGET_WIDTH, WIDGET_HEIGHT)),
                    ])
                })
            }

            // Revenir en plein ecran
            Message::SwitchToFullscreen => {
                tracing::info!("Retour en mode plein ecran");
                self.widget_mode = false;
                self.screen = Screen::Session;

                window::get_latest().and_then(|id| {
                    window::change_mode(id, window::Mode::Fullscreen)
                })
            }

            Message::WidgetModeSet => {
                Task::none()
            }

            // Fin de session
            Message::EndSession => {
                tracing::info!("Fin de session");

                // Revenir en plein ecran si en mode widget
                if self.widget_mode {
                    self.widget_mode = false;
                }

                self.show_notification(
                    "Session Expiree",
                    "Votre temps est ecoule.",
                    Urgency::Critical,
                );

                let session_manager = self.session_manager.clone();
                let kiosk_mode = self.config.kiosk_mode;

                Task::perform(
                    async move {
                        let guard = session_manager.lock().await;
                        if let Some(manager) = guard.as_ref() {
                            manager.cleanup_only();
                        }
                    },
                    move |_| Message::SessionEnded,
                ).chain(if kiosk_mode {
                    window::get_latest().and_then(|id| {
                        window::change_mode(id, window::Mode::Fullscreen)
                    })
                } else {
                    Task::none()
                })
            }

            // Session terminee
            Message::SessionEnded => {
                self.screen = Screen::Expired;
                self.session_info = None;
                Task::none()
            }

            // Retour a l'ecran de login
            Message::ReturnToLogin => {
                self.screen = Screen::Login;
                self.code_input.clear();
                self.error_message = None;
                self.remaining_time = 0;
                self.total_duration = 0;

                if self.config.kiosk_mode {
                    Task::done(Message::RequestFullscreen)
                } else {
                    Task::none()
                }
            }

            // Gestion du clavier
            Message::KeyPressed(key, modifiers) => {
                // Ctrl+Alt+Shift+K pour deverrouillage admin
                if modifiers.control() && modifiers.alt() && modifiers.shift() {
                    if let Key::Character(c) = &key {
                        if c.to_lowercase() == "k" {
                            if self.kiosk_active && self.config.kiosk_admin_password.is_some() {
                                return Task::done(Message::ShowAdminDialog);
                            }
                        }
                    }
                }

                // Bloquer Escape en mode kiosque
                if self.kiosk_active {
                    if key == Key::Named(keyboard::key::Named::Escape) {
                        return Task::none();
                    }
                }

                Task::none()
            }

            // Demande de plein ecran
            Message::RequestFullscreen => {
                window::get_latest().and_then(|id| {
                    window::change_mode(id, window::Mode::Fullscreen)
                })
            }

            Message::WindowResized => Task::none(),

            // Afficher le dialogue admin
            Message::ShowAdminDialog => {
                tracing::info!("Affichage du dialogue admin");
                self.previous_screen = Some(self.screen.clone());
                self.screen = Screen::AdminUnlock;
                self.admin_password_input.clear();
                self.admin_error = None;
                Task::none()
            }

            // Saisie mot de passe admin
            Message::AdminPasswordChanged(value) => {
                self.admin_password_input = value;
                self.admin_error = None;
                Task::none()
            }

            // Valider mot de passe admin
            Message::ValidateAdminPassword => {
                if let Some(ref expected) = self.config.kiosk_admin_password {
                    if self.admin_password_input == *expected {
                        tracing::info!("Mot de passe admin correct - deverrouillage");
                        return Task::done(Message::KioskUnlocked);
                    } else {
                        tracing::warn!("Mot de passe admin incorrect");
                        self.admin_error = Some("Mot de passe incorrect".to_string());
                    }
                }
                Task::none()
            }

            // Annuler dialogue admin
            Message::CancelAdminDialog => {
                if let Some(prev) = self.previous_screen.take() {
                    self.screen = prev;
                } else {
                    self.screen = Screen::Login;
                }
                self.admin_password_input.clear();
                self.admin_error = None;
                Task::none()
            }

            // Kiosque deverrouille
            Message::KioskUnlocked => {
                tracing::info!("Mode kiosque desactive");
                self.kiosk_active = false;
                self.admin_password_input.clear();
                self.admin_error = None;

                if let Some(prev) = self.previous_screen.take() {
                    self.screen = prev;
                } else {
                    self.screen = Screen::Login;
                }

                self.show_notification(
                    "Mode kiosque desactive",
                    "Vous pouvez maintenant fermer l'application",
                    Urgency::Normal,
                );

                // Sortir du plein ecran
                window::get_latest().and_then(|id| {
                    Task::batch([
                        window::change_mode(id, window::Mode::Windowed),
                        window::resize(id, Size::new(800.0, 600.0)),
                    ])
                })
            }
        }
    }

    /// Rendu de l'interface
    fn view(&self) -> Element<'_, Message> {
        let content = match self.screen {
            Screen::Login => self.view_login(),
            Screen::Session => self.view_session(),
            Screen::Widget => self.view_widget(),
            Screen::Expired => self.view_expired(),
            Screen::AdminUnlock => self.view_admin_dialog(),
        };

        container(content)
            .width(Fill)
            .height(Fill)
            .center_x(Fill)
            .center_y(Fill)
            .into()
    }

    /// Vue de l'ecran de login
    fn view_login(&self) -> Element<'_, Message> {
        let title = text("EPN Client").size(40);

        let subtitle = text("Espace Public Numerique").size(20);

        let status = if self.is_initializing {
            text("Connexion au serveur...").size(14)
        } else if self.is_connected {
            text("Connecte au serveur").size(14)
        } else {
            text("Non connecte").size(14)
        };

        let server_info = text(format!("Serveur: {}", self.config.server_url)).size(12);

        let code_label = text("Entrez votre code d'acces:").size(16);

        let code_field = text_input("CODE", &self.code_input)
            .on_input(Message::CodeInputChanged)
            .on_submit(Message::ValidateCode)
            .padding(15)
            .size(24)
            .width(300);

        let validate_button = if self.is_validating {
            button(text("Validation...").size(18)).padding([15, 40])
        } else {
            button(text("Valider").size(18))
                .on_press(Message::ValidateCode)
                .padding([15, 40])
                .style(button::primary)
        };

        let error_text = if let Some(ref error) = self.error_message {
            text(error).size(14)
        } else {
            text("").size(14)
        };

        column![
            title,
            subtitle,
            Space::with_height(20),
            status,
            server_info,
            Space::with_height(40),
            code_label,
            Space::with_height(10),
            code_field,
            Space::with_height(20),
            validate_button,
            Space::with_height(10),
            error_text,
        ]
        .spacing(5)
        .align_x(Center)
        .into()
    }

    /// Vue de l'ecran de session (plein ecran)
    fn view_session(&self) -> Element<'_, Message> {
        let session = self.session_info.as_ref();

        let user_name = session
            .map(|s| s.user_name.as_str())
            .unwrap_or("Utilisateur");

        let workstation = session
            .map(|s| s.workstation.as_str())
            .unwrap_or("Poste");

        let title = text("Session Active").size(30);

        let user_info = text(format!("Utilisateur: {}", user_name)).size(18);

        let workstation_info = text(format!("Poste: {}", workstation)).size(18);

        // Formatage du temps restant
        let minutes = self.remaining_time / 60;
        let seconds = self.remaining_time % 60;
        let time_display = text(format!("{:02}:{:02}", minutes, seconds)).size(80);

        // Calcul du pourcentage
        let percentage = if self.total_duration > 0 {
            (self.remaining_time as f32 / self.total_duration as f32) * 100.0
        } else {
            0.0
        };

        let progress = progress_bar(0.0..=100.0, percentage)
            .width(400)
            .height(20);

        let total_time = text(format!(
            "Duree totale: {} minutes",
            self.total_duration / 60
        ))
        .size(14);

        // Message d'avertissement
        let warning = if self.remaining_time <= 60 {
            text("ATTENTION: Il vous reste moins d'une minute!").size(18)
        } else if self.remaining_time <= 300 {
            text(format!("Attention: Il vous reste {} minutes", minutes)).size(16)
        } else {
            text("").size(16)
        };

        // Bouton pour basculer vers le widget (si mode kiosque)
        let widget_button = if self.config.kiosk_mode {
            button(text("Mode widget").size(14))
                .on_press(Message::SwitchToWidget)
                .padding([10, 20])
        } else {
            button(text("").size(14)).padding([10, 20])
        };

        column![
            title,
            Space::with_height(20),
            user_info,
            workstation_info,
            Space::with_height(40),
            text("Temps restant").size(16),
            time_display,
            progress,
            Space::with_height(10),
            total_time,
            Space::with_height(20),
            warning,
            Space::with_height(20),
            widget_button,
        ]
        .spacing(5)
        .align_x(Center)
        .into()
    }

    /// Vue du widget (petite fenetre flottante)
    fn view_widget(&self) -> Element<'_, Message> {
        // Formatage du temps restant
        let minutes = self.remaining_time / 60;
        let seconds = self.remaining_time % 60;

        let time_display = text(format!("{:02}:{:02}", minutes, seconds)).size(32);

        // Calcul du pourcentage
        let percentage = if self.total_duration > 0 {
            (self.remaining_time as f32 / self.total_duration as f32) * 100.0
        } else {
            0.0
        };

        let progress = progress_bar(0.0..=100.0, percentage)
            .width(Fill)
            .height(8);

        // Bouton pour revenir en plein ecran
        let expand_button = button(text("+").size(16))
            .on_press(Message::SwitchToFullscreen)
            .padding([5, 10]);

        // Layout compact pour le widget
        let content = column![
            row![
                time_display,
                Space::with_width(Fill),
                expand_button,
            ]
            .spacing(10)
            .align_y(Center),
            progress,
        ]
        .spacing(8)
        .padding(10);

        container(content)
            .width(Fill)
            .height(Fill)
            .into()
    }

    /// Vue de l'ecran d'expiration
    fn view_expired(&self) -> Element<'_, Message> {
        let title = text("Session Terminee").size(40);

        let message = text("Votre temps est ecoule.").size(20);

        let subtitle = text("Merci d'avoir utilise nos services.").size(16);

        let return_button = button(text("Nouvelle session").size(18))
            .on_press(Message::ReturnToLogin)
            .padding([15, 40])
            .style(button::primary);

        column![
            title,
            Space::with_height(30),
            message,
            subtitle,
            Space::with_height(40),
            return_button,
        ]
        .spacing(10)
        .align_x(Center)
        .into()
    }

    /// Vue du dialogue de mot de passe admin
    fn view_admin_dialog(&self) -> Element<'_, Message> {
        let title = text("Deverrouillage Admin").size(24);

        let instruction = text("Entrez le mot de passe administrateur:").size(14);

        let password_field = text_input("Mot de passe", &self.admin_password_input)
            .on_input(Message::AdminPasswordChanged)
            .on_submit(Message::ValidateAdminPassword)
            .secure(true)
            .padding(10)
            .size(16)
            .width(250);

        let error_text = if let Some(ref error) = self.admin_error {
            text(error).size(14)
        } else {
            text("").size(14)
        };

        let buttons = row![
            button(text("Annuler").size(14))
                .on_press(Message::CancelAdminDialog)
                .padding([10, 20]),
            Space::with_width(20),
            button(text("Valider").size(14))
                .on_press(Message::ValidateAdminPassword)
                .padding([10, 20])
                .style(button::primary),
        ];

        column![
            title,
            Space::with_height(20),
            instruction,
            Space::with_height(10),
            password_field,
            Space::with_height(10),
            error_text,
            Space::with_height(20),
            buttons,
        ]
        .spacing(5)
        .align_x(Center)
        .into()
    }

    /// Abonnements (timer, clavier)
    fn subscription(&self) -> Subscription<Message> {
        let mut subscriptions = vec![];

        // Timer chaque seconde si en session ou widget
        if self.screen == Screen::Session || self.screen == Screen::Widget {
            subscriptions.push(time::every(Duration::from_secs(1)).map(|_| Message::Tick));
        }

        // Ecoute des touches clavier
        subscriptions.push(keyboard::on_key_press(|key, modifiers| {
            Some(Message::KeyPressed(key, modifiers))
        }));

        Subscription::batch(subscriptions)
    }

    /// Theme de l'application
    fn theme(&self) -> Theme {
        Theme::Dark
    }

    /// Afficher une notification systeme
    fn show_notification(&self, title: &str, message: &str, urgency: Urgency) {
        let notifier = get_notifier();
        if let Err(e) = notifier.show(title, message, urgency) {
            tracing::error!("Erreur notification: {}", e);
        }
    }
}
