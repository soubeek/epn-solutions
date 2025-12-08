#!/usr/bin/env python
"""
Script securise pour creer un superuser Django.

Usage:
    # Interactif (recommande)
    python manage.py shell < scripts/create_superuser.py

    # Avec variables d'environnement
    ADMIN_USERNAME=admin ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD=secret python manage.py shell < scripts/create_superuser.py

    # Depuis le script directement
    cd backend && python scripts/create_superuser.py
"""

import os
import sys
import getpass
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def get_password_securely(prompt="Mot de passe: "):
    """Demande un mot de passe sans l'afficher."""
    try:
        return getpass.getpass(prompt)
    except Exception:
        # Fallback si getpass ne fonctionne pas (Docker sans TTY)
        return input(prompt)


def create_superuser():
    """Cree un superuser de maniere securisee."""
    # Essayer d'importer Django
    try:
        import django
        from django.conf import settings
        if not settings.configured:
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
            django.setup()
        from django.contrib.auth import get_user_model
    except ImportError:
        logger.error("Django n'est pas installe ou le projet n'est pas configure.")
        sys.exit(1)

    User = get_user_model()

    # Recuperer les credentials
    username = os.environ.get('ADMIN_USERNAME')
    email = os.environ.get('ADMIN_EMAIL')
    password = os.environ.get('ADMIN_PASSWORD')

    # Mode interactif si les variables ne sont pas definies
    interactive = not all([username, email, password])

    if interactive:
        logger.info("=== Creation d'un superuser EPN ===")
        logger.info("")

        if not username:
            username = input("Nom d'utilisateur: ").strip()
        if not email:
            email = input("Email: ").strip()
        if not password:
            while True:
                password = get_password_securely("Mot de passe: ")
                password_confirm = get_password_securely("Confirmer le mot de passe: ")
                if password == password_confirm:
                    break
                logger.warning("Les mots de passe ne correspondent pas. Reessayez.")

    # Validation
    if not username or not email or not password:
        logger.error("Username, email et password sont obligatoires.")
        sys.exit(1)

    if len(password) < 8:
        logger.error("Le mot de passe doit faire au moins 8 caracteres.")
        sys.exit(1)

    # Verifier si l'utilisateur existe
    if User.objects.filter(username=username).exists():
        logger.warning(f"L'utilisateur '{username}' existe deja.")
        if interactive:
            response = input("Mettre a jour le mot de passe? [o/N]: ").strip().lower()
            if response == 'o':
                user = User.objects.get(username=username)
                user.set_password(password)
                user.email = email
                user.is_superuser = True
                user.is_staff = True
                user.save()
                logger.info(f"Utilisateur '{username}' mis a jour.")
            else:
                logger.info("Operation annulee.")
        return

    # Creer l'utilisateur
    try:
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )
        logger.info(f"Superuser '{username}' cree avec succes.")

        # Ne pas afficher le mot de passe dans les logs
        if not interactive:
            logger.info("(mot de passe configure depuis les variables d'environnement)")

    except Exception as e:
        logger.error(f"Erreur lors de la creation: {e}")
        sys.exit(1)


if __name__ == '__main__':
    create_superuser()
