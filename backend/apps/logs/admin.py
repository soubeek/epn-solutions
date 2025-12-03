"""
Django Admin pour Logs
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Log


@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    """Administration des logs"""

    list_display = [
        'created_at',
        'action_display',
        'operateur',
        'session_link',
        'details_short'
    ]

    list_filter = [
        'action',
        'created_at',
        'operateur'
    ]

    search_fields = [
        'details',
        'operateur',
        'ip_address',
        'session__code_acces'
    ]

    readonly_fields = [
        'created_at',
        'action',
        'operateur',
        'details',
        'session',
        'ip_address',
        'metadata'
    ]

    fieldsets = (
        ('Information principale', {
            'fields': (
                'created_at',
                'action',
                'operateur',
                'session'
            )
        }),
        ('Détails', {
            'fields': (
                'details',
                'ip_address',
                'metadata'
            )
        })
    )

    def has_add_permission(self, request):
        """Empêcher l'ajout manuel de logs"""
        return False

    def has_change_permission(self, request, obj=None):
        """Empêcher la modification des logs"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Permettre uniquement la suppression en masse (nettoyage)"""
        return request.user.is_superuser

    def action_display(self, obj):
        """Affichage coloré de l'action"""
        colors = {
            'creation_utilisateur': 'blue',
            'generation_code': 'blue',
            'demarrage_session': 'green',
            'ajout_temps': 'orange',
            'fermeture': 'gray',
            'expiration': 'red',
            'erreur': 'red',
            'warning': 'orange',
            'info': 'blue'
        }
        color = colors.get(obj.action, 'black')
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_action_display()
        )
    action_display.short_description = 'Action'

    def session_link(self, obj):
        """Lien vers la session"""
        if obj.session:
            return format_html(
                '<a href="/admin/sessions/session/{}/change/">{}</a>',
                obj.session.id,
                obj.session.code_acces
            )
        return "-"
    session_link.short_description = 'Session'

    def details_short(self, obj):
        """Détails tronqués"""
        max_length = 80
        if len(obj.details) > max_length:
            return obj.details[:max_length] + '...'
        return obj.details
    details_short.short_description = 'Détails'

    actions = ['cleanup_old_logs']

    @admin.action(description='Nettoyer les logs de plus de 90 jours')
    def cleanup_old_logs(self, request, queryset):
        """Action pour nettoyer les vieux logs"""
        deleted_count = Log.cleanup_old_logs(days=90)
        self.message_user(request, f"{deleted_count} log(s) supprimé(s)")
