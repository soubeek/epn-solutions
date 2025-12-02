#!/bin/bash
#
# Script de génération des certificats SSL avec CA locale
# Pour EPN Solutions - Gestion des Postes Publics
#
# Usage: ./generate-certificates.sh [OPTIONS]
#   -d, --domain    Domaine principal (défaut: postes.mairie.local)
#   -i, --ip        Adresse IP du serveur (défaut: 192.168.1.10)
#   -o, --output    Répertoire de sortie (défaut: ../certs)
#   -f, --force     Écraser les certificats existants
#   -h, --help      Afficher l'aide
#
# Exemple:
#   ./generate-certificates.sh -d postes.mairie.local -i 192.168.1.10
#

set -e

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Valeurs par défaut
DOMAIN="postes.mairie.local"
SERVER_IP="192.168.1.10"
OUTPUT_DIR="../certs"
FORCE=false

# Informations du certificat
COUNTRY="FR"
STATE="Reunion"
CITY="Saint-Denis"
ORG="Mairie"
OU="IT"
CA_CN="EPN-CA"

# Durées de validité
CA_DAYS=3650      # 10 ans pour la CA
SERVER_DAYS=730   # 2 ans pour le serveur

#######################################
# Affiche l'aide
#######################################
show_help() {
    echo -e "${BLUE}=== Générateur de Certificats SSL EPN ===${NC}"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -d, --domain DOMAIN   Domaine principal (défaut: $DOMAIN)"
    echo "  -i, --ip IP           Adresse IP du serveur (défaut: $SERVER_IP)"
    echo "  -o, --output DIR      Répertoire de sortie (défaut: $OUTPUT_DIR)"
    echo "  -f, --force           Écraser les certificats existants"
    echo "  -h, --help            Afficher cette aide"
    echo ""
    echo "Exemple:"
    echo "  $0 -d postes.mairie.local -i 192.168.1.10"
    echo ""
    echo "Fichiers générés:"
    echo "  ca.key        - Clé privée de l'autorité de certification"
    echo "  ca.crt        - Certificat de l'autorité de certification"
    echo "  server.key    - Clé privée du serveur"
    echo "  server.crt    - Certificat du serveur"
    echo ""
}

#######################################
# Parse les arguments
#######################################
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--domain)
                DOMAIN="$2"
                shift 2
                ;;
            -i|--ip)
                SERVER_IP="$2"
                shift 2
                ;;
            -o|--output)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            -f|--force)
                FORCE=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                echo -e "${RED}Erreur: Option inconnue: $1${NC}"
                show_help
                exit 1
                ;;
        esac
    done
}

#######################################
# Vérifie les prérequis
#######################################
check_prerequisites() {
    echo -e "${BLUE}Vérification des prérequis...${NC}"

    if ! command -v openssl &> /dev/null; then
        echo -e "${RED}Erreur: openssl n'est pas installé${NC}"
        echo "Installez-le avec: sudo apt install openssl"
        exit 1
    fi

    echo -e "${GREEN}✓ openssl est disponible${NC}"
}

#######################################
# Crée le répertoire de sortie
#######################################
create_output_dir() {
    if [ -d "$OUTPUT_DIR" ]; then
        if [ "$FORCE" = false ]; then
            if [ -f "$OUTPUT_DIR/ca.crt" ] || [ -f "$OUTPUT_DIR/server.crt" ]; then
                echo -e "${YELLOW}Attention: Des certificats existent déjà dans $OUTPUT_DIR${NC}"
                read -p "Voulez-vous les écraser? (o/N) " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Oo]$ ]]; then
                    echo -e "${RED}Opération annulée${NC}"
                    exit 1
                fi
            fi
        fi
    else
        echo -e "${BLUE}Création du répertoire $OUTPUT_DIR...${NC}"
        mkdir -p "$OUTPUT_DIR"
    fi
}

#######################################
# Génère la CA (Autorité de Certification)
#######################################
generate_ca() {
    echo -e "${BLUE}Génération de l'Autorité de Certification (CA)...${NC}"

    # Générer la clé privée de la CA (4096 bits pour plus de sécurité)
    openssl genrsa -out "$OUTPUT_DIR/ca.key" 4096 2>/dev/null

    # Créer le certificat CA auto-signé
    openssl req -x509 -new -nodes \
        -key "$OUTPUT_DIR/ca.key" \
        -sha256 \
        -days $CA_DAYS \
        -out "$OUTPUT_DIR/ca.crt" \
        -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORG/OU=$OU/CN=$CA_CN"

    echo -e "${GREEN}✓ CA générée (valide $CA_DAYS jours)${NC}"
}

#######################################
# Génère le certificat serveur
#######################################
generate_server_cert() {
    echo -e "${BLUE}Génération du certificat serveur...${NC}"

    # Générer la clé privée du serveur
    openssl genrsa -out "$OUTPUT_DIR/server.key" 2048 2>/dev/null

    # Créer la demande de certificat (CSR)
    openssl req -new \
        -key "$OUTPUT_DIR/server.key" \
        -out "$OUTPUT_DIR/server.csr" \
        -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORG/OU=$OU/CN=$DOMAIN"

    # Créer le fichier d'extensions pour SAN (Subject Alternative Names)
    cat > "$OUTPUT_DIR/server.ext" << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = $DOMAIN
DNS.2 = *.$DOMAIN
DNS.3 = localhost
IP.1 = $SERVER_IP
IP.2 = 127.0.0.1
EOF

    # Signer le certificat serveur avec la CA
    openssl x509 -req \
        -in "$OUTPUT_DIR/server.csr" \
        -CA "$OUTPUT_DIR/ca.crt" \
        -CAkey "$OUTPUT_DIR/ca.key" \
        -CAcreateserial \
        -out "$OUTPUT_DIR/server.crt" \
        -days $SERVER_DAYS \
        -sha256 \
        -extfile "$OUTPUT_DIR/server.ext"

    # Nettoyer les fichiers temporaires
    rm -f "$OUTPUT_DIR/server.csr" "$OUTPUT_DIR/server.ext" "$OUTPUT_DIR/ca.srl"

    echo -e "${GREEN}✓ Certificat serveur généré (valide $SERVER_DAYS jours)${NC}"
}

#######################################
# Définit les permissions
#######################################
set_permissions() {
    echo -e "${BLUE}Configuration des permissions...${NC}"

    # Certificats lisibles par tous
    chmod 644 "$OUTPUT_DIR/ca.crt"
    chmod 644 "$OUTPUT_DIR/server.crt"

    # Clés privées protégées
    chmod 600 "$OUTPUT_DIR/ca.key"
    chmod 600 "$OUTPUT_DIR/server.key"

    echo -e "${GREEN}✓ Permissions configurées${NC}"
}

#######################################
# Vérifie les certificats
#######################################
verify_certificates() {
    echo -e "${BLUE}Vérification des certificats...${NC}"

    # Vérifier que le certificat serveur est signé par la CA
    if openssl verify -CAfile "$OUTPUT_DIR/ca.crt" "$OUTPUT_DIR/server.crt" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Chaîne de certification valide${NC}"
    else
        echo -e "${RED}✗ Erreur de vérification de la chaîne${NC}"
        exit 1
    fi

    # Afficher les infos du certificat serveur
    echo -e "${BLUE}Informations du certificat serveur:${NC}"
    echo "  Domaine: $DOMAIN"
    echo "  IP: $SERVER_IP"
    echo "  Validité: $(openssl x509 -in "$OUTPUT_DIR/server.crt" -noout -dates | grep 'notAfter' | cut -d'=' -f2)"

    # Afficher les SANs
    echo -e "${BLUE}Subject Alternative Names:${NC}"
    openssl x509 -in "$OUTPUT_DIR/server.crt" -noout -text 2>/dev/null | \
        grep -A1 "Subject Alternative Name" | tail -1 | \
        sed 's/,/\n  /g' | sed 's/^/  /'
}

#######################################
# Affiche les instructions
#######################################
show_instructions() {
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}   Certificats générés avec succès!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${YELLOW}Fichiers créés dans $OUTPUT_DIR/:${NC}"
    echo "  ca.key        - Clé privée CA (GARDER SECRET!)"
    echo "  ca.crt        - Certificat CA (à distribuer aux clients)"
    echo "  server.key    - Clé privée serveur"
    echo "  server.crt    - Certificat serveur"
    echo ""
    echo -e "${YELLOW}Prochaines étapes:${NC}"
    echo ""
    echo "1. Démarrer les services Docker:"
    echo -e "   ${BLUE}cd /opt/epn-solutions/docker${NC}"
    echo -e "   ${BLUE}docker compose up -d${NC}"
    echo ""
    echo "2. Installer la CA sur les clients Linux:"
    echo -e "   ${BLUE}sudo cp $OUTPUT_DIR/ca.crt /usr/local/share/ca-certificates/epn-ca.crt${NC}"
    echo -e "   ${BLUE}sudo update-ca-certificates${NC}"
    echo ""
    echo "3. Installer la CA sur les clients Windows:"
    echo "   - Double-cliquer sur ca.crt"
    echo "   - Installer dans 'Autorités de certification racines de confiance'"
    echo ""
    echo "4. Configurer le DNS ou /etc/hosts:"
    echo -e "   ${BLUE}echo '$SERVER_IP $DOMAIN' | sudo tee -a /etc/hosts${NC}"
    echo ""
    echo -e "${YELLOW}Test de connexion:${NC}"
    echo -e "   ${BLUE}curl --cacert $OUTPUT_DIR/ca.crt https://$DOMAIN/api/health/${NC}"
    echo ""
}

#######################################
# Main
#######################################
main() {
    echo -e "${GREEN}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║     EPN Solutions - Générateur de Certificats SSL        ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    parse_args "$@"
    check_prerequisites
    create_output_dir
    generate_ca
    generate_server_cert
    set_permissions
    verify_certificates
    show_instructions
}

# Exécuter le script
main "$@"
