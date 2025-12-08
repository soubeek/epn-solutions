#!/bin/bash
# =============================================================================
# EPN Solutions - Script de configuration du verrouillage systeme Linux
# =============================================================================
#
# Ce script configure les restrictions systeme pour un poste kiosque:
# - Restrictions bureau GNOME via dconf
# - Auto-login de l'utilisateur
# - Autostart du client EPN
# - Optionnel: blocage USB
#
# Usage: sudo ./configure-lockdown.sh [OPTIONS]
#
# Options:
#   --user USERNAME     Utilisateur kiosque (defaut: epn)
#   --profile PROFILE   Profil de restriction: strict|standard|permissive|gaming
#   --apply             Appliquer les restrictions
#   --remove            Retirer les restrictions
#   --status            Afficher le statut actuel
#   --help              Afficher l'aide
# =============================================================================

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration par defaut
KIOSK_USER="epn"
PROFILE="standard"
ACTION=""
EPN_CLIENT_PATH="/usr/local/bin/epn-gui"

# Affiche un message
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
    echo -e "${RED}[ERREUR]${NC} $1"
}

# Affiche l'aide
show_help() {
    cat << EOF
EPN Solutions - Configuration verrouillage systeme

Usage: sudo $0 [OPTIONS]

Options:
  --user USERNAME     Utilisateur kiosque (defaut: epn)
  --profile PROFILE   Profil: strict|standard|permissive|gaming (defaut: standard)
  --apply             Appliquer les restrictions
  --remove            Retirer les restrictions
  --status            Afficher le statut actuel
  --help              Afficher cette aide

Profils disponibles:
  strict      Navigation web uniquement (Firefox)
  standard    Navigation + bureautique (Firefox + LibreOffice)
  permissive  Navigation + bureautique + multimedia
  gaming      Navigation + jeux (Steam, Heroic, Lutris)

Exemples:
  sudo $0 --apply --user epn --profile standard
  sudo $0 --status
  sudo $0 --remove

EOF
}

# Verifie les prerequis
check_prerequisites() {
    # Verifier les droits root
    if [[ $EUID -ne 0 ]]; then
        log_error "Ce script doit etre execute en tant que root (sudo)"
        exit 1
    fi

    # Verifier que dconf est installe
    if ! command -v dconf &> /dev/null; then
        log_error "dconf n'est pas installe. Installez-le avec: sudo apt install dconf-cli"
        exit 1
    fi

    # Verifier que l'utilisateur existe
    if ! id "$KIOSK_USER" &>/dev/null; then
        log_warning "L'utilisateur '$KIOSK_USER' n'existe pas."
        read -p "Voulez-vous le creer? [o/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Oo]$ ]]; then
            create_kiosk_user
        else
            log_error "Utilisateur requis pour continuer."
            exit 1
        fi
    fi
}

# Cree l'utilisateur kiosque
create_kiosk_user() {
    log_info "Creation de l'utilisateur '$KIOSK_USER'..."

    useradd -m -s /bin/bash -c "EPN Kiosk User" "$KIOSK_USER"

    # Ajouter aux groupes necessaires
    usermod -aG audio,video,plugdev "$KIOSK_USER" 2>/dev/null || true

    log_success "Utilisateur '$KIOSK_USER' cree"
}

# Applique les restrictions dconf pour l'utilisateur
apply_dconf_restrictions() {
    log_info "Application des restrictions dconf pour '$KIOSK_USER'..."

    DBUS_LAUNCH="dbus-launch --exit-with-session"

    # Fonction helper pour dconf en tant que l'utilisateur kiosque
    run_dconf() {
        sudo -u "$KIOSK_USER" $DBUS_LAUNCH dconf "$@" 2>/dev/null || true
    }

    # Restrictions lockdown GNOME
    log_info "  - Desactivation ligne de commande..."
    run_dconf write /org/gnome/desktop/lockdown/disable-command-line true

    log_info "  - Desactivation changement utilisateur..."
    run_dconf write /org/gnome/desktop/lockdown/disable-user-switching true

    log_info "  - Desactivation deconnexion..."
    run_dconf write /org/gnome/desktop/lockdown/disable-log-out true

    log_info "  - Desactivation configuration impression..."
    run_dconf write /org/gnome/desktop/lockdown/disable-print-setup true

    # Restrictions bureau
    log_info "  - Desactivation touche Super..."
    run_dconf write /org/gnome/mutter/overlay-key "''"

    log_info "  - Desactivation hot corners..."
    run_dconf write /org/gnome/desktop/interface/enable-hot-corners false

    log_info "  - Desactivation raccourci Alt+F2..."
    run_dconf write /org/gnome/desktop/wm/keybindings/panel-run-dialog "['']"

    log_info "  - Desactivation notifications..."
    run_dconf write /org/gnome/desktop/notifications/show-banners false

    log_success "Restrictions dconf appliquees"
}

# Retire les restrictions dconf
remove_dconf_restrictions() {
    log_info "Retrait des restrictions dconf pour '$KIOSK_USER'..."

    DBUS_LAUNCH="dbus-launch --exit-with-session"

    run_dconf() {
        sudo -u "$KIOSK_USER" $DBUS_LAUNCH dconf "$@" 2>/dev/null || true
    }

    # Reset toutes les cles lockdown
    run_dconf reset /org/gnome/desktop/lockdown/disable-command-line
    run_dconf reset /org/gnome/desktop/lockdown/disable-user-switching
    run_dconf reset /org/gnome/desktop/lockdown/disable-log-out
    run_dconf reset /org/gnome/desktop/lockdown/disable-print-setup
    run_dconf reset /org/gnome/mutter/overlay-key
    run_dconf reset /org/gnome/desktop/interface/enable-hot-corners
    run_dconf reset /org/gnome/desktop/wm/keybindings/panel-run-dialog
    run_dconf reset /org/gnome/desktop/notifications/show-banners

    log_success "Restrictions dconf retirees"
}

# Configure l'auto-login GDM
configure_autologin() {
    log_info "Configuration auto-login pour '$KIOSK_USER'..."

    GDM_CONFIG="/etc/gdm3/custom.conf"

    # Backup
    if [[ -f "$GDM_CONFIG" ]]; then
        cp "$GDM_CONFIG" "${GDM_CONFIG}.bak.$(date +%Y%m%d)"
    fi

    cat > "$GDM_CONFIG" << EOF
# GDM configuration - EPN Solutions
[daemon]
AutomaticLoginEnable=true
AutomaticLogin=$KIOSK_USER

[security]

[xdmcp]

[chooser]

[debug]
EOF

    log_success "Auto-login configure dans $GDM_CONFIG"
}

# Retire l'auto-login
remove_autologin() {
    log_info "Retrait auto-login..."

    GDM_CONFIG="/etc/gdm3/custom.conf"

    # Restaurer le backup s'il existe
    BACKUP=$(ls -t "${GDM_CONFIG}.bak."* 2>/dev/null | head -1)
    if [[ -n "$BACKUP" ]]; then
        cp "$BACKUP" "$GDM_CONFIG"
        log_success "Configuration GDM restauree depuis $BACKUP"
    else
        # Creer une config vide
        cat > "$GDM_CONFIG" << EOF
[daemon]

[security]

[xdmcp]

[chooser]

[debug]
EOF
        log_success "Auto-login desactive"
    fi
}

# Configure l'autostart du client EPN
configure_autostart() {
    log_info "Configuration autostart du client EPN..."

    AUTOSTART_DIR="/home/$KIOSK_USER/.config/autostart"
    mkdir -p "$AUTOSTART_DIR"

    cat > "$AUTOSTART_DIR/epn-client.desktop" << EOF
[Desktop Entry]
Type=Application
Name=EPN Client
Comment=Client EPN Solutions
Exec=$EPN_CLIENT_PATH
Terminal=false
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=2
EOF

    chown -R "$KIOSK_USER:$KIOSK_USER" "/home/$KIOSK_USER/.config"

    log_success "Autostart configure: $AUTOSTART_DIR/epn-client.desktop"
}

# Retire l'autostart
remove_autostart() {
    log_info "Retrait autostart..."

    AUTOSTART_FILE="/home/$KIOSK_USER/.config/autostart/epn-client.desktop"
    if [[ -f "$AUTOSTART_FILE" ]]; then
        rm "$AUTOSTART_FILE"
        log_success "Autostart retire"
    fi
}

# Configure le blocage USB
configure_usb_block() {
    log_info "Configuration blocage USB storage..."

    cat > /etc/udev/rules.d/99-epn-block-usb-storage.rules << EOF
# EPN Solutions - Bloquer les peripheriques USB de stockage
ACTION=="add", SUBSYSTEMS=="usb", DRIVERS=="usb-storage", ATTR{authorized}="0"
EOF

    udevadm control --reload-rules

    log_success "Blocage USB configure"
}

# Retire le blocage USB
remove_usb_block() {
    log_info "Retrait blocage USB..."

    RULE_FILE="/etc/udev/rules.d/99-epn-block-usb-storage.rules"
    if [[ -f "$RULE_FILE" ]]; then
        rm "$RULE_FILE"
        udevadm control --reload-rules
        log_success "Blocage USB retire"
    fi
}

# Configure le service systemd pour redemarrage auto
configure_systemd_service() {
    log_info "Configuration service systemd..."

    cat > /etc/systemd/system/epn-client.service << EOF
[Unit]
Description=EPN Client Auto-restart
After=graphical-session.target

[Service]
Type=simple
User=$KIOSK_USER
Environment=DISPLAY=:0
ExecStart=$EPN_CLIENT_PATH
Restart=always
RestartSec=5

[Install]
WantedBy=graphical-session.target
EOF

    systemctl daemon-reload

    log_success "Service systemd configure"
}

# Affiche le statut actuel
show_status() {
    echo ""
    echo "=========================================="
    echo "  EPN Solutions - Statut verrouillage"
    echo "=========================================="
    echo ""

    # Utilisateur
    if id "$KIOSK_USER" &>/dev/null; then
        echo -e "Utilisateur kiosque:  ${GREEN}$KIOSK_USER${NC} (existe)"
    else
        echo -e "Utilisateur kiosque:  ${RED}$KIOSK_USER${NC} (n'existe pas)"
    fi

    # Auto-login
    if grep -q "AutomaticLogin=$KIOSK_USER" /etc/gdm3/custom.conf 2>/dev/null; then
        echo -e "Auto-login GDM:       ${GREEN}Active${NC}"
    else
        echo -e "Auto-login GDM:       ${YELLOW}Inactif${NC}"
    fi

    # Autostart
    if [[ -f "/home/$KIOSK_USER/.config/autostart/epn-client.desktop" ]]; then
        echo -e "Autostart client:     ${GREEN}Configure${NC}"
    else
        echo -e "Autostart client:     ${YELLOW}Non configure${NC}"
    fi

    # Blocage USB
    if [[ -f "/etc/udev/rules.d/99-epn-block-usb-storage.rules" ]]; then
        echo -e "Blocage USB:          ${GREEN}Actif${NC}"
    else
        echo -e "Blocage USB:          ${YELLOW}Inactif${NC}"
    fi

    # Restrictions dconf
    echo ""
    echo "Restrictions dconf:"

    DBUS_LAUNCH="dbus-launch --exit-with-session"
    check_dconf() {
        local val=$(sudo -u "$KIOSK_USER" $DBUS_LAUNCH dconf read "$1" 2>/dev/null)
        if [[ "$val" == "true" ]] || [[ "$val" == "''" ]]; then
            echo -e "  $2: ${GREEN}Oui${NC}"
        else
            echo -e "  $2: ${YELLOW}Non${NC}"
        fi
    }

    check_dconf "/org/gnome/desktop/lockdown/disable-command-line" "Terminal desactive"
    check_dconf "/org/gnome/desktop/lockdown/disable-user-switching" "Changement user desactive"
    check_dconf "/org/gnome/desktop/lockdown/disable-log-out" "Deconnexion desactivee"
    check_dconf "/org/gnome/mutter/overlay-key" "Touche Super desactivee"

    echo ""
}

# Applique toutes les restrictions
apply_all() {
    log_info "Application du profil '$PROFILE' pour l'utilisateur '$KIOSK_USER'..."
    echo ""

    check_prerequisites
    apply_dconf_restrictions
    configure_autologin
    configure_autostart

    if [[ "$PROFILE" == "strict" ]] || [[ "$PROFILE" == "standard" ]]; then
        configure_usb_block
    fi

    echo ""
    log_success "Configuration terminee!"
    echo ""
    echo "Prochaines etapes:"
    echo "  1. Redemarrer le systeme"
    echo "  2. Le systeme demarrera automatiquement sur '$KIOSK_USER'"
    echo "  3. Le client EPN demarrera automatiquement"
    echo ""
    echo "Pour retirer les restrictions: sudo $0 --remove"
}

# Retire toutes les restrictions
remove_all() {
    log_info "Retrait de toutes les restrictions..."
    echo ""

    remove_dconf_restrictions
    remove_autologin
    remove_autostart
    remove_usb_block

    echo ""
    log_success "Toutes les restrictions ont ete retirees"
    echo ""
    echo "Note: Un redemarrage peut etre necessaire"
}

# Parse les arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --user)
            KIOSK_USER="$2"
            shift 2
            ;;
        --profile)
            PROFILE="$2"
            shift 2
            ;;
        --apply)
            ACTION="apply"
            shift
            ;;
        --remove)
            ACTION="remove"
            shift
            ;;
        --status)
            ACTION="status"
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            log_error "Option inconnue: $1"
            show_help
            exit 1
            ;;
    esac
done

# Execute l'action
case $ACTION in
    apply)
        apply_all
        ;;
    remove)
        remove_all
        ;;
    status)
        show_status
        ;;
    *)
        show_help
        exit 1
        ;;
esac
