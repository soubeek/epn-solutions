// Gestion des certificats mTLS pour l'authentification client
//
// Ce module gère le stockage et le chargement des certificats TLS clients
// utilisés pour l'authentification mutuelle avec le serveur.

use crate::types::{ClientError, Result};
use std::fs::{self, File, Permissions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};

#[cfg(unix)]
use std::os::unix::fs::PermissionsExt;

/// Chemins des fichiers de certificat
const CERT_DIR_NAME: &str = "epn-client";
const CLIENT_CERT_FILE: &str = "client.crt";
const CLIENT_KEY_FILE: &str = "client.key";
const CA_CERT_FILE: &str = "ca.crt";

/// Gestionnaire de stockage des certificats
#[derive(Debug, Clone)]
pub struct CertificateStore {
    /// Répertoire de stockage des certificats
    cert_dir: PathBuf,
}

/// Certificats chargés en mémoire
#[derive(Debug, Clone)]
pub struct ClientCertificates {
    /// Certificat client (PEM)
    pub client_cert: String,
    /// Clé privée client (PEM)
    pub client_key: String,
    /// Certificat de l'autorité de certification (PEM)
    pub ca_cert: String,
}

impl CertificateStore {
    /// Crée un nouveau gestionnaire de certificats avec le répertoire par défaut
    pub fn new() -> Result<Self> {
        let cert_dir = Self::default_cert_dir()?;
        Ok(Self { cert_dir })
    }

    /// Crée un gestionnaire avec un répertoire personnalisé
    pub fn with_dir<P: AsRef<Path>>(path: P) -> Self {
        Self {
            cert_dir: path.as_ref().to_path_buf(),
        }
    }

    /// Obtient le répertoire de stockage par défaut
    fn default_cert_dir() -> Result<PathBuf> {
        // Utiliser XDG_DATA_HOME sur Linux, ou équivalent sur autres OS
        #[cfg(target_os = "linux")]
        {
            let base = std::env::var("XDG_DATA_HOME")
                .map(PathBuf::from)
                .unwrap_or_else(|_| {
                    let home = std::env::var("HOME").unwrap_or_else(|_| "/tmp".to_string());
                    PathBuf::from(home).join(".local/share")
                });
            Ok(base.join(CERT_DIR_NAME))
        }

        #[cfg(target_os = "windows")]
        {
            let base = std::env::var("LOCALAPPDATA")
                .map(PathBuf::from)
                .unwrap_or_else(|_| PathBuf::from("C:\\ProgramData"));
            Ok(base.join(CERT_DIR_NAME))
        }

        #[cfg(target_os = "macos")]
        {
            let home = std::env::var("HOME").unwrap_or_else(|_| "/tmp".to_string());
            Ok(PathBuf::from(home)
                .join("Library/Application Support")
                .join(CERT_DIR_NAME))
        }
    }

    /// Vérifie si le client est enregistré (certificats présents)
    pub fn is_registered(&self) -> bool {
        self.client_cert_path().exists()
            && self.client_key_path().exists()
            && self.ca_cert_path().exists()
    }

    /// Chemin vers le certificat client
    pub fn client_cert_path(&self) -> PathBuf {
        self.cert_dir.join(CLIENT_CERT_FILE)
    }

    /// Chemin vers la clé privée client
    pub fn client_key_path(&self) -> PathBuf {
        self.cert_dir.join(CLIENT_KEY_FILE)
    }

    /// Chemin vers le certificat CA
    pub fn ca_cert_path(&self) -> PathBuf {
        self.cert_dir.join(CA_CERT_FILE)
    }

    /// Stocke les certificats reçus lors de l'enregistrement
    pub fn store_certificates(&self, certs: &ClientCertificates) -> Result<()> {
        // Créer le répertoire avec permissions restrictives
        self.ensure_cert_dir()?;

        // Écrire le certificat client
        self.write_secure_file(&self.client_cert_path(), &certs.client_cert)?;
        tracing::info!("Certificat client stocké: {:?}", self.client_cert_path());

        // Écrire la clé privée (permissions 0600)
        self.write_secure_file(&self.client_key_path(), &certs.client_key)?;
        tracing::info!("Clé privée stockée: {:?}", self.client_key_path());

        // Écrire le certificat CA
        self.write_secure_file(&self.ca_cert_path(), &certs.ca_cert)?;
        tracing::info!("Certificat CA stocké: {:?}", self.ca_cert_path());

        Ok(())
    }

    /// Charge les certificats depuis le disque
    pub fn load_certificates(&self) -> Result<ClientCertificates> {
        if !self.is_registered() {
            return Err(ClientError::Other(
                "Client non enregistré - certificats manquants".to_string(),
            ));
        }

        let client_cert = self.read_file(&self.client_cert_path())?;
        let client_key = self.read_file(&self.client_key_path())?;
        let ca_cert = self.read_file(&self.ca_cert_path())?;

        tracing::debug!("Certificats chargés depuis {:?}", self.cert_dir);

        Ok(ClientCertificates {
            client_cert,
            client_key,
            ca_cert,
        })
    }

    /// Supprime les certificats (désenregistrement)
    pub fn remove_certificates(&self) -> Result<()> {
        let paths = [
            self.client_cert_path(),
            self.client_key_path(),
            self.ca_cert_path(),
        ];

        for path in paths {
            if path.exists() {
                fs::remove_file(&path)?;
                tracing::info!("Fichier supprimé: {:?}", path);
            }
        }

        // Supprimer le répertoire s'il est vide
        if self.cert_dir.exists() {
            if fs::read_dir(&self.cert_dir)?.next().is_none() {
                fs::remove_dir(&self.cert_dir)?;
                tracing::info!("Répertoire supprimé: {:?}", self.cert_dir);
            }
        }

        Ok(())
    }

    /// Crée le répertoire de certificats avec permissions restrictives
    fn ensure_cert_dir(&self) -> Result<()> {
        if !self.cert_dir.exists() {
            fs::create_dir_all(&self.cert_dir)?;

            // Sur Unix, définir les permissions du répertoire à 0700
            #[cfg(unix)]
            {
                let perms = Permissions::from_mode(0o700);
                fs::set_permissions(&self.cert_dir, perms)?;
            }

            tracing::info!("Répertoire de certificats créé: {:?}", self.cert_dir);
        }
        Ok(())
    }

    /// Écrit un fichier avec permissions restrictives (0600 sur Unix)
    fn write_secure_file<P: AsRef<Path>>(&self, path: P, content: &str) -> Result<()> {
        let path = path.as_ref();

        // Créer ou écraser le fichier
        let mut file = File::create(path)?;
        file.write_all(content.as_bytes())?;
        file.flush()?;

        // Définir les permissions à 0600 (lecture/écriture propriétaire uniquement)
        #[cfg(unix)]
        {
            let perms = Permissions::from_mode(0o600);
            fs::set_permissions(path, perms)?;
        }

        Ok(())
    }

    /// Lit le contenu d'un fichier
    fn read_file<P: AsRef<Path>>(&self, path: P) -> Result<String> {
        let mut file = File::open(path)?;
        let mut content = String::new();
        file.read_to_string(&mut content)?;
        Ok(content)
    }

    /// Obtient des informations sur les certificats stockés
    pub fn certificate_info(&self) -> Option<CertificateInfo> {
        if !self.is_registered() {
            return None;
        }

        // Vérifier que le certificat est lisible
        if self.read_file(&self.client_cert_path()).is_err() {
            return None;
        }

        // Retourner les informations de base
        // Note: Parser le CN/expiration nécessiterait x509-parser
        Some(CertificateInfo {
            cert_path: self.client_cert_path(),
            key_path: self.client_key_path(),
            ca_path: self.ca_cert_path(),
            common_name: None,
            expires_at: None,
        })
    }
}

impl Default for CertificateStore {
    fn default() -> Self {
        Self::new().expect("Impossible de créer le CertificateStore par défaut")
    }
}

/// Informations sur les certificats stockés
#[derive(Debug, Clone)]
pub struct CertificateInfo {
    pub cert_path: PathBuf,
    pub key_path: PathBuf,
    pub ca_path: PathBuf,
    pub common_name: Option<String>,
    pub expires_at: Option<String>,
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::env;

    fn temp_cert_dir() -> PathBuf {
        env::temp_dir().join(format!("epn-test-certs-{}", uuid::Uuid::new_v4()))
    }

    #[test]
    fn test_certificate_store_creation() {
        let dir = temp_cert_dir();
        let store = CertificateStore::with_dir(&dir);
        assert!(!store.is_registered());

        // Cleanup
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn test_store_and_load_certificates() {
        let dir = temp_cert_dir();
        let store = CertificateStore::with_dir(&dir);

        let certs = ClientCertificates {
            client_cert: "-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----".to_string(),
            client_key: "-----BEGIN PRIVATE KEY-----\nTEST\n-----END PRIVATE KEY-----".to_string(),
            ca_cert: "-----BEGIN CERTIFICATE-----\nCA TEST\n-----END CERTIFICATE-----".to_string(),
        };

        // Store
        assert!(store.store_certificates(&certs).is_ok());
        assert!(store.is_registered());

        // Load
        let loaded = store.load_certificates().unwrap();
        assert_eq!(loaded.client_cert, certs.client_cert);
        assert_eq!(loaded.client_key, certs.client_key);
        assert_eq!(loaded.ca_cert, certs.ca_cert);

        // Verify permissions on Unix
        #[cfg(unix)]
        {
            let key_meta = fs::metadata(store.client_key_path()).unwrap();
            let mode = key_meta.permissions().mode() & 0o777;
            assert_eq!(mode, 0o600, "La clé privée doit avoir les permissions 0600");
        }

        // Cleanup
        assert!(store.remove_certificates().is_ok());
        assert!(!store.is_registered());
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn test_load_nonexistent_certificates() {
        let dir = temp_cert_dir();
        let store = CertificateStore::with_dir(&dir);

        assert!(!store.is_registered());
        assert!(store.load_certificates().is_err());

        // Cleanup
        let _ = fs::remove_dir_all(&dir);
    }
}
