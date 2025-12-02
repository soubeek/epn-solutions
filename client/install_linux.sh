#!/bin/bash
###############################################################################
# Script d'installation du client Poste Public - Linux
# Usage: sudo ./install_linux.sh
###############################################################################

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/poste-client"
SERVICE_NAME="poste-client"
USER="poste"
GROUP="poste"

echo -e "${GREEN}====================================================================${NC}"
echo -e "${GREEN}  Installation du Client Poste Public${NC}"
echo -e "${GREEN}====================================================================${NC}"
echo ""

# Vérifier si root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}✗ Ce script doit être exécuté avec sudo${NC}"
   exit 1
fi

echo -e "${YELLOW}[1/7]${NC} Vérification des dépendances..."

# Vérifier Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 non trouvé. Installation...${NC}"
    apt-get update
    apt-get install -y python3 python3-pip
fi

python3 --version
echo -e "${GREEN}✓ Python 3 installé${NC}"

# Vérifier pip
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}✗ pip3 non trouvé. Installation...${NC}"
    apt-get install -y python3-pip
fi

echo -e "${GREEN}✓ pip3 installé${NC}"

echo ""
echo -e "${YELLOW}[2/7]${NC} Création de l'utilisateur système..."

# Créer l'utilisateur poste si n'existe pas
if ! id "$USER" &>/dev/null; then
    useradd -r -s /bin/bash -d "$INSTALL_DIR" -m "$USER"
    echo -e "${GREEN}✓ Utilisateur '$USER' créé${NC}"
else
    echo -e "${GREEN}✓ Utilisateur '$USER' existe déjà${NC}"
fi

echo ""
echo -e "${YELLOW}[3/7]${NC} Installation des fichiers..."

# Créer le répertoire d'installation
mkdir -p "$INSTALL_DIR"

# Copier les fichiers
cp poste_client.py "$INSTALL_DIR/"
cp session_manager.py "$INSTALL_DIR/"
cp config.py "$INSTALL_DIR/"
cp requirements.txt "$INSTALL_DIR/"

# Rendre exécutable
chmod +x "$INSTALL_DIR/poste_client.py"

echo -e "${GREEN}✓ Fichiers copiés vers $INSTALL_DIR${NC}"

echo ""
echo -e "${YELLOW}[4/7]${NC} Installation des dépendances Python..."

cd "$INSTALL_DIR"
pip3 install -r requirements.txt --break-system-packages 2>/dev/null || pip3 install -r requirements.txt

echo -e "${GREEN}✓ Dépendances Python installées${NC}"

echo ""
echo -e "${YELLOW}[5/7]${NC} Configuration des permissions..."

# Créer le répertoire de logs
mkdir -p /var/log
touch /var/log/poste-client.log
chown "$USER:$GROUP" /var/log/poste-client.log

# Permissions sur le répertoire
chown -R "$USER:$GROUP" "$INSTALL_DIR"

echo -e "${GREEN}✓ Permissions configurées${NC}"

echo ""
echo -e "${YELLOW}[6/7]${NC} Installation du service systemd..."

# Copier le fichier service
cp systemd/poste-client.service /etc/systemd/system/

# Recharger systemd
systemctl daemon-reload

echo -e "${GREEN}✓ Service systemd installé${NC}"

echo ""
echo -e "${YELLOW}[7/7]${NC} Configuration du service..."

# Demander l'URL du serveur
echo ""
echo -e "${YELLOW}Configuration:${NC}"
read -p "URL du serveur API (ex: http://192.168.1.10:8001): " SERVER_URL

if [ -z "$SERVER_URL" ]; then
    SERVER_URL="http://localhost:8001"
fi

WS_URL="${SERVER_URL/http/ws}"

# Mettre à jour le fichier service
sed -i "s|POSTE_SERVER_URL=.*|POSTE_SERVER_URL=$SERVER_URL\"|g" /etc/systemd/system/poste-client.service
sed -i "s|POSTE_WS_URL=.*|POSTE_WS_URL=$WS_URL\"|g" /etc/systemd/system/poste-client.service

# Recharger
systemctl daemon-reload

echo -e "${GREEN}✓ Configuration terminée${NC}"

echo ""
echo -e "${GREEN}====================================================================${NC}"
echo -e "${GREEN}  Installation terminée avec succès !${NC}"
echo -e "${GREEN}====================================================================${NC}"
echo ""
echo -e "Commandes utiles:"
echo -e "  ${YELLOW}Démarrer${NC}  : sudo systemctl start $SERVICE_NAME"
echo -e "  ${YELLOW}Arrêter${NC}   : sudo systemctl stop $SERVICE_NAME"
echo -e "  ${YELLOW}Statut${NC}    : sudo systemctl status $SERVICE_NAME"
echo -e "  ${YELLOW}Logs${NC}      : sudo journalctl -u $SERVICE_NAME -f"
echo -e "  ${YELLOW}Auto-start${NC}: sudo systemctl enable $SERVICE_NAME"
echo ""
echo -e "Mode manuel:"
echo -e "  ${YELLOW}cd $INSTALL_DIR${NC}"
echo -e "  ${YELLOW}sudo -u $USER python3 poste_client.py --interactive${NC}"
echo ""
echo -e "${GREEN}====================================================================${NC}"

# Proposer de démarrer le service
echo ""
read -p "Démarrer le service maintenant ? (o/N) " START_NOW

if [[ $START_NOW =~ ^[Oo]$ ]]; then
    systemctl start $SERVICE_NAME
    systemctl enable $SERVICE_NAME
    echo ""
    echo -e "${GREEN}✓ Service démarré et activé au boot${NC}"
    echo ""
    systemctl status $SERVICE_NAME
fi

echo ""
echo -e "${GREEN}Installation complète !${NC}"
