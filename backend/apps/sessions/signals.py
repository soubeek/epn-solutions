"""
Signals pour l'app Sessions
Gère les logs automatiques et autres actions
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Session
from apps.logs.models import Log


@receiver(post_save, sender=Session)
def log_session_creation(sender, instance, created, **kwargs):
    """Log la création d'une session (génération de code)"""
    if created:
        Log.log_action(
            action='generation_code',
            details=f"Code {instance.code_acces} généré pour {instance.utilisateur.get_full_name()}",
            operateur=instance.operateur,
            session=instance,
            metadata={
                'code': instance.code_acces,
                'duree_initiale': instance.duree_initiale,
                'utilisateur_id': instance.utilisateur.id,
                'poste_id': instance.poste.id
            }
        )
