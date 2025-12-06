#!/bin/bash
# Script wrapper qui relance l'application EPN en boucle
# À utiliser avec l'autostart GNOME

EPN_BIN="/usr/local/bin/epn-gui"

while true; do
    echo "[$(date)] Démarrage de EPN Client..."
    "$EPN_BIN"
    EXIT_CODE=$?
    echo "[$(date)] EPN Client terminé avec code $EXIT_CODE"

    # Pause de 2 secondes avant de relancer
    sleep 2
done
