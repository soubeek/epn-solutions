#!/bin/bash
#
# Script d'installation automatique du client EPN sur Ubuntu 24.04
#
# Usage:
#   sudo ./install-client.sh --server 192.168.1.25 --token "votre-token"
#
# Options:
#   --server      IP ou hostname du serveur EPN (requis)
#   --token       Token de découverte (requis)
#   --user        Nom de l'utilisateur à créer (défaut: epn)
#   --type        Type de poste: bureautique ou gaming (défaut: bureautique)
#   --autologin   Configurer l'auto-login (défaut: yes)
#   --compile     Compiler depuis les sources (défaut: no, utilise le binaire pré-compilé)
#   --help        Afficher l'aide
#

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Valeurs par défaut
EPN_USER="epn"
POSTE_TYPE="bureautique"
AUTOLOGIN="yes"
COMPILE="no"
SERVER_IP=""
DISCOVERY_TOKEN=""

# Chemins
INSTALL_DIR="/opt/epn-client"
CONFIG_DIR="/etc/epn-client"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Fonctions utilitaires
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_help() {
    cat << EOF
Installation du client EPN sur Ubuntu 24.04

Usage:
    sudo $0 --server <IP> --token <TOKEN> [OPTIONS]

Options requises:
    --server <IP>       IP ou hostname du serveur EPN
    --token <TOKEN>     Token de découverte (fourni par l'admin)

Options facultatives:
    --user <NAME>       Nom de l'utilisateur (défaut: epn)
    --type <TYPE>       Type de poste: bureautique ou gaming (défaut: bureautique)
    --autologin <BOOL>  Configurer l'auto-login: yes ou no (défaut: yes)
    --compile           Compiler depuis les sources Rust
    --help              Afficher cette aide

Exemples:
    # Installation standard
    sudo $0 --server 192.168.1.25 --token "abc123..."

    # Poste gaming sans auto-login
    sudo $0 --server 192.168.1.25 --token "abc123..." --type gaming --autologin no

    # Compiler depuis les sources
    sudo $0 --server 192.168.1.25 --token "abc123..." --compile

EOF
    exit 0
}

# Parser les arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --server)
                SERVER_IP="$2"
                shift 2
                ;;
            --token)
                DISCOVERY_TOKEN="$2"
                shift 2
                ;;
            --user)
                EPN_USER="$2"
                shift 2
                ;;
            --type)
                POSTE_TYPE="$2"
                shift 2
                ;;
            --autologin)
                AUTOLOGIN="$2"
                shift 2
                ;;
            --compile)
                COMPILE="yes"
                shift
                ;;
            --help)
                show_help
                ;;
            *)
                log_error "Option inconnue: $1"
                show_help
                ;;
        esac
    done

    # Vérifier les arguments requis
    if [[ -z "$SERVER_IP" ]]; then
        log_error "L'option --server est requise"
        exit 1
    fi

    if [[ -z "$DISCOVERY_TOKEN" ]]; then
        log_error "L'option --token est requise"
        exit 1
    fi
}

# Vérifier les privilèges root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Ce script doit être exécuté en tant que root (sudo)"
        exit 1
    fi
}

# Installer les dépendances système
install_dependencies() {
    log_info "Installation des dépendances système..."

    apt-get update -qq

    apt-get install -y -qq \
        build-essential \
        pkg-config \
        libssl-dev \
        libdbus-1-dev \
        libglib2.0-dev \
        libgtk-3-dev \
        libwebkit2gtk-4.1-dev \
        libayatana-appindicator3-dev \
        librsvg2-dev \
        libnotify-bin \
        xprintidle \
        curl

    log_success "Dépendances installées"
}

# Installer Rust si compilation demandée
install_rust() {
    if [[ "$COMPILE" == "yes" ]]; then
        if ! command -v rustc &> /dev/null; then
            log_info "Installation de Rust..."
            curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
            source "$HOME/.cargo/env"
            log_success "Rust installé"
        else
            log_info "Rust déjà installé"
        fi
    fi
}

# Compiler le client
compile_client() {
    if [[ "$COMPILE" == "yes" ]]; then
        log_info "Compilation du client EPN..."

        cd "$PROJECT_DIR/rust-client"
        source "$HOME/.cargo/env" 2>/dev/null || true
        cargo build --release

        log_success "Compilation terminée"
    fi
}

# Installer les binaires
install_binaries() {
    log_info "Installation des binaires..."

    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"

    if [[ "$COMPILE" == "yes" ]]; then
        cp "$PROJECT_DIR/rust-client/target/release/epn-gui" "$INSTALL_DIR/"
    else
        # Vérifier si le binaire pré-compilé existe
        if [[ -f "$PROJECT_DIR/rust-client/target/release/epn-gui" ]]; then
            cp "$PROJECT_DIR/rust-client/target/release/epn-gui" "$INSTALL_DIR/"
        else
            log_error "Binaire non trouvé. Utilisez --compile pour compiler depuis les sources."
            exit 1
        fi
    fi

    chmod +x "$INSTALL_DIR/epn-gui"

    log_success "Binaires installés dans $INSTALL_DIR"
}

# Créer la configuration
create_config() {
    log_info "Création de la configuration..."

    cat > "$CONFIG_DIR/config.yaml" << EOF
# Configuration du client EPN
# Généré automatiquement le $(date)

# ============== Connexion au serveur ==============
server_url: http://${SERVER_IP}:8001
ws_url: ws://${SERVER_IP}:8001

# ============== Token de découverte ==============
discovery_token: ${DISCOVERY_TOKEN}

# ============== Comportement fin de session ==============
lock_on_expire: true
logout_on_expire: false
lock_delay_secs: 5

# ============== Nettoyage automatique ==============
enable_cleanup: true
cleanup_firefox: true
cleanup_libreoffice: true
cleanup_user_documents: true
cleanup_system_history: true

# ============== Surveillance d'inactivité ==============
inactivity_enabled: true
inactivity_warning_secs: 300
inactivity_timeout_secs: 600

# ============== Type de poste ==============
poste_type: ${POSTE_TYPE}

# ============== Mode kiosque ==============
kiosk_mode: true
kiosk_admin_password: "admin123"
EOF

    # Ajouter config gaming si nécessaire
    if [[ "$POSTE_TYPE" == "gaming" ]]; then
        cat >> "$CONFIG_DIR/config.yaml" << EOF

# ============== Configuration Gaming ==============
gaming_enabled: true
gaming_auto_start_launchers:
  - steam
gaming_close_on_end: true
gaming_close_games_on_end: true
gaming_steam_big_picture: false
EOF
    fi

    log_success "Configuration créée dans $CONFIG_DIR/config.yaml"
}

# Créer l'utilisateur dédié
create_user() {
    log_info "Configuration de l'utilisateur '$EPN_USER'..."

    # Créer l'utilisateur s'il n'existe pas
    if ! id "$EPN_USER" &>/dev/null; then
        useradd -m -s /bin/bash -c "Utilisateur EPN Public" "$EPN_USER"
        log_success "Utilisateur '$EPN_USER' créé"
    else
        log_info "Utilisateur '$EPN_USER' existe déjà"
    fi

    # Créer le dossier pour les certificats
    mkdir -p "/home/$EPN_USER/.epn-client"
    chown -R "$EPN_USER:$EPN_USER" "/home/$EPN_USER/.epn-client"

    log_success "Répertoire certificats créé"
}

# Configurer l'auto-login
configure_autologin() {
    if [[ "$AUTOLOGIN" != "yes" ]]; then
        log_info "Auto-login désactivé (--autologin no)"
        return
    fi

    log_info "Configuration de l'auto-login..."

    # Détecter le display manager
    if [[ -f /etc/gdm3/custom.conf ]]; then
        # GDM (GNOME)
        log_info "Détecté: GDM"

        # Backup
        cp /etc/gdm3/custom.conf /etc/gdm3/custom.conf.backup 2>/dev/null || true

        # Configurer auto-login
        if grep -q "^\[daemon\]" /etc/gdm3/custom.conf; then
            sed -i "/^\[daemon\]/a AutomaticLoginEnable=true\nAutomaticLogin=$EPN_USER" /etc/gdm3/custom.conf
        else
            cat >> /etc/gdm3/custom.conf << EOF

[daemon]
AutomaticLoginEnable=true
AutomaticLogin=$EPN_USER
EOF
        fi

        log_success "Auto-login configuré pour GDM"

    elif [[ -f /etc/lightdm/lightdm.conf ]] || [[ -d /etc/lightdm ]]; then
        # LightDM
        log_info "Détecté: LightDM"

        mkdir -p /etc/lightdm
        cat > /etc/lightdm/lightdm.conf << EOF
[Seat:*]
autologin-user=$EPN_USER
autologin-user-timeout=0
EOF

        log_success "Auto-login configuré pour LightDM"

    else
        log_warning "Display manager non reconnu. Configurez l'auto-login manuellement."
    fi
}

# Configurer le mode kiosque GNOME
configure_kiosk_gnome() {
    log_info "Configuration du mode kiosque GNOME..."

    # Vérifier si on utilise GNOME
    if ! command -v gsettings &> /dev/null; then
        log_warning "gsettings non trouvé. Configuration kiosque GNOME ignorée."
        return
    fi

    # Exécuter les commandes en tant qu'utilisateur EPN
    # Note: dbus-launch est nécessaire pour les commandes gsettings en mode script

    # Masquer le dock Ubuntu (si Dash to Dock est installé)
    sudo -u "$EPN_USER" dbus-launch gsettings set org.gnome.shell.extensions.dash-to-dock autohide true 2>/dev/null || true
    sudo -u "$EPN_USER" dbus-launch gsettings set org.gnome.shell.extensions.dash-to-dock dock-fixed false 2>/dev/null || true
    sudo -u "$EPN_USER" dbus-launch gsettings set org.gnome.shell.extensions.dash-to-dock intellihide true 2>/dev/null || true

    # Désactiver les raccourcis système problématiques
    sudo -u "$EPN_USER" dbus-launch gsettings set org.gnome.desktop.wm.keybindings switch-applications "[]" 2>/dev/null || true
    sudo -u "$EPN_USER" dbus-launch gsettings set org.gnome.desktop.wm.keybindings switch-windows "[]" 2>/dev/null || true
    sudo -u "$EPN_USER" dbus-launch gsettings set org.gnome.mutter overlay-key "" 2>/dev/null || true
    sudo -u "$EPN_USER" dbus-launch gsettings set org.gnome.shell.keybindings toggle-overview "[]" 2>/dev/null || true

    # Désactiver le bouton d'activités (Activities)
    sudo -u "$EPN_USER" dbus-launch gsettings set org.gnome.shell.extensions.dash-to-dock show-apps-button false 2>/dev/null || true

    # Désactiver l'écran de verrouillage automatique GNOME (on gère nous-mêmes)
    sudo -u "$EPN_USER" dbus-launch gsettings set org.gnome.desktop.screensaver lock-enabled false 2>/dev/null || true
    sudo -u "$EPN_USER" dbus-launch gsettings set org.gnome.desktop.session idle-delay 0 2>/dev/null || true

    log_success "Configuration GNOME appliquée"
}

# Créer le service systemd
create_service() {
    log_info "Création du service systemd..."

    cat > /etc/systemd/system/epn-client.service << EOF
[Unit]
Description=Client EPN - Gestion des postes publics
After=network-online.target graphical.target
Wants=network-online.target

[Service]
Type=simple
User=$EPN_USER
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/$EPN_USER/.Xauthority
ExecStart=$INSTALL_DIR/epn-gui
Restart=always
RestartSec=5

[Install]
WantedBy=graphical.target
EOF

    systemctl daemon-reload
    systemctl enable epn-client

    log_success "Service systemd créé et activé"
}

# Afficher le résumé
show_summary() {
    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}  Installation terminée avec succès !${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo ""
    echo -e "Serveur:        ${BLUE}http://${SERVER_IP}:8001${NC}"
    echo -e "Utilisateur:    ${BLUE}${EPN_USER}${NC}"
    echo -e "Type de poste:  ${BLUE}${POSTE_TYPE}${NC}"
    echo -e "Auto-login:     ${BLUE}${AUTOLOGIN}${NC}"
    echo -e "Mode kiosque:   ${BLUE}Activé${NC} (Ctrl+Alt+Shift+K pour déverrouiller)"
    echo ""
    echo -e "Fichiers installés:"
    echo -e "  - Binaire:     ${INSTALL_DIR}/epn-gui"
    echo -e "  - Config:      ${CONFIG_DIR}/config.yaml"
    echo -e "  - Service:     /etc/systemd/system/epn-client.service"
    echo -e "  - Certificats: /home/${EPN_USER}/.epn-client/"
    echo ""
    echo -e "${YELLOW}Prochaines étapes:${NC}"
    echo -e "  1. Redémarrer le système: ${BLUE}sudo reboot${NC}"
    echo -e "  2. Le client va démarrer automatiquement"
    echo -e "  3. Aller sur ${BLUE}http://${SERVER_IP}:3001${NC} → Postes → En attente"
    echo -e "  4. Valider le nouveau poste"
    echo ""
    echo -e "Commandes utiles:"
    echo -e "  - Voir les logs:    ${BLUE}sudo journalctl -u epn-client -f${NC}"
    echo -e "  - Statut service:   ${BLUE}sudo systemctl status epn-client${NC}"
    echo -e "  - Redémarrer:       ${BLUE}sudo systemctl restart epn-client${NC}"
    echo ""
}

# Main
main() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  Installation du Client EPN - Ubuntu 24.04 ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}"
    echo ""

    parse_args "$@"
    check_root
    install_dependencies
    install_rust
    compile_client
    install_binaries
    create_config
    create_user
    configure_autologin
    configure_kiosk_gnome
    create_service
    show_summary
}

main "$@"
