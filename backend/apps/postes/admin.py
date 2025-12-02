"""
Django Admin pour Postes
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Poste


@admin.register(Poste)
class PosteAdmin(admin.ModelAdmin):
    """Administration des postes"""

    list_display = [
        'nom',
        'ip_address',
        'statut_display',
        'est_en_ligne_display',
        'session_active_display',
        'nombre_sessions_total',
        'derniere_connexion'
    ]

    list_filter = [
        'statut',
        'created_at',
        'derniere_connexion'
    ]

    search_fields = [
        'nom',
        'ip_address',
        'mac_address',
        'emplacement'
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
        'nombre_sessions_total',
        'derniere_connexion',
        'est_en_ligne_display',
        'session_active_display'
    ]

    fieldsets = (
        ('Identification', {
            'fields': ('nom', 'emplacement')
        }),
        ('Réseau', {
            'fields': (
                'ip_address',
                'mac_address',
                'version_client'
            )
        }),
        ('État', {
            'fields': (
                'statut',
                'est_en_ligne_display',
                'session_active_display',
                'derniere_connexion'
            )
        }),
        ('Informations', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': (
                'nombre_sessions_total',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )

    actions = [
        'marquer_disponible',
        'marquer_maintenance',
        'marquer_hors_ligne'
    ]

    def statut_display(self, obj):
        """Affichage coloré du statut"""
        colors = {
            'disponible': 'green',
            'occupe': 'orange',
            'reserve': 'blue',
            'hors_ligne': 'red',
            'maintenance': 'gray'
        }
        color = colors.get(obj.statut, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_statut_display()
        )
    statut_display.short_description = 'Statut'

    def est_en_ligne_display(self, obj):
        """Affichage de l'état en ligne"""
        if obj.est_en_ligne:
            return format_html('<span style="color: green;">● En ligne</span>')
        return format_html('<span style="color: red;">○ Hors ligne</span>')
    est_en_ligne_display.short_description = 'État'

    def session_active_display(self, obj):
        """Affichage de la session active"""
        session = obj.session_active
        if session:
            return format_html(
                '<a href="/admin/sessions/session/{}/change/">{}</a>',
                session.id,
                f"Session {session.code_acces}"
            )
        return "-"
    session_active_display.short_description = 'Session active'

    @admin.action(description='Marquer comme disponible')
    def marquer_disponible(self, request, queryset):
        """Action pour marquer les postes comme disponibles"""
        queryset.update(statut='disponible')
        self.message_user(request, f"{queryset.count()} poste(s) marqué(s) comme disponible(s)")

    @admin.action(description='Marquer en maintenance')
    def marquer_maintenance(self, request, queryset):
        """Action pour marquer les postes en maintenance"""
        queryset.update(statut='maintenance')
        self.message_user(request, f"{queryset.count()} poste(s) marqué(s) en maintenance")

    @admin.action(description='Marquer hors ligne')
    def marquer_hors_ligne(self, request, queryset):
        """Action pour marquer les postes hors ligne"""
        queryset.update(statut='hors_ligne')
        self.message_user(request, f"{queryset.count()} poste(s) marqué(s) hors ligne")
