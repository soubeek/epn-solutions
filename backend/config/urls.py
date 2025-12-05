"""
Configuration des URLs principales pour Poste Public Manager
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # API Authentication (JWT)
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # API Apps
    path('api/auth/', include('apps.auth.urls')),
    path('api/utilisateurs/', include('apps.utilisateurs.urls')),
    path('api/postes/', include('apps.postes.urls')),
    path('api/sessions/', include('apps.sessions.urls')),
    path('api/extension-requests/', include('apps.sessions.extension_urls')),
    path('api/logs/', include('apps.logs.urls')),
]

# Servir les fichiers media en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Django Debug Toolbar
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass

# Personnalisation de l'admin
admin.site.site_header = "Poste Public Manager - Administration"
admin.site.site_title = "Administration Postes Publics"
admin.site.index_title = "Bienvenue dans l'interface d'administration"
