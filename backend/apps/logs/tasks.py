"""
Tâches Celery pour les logs
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Log


@shared_task
def cleanup_old_logs(days=90):
    """
    Supprime les logs plus anciens que X jours
    Exécuté quotidiennement via Celery Beat

    Args:
        days: Nombre de jours à conserver (défaut: 90)
    """
    deleted_count = Log.cleanup_old_logs(days=days)

    # Logger cette action
    Log.objects.create(
        action='info',
        operateur='system',
        details=f"Nettoyage automatique : {deleted_count} log(s) supprimé(s) (plus de {days} jours)"
    )

    return f"{deleted_count} log(s) supprimé(s)"


@shared_task
def generate_logs_report():
    """
    Génère un rapport quotidien des logs
    Exécuté quotidiennement via Celery Beat
    """
    from django.db.models import Count

    # Statistiques des dernières 24h
    yesterday = timezone.now() - timedelta(days=1)

    total = Log.objects.filter(created_at__gte=yesterday).count()

    # Stats par action
    stats_by_action = Log.objects.filter(
        created_at__gte=yesterday
    ).values('action').annotate(count=Count('id')).order_by('-count')

    # Logs d'erreurs
    errors = Log.objects.filter(
        created_at__gte=yesterday,
        action='erreur'
    ).count()

    warnings = Log.objects.filter(
        created_at__gte=yesterday,
        action='warning'
    ).count()

    report = {
        'date': timezone.now().isoformat(),
        'period': '24h',
        'total_logs': total,
        'errors': errors,
        'warnings': warnings,
        'by_action': {item['action']: item['count'] for item in stats_by_action}
    }

    # Logger le rapport
    Log.objects.create(
        action='info',
        operateur='system',
        details='Rapport quotidien des logs généré',
        metadata=report
    )

    return f"Rapport généré : {total} logs en 24h ({errors} erreurs, {warnings} warnings)"


@shared_task
def archive_old_logs(days=180):
    """
    Archive les logs anciens (export vers fichier)
    Exécuté mensuellement via Celery Beat

    Args:
        days: Logs plus anciens que X jours à archiver
    """
    import json
    from pathlib import Path

    cutoff_date = timezone.now() - timedelta(days=days)

    logs_to_archive = Log.objects.filter(created_at__lt=cutoff_date)
    count = logs_to_archive.count()

    if count == 0:
        return "Aucun log à archiver"

    # Créer le répertoire d'archives
    archive_dir = Path('/var/log/poste_public/archives')
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Nom du fichier d'archive
    archive_file = archive_dir / f"logs_{cutoff_date.strftime('%Y%m%d')}.json"

    # Exporter les logs
    logs_data = []
    for log in logs_to_archive:
        logs_data.append({
            'id': log.id,
            'created_at': log.created_at.isoformat(),
            'action': log.action,
            'operateur': log.operateur,
            'details': log.details,
            'session_id': log.session_id,
            'ip_address': log.ip_address,
            'metadata': log.metadata
        })

    # Sauvegarder
    with open(archive_file, 'w', encoding='utf-8') as f:
        json.dump(logs_data, f, indent=2, ensure_ascii=False)

    # Logger l'archivage
    Log.objects.create(
        action='info',
        operateur='system',
        details=f"Archivage de {count} logs vers {archive_file}"
    )

    return f"{count} logs archivés vers {archive_file}"
