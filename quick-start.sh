#!/bin/bash
# Script de démarrage rapide pour Poste Public Manager

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║   Poste Public Manager - Script de Démarrage Rapide       ║"
echo "║   Système de gestion d'espaces publics numériques         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Fonction pour afficher les messages
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Vérifier si on est root
if [[ $EUID -ne 0 ]]; then
   error "Ce script doit être exécuté en tant que root"
   exit 1
fi

info "Démarrage de l'installation..."

# 1. Vérifier les prérequis
info "Vérification des prérequis..."

if ! command -v ansible &> /dev/null; then
    warning "Ansible n'est pas installé. Installation en cours..."
    apt update
    apt install -y ansible
    success "Ansible installé"
fi

if ! command -v docker &> /dev/null; then
    warning "Docker n'est pas installé. Il sera installé via Ansible."
fi

# 2. Configuration de l'inventaire
info "Configuration de l'inventaire Ansible..."

if [ ! -f "ansible/inventory/hosts.yml" ]; then
    cp ansible/inventory/hosts.yml.example ansible/inventory/hosts.yml
    warning "Fichier hosts.yml créé. Veuillez le modifier selon votre configuration."
    warning "Éditez ansible/inventory/hosts.yml puis relancez ce script."
    exit 1
fi

if [ ! -f "ansible/inventory/group_vars/all.yml" ]; then
    cp ansible/inventory/group_vars/all.yml.example ansible/inventory/group_vars/all.yml
    warning "Fichier all.yml créé. Veuillez le modifier selon votre configuration."
    warning "Éditez ansible/inventory/group_vars/all.yml puis relancez ce script."
    exit 1
fi

# 3. Demander confirmation
echo ""
echo -e "${YELLOW}Configuration actuelle :${NC}"
echo "  - Inventaire : ansible/inventory/hosts.yml"
echo "  - Variables : ansible/inventory/group_vars/all.yml"
echo ""
read -p "Voulez-vous continuer avec cette configuration ? (o/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Oo]$ ]]; then
    info "Installation annulée."
    exit 1
fi

# 4. Exécuter les playbooks Ansible
info "Exécution des playbooks Ansible..."

cd ansible

# Playbook 1 : Préparation du serveur
info "Étape 1/5 : Préparation du serveur..."
ansible-playbook playbooks/01-prepare-server.yml -i inventory/hosts.yml
success "Serveur préparé"

# Playbook 2 : Configuration réseau
info "Étape 2/5 : Configuration réseau..."
ansible-playbook playbooks/02-configure-network.yml -i inventory/hosts.yml
success "Réseau configuré"

# Playbook 3 : Setup PXE
info "Étape 3/5 : Configuration PXE/TFTP..."
ansible-playbook playbooks/03-setup-pxe.yml -i inventory/hosts.yml
success "PXE configuré"

# Playbook 4 : Build Live Image (optionnel - peut être long)
read -p "Voulez-vous builder l'image Live Debian maintenant ? (peut prendre 30-60 min) (o/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Oo]$ ]]; then
    info "Étape 4/5 : Build de l'image Live Debian..."
    ansible-playbook playbooks/04-build-live-image.yml -i inventory/hosts.yml
    success "Image Live buildée"
else
    warning "Étape 4/5 : Build de l'image Live IGNORÉE (vous pourrez la lancer plus tard)"
fi

# Playbook 5 : Déploiement des services Docker
info "Étape 5/5 : Déploiement des services Docker..."
ansible-playbook playbooks/05-deploy-services.yml -i inventory/hosts.yml
success "Services déployés"

cd ..

# 5. Vérification
info "Vérification de l'installation..."

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          Installation terminée avec succès ! ✓             ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Afficher les informations d'accès
SERVER_IP=$(grep "server_ip:" ansible/inventory/group_vars/all.yml | awk '{print $2}' | tr -d '"')
SERVER_FQDN=$(grep "server_fqdn:" ansible/inventory/group_vars/all.yml | awk '{print $2}' | tr -d '"')

echo -e "${BLUE}📋 Informations d'accès :${NC}"
echo ""
echo "  🌐 Interface d'administration :"
echo "     https://${SERVER_FQDN}"
echo "     ou https://${SERVER_IP}"
echo ""
echo "  🔐 Django Admin :"
echo "     https://${SERVER_FQDN}/admin"
echo "     Identifiant : admin"
echo "     Mot de passe : (voir docker/.env)"
echo ""
echo "  🛡️  Pi-hole :"
echo "     https://pihole.mairie.local/admin"
echo "     Mot de passe : (voir docker/.env)"
echo ""
echo "  🔀 Traefik Dashboard :"
echo "     https://traefik.mairie.local"
echo ""

echo -e "${YELLOW}⚠️  Prochaines étapes :${NC}"
echo ""
echo "  1. Vérifier que tous les services sont démarrés :"
echo "     cd docker && docker compose ps"
echo ""
echo "  2. Consulter les logs si nécessaire :"
echo "     docker compose logs -f"
echo ""
echo "  3. Créer votre premier utilisateur via l'interface web"
echo ""
echo "  4. Générer un code d'accès et tester sur un poste client"
echo ""

echo -e "${BLUE}📚 Documentation :${NC}"
echo "  - Guide complet : docs/README.md"
echo "  - Dépannage : docs/TROUBLESHOOTING.md"
echo "  - API : docs/API.md"
echo ""

echo -e "${GREEN}Bon déploiement ! 🚀${NC}"
echo ""
