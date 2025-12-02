"""
Permissions personnalisées pour l'application EPN
Classes de permissions pour le contrôle d'accès basé sur les rôles
"""

from rest_framework import permissions


class IsAdminUser(permissions.BasePermission):
    """
    Permission accordée uniquement aux administrateurs (staff ou superuser)
    """
    message = "Seuls les administrateurs peuvent effectuer cette action."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.is_staff or request.user.is_superuser)
        )


class IsOperator(permissions.BasePermission):
    """
    Permission accordée aux opérateurs (utilisateurs authentifiés actifs)
    Les opérateurs peuvent gérer les sessions et les utilisateurs
    """
    message = "Seuls les opérateurs authentifiés peuvent effectuer cette action."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_active
        )


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission en lecture pour tous les authentifiés,
    écriture uniquement pour les admins
    """
    message = "Seuls les administrateurs peuvent modifier ces données."

    def has_permission(self, request, view):
        # Lecture autorisée pour tous les authentifiés
        if request.method in permissions.SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)

        # Écriture réservée aux admins
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.is_staff or request.user.is_superuser)
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission accordée au propriétaire de l'objet ou aux admins
    Utile pour les ressources utilisateur (profil, etc.)
    """
    message = "Vous n'avez pas la permission d'accéder à cette ressource."

    def has_object_permission(self, request, view, obj):
        # Les admins ont toujours accès
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Vérifier si l'objet a un attribut 'user' ou 'utilisateur'
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'utilisateur'):
            return obj.utilisateur == request.user
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user.username

        return False


class CanManageSessions(permissions.BasePermission):
    """
    Permission pour gérer les sessions
    Tous les opérateurs authentifiés peuvent gérer les sessions
    """
    message = "Vous n'avez pas la permission de gérer les sessions."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_active
        )

    def has_object_permission(self, request, view, obj):
        # Les admins peuvent tout faire
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Les opérateurs peuvent gérer les sessions qu'ils ont créées
        # ou toutes les sessions s'ils sont actifs
        return request.user.is_active


class CanViewLogs(permissions.BasePermission):
    """
    Permission pour consulter les logs
    Réservé aux administrateurs et opérateurs autorisés
    """
    message = "Vous n'avez pas la permission de consulter les logs."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.is_staff or request.user.is_superuser)
        )
