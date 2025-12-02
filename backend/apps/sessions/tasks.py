"""
Tâches Celery pour les sessions
"""

from celery import shared_task
from django.utils import timezone
from django.conf import settings
from .models import Session
from .websocket_utils import send_time_update, send_session_warning, send_session_terminated


@shared_task
def cleanup_expired_sessions():
    """
    Nettoie les sessions expirées
    Exécuté toutes les 5 minutes via Celery Beat
    """
    # Récupérer les sessions actives expirées
    expired_sessions = Session.objects.filter(
        statut='active',
        temps_restant__lte=0
    )

    count = 0
    for session in expired_sessions:
        # Marquer comme expirée
        session.statut = 'expiree'
        session.fin_session = timezone.now()
        session.save(update_fields=['statut', 'fin_session', 'updated_at'])

        # Libérer le poste
        session.poste.marquer_disponible()

        # Log
        from apps.logs.models import Log
        Log.objects.create(
            session=session,
            action='expiration',
            operateur='system',
            details=f"Session {session.code_acces} expirée automatiquement"
        )

        # Notifier via WebSocket
        send_session_terminated(session, raison='expiration', message='Temps écoulé')

        count += 1

    return f"{count} session(s) expirée(s) nettoyée(s)"


@shared_task
def update_session_times():
    """
    Décrémente le temps restant de toutes les sessions actives
    Exécuté toutes les secondes via Celery Beat

    Note: Cette tâche peut être désactivée si le temps est géré
    côté client (calcul depuis debut_session)
    """
    sessions = Session.objects.filter(statut='active')

    for session in sessions:
        # Décrémenter 1 seconde
        session.decremente_temps(secondes=1)

        # Envoyer mise à jour WebSocket
        send_time_update(session)

    return f"{sessions.count()} session(s) mises à jour"


@shared_task
def send_time_warnings():
    """
    Envoie des avertissements pour les sessions dont le temps est bientôt écoulé
    Exécuté toutes les 10 secondes via Celery Beat

    Avertissements aux temps : 5 min, 2 min, 1 min, 30s, 10s
    """
    warning_times = settings.POSTE_PUBLIC.get('WARNING_TIMES', [300, 120, 60, 30, 10])

    sessions = Session.objects.filter(statut='active')

    warnings_sent = 0

    for session in sessions:
        temps_restant = session.temps_restant

        # Vérifier si on est proche d'un temps d'avertissement
        # (avec une marge de ±5 secondes pour ne pas rater)
        for warning_time in warning_times:
            if warning_time - 5 <= temps_restant <= warning_time + 5:
                # Formater le message
                if warning_time >= 60:
                    minutes = warning_time // 60
                    message = f"Attention : il reste {minutes} minute(s)"
                else:
                    message = f"Attention : il reste {warning_time} secondes"

                # Déterminer le niveau
                if warning_time <= 30:
                    level = 'error'
                elif warning_time <= 120:
                    level = 'warning'
                else:
                    level = 'info'

                # Envoyer l'avertissement
                send_session_warning(session, message, level=level)

                warnings_sent += 1
                break  # Un seul avertissement par session

    return f"{warnings_sent} avertissement(s) envoyé(s)"


@shared_task
def cleanup_old_sessions():
    """
    Supprime les vieilles sessions terminées/expirées
    Exécuté quotidiennement via Celery Beat

    Conserve les sessions des 90 derniers jours
    """
    from datetime import timedelta

    cutoff_date = timezone.now() - timedelta(days=90)

    deleted_count, _ = Session.objects.filter(
        statut__in=['terminee', 'expiree'],
        fin_session__lt=cutoff_date
    ).delete()

    return f"{deleted_count} vieille(s) session(s) supprimée(s)"


@shared_task
def generate_sessions_report():
    """
    Génère un rapport quotidien des sessions
    Exécuté quotidiennement via Celery Beat
    """
    from datetime import timedelta
    from django.db.models import Count, Avg, Sum

    # Statistiques des dernières 24h
    yesterday = timezone.now() - timedelta(days=1)

    stats = Session.objects.filter(created_at__gte=yesterday).aggregate(
        total=Count('id'),
        avg_duration=Avg('duree_initiale'),
        total_time_added=Sum('temps_ajoute')
    )

    # Stats par statut
    stats_by_status = Session.objects.filter(
        created_at__gte=yesterday
    ).values('statut').annotate(count=Count('id'))

    report = {
        'date': timezone.now().isoformat(),
        'period': '24h',
        'total_sessions': stats['total'] or 0,
        'avg_duration_minutes': int((stats['avg_duration'] or 0) / 60),
        'total_time_added_minutes': int((stats['total_time_added'] or 0) / 60),
        'by_status': {item['statut']: item['count'] for item in stats_by_status}
    }

    # Log le rapport
    from apps.logs.models import Log
    Log.objects.create(
        action='info',
        operateur='system',
        details='Rapport quotidien des sessions généré',
        metadata=report
    )

    return f"Rapport généré : {stats['total']} sessions en 24h"
