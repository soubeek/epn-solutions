#!/bin/bash
# Installation de l'autostart EPN Client pour GNOME
# À exécuter en tant qu'utilisateur epn

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTOSTART_DIR="$HOME/.config/autostart"

echo "=== Installation autostart EPN Client ==="

# Créer le répertoire autostart si nécessaire
mkdir -p "$AUTOSTART_DIR"

# Copier le fichier .desktop
cp "$SCRIPT_DIR/epn-client.desktop" "$AUTOSTART_DIR/"
echo "✓ Fichier .desktop copié dans $AUTOSTART_DIR"

# Copier le script loop dans /usr/local/bin (nécessite sudo)
echo ""
echo "Installation du script de boucle (nécessite sudo)..."
sudo cp "$SCRIPT_DIR/epn-client-loop.sh" /usr/local/bin/
sudo chmod +x /usr/local/bin/epn-client-loop.sh
echo "✓ Script loop installé dans /usr/local/bin"

echo ""
echo "=== Installation terminée ==="
echo ""
echo "L'application EPN Client démarrera automatiquement à la connexion."
echo "Pour tester maintenant: /usr/local/bin/epn-client-loop.sh"
