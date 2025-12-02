#!/bin/bash
# Génération de certificat SSL self-signed pour Poste Public
# Usage: sudo ./generate-ssl-cert.sh [IP_SERVEUR] [HOSTNAME]

set -e

IP_SERVEUR="${1:-192.168.1.10}"
HOSTNAME="${2:-poste-public.mairie.local}"

echo "======================================================================"
echo "  Génération Certificat SSL Self-Signed"
echo "======================================================================"
echo ""
echo "  IP Serveur : $IP_SERVEUR"
echo "  Hostname   : $HOSTNAME"
echo ""

# Vérifier si on est root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Ce script doit être exécuté en tant que root (sudo)"
    exit 1
fi

# Créer répertoires si nécessaire
mkdir -p /etc/ssl/private
mkdir -p /etc/ssl/certs

# Générer certificat (valide 10 ans)
echo "[1/4] Génération de la clé privée et du certificat..."
openssl req -x509 -nodes -days 3650 \
    -newkey rsa:4096 \
    -keyout /etc/ssl/private/poste-public.key \
    -out /etc/ssl/certs/poste-public.crt \
    -subj "/C=FR/ST=Reunion/L=Saint-Denis/O=Mairie de La Réunion/OU=IT/CN=$HOSTNAME" \
    -addext "subjectAltName=DNS:$HOSTNAME,DNS:localhost,IP:$IP_SERVEUR,IP:127.0.0.1"

echo "✓ Certificat généré"

# Permissions
echo "[2/4] Configuration des permissions..."
chmod 600 /etc/ssl/private/poste-public.key
chmod 644 /etc/ssl/certs/poste-public.crt
echo "✓ Permissions configurées"

# Copier certificat pour distribution
echo "[3/4] Copie du certificat pour distribution..."
DEPLOY_DIR="$(dirname "$0")/../ssl"
mkdir -p "$DEPLOY_DIR"
cp /etc/ssl/certs/poste-public.crt "$DEPLOY_DIR/poste-public.crt"
echo "✓ Certificat copié dans $DEPLOY_DIR/"

# Afficher informations
echo "[4/4] Informations du certificat..."
openssl x509 -in /etc/ssl/certs/poste-public.crt -noout -subject -dates -ext subjectAltName

echo ""
echo "======================================================================"
echo "  ✅ Certificat SSL créé avec succès !"
echo "======================================================================"
echo ""
echo "Fichiers créés :"
echo "  • Clé privée  : /etc/ssl/private/poste-public.key"
echo "  • Certificat  : /etc/ssl/certs/poste-public.crt"
echo "  • Distribution: $DEPLOY_DIR/poste-public.crt"
echo ""
echo "Pour distribuer aux clients :"
echo "  1. Copier $DEPLOY_DIR/poste-public.crt sur chaque poste"
echo "  2. Exécuter: sudo cp poste-public.crt /usr/local/share/ca-certificates/"
echo "  3. Exécuter: sudo update-ca-certificates"
echo ""
