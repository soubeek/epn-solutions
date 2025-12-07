#!/bin/bash
# Installation de l'autostart EPN Client pour GNOME
# À exécuter depuis le répertoire rust-client

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
AUTOSTART_DIR="$HOME/.config/autostart"
BINARY_PATH="$PROJECT_DIR/target/release/epn-gui"

echo "=== Installation autostart EPN Client ==="

# Vérifier que le binaire existe
if [ ! -f "$BINARY_PATH" ]; then
    echo "❌ Binaire non trouvé: $BINARY_PATH"
    echo "   Exécutez d'abord: cargo build --release"
    exit 1
fi

# Créer le répertoire autostart si nécessaire
mkdir -p "$AUTOSTART_DIR"

# Copier le fichier .desktop
cp "$SCRIPT_DIR/epn-client.desktop" "$AUTOSTART_DIR/"
echo "✓ Fichier .desktop copié dans $AUTOSTART_DIR"

# Installer le binaire et le script (nécessite sudo)
echo ""
echo "Installation des binaires (nécessite sudo)..."
sudo cp "$BINARY_PATH" /usr/local/bin/epn-gui
sudo chmod +x /usr/local/bin/epn-gui
echo "✓ Binaire epn-gui installé dans /usr/local/bin"

sudo cp "$SCRIPT_DIR/epn-client-loop.sh" /usr/local/bin/
sudo chmod +x /usr/local/bin/epn-client-loop.sh
echo "✓ Script loop installé dans /usr/local/bin"

echo ""
echo "=== Installation terminée ==="
echo ""
echo "L'application EPN Client démarrera automatiquement à la connexion."
echo "Pour tester maintenant: /usr/local/bin/epn-client-loop.sh"
