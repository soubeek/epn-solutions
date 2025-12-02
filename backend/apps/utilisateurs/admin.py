"""
Django Admin pour Utilisateurs
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Utilisateur


@admin.register(Utilisateur)
class UtilisateurAdmin(admin.ModelAdmin):
    """Administration des utilisateurs"""

    list_display = [
        'nom',
        'prenom',
        'email',
        'telephone',
        'consentement_rgpd_display',
        'nombre_sessions_total',
        'derniere_session',
        'created_at'
    ]

    list_filter = [
        'consentement_rgpd',
        'created_at',
        'derniere_session'
    ]

    search_fields = [
        'nom',
        'prenom',
        'email',
        'telephone',
        'carte_identite'
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
        'nombre_sessions_total',
        'derniere_session',
        'date_consentement',
        'age_display',
        'photo_preview'
    ]

    fieldsets = (
        ('Informations personnelles', {
            'fields': (
                'nom',
                'prenom',
                'email',
                'telephone',
                'date_naissance',
                'age_display',
                'adresse'
            )
        }),
        ('Pièce d\'identité', {
            'fields': ('carte_identite',)
        }),
        ('Photo', {
            'fields': ('photo', 'photo_preview'),
            'classes': ('collapse',)
        }),
        ('RGPD', {
            'fields': (
                'consentement_rgpd',
                'date_consentement'
            ),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': (
                'created_by',
                'notes',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        }),
        ('Statistiques', {
            'fields': (
                'nombre_sessions_total',
                'derniere_session'
            ),
            'classes': ('collapse',)
        })
    )

    def consentement_rgpd_display(self, obj):
        """Affichage visuel du consentement RGPD"""
        if obj.consentement_rgpd:
            return format_html(
                '<span style="color: green;">✓ Oui</span>'
            )
        return format_html(
            '<span style="color: red;">✗ Non</span>'
        )
    consentement_rgpd_display.short_description = 'RGPD'

    def age_display(self, obj):
        """Affichage de l'âge"""
        if obj.age:
            return f"{obj.age} ans"
        return "-"
    age_display.short_description = 'Âge'

    def photo_preview(self, obj):
        """Prévisualisation de la photo"""
        if obj.photo:
            return format_html(
                '<img src="{}" width="150" height="150" style="object-fit: cover;" />',
                obj.photo.url
            )
        return "Pas de photo"
    photo_preview.short_description = 'Aperçu'

    def save_model(self, request, obj, form, change):
        """Sauvegarde avec attribution de l'opérateur"""
        if not change:  # Nouvelle création
            obj.created_by = request.user.username
        else:  # Modification
            obj._modified_by = request.user.username
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        """Suppression avec attribution de l'opérateur"""
        obj._deleted_by = request.user.username
        super().delete_model(request, obj)
