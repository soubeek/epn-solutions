"""
Django Admin pour Postes
"""

import secrets
from datetime import timedelta

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import Poste


@admin.register(Poste)
class PosteAdmin(admin.ModelAdmin):
    """Administration des postes"""

    list_display = [
        'nom',
        'type_poste_display',
        'ip_address',
        'mac_address',
        'statut_display',
        'est_en_ligne_display',
        'discovered_at',
        'session_active_display',
        'nombre_sessions_total',
        'derniere_connexion'
    ]

    list_filter = [
        'type_poste',
        'statut',
        ('discovered_at', admin.EmptyFieldListFilter),
        'created_at',
        'derniere_connexion'
    ]

    search_fields = [
        'nom',
        'ip_address',
        'mac_address',
        'emplacement',
        'discovered_hostname'
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
        'nombre_sessions_total',
        'derniere_connexion',
        'est_en_ligne_display',
        'session_active_display',
        'discovered_at',
        'discovered_hostname',
        'validated_by',
        'validated_at',
        'certificate_cn',
        'certificate_fingerprint',
        'certificate_issued_at',
        'certificate_expires_at',
        'is_certificate_revoked',
        'registration_token',
        'registration_token_expires'
    ]

    fieldsets = (
        ('Identification', {
            'fields': ('nom', 'type_poste', 'emplacement')
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
        ('Découverte automatique', {
            'fields': (
                'discovered_at',
                'discovered_hostname',
                'validated_by',
                'validated_at'
            ),
            'classes': ('collapse',)
        }),
        ('Certificat mTLS', {
            'fields': (
                'certificate_cn',
                'certificate_fingerprint',
                'certificate_issued_at',
                'certificate_expires_at',
                'is_certificate_revoked'
            ),
            'classes': ('collapse',)
        }),
        ('Enregistrement', {
            'fields': (
                'registration_token',
                'registration_token_expires'
            ),
            'classes': ('collapse',)
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
        'marquer_hors_ligne',
        'valider_postes_decouverts',
        'generer_tokens_enregistrement',
        'revoquer_certificats'
    ]

    def statut_display(self, obj):
        """Affichage coloré du statut"""
        colors = {
            'en_attente_validation': '#ff9800',  # Orange vif
            'disponible': 'green',
            'occupe': 'orange',
            'reserve': 'blue',
            'hors_ligne': 'red',
            'maintenance': 'gray'
        }
        color = colors.get(obj.statut, 'black')
        icon = '⏳ ' if obj.statut == 'en_attente_validation' else ''
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}{}</span>',
            color,
            icon,
            obj.get_statut_display()
        )
    statut_display.short_description = 'Statut'

    def type_poste_display(self, obj):
        """Affichage du type de poste avec icône"""
        icons = {
            'bureautique': '🖥️',
            'gaming': '🎮',
        }
        icon = icons.get(obj.type_poste, '')
        return format_html(
            '{} {}',
            icon,
            obj.get_type_poste_display()
        )
    type_poste_display.short_description = 'Type'

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

    @admin.action(description='Valider les postes découverts')
    def valider_postes_decouverts(self, request, queryset):
        """Action pour valider les postes en attente de validation"""
        pending = queryset.filter(statut='en_attente_validation')
        count = pending.count()
        if count == 0:
            self.message_user(
                request,
                "Aucun poste en attente de validation sélectionné",
                level='warning'
            )
            return

        for poste in pending:
            poste.validate_discovery(request.user.username)

        self.message_user(request, f"{count} poste(s) validé(s) avec succès")

    @admin.action(description='Générer tokens d\'enregistrement')
    def generer_tokens_enregistrement(self, request, queryset):
        """Action pour générer des tokens d'enregistrement pour les postes validés"""
        # Exclure les postes en attente et ceux déjà enregistrés
        eligible = queryset.exclude(
            statut='en_attente_validation'
        ).filter(
            certificate_cn__isnull=True
        )
        count = 0

        for poste in eligible:
            # Ne pas régénérer si un token valide existe
            if poste.has_pending_registration:
                continue

            # Générer un nouveau token
            poste.registration_token = secrets.token_urlsafe(32)
            poste.registration_token_expires = timezone.now() + timedelta(hours=24)
            poste.save(update_fields=['registration_token', 'registration_token_expires'])
            count += 1

        if count == 0:
            self.message_user(
                request,
                "Aucun poste éligible (déjà enregistrés ou en attente de validation)",
                level='warning'
            )
        else:
            self.message_user(request, f"{count} token(s) d'enregistrement généré(s)")

    @admin.action(description='Révoquer les certificats')
    def revoquer_certificats(self, request, queryset):
        """Action pour révoquer les certificats des postes sélectionnés"""
        registered = queryset.filter(
            certificate_cn__isnull=False,
            is_certificate_revoked=False
        )
        count = registered.count()

        if count == 0:
            self.message_user(
                request,
                "Aucun poste avec certificat actif sélectionné",
                level='warning'
            )
            return

        for poste in registered:
            poste.revoke_certificate()

        self.message_user(
            request,
            f"{count} certificat(s) révoqué(s). Les clients devront se ré-enregistrer.",
            level='success'
        )
