from django.apps import AppConfig


class SessionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.sessions'
    label = 'poste_sessions'  # Éviter conflit avec django.contrib.sessions
    verbose_name = 'Sessions'

    def ready(self):
        import apps.sessions.signals  # noqa
