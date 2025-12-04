"""
Gestionnaire de certificats pour l'authentification mTLS des clients.

Ce module gère :
- La création et la gestion de la CA (Certificate Authority) interne
- La génération de certificats clients signés par la CA
- La vérification des certificats clients
"""

import os
import re
from datetime import datetime, timedelta, timezone as dt_timezone
from pathlib import Path

from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

from django.conf import settings
from django.utils import timezone


class CertificateManager:
    """
    Gère la CA interne et la génération de certificats clients.

    Configuration requise dans settings:
        CA_CERT_PATH: Chemin vers le certificat CA (ex: /etc/epn/ca/ca.crt)
        CA_KEY_PATH: Chemin vers la clé privée CA (ex: /etc/epn/ca/ca.key)
        CA_KEY_PASSWORD: Mot de passe de la clé CA (optionnel, None si non chiffré)
        CLIENT_CERT_VALIDITY_DAYS: Durée de validité des certificats clients (défaut: 365)
    """

    def __init__(self):
        self.ca_cert_path = Path(getattr(settings, 'CA_CERT_PATH', '/etc/epn/ca/ca.crt'))
        self.ca_key_path = Path(getattr(settings, 'CA_KEY_PATH', '/etc/epn/ca/ca.key'))
        self.ca_key_password = getattr(settings, 'CA_KEY_PASSWORD', None)
        self.cert_validity_days = getattr(settings, 'CLIENT_CERT_VALIDITY_DAYS', 365)
        self.organization_name = getattr(settings, 'CA_ORGANIZATION_NAME', 'EPN')

    def ensure_ca_exists(self):
        """S'assure que la CA existe, la crée si nécessaire"""
        if not self.ca_cert_path.exists() or not self.ca_key_path.exists():
            self._generate_ca()
        return True

    def _generate_ca(self):
        """Génère une nouvelle CA auto-signée"""
        # Créer le répertoire si nécessaire
        self.ca_cert_path.parent.mkdir(parents=True, exist_ok=True)

        # Génère clé privée RSA 4096 bits
        ca_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=default_backend()
        )

        # Informations du certificat CA
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, self.organization_name),
            x509.NameAttribute(NameOID.COMMON_NAME, f"{self.organization_name} Internal CA"),
        ])

        # Génère le certificat CA (validité 10 ans)
        ca_cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(ca_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(dt_timezone.utc))
            .not_valid_after(datetime.now(dt_timezone.utc) + timedelta(days=3650))
            .add_extension(
                x509.BasicConstraints(ca=True, path_length=0),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_cert_sign=True,
                    crl_sign=True,
                    key_encipherment=False,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()),
                critical=False,
            )
            .sign(ca_key, hashes.SHA256(), default_backend())
        )

        # Sauvegarde la clé privée
        encryption = serialization.NoEncryption()
        if self.ca_key_password:
            encryption = serialization.BestAvailableEncryption(
                self.ca_key_password.encode()
            )

        with open(self.ca_key_path, "wb") as f:
            f.write(ca_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=encryption
            ))

        # Permissions restrictives sur la clé
        os.chmod(self.ca_key_path, 0o600)

        # Sauvegarde le certificat
        with open(self.ca_cert_path, "wb") as f:
            f.write(ca_cert.public_bytes(serialization.Encoding.PEM))

        return ca_cert, ca_key

    def _load_ca_cert(self):
        """Charge le certificat CA"""
        with open(self.ca_cert_path, "rb") as f:
            return x509.load_pem_x509_certificate(f.read(), default_backend())

    def _load_ca_key(self):
        """Charge la clé privée CA"""
        password = self.ca_key_password.encode() if self.ca_key_password else None
        with open(self.ca_key_path, "rb") as f:
            return serialization.load_pem_private_key(
                f.read(),
                password=password,
                backend=default_backend()
            )

    def generate_client_certificate(self, poste):
        """
        Génère un certificat client pour un poste.

        Args:
            poste: Instance du modèle Poste

        Returns:
            dict avec: client_cert, client_key, ca_cert, cn, fingerprint, expires_at
        """
        self.ensure_ca_exists()

        ca_cert = self._load_ca_cert()
        ca_key = self._load_ca_key()

        # Génère clé client RSA 2048 bits
        client_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        # CN unique : format "poste-{id}-{nom_sanitized}"
        nom_sanitized = re.sub(r'[^a-zA-Z0-9]', '', poste.nom)[:20]
        cn = f"poste-{poste.id}-{nom_sanitized}"

        # Informations du certificat client
        subject = x509.Name([
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, self.organization_name),
            x509.NameAttribute(NameOID.COMMON_NAME, cn),
        ])

        # Date d'expiration
        expires_at = datetime.now(dt_timezone.utc) + timedelta(days=self.cert_validity_days)

        # Génère le certificat client
        client_cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(ca_cert.subject)
            .public_key(client_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(dt_timezone.utc))
            .not_valid_after(expires_at)
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=True,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.ExtendedKeyUsage([
                    ExtendedKeyUsageOID.CLIENT_AUTH,
                ]),
                critical=False,
            )
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(client_key.public_key()),
                critical=False,
            )
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
                critical=False,
            )
            .sign(ca_key, hashes.SHA256(), default_backend())
        )

        # Fingerprint SHA256
        fingerprint = client_cert.fingerprint(hashes.SHA256()).hex()

        return {
            'client_cert': client_cert.public_bytes(serialization.Encoding.PEM).decode(),
            'client_key': client_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode(),
            'ca_cert': ca_cert.public_bytes(serialization.Encoding.PEM).decode(),
            'cn': cn,
            'fingerprint': fingerprint,
            'expires_at': expires_at,
        }

    def verify_client_certificate(self, cert_pem):
        """
        Vérifie un certificat client.

        Args:
            cert_pem: Certificat au format PEM (str ou bytes)

        Returns:
            tuple: (is_valid: bool, result: str)
                - Si valide: (True, cn)
                - Si invalide: (False, message_erreur)
        """
        from .models import Poste

        self.ensure_ca_exists()

        try:
            ca_cert = self._load_ca_cert()

            # Charge le certificat client
            if isinstance(cert_pem, str):
                cert_pem = cert_pem.encode()
            client_cert = x509.load_pem_x509_certificate(cert_pem, default_backend())

            # Vérifie la signature (certificat signé par notre CA)
            try:
                ca_cert.public_key().verify(
                    client_cert.signature,
                    client_cert.tbs_certificate_bytes,
                    padding.PKCS1v15(),
                    client_cert.signature_hash_algorithm,
                )
            except Exception:
                return False, "Signature invalide - certificat non signé par notre CA"

            # Vérifie la date de validité
            now = datetime.now(dt_timezone.utc)
            if client_cert.not_valid_before_utc > now:
                return False, "Certificat pas encore valide"
            if client_cert.not_valid_after_utc < now:
                return False, "Certificat expiré"

            # Extrait le CN
            cn_attrs = client_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
            if not cn_attrs:
                return False, "CN manquant dans le certificat"
            cn = cn_attrs[0].value

            # Vérifie le format du CN (poste-{id}-{nom})
            match = re.match(r'^poste-(\d+)-', cn)
            if not match:
                return False, f"Format CN invalide: {cn}"

            poste_id = int(match.group(1))

            # Vérifie que le poste existe et n'est pas révoqué
            try:
                poste = Poste.objects.get(id=poste_id)
            except Poste.DoesNotExist:
                return False, f"Poste {poste_id} introuvable"

            if poste.is_certificate_revoked:
                return False, "Certificat révoqué"

            # Vérifie le fingerprint si enregistré
            fingerprint = client_cert.fingerprint(hashes.SHA256()).hex()
            if poste.certificate_fingerprint and poste.certificate_fingerprint != fingerprint:
                return False, "Empreinte du certificat ne correspond pas"

            return True, cn

        except Exception as e:
            return False, f"Erreur de vérification: {str(e)}"

    def get_ca_certificate(self):
        """Retourne le certificat CA au format PEM"""
        self.ensure_ca_exists()
        ca_cert = self._load_ca_cert()
        return ca_cert.public_bytes(serialization.Encoding.PEM).decode()


# Instance singleton pour faciliter l'utilisation
_certificate_manager = None


def get_certificate_manager():
    """Retourne une instance du CertificateManager (singleton)"""
    global _certificate_manager
    if _certificate_manager is None:
        _certificate_manager = CertificateManager()
    return _certificate_manager
