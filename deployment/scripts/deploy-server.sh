#!/bin/bash
# Script de déploiement du serveur Poste Public en production
# Usage: sudo ./deploy-server.sh

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}======================================================================"
echo -e "  Déploiement Serveur Poste Public - Production"
echo -e "======================================================================${NC}"
echo ""

# Vérifier si on est root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Ce script doit être exécuté en tant que root (sudo)${NC}"
    exit 1
fi

# Variables
PROJECT_DIR="/opt/poste-public"
BACKEND_DIR="$PROJECT_DIR/backend"
VENV_DIR="$PROJECT_DIR/venv"
DB_NAME="poste_public_prod"
DB_USER="poste_user"

# Demander le mot de passe DB
echo -n "Mot de passe pour l'utilisateur PostgreSQL '$DB_USER': "
read -s DB_PASSWORD
echo ""

# Demander l'IP du serveur
echo -n "Adresse IP du serveur [192.168.1.10]: "
read SERVER_IP
SERVER_IP="${SERVER_IP:-192.168.1.10}"
echo ""

# === ÉTAPE 1 : Installation des dépendances système ===
echo -e "${YELLOW}[1/10] Installation des dépendances système...${NC}"
apt update
apt install -y \
    postgresql \
    postgresql-contrib \
    redis-server \
    nginx \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    libpq-dev \
    git \
    curl

echo -e "${GREEN}✓ Dépendances système installées${NC}"

# === ÉTAPE 2 : Configuration PostgreSQL ===
echo -e "${YELLOW}[2/10] Configuration de PostgreSQL...${NC}"

# Démarrer PostgreSQL
systemctl start postgresql
systemctl enable postgresql

# Créer base de données et utilisateur
sudo -u postgres psql << EOF
-- Créer utilisateur s'il n'existe pas
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '$DB_USER') THEN
        CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
    END IF;
END
\$\$;

-- Créer base de données si elle n'existe pas
SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

-- Accorder tous les privilèges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF

echo -e "${GREEN}✓ PostgreSQL configuré${NC}"

# === ÉTAPE 3 : Configuration Redis ===
echo -e "${YELLOW}[3/10] Configuration de Redis...${NC}"
systemctl start redis-server
systemctl enable redis-server
echo -e "${GREEN}✓ Redis configuré${NC}"

# === ÉTAPE 4 : Génération certificat SSL ===
echo -e "${YELLOW}[4/10] Génération du certificat SSL...${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$SCRIPT_DIR/generate-ssl-cert.sh" "$SERVER_IP" "poste-public.mairie.local"
echo -e "${GREEN}✓ Certificat SSL généré${NC}"

# === ÉTAPE 5 : Déploiement de l'application ===
echo -e "${YELLOW}[5/10] Déploiement de l'application Django...${NC}"

# Créer répertoires
mkdir -p "$PROJECT_DIR"
mkdir -p /var/log/poste-public

# Copier le code (depuis le répertoire parent)
SOURCE_DIR="$(cd "$SCRIPT_DIR/../../backend" && pwd)"
echo "  Copie depuis: $SOURCE_DIR"
cp -r "$SOURCE_DIR" "$BACKEND_DIR"

# Créer environnement virtuel
echo "  Création de l'environnement virtuel..."
python3 -m venv "$VENV_DIR"

# Installer les dépendances Python
echo "  Installation des dépendances Python..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt"

echo -e "${GREEN}✓ Application déployée${NC}"

# === ÉTAPE 6 : Configuration Django ===
echo -e "${YELLOW}[6/10] Configuration Django...${NC}"

# Générer SECRET_KEY
SECRET_KEY=$("$VENV_DIR/bin/python" -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")

# Créer fichier .env.production
cat > "$BACKEND_DIR/.env.production" << EOF
DJANGO_ENV=production
DEBUG=False
SECRET_KEY=$SECRET_KEY
ALLOWED_HOSTS=poste-public.mairie.local,$SERVER_IP,localhost
CSRF_TRUSTED_ORIGINS=https://poste-public.mairie.local,https://$SERVER_IP

DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME

REDIS_URL=redis://localhost:6379/0

SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_BROWSER_XSS_FILTER=True
SECURE_CONTENT_TYPE_NOSNIFF=True
X_FRAME_OPTIONS=SAMEORIGIN

STATIC_ROOT=$BACKEND_DIR/staticfiles
MEDIA_ROOT=$BACKEND_DIR/media
LOG_FILE=/var/log/poste-public/django.log
EOF

echo -e "${GREEN}✓ Configuration Django créée${NC}"

# === ÉTAPE 7 : Migrations et fichiers statiques ===
echo -e "${YELLOW}[7/10] Migrations de la base de données...${NC}"
cd "$BACKEND_DIR"
DJANGO_ENV=production "$VENV_DIR/bin/python" manage.py migrate --noinput
echo -e "${GREEN}✓ Migrations appliquées${NC}"

echo -e "${YELLOW}[7/10] Collecte des fichiers statiques...${NC}"
DJANGO_ENV=production "$VENV_DIR/bin/python" manage.py collectstatic --noinput
echo -e "${GREEN}✓ Fichiers statiques collectés${NC}"

# Créer superuser (optionnel)
echo ""
echo -e "${YELLOW}Voulez-vous créer un superuser Django ? (o/N)${NC}"
read -r CREATE_SUPERUSER
if [[ "$CREATE_SUPERUSER" =~ ^[Oo]$ ]]; then
    DJANGO_ENV=production "$VENV_DIR/bin/python" manage.py createsuperuser
fi

# === ÉTAPE 8 : Configuration Nginx ===
echo -e "${YELLOW}[8/10] Configuration de Nginx...${NC}"

# Copier configuration
cp "$SCRIPT_DIR/../nginx/poste-public.conf" /etc/nginx/sites-available/poste-public

# Activer le site
ln -sf /etc/nginx/sites-available/poste-public /etc/nginx/sites-enabled/poste-public

# Désactiver le site par défaut
rm -f /etc/nginx/sites-enabled/default

# Tester configuration
nginx -t

# Redémarrer Nginx
systemctl restart nginx
systemctl enable nginx

echo -e "${GREEN}✓ Nginx configuré${NC}"

# === ÉTAPE 9 : Service systemd ===
echo -e "${YELLOW}[9/10] Configuration du service systemd...${NC}"

# Créer utilisateur www-data si nécessaire
id -u www-data &>/dev/null || useradd -r -s /bin/false www-data

# Changer permissions
chown -R www-data:www-data "$PROJECT_DIR"
chown -R www-data:www-data /var/log/poste-public

# Copier service
cp "$SCRIPT_DIR/../systemd/poste-public-server.service" /etc/systemd/system/poste-public.service

# Activer et démarrer
systemctl daemon-reload
systemctl enable poste-public
systemctl start poste-public

# Attendre 3 secondes
sleep 3

echo -e "${GREEN}✓ Service démarré${NC}"

# === ÉTAPE 10 : Vérification ===
echo -e "${YELLOW}[10/10] Vérification du déploiement...${NC}"

# Status des services
echo "  PostgreSQL: $(systemctl is-active postgresql)"
echo "  Redis:      $(systemctl is-active redis-server)"
echo "  Nginx:      $(systemctl is-active nginx)"
echo "  Django:     $(systemctl is-active poste-public)"

# Test HTTP
sleep 2
if curl -k -s "https://localhost/api/" > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓ API accessible${NC}"
else
    echo -e "  ${RED}✗ API non accessible${NC}"
fi

echo ""
echo -e "${GREEN}======================================================================"
echo -e "  ✅ Déploiement terminé avec succès !"
echo -e "======================================================================${NC}"
echo ""
echo -e "Serveur accessible sur:"
echo -e "  • ${GREEN}https://$SERVER_IP${NC}"
echo -e "  • ${GREEN}https://poste-public.mairie.local${NC} (si DNS configuré)"
echo ""
echo -e "Admin Django:"
echo -e "  • ${GREEN}https://$SERVER_IP/admin/${NC}"
echo ""
echo -e "Certificat SSL à distribuer aux clients:"
echo -e "  • ${YELLOW}$SCRIPT_DIR/../ssl/poste-public.crt${NC}"
echo ""
echo -e "Commandes utiles:"
echo -e "  • Logs Django:    ${YELLOW}journalctl -u poste-public -f${NC}"
echo -e "  • Logs Nginx:     ${YELLOW}tail -f /var/log/nginx/poste-public-*.log${NC}"
echo -e "  • Status service: ${YELLOW}systemctl status poste-public${NC}"
echo -e "  • Redémarrer:     ${YELLOW}systemctl restart poste-public${NC}"
echo ""
