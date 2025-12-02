#!/bin/bash
# Script d'installation du client Python EPN sur un poste public
# Usage: sudo ./install-client-python.sh [IP_SERVEUR]
# Pour installation manuelle sur postes Linux

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}======================================================================"
echo -e "  Installation Client EPN Python - Poste Public"
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
    echo -n "Adresse IP du serveur EPN [192.168.1.10]: "
    read SERVER_IP
    SERVER_IP="${SERVER_IP:-192.168.1.10}"
fi

echo -e "  Serveur: ${GREEN}https://$SERVER_IP${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# === ÉTAPE 1 : Installation des dépendances système ===
echo -e "${YELLOW}[1/6] Installation des dépendances système...${NC}"

apt-get update -qq
apt-get install -y -qq \
    python3 \
    python3-pip \
    python3-websocket \
    python3-requests \
    ca-certificates \
    > /dev/null 2>&1

echo -e "${GREEN}✓ Dépendances installées${NC}"

# === ÉTAPE 2 : Installation du certificat SSL ===
echo -e "${YELLOW}[2/6] Installation du certificat SSL...${NC}"

CERT_FILE="$PROJECT_DIR/deployment/ssl/poste-public.crt"
if [ ! -f "$CERT_FILE" ]; then
    # Essayer de télécharger depuis le serveur
    echo -e "  ${YELLOW}Tentative de téléchargement du certificat depuis le serveur...${NC}"
    if scp -o StrictHostKeyChecking=no root@$SERVER_IP:/etc/ssl/certs/poste-public.crt /tmp/poste-public.crt 2>/dev/null; then
        CERT_FILE="/tmp/poste-public.crt"
    else
        echo -e "${RED}❌ Certificat SSL non trouvé${NC}"
        echo -e "  Options:"
        echo -e "  1. Copiez le certificat depuis le serveur dans: $PROJECT_DIR/deployment/ssl/"
        echo -e "  2. Ou exécutez d'abord ./generate-ssl-cert.sh sur le serveur"
        exit 1
    fi
fi

cp "$CERT_FILE" /usr/local/share/ca-certificates/epn-server.crt
chmod 644 /usr/local/share/ca-certificates/epn-server.crt
update-ca-certificates > /dev/null 2>&1

echo -e "${GREEN}✓ Certificat SSL installé${NC}"

# === ÉTAPE 3 : Installation du client Python ===
echo -e "${YELLOW}[3/6] Installation du client Python...${NC}"

# Créer répertoires
mkdir -p /opt/epn-client
mkdir -p /var/log/epn-client
mkdir -p /etc/epn-client

# Copier le client Python
CLIENT_DIR="$PROJECT_DIR/client"
if [ -d "$CLIENT_DIR" ]; then
    cp -r "$CLIENT_DIR"/* /opt/epn-client/
else
    echo -e "${RED}❌ Répertoire client non trouvé: $CLIENT_DIR${NC}"
    exit 1
fi

chmod +x /opt/epn-client/*.py 2>/dev/null || true

echo -e "${GREEN}✓ Client Python installé${NC}"

# === ÉTAPE 4 : Configuration du client ===
echo -e "${YELLOW}[4/6] Configuration du client...${NC}"

cat > /etc/epn-client/config.yaml << EOF
# Configuration Client EPN Python
# Généré le $(date)

# Serveur EPN
server_url: https://$SERVER_IP
ws_url: wss://$SERVER_IP/ws/sessions/

# Paramètres de session
check_interval: 5
warning_time: 300
critical_time: 60

# Actions à l'expiration de session
enable_screen_lock: true
lock_on_expire: true
logout_on_expire: false

# Logging
debug: false
log_file: /var/log/epn-client/client.log
EOF

chmod 644 /etc/epn-client/config.yaml

echo -e "${GREEN}✓ Configuration créée${NC}"

# === ÉTAPE 5 : Installation du service systemd ===
echo -e "${YELLOW}[5/6] Installation du service systemd...${NC}"

cat > /etc/systemd/system/epn-client.service << 'EOF'
[Unit]
Description=EPN Client Python - Gestion Poste Public
After=network-online.target graphical.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/epn-client
Environment="PYTHONUNBUFFERED=1"
Environment="EPN_CONFIG=/etc/epn-client/config.yaml"

ExecStartPre=/bin/sleep 10
ExecStart=/usr/bin/python3 /opt/epn-client/poste_client.py

Restart=always
RestartSec=10
StartLimitInterval=0

StandardOutput=append:/var/log/epn-client/client.log
StandardError=append:/var/log/epn-client/client.log

[Install]
WantedBy=graphical.target
EOF

systemctl daemon-reload
systemctl enable epn-client

echo -e "${GREEN}✓ Service systemd installé${NC}"

# === ÉTAPE 6 : Démarrage du service ===
echo -e "${YELLOW}[6/6] Démarrage du service...${NC}"

systemctl start epn-client
sleep 3

if systemctl is-active --quiet epn-client; then
    echo -e "${GREEN}✓ Service démarré avec succès${NC}"
    STATUS="${GREEN}ACTIF${NC}"
else
    echo -e "${YELLOW}⚠ Service en cours de démarrage (vérifiez les logs)${NC}"
    STATUS="${YELLOW}EN COURS${NC}"
fi

echo ""
echo -e "${BLUE}======================================================================"
echo -e "  ✅ Installation terminée !"
echo -e "======================================================================${NC}"
echo ""
echo -e "Statut du service: $STATUS"
echo ""
echo -e "Configuration:"
echo -e "  • Client:       ${GREEN}/opt/epn-client/${NC}"
echo -e "  • Config:       ${GREEN}/etc/epn-client/config.yaml${NC}"
echo -e "  • Logs:         ${GREEN}/var/log/epn-client/client.log${NC}"
echo -e "  • Serveur:      ${GREEN}https://$SERVER_IP${NC}"
echo ""
echo -e "Commandes utiles:"
echo -e "  ${YELLOW}systemctl status epn-client${NC}      # Voir le status"
echo -e "  ${YELLOW}journalctl -u epn-client -f${NC}      # Logs temps réel"
echo -e "  ${YELLOW}systemctl restart epn-client${NC}     # Redémarrer"
echo -e "  ${YELLOW}tail -f /var/log/epn-client/client.log${NC}  # Logs fichier"
echo ""

# Test de connectivité
echo -e "${YELLOW}Test de connectivité au serveur...${NC}"
if curl -sk --connect-timeout 5 "https://$SERVER_IP/api/" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Connexion au serveur OK${NC}"
else
    echo -e "${RED}⚠ Impossible de contacter le serveur${NC}"
    echo -e "  Vérifiez que le serveur est accessible sur $SERVER_IP"
fi
echo ""
