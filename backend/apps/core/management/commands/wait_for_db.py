"""
Commande Django pour attendre que la base de données soit prête
Utile au démarrage des conteneurs Docker
"""

import time
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    """Commande pour attendre que la base de données soit disponible"""

    help = "Attend que la base de données soit disponible"

    def handle(self, *args, **options):
        self.stdout.write('En attente de la base de données...')
        db_conn = None
        max_attempts = 30
        attempt = 0

        while not db_conn and attempt < max_attempts:
            try:
                db_conn = connections['default']
                db_conn.cursor()
            except OperationalError:
                attempt += 1
                self.stdout.write(
                    f'Base de données indisponible, nouvelle tentative dans 1s... ({attempt}/{max_attempts})'
                )
                time.sleep(1)

        if db_conn:
            self.stdout.write(self.style.SUCCESS('Base de données disponible !'))
        else:
            self.stdout.write(
                self.style.ERROR(f'Impossible de se connecter à la base après {max_attempts} tentatives')
            )
            raise OperationalError('Database unavailable')
