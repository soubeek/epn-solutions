#!/bin/bash
# Script d'installation du client EPN sur un poste public
# Usage: sudo ./install-client.sh [IP_SERVEUR]

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}======================================================================"
echo -e "  Installation Client EPN - Poste Public"
echo -e "======================================================================${NC}"
echo ""

# Vérifier si on est root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Ce script doit être exécuté en tant que root (sudo)${NC}"
    exit 1
fi

# IP du serveur
SERVER_IP="${1}"
if [ -z "$SERVER_IP" ]; then
    echo -n "Adresse IP du serveur [192.168.1.10]: "
    read SERVER_IP
    SERVER_IP="${SERVER_IP:-192.168.1.10}"
fi

echo -e "  Serveur: ${GREEN}https://$SERVER_IP${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# === ÉTAPE 1 : Vérification des fichiers requis ===
echo -e "${YELLOW}[1/7] Vérification des fichiers requis...${NC}"

# Binaire client
CLIENT_BINARY="$SCRIPT_DIR/../../rust-client/target/release/epn-gui"
if [ ! -f "$CLIENT_BINARY" ]; then
    echo -e "${RED}❌ Binaire client non trouvé: $CLIENT_BINARY${NC}"
    echo -e "  Compilez d'abord le client Rust avec: cargo build --release"
    exit 1
fi

# Certificat SSL
CERT_FILE="$SCRIPT_DIR/../ssl/poste-public.crt"
if [ ! -f "$CERT_FILE" ]; then
    echo -e "${RED}❌ Certificat SSL non trouvé: $CERT_FILE${NC}"
    echo -e "  Générez d'abord le certificat sur le serveur avec: ./generate-ssl-cert.sh"
    exit 1
fi

echo -e "${GREEN}✓ Fichiers requis trouvés${NC}"

# === ÉTAPE 2 : Installation du certificat SSL ===
echo -e "${YELLOW}[2/7] Installation du certificat SSL...${NC}"

# Copier certificat
cp "$CERT_FILE" /usr/local/share/ca-certificates/poste-public.crt
chmod 644 /usr/local/share/ca-certificates/poste-public.crt

# Mettre à jour le trust store
update-ca-certificates

echo -e "${GREEN}✓ Certificat SSL installé${NC}"

# === ÉTAPE 3 : Installation du binaire ===
echo -e "${YELLOW}[3/7] Installation du binaire client...${NC}"

# Copier le binaire
cp "$CLIENT_BINARY" /usr/local/bin/epn-client
chmod 755 /usr/local/bin/epn-client

# Vérifier
if /usr/local/bin/epn-client --help > /dev/null 2>&1 || [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Binaire installé et fonctionnel${NC}"
else
    echo -e "${YELLOW}⚠ Binaire installé (vérification non conclusive)${NC}"
fi

# === ÉTAPE 4 : Configuration ===
echo -e "${YELLOW}[4/7] Configuration du client...${NC}"

# Créer répertoires
mkdir -p /etc/epn-client
mkdir -p /var/log/epn-client
mkdir -p /opt/epn-client

# Créer fichier de configuration
cat > /etc/epn-client/config.yaml << EOF
# Configuration Client EPN - Poste Public
# Généré automatiquement le $(date)

# URLs du serveur (HTTPS/WSS)
server_url: https://$SERVER_IP
ws_url: wss://$SERVER_IP

# Paramètres de session
check_interval: 5
warning_time: 300
critical_time: 60

# Actions à l'expiration
enable_screen_lock: true
lock_on_expire: true
logout_on_expire: false

# Logging
debug: false
log_level: info

# SSL (certificat self-signed installé)
skip_ssl_verification: false
EOF

chmod 644 /etc/epn-client/config.yaml

echo -e "${GREEN}✓ Configuration créée${NC}"

# === ÉTAPE 5 : Création utilisateur service ===
echo -e "${YELLOW}[5/7] Création de l'utilisateur service...${NC}"

# Créer utilisateur 'epn' si nécessaire
if ! id -u epn > /dev/null 2>&1; then
    useradd -r -s /bin/false -d /opt/epn-client -c "EPN Client Service" epn
    echo -e "  ${GREEN}✓ Utilisateur 'epn' créé${NC}"
else
    echo -e "  ${YELLOW}⚠ Utilisateur 'epn' existe déjà${NC}"
fi

# Permissions
chown -R epn:epn /opt/epn-client
chown -R epn:epn /var/log/epn-client

echo -e "${GREEN}✓ Utilisateur configuré${NC}"

# === ÉTAPE 6 : Installation du service systemd ===
echo -e "${YELLOW}[6/7] Installation du service systemd...${NC}"

# Copier service ou le créer
SERVICE_FILE="$SCRIPT_DIR/../systemd/epn-client.service"
if [ -f "$SERVICE_FILE" ]; then
    cp "$SERVICE_FILE" /etc/systemd/system/epn-client.service
else
    # Créer le service directement
    cat > /etc/systemd/system/epn-client.service << 'EOF'
[Unit]
Description=EPN Client - Gestion Poste Public
Documentation=https://github.com/mairie-reunion/epn-client
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=epn
Group=epn
WorkingDirectory=/opt/epn-client

Environment="RUST_LOG=info"
Environment="EPN_CONFIG=/etc/epn-client/config.yaml"

ExecStart=/usr/local/bin/epn-client

Restart=always
RestartSec=10
StartLimitInterval=0

ExecStartPre=/bin/sleep 5

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/epn-client

StandardOutput=journal
StandardError=journal
SyslogIdentifier=epn-client

[Install]
WantedBy=multi-user.target
EOF
fi

# Recharger systemd
systemctl daemon-reload

# Activer le service
systemctl enable epn-client

echo -e "${GREEN}✓ Service systemd installé${NC}"

# === ÉTAPE 7 : Démarrage du service ===
echo -e "${YELLOW}[7/7] Démarrage du service...${NC}"

# Démarrer
systemctl start epn-client

# Attendre 3 secondes
sleep 3

# Vérifier status
if systemctl is-active --quiet epn-client; then
    echo -e "${GREEN}✓ Service démarré avec succès${NC}"
    STATUS="${GREEN}ACTIF${NC}"
else
    echo -e "${RED}✗ Échec du démarrage du service${NC}"
    STATUS="${RED}INACTIF${NC}"
fi

echo ""
echo -e "${GREEN}======================================================================"
echo -e "  ✅ Installation terminée !"
echo -e "======================================================================${NC}"
echo ""
echo -e "Statut du service: $STATUS"
echo ""
echo -e "Configuration:"
echo -e "  • Binaire:      ${GREEN}/usr/local/bin/epn-client${NC}"
echo -e "  • Config:       ${GREEN}/etc/epn-client/config.yaml${NC}"
echo -e "  • Logs:         ${GREEN}/var/log/epn-client/${NC}"
echo -e "  • Serveur:      ${GREEN}https://$SERVER_IP${NC}"
echo ""
echo -e "Commandes utiles:"
echo -e "  • Status:       ${YELLOW}systemctl status epn-client${NC}"
echo -e "  • Logs temps réel: ${YELLOW}journalctl -u epn-client -f${NC}"
echo -e "  • Redémarrer:   ${YELLOW}systemctl restart epn-client${NC}"
echo -e "  • Arrêter:      ${YELLOW}systemctl stop epn-client${NC}"
echo -e "  • Désactiver:   ${YELLOW}systemctl disable epn-client${NC}"
echo ""

# Afficher logs récents si erreur
if ! systemctl is-active --quiet epn-client; then
    echo -e "${YELLOW}Logs récents (dernières 20 lignes):${NC}"
    journalctl -u epn-client -n 20 --no-pager
    echo ""
fi
