#!/bin/bash
# Script pour sauvegarder le profil Firefox actuel comme template
# À exécuter avec sudo après avoir configuré Firefox

set -e

TEMPLATE_DIR="/usr/share/epn/firefox-template"
SOURCE_USER="${1:-epn}"
SOURCE_DIR="/home/$SOURCE_USER/.mozilla/firefox"

echo "=== Sauvegarde du template Firefox ==="
echo "Utilisateur source: $SOURCE_USER"
echo "Dossier source: $SOURCE_DIR"
echo "Dossier template: $TEMPLATE_DIR"
echo ""

# Vérifier que le dossier source existe
if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ Dossier Firefox non trouvé: $SOURCE_DIR"
    echo "   Lancez Firefox une fois pour créer le profil"
    exit 1
fi

# Vérifier que Firefox n'est pas en cours d'exécution
if pgrep -u "$SOURCE_USER" firefox > /dev/null; then
    echo "❌ Firefox est en cours d'exécution pour $SOURCE_USER"
    echo "   Fermez Firefox avant de sauvegarder le template"
    exit 1
fi

# Créer le dossier template
echo "Création du dossier template..."
mkdir -p "$TEMPLATE_DIR"

# Copier le profil Firefox
echo "Copie du profil Firefox..."
cp -r "$SOURCE_DIR"/* "$TEMPLATE_DIR/"

# Nettoyer les données de session du template (optionnel mais recommandé)
echo "Nettoyage des données de session du template..."
find "$TEMPLATE_DIR" -name "*.sqlite-wal" -delete 2>/dev/null || true
find "$TEMPLATE_DIR" -name "*.sqlite-shm" -delete 2>/dev/null || true
find "$TEMPLATE_DIR" -name "cookies.sqlite" -delete 2>/dev/null || true
find "$TEMPLATE_DIR" -name "places.sqlite" -delete 2>/dev/null || true
find "$TEMPLATE_DIR" -name "formhistory.sqlite" -delete 2>/dev/null || true
find "$TEMPLATE_DIR" -name "sessionstore*" -delete 2>/dev/null || true
find "$TEMPLATE_DIR" -type d -name "cache2" -exec rm -rf {} + 2>/dev/null || true
find "$TEMPLATE_DIR" -type d -name "storage" -exec rm -rf {} + 2>/dev/null || true

# Fixer les permissions
echo "Configuration des permissions..."
chmod -R 755 "$TEMPLATE_DIR"

echo ""
echo "=== Template Firefox sauvegardé ==="
echo "Le profil sera restauré à chaque fin de session EPN."
echo ""
echo "Contenu du template:"
ls -la "$TEMPLATE_DIR"
