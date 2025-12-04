"""
Middleware pour l'authentification mTLS des clients.

Ce middleware extrait le certificat client de la connexion TLS
et le rend disponible dans le scope de la requête.

Note: Le certificat doit être passé par le reverse proxy (Traefik/Nginx)
via des headers HTTP, car Django/Daphne ne gère pas directement mTLS.
"""

from channels.db import database_sync_to_async
from django.conf import settings


class ClientCertificateMiddleware:
    """
    Middleware Channels pour extraire le certificat client des headers.

    Le reverse proxy (Traefik) doit être configuré pour passer le certificat
    dans un header HTTP (ex: X-Client-Cert ou X-SSL-Client-Cert).

    Configuration Traefik:
        tls:
          options:
            default:
              clientAuth:
                caFiles:
                  - /etc/epn/ca/ca.crt
                clientAuthType: RequestClientCert

        middlewares:
          client-cert:
            passTLSClientCert:
              pem: true
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            # Extraire le certificat des headers
            headers = dict(scope.get("headers", []))

            # Traefik passe le certificat dans X-Forwarded-Tls-Client-Cert
            # Nginx utilise généralement X-SSL-Client-Cert
            cert_header = (
                headers.get(b"x-forwarded-tls-client-cert") or
                headers.get(b"x-ssl-client-cert") or
                headers.get(b"x-client-cert")
            )

            if cert_header:
                # Le certificat est URL-encoded, on le décode
                import urllib.parse
                cert_pem = urllib.parse.unquote(cert_header.decode("utf-8"))
                scope["client_cert"] = cert_pem
            else:
                scope["client_cert"] = None

            # Extraire aussi l'IP du client
            x_forwarded_for = headers.get(b"x-forwarded-for")
            if x_forwarded_for:
                scope["client_ip"] = x_forwarded_for.decode("utf-8").split(",")[0].strip()
            else:
                client = scope.get("client")
                scope["client_ip"] = client[0] if client else None

        return await self.app(scope, receive, send)


class ClientCertAuthMiddleware:
    """
    Middleware qui authentifie le client via son certificat TLS.

    Ajoute `scope["poste"]` si le certificat est valide.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            cert_pem = scope.get("client_cert")

            if cert_pem:
                # Vérifier le certificat
                from apps.postes.certificate_manager import get_certificate_manager
                cert_manager = get_certificate_manager()
                is_valid, result = cert_manager.verify_client_certificate(cert_pem)

                if is_valid:
                    # result contient le CN, on récupère le poste
                    poste = await self._get_poste_from_cn(result)
                    scope["poste"] = poste
                    scope["poste_cn"] = result
                    scope["cert_valid"] = True
                else:
                    scope["poste"] = None
                    scope["cert_valid"] = False
                    scope["cert_error"] = result
            else:
                scope["poste"] = None
                scope["cert_valid"] = None  # Pas de certificat fourni

        return await self.app(scope, receive, send)

    @database_sync_to_async
    def _get_poste_from_cn(self, cn):
        """Récupère le poste depuis le CN du certificat"""
        import re
        from apps.postes.models import Poste

        match = re.match(r'^poste-(\d+)-', cn)
        if match:
            poste_id = int(match.group(1))
            try:
                return Poste.objects.get(id=poste_id)
            except Poste.DoesNotExist:
                return None
        return None
