"""
Utilitaires pour envoyer des messages WebSocket
Utilisé par les ViewSets et les tâches Celery
"""

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def send_time_update(session):
    """
    Envoie une mise à jour du temps restant via WebSocket

    Args:
        session: Instance de Session
    """
    channel_layer = get_channel_layer()
    group_name = f'session_{session.id}'

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'time_update',
            'temps_restant': session.temps_restant,
            'temps_restant_minutes': f"{session.temps_restant // 60:02d}:{session.temps_restant % 60:02d}",
            'pourcentage_utilise': session.pourcentage_utilise,
            'statut': session.statut
        }
    )


def send_time_added(session, secondes, operateur):
    """
    Notifie qu'on a ajouté du temps à la session

    Args:
        session: Instance de Session
        secondes: Nombre de secondes ajoutées
        operateur: Nom de l'opérateur
    """
    channel_layer = get_channel_layer()
    group_name = f'session_{session.id}'

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'time_added',
            'secondes': secondes,
            'temps_restant': session.temps_restant,
            'operateur': operateur
        }
    )


def send_session_terminated(session, raison='fermeture_normale', message='Session terminée'):
    """
    Notifie que la session a été terminée

    Args:
        session: Instance de Session
        raison: Raison de la terminaison
        message: Message à afficher
    """
    channel_layer = get_channel_layer()
    group_name = f'session_{session.id}'

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'session_terminated',
            'raison': raison,
            'message': message
        }
    )


def send_session_warning(session, message, level='warning'):
    """
    Envoie un avertissement à la session

    Args:
        session: Instance de Session
        message: Message d'avertissement
        level: Niveau (info, warning, error)
    """
    channel_layer = get_channel_layer()
    group_name = f'session_{session.id}'

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'session_warning',
            'level': level,
            'message': message,
            'temps_restant': session.temps_restant
        }
    )


def broadcast_to_all_sessions(message_type, data):
    """
    Envoie un message à toutes les sessions actives

    Args:
        message_type: Type de message
        data: Données à envoyer
    """
    from .models import Session

    channel_layer = get_channel_layer()

    # Récupérer toutes les sessions actives
    sessions = Session.objects.filter(statut='active')

    for session in sessions:
        group_name = f'session_{session.id}'
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': message_type,
                **data
            }
        )
