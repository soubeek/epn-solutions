"""
Django Admin pour Sessions
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Session


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    """Administration des sessions"""

    list_display = [
        'code_acces',
        'utilisateur',
        'poste',
        'statut_display',
        'temps_restant_display',
        'debut_session',
        'created_at'
    ]

    list_filter = [
        'statut',
        'created_at',
        'debut_session',
        'poste'
    ]

    search_fields = [
        'code_acces',
        'utilisateur__nom',
        'utilisateur__prenom',
        'poste__nom',
        'operateur'
    ]

    readonly_fields = [
        'code_acces',
        'created_at',
        'updated_at',
        'duree_totale_display',
        'temps_ecoule_display',
        'pourcentage_utilise_display'
    ]

    fieldsets = (
        ('Session', {
            'fields': (
                'code_acces',
                'utilisateur',
                'poste',
                'statut'
            )
        }),
        ('Durée', {
            'fields': (
                'duree_initiale',
                'temps_restant',
                'temps_ajoute',
                'duree_totale_display',
                'temps_ecoule_display',
                'pourcentage_utilise_display'
            )
        }),
        ('Dates', {
            'fields': (
                'debut_session',
                'fin_session',
                'created_at',
                'updated_at'
            )
        }),
        ('Métadonnées', {
            'fields': (
                'operateur',
                'notes'
            ),
            'classes': ('collapse',)
        })
    )

    actions = [
        'terminer_sessions',
        'ajouter_15_minutes',
        'ajouter_30_minutes'
    ]

    def statut_display(self, obj):
        """Affichage coloré du statut"""
        colors = {
            'en_attente': 'blue',
            'active': 'green',
            'terminee': 'gray',
            'suspendue': 'orange',
            'expiree': 'red'
        }
        color = colors.get(obj.statut, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_statut_display()
        )
    statut_display.short_description = 'Statut'

    def temps_restant_display(self, obj):
        """Affichage du temps restant"""
        if obj.temps_restant > 0:
            minutes = obj.temps_restant // 60
            secondes = obj.temps_restant % 60
            if obj.temps_restant <= 300:  # < 5 minutes
                color = 'red'
            elif obj.temps_restant <= 600:  # < 10 minutes
                color = 'orange'
            else:
                color = 'green'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{:02d}:{:02d}</span>',
                color,
                minutes,
                secondes
            )
        return format_html('<span style="color: gray;">00:00</span>')
    temps_restant_display.short_description = 'Temps restant'

    def duree_totale_display(self, obj):
        """Affichage de la durée totale"""
        minutes = obj.duree_totale // 60
        return f"{minutes} minutes"
    duree_totale_display.short_description = 'Durée totale'

    def temps_ecoule_display(self, obj):
        """Affichage du temps écoulé"""
        if obj.debut_session:
            minutes = obj.temps_ecoule // 60
            return f"{minutes} minutes"
        return "-"
    temps_ecoule_display.short_description = 'Temps écoulé'

    def pourcentage_utilise_display(self, obj):
        """Affichage du pourcentage utilisé"""
        if obj.debut_session:
            return f"{obj.pourcentage_utilise}%"
        return "-"
    pourcentage_utilise_display.short_description = '% utilisé'

    @admin.action(description='Terminer les sessions sélectionnées')
    def terminer_sessions(self, request, queryset):
        """Action pour terminer les sessions"""
        count = 0
        for session in queryset.filter(statut='active'):
            session.terminer(operateur=request.user.username, raison='fermeture_admin')
            count += 1
        self.message_user(request, f"{count} session(s) terminée(s)")

    @admin.action(description='Ajouter 15 minutes')
    def ajouter_15_minutes(self, request, queryset):
        """Action pour ajouter 15 minutes"""
        count = 0
        for session in queryset.filter(statut='active'):
            session.ajouter_temps(secondes=900, operateur=request.user.username)
            count += 1
        self.message_user(request, f"15 minutes ajoutées à {count} session(s)")

    @admin.action(description='Ajouter 30 minutes')
    def ajouter_30_minutes(self, request, queryset):
        """Action pour ajouter 30 minutes"""
        count = 0
        for session in queryset.filter(statut='active'):
            session.ajouter_temps(secondes=1800, operateur=request.user.username)
            count += 1
        self.message_user(request, f"30 minutes ajoutées à {count} session(s)")
