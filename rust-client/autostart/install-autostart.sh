#!/bin/bash
# Installation de l'autostart EPN Client pour GNOME
# À exécuter avec sudo depuis le répertoire rust-client

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BINARY_PATH="$PROJECT_DIR/target/release/epn-gui"

# Utilisateur cible (par défaut: epn)
TARGET_USER="${1:-epn}"
TARGET_HOME="/home/$TARGET_USER"
AUTOSTART_DIR="$TARGET_HOME/.config/autostart"

echo "=== Installation autostart EPN Client ==="
echo "Utilisateur cible: $TARGET_USER"

# Vérifier que le binaire existe
if [ ! -f "$BINARY_PATH" ]; then
    echo "❌ Binaire non trouvé: $BINARY_PATH"
    echo "   Exécutez d'abord: cargo build --release"
    exit 1
fi

# Vérifier que l'utilisateur existe
if ! id "$TARGET_USER" &>/dev/null; then
    echo "❌ Utilisateur $TARGET_USER n'existe pas"
    exit 1
fi

# Créer le répertoire autostart si nécessaire
mkdir -p "$AUTOSTART_DIR"
chown "$TARGET_USER:$TARGET_USER" "$AUTOSTART_DIR"
echo "✓ Répertoire autostart créé: $AUTOSTART_DIR"

# Copier le fichier .desktop
cp "$SCRIPT_DIR/epn-client.desktop" "$AUTOSTART_DIR/"
chown "$TARGET_USER:$TARGET_USER" "$AUTOSTART_DIR/epn-client.desktop"
echo "✓ Fichier .desktop copié dans $AUTOSTART_DIR"

# Installer le binaire et le script
echo ""
echo "Installation des binaires..."
cp "$BINARY_PATH" /usr/local/bin/epn-gui
chmod +x /usr/local/bin/epn-gui
echo "✓ Binaire epn-gui installé dans /usr/local/bin"

cp "$SCRIPT_DIR/epn-client-loop.sh" /usr/local/bin/
chmod +x /usr/local/bin/epn-client-loop.sh
echo "✓ Script loop installé dans /usr/local/bin"

echo ""
echo "=== Installation terminée ==="
echo ""
echo "L'application EPN Client démarrera automatiquement à la connexion de $TARGET_USER."
echo "Pour tester: su - $TARGET_USER -c '/usr/local/bin/epn-client-loop.sh'"
