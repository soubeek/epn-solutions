"""
Signals pour l'app Utilisateurs
Gère les logs automatiques lors des opérations CRUD
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Utilisateur
from apps.logs.models import Log


@receiver(post_save, sender=Utilisateur)
def log_utilisateur_save(sender, instance, created, **kwargs):
    """Log la création ou modification d'un utilisateur"""
    if created:
        Log.log_utilisateur_creation(
            utilisateur=instance,
            operateur=instance.created_by
        )
    else:
        Log.log_action(
            action='modification_utilisateur',
            details=f"Utilisateur {instance.get_full_name()} modifié",
            operateur=getattr(instance, '_modified_by', 'system'),
            metadata={'utilisateur_id': instance.id}
        )


@receiver(post_delete, sender=Utilisateur)
def log_utilisateur_delete(sender, instance, **kwargs):
    """Log la suppression d'un utilisateur"""
    Log.log_action(
        action='suppression_utilisateur',
        details=f"Utilisateur {instance.get_full_name()} supprimé",
        operateur=getattr(instance, '_deleted_by', 'system'),
        metadata={'utilisateur_id': instance.id, 'nom_complet': instance.get_full_name()}
    )
