#!/bin/bash
# Script d'installation du service systemd pour EPN Client
# À exécuter en tant qu'utilisateur epn

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/epn-client.service"
USER_SERVICE_DIR="$HOME/.config/systemd/user"

echo "=== Installation du service EPN Client ==="

# Créer le répertoire si nécessaire
mkdir -p "$USER_SERVICE_DIR"

# Copier le fichier service
cp "$SERVICE_FILE" "$USER_SERVICE_DIR/"
echo "✓ Service copié dans $USER_SERVICE_DIR"

# Recharger systemd
systemctl --user daemon-reload
echo "✓ Systemd rechargé"

# Activer le service
systemctl --user enable epn-client.service
echo "✓ Service activé"

# Démarrer le service
systemctl --user start epn-client.service
echo "✓ Service démarré"

# Afficher le statut
echo ""
echo "=== Statut du service ==="
systemctl --user status epn-client.service --no-pager

echo ""
echo "=== Commandes utiles ==="
echo "  Voir les logs:    journalctl --user -u epn-client -f"
echo "  Redémarrer:       systemctl --user restart epn-client"
echo "  Arrêter:          systemctl --user stop epn-client"
echo "  Désactiver:       systemctl --user disable epn-client"
