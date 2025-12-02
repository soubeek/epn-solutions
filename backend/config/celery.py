"""
Configuration Celery pour Poste Public Manager
Gère les tâches asynchrones et planifiées
"""

import os
from celery import Celery
from celery.schedules import crontab

# Définir le module de settings Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('poste_public')

# Configuration depuis Django settings avec le namespace 'CELERY'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-découverte des tâches dans les apps Django
app.autodiscover_tasks()

# Configuration des tâches périodiques
app.conf.beat_schedule = {
    # === SESSIONS ===

    # Nettoyage des sessions expirées toutes les 5 minutes
    'cleanup-expired-sessions': {
        'task': 'apps.sessions.tasks.cleanup_expired_sessions',
        'schedule': crontab(minute='*/5'),
    },

    # Envoi des avertissements de fin de session (toutes les 10 secondes)
    'send-session-warnings': {
        'task': 'apps.sessions.tasks.send_time_warnings',
        'schedule': 10.0,  # Toutes les 10 secondes
    },

    # Mise à jour des temps de session (toutes les secondes)
    # NOTE: Peut être désactivé si le temps est calculé côté client
    'update-session-times': {
        'task': 'apps.sessions.tasks.update_session_times',
        'schedule': 1.0,  # Toutes les secondes
    },

    # Nettoyage des vieilles sessions (tous les jours à 4h)
    'cleanup-old-sessions': {
        'task': 'apps.sessions.tasks.cleanup_old_sessions',
        'schedule': crontab(hour=4, minute=0),
    },

    # Rapport quotidien des sessions (tous les jours à 6h)
    'sessions-daily-report': {
        'task': 'apps.sessions.tasks.generate_sessions_report',
        'schedule': crontab(hour=6, minute=0),
    },

    # === LOGS ===

    # Nettoyage des logs anciens (tous les jours à 3h du matin)
    'cleanup-old-logs': {
        'task': 'apps.logs.tasks.cleanup_old_logs',
        'schedule': crontab(hour=3, minute=0),
    },

    # Rapport quotidien des logs (tous les jours à 6h30)
    'logs-daily-report': {
        'task': 'apps.logs.tasks.generate_logs_report',
        'schedule': crontab(hour=6, minute=30),
    },

    # Archivage des logs (tous les 1ers du mois à 1h)
    'archive-old-logs': {
        'task': 'apps.logs.tasks.archive_old_logs',
        'schedule': crontab(hour=1, minute=0, day_of_month=1),
    },

    # === SYSTÈME ===

    # Backup automatique de la base (tous les jours à 2h du matin)
    # TODO: Créer apps/core/tasks.py avec la tâche daily_backup
    # 'daily-backup': {
    #     'task': 'apps.core.tasks.daily_backup',
    #     'schedule': crontab(hour=2, minute=0),
    # },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Tâche de debug"""
    print(f'Request: {self.request!r}')
