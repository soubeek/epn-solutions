// Module d'enregistrement du client auprès du serveur
//
// Ce module gère le processus d'enregistrement d'un nouveau client :
// 1. Envoi du token + hostname + MAC address au serveur
// 2. Réception et stockage du certificat client

use crate::certificate::{CertificateStore, ClientCertificates};
use crate::types::{ClientError, Result};
use serde::{Deserialize, Serialize};

/// Requête d'enregistrement envoyée au serveur
#[derive(Debug, Serialize)]
pub struct RegistrationRequest {
    pub token: String,
    pub hostname: String,
    pub mac_address: String,
}

/// Réponse d'enregistrement du serveur
#[derive(Debug, Deserialize)]
pub struct RegistrationResponse {
    pub success: bool,
    #[serde(default)]
    pub message: Option<String>,
    #[serde(default)]
    pub client_cert: Option<String>,
    #[serde(default)]
    pub client_key: Option<String>,
    #[serde(default)]
    pub ca_cert: Option<String>,
    #[serde(default)]
    pub poste_id: Option<u64>,
    #[serde(default)]
    pub poste_nom: Option<String>,
}

/// Informations sur le poste après enregistrement
#[derive(Debug, Clone)]
pub struct PosteInfo {
    pub id: u64,
    pub nom: String,
}

/// Client d'enregistrement
pub struct RegistrationClient {
    server_url: String,
    store: CertificateStore,
}

impl RegistrationClient {
    /// Crée un nouveau client d'enregistrement
    pub fn new(server_url: &str) -> Result<Self> {
        let store = CertificateStore::new()?;
        Ok(Self {
            server_url: server_url.trim_end_matches('/').to_string(),
            store,
        })
    }

    /// Vérifie si le client est déjà enregistré
    pub fn is_registered(&self) -> bool {
        self.store.is_registered()
    }

    /// Enregistre le client auprès du serveur
    ///
    /// # Arguments
    /// * `token` - Token d'enregistrement fourni par l'administrateur
    ///
    /// # Returns
    /// Informations sur le poste si l'enregistrement réussit
    pub async fn register(&self, token: &str) -> Result<PosteInfo> {
        if self.is_registered() {
            return Err(ClientError::Other(
                "Ce client est déjà enregistré. Utilisez unregister d'abord.".to_string(),
            ));
        }

        // Récupérer les informations système
        let hostname = Self::get_hostname()?;
        let mac_address = Self::get_mac_address()?;

        tracing::info!("Enregistrement du client...");
        tracing::debug!("Hostname: {}, MAC: {}", hostname, mac_address);

        // Construire la requête
        let request = RegistrationRequest {
            token: token.to_string(),
            hostname,
            mac_address,
        };

        // Envoyer la requête au serveur
        let url = format!("{}/api/postes/register_client/", self.server_url);
        tracing::debug!("URL d'enregistrement: {}", url);

        let client = reqwest::Client::builder()
            .danger_accept_invalid_certs(true) // Pour l'enregistrement initial, on accepte tout
            .build()
            .map_err(|e| ClientError::Connection(format!("Erreur de création du client HTTP: {}", e)))?;

        let response = client
            .post(&url)
            .json(&request)
            .send()
            .await
            .map_err(|e| ClientError::Connection(format!("Erreur de connexion au serveur: {}", e)))?;

        let status = response.status();
        let body = response
            .text()
            .await
            .map_err(|e| ClientError::Connection(format!("Erreur de lecture de la réponse: {}", e)))?;

        tracing::debug!("Réponse du serveur ({}): {}", status, body);

        if !status.is_success() {
            // Essayer de parser l'erreur
            if let Ok(error_response) = serde_json::from_str::<RegistrationResponse>(&body) {
                return Err(ClientError::Other(
                    error_response.message.unwrap_or_else(|| format!("Erreur {}", status)),
                ));
            }
            return Err(ClientError::Connection(format!(
                "Erreur du serveur: {} - {}",
                status, body
            )));
        }

        // Parser la réponse
        let response: RegistrationResponse = serde_json::from_str(&body)
            .map_err(|e| ClientError::Other(format!("Erreur de parsing de la réponse: {}", e)))?;

        if !response.success {
            return Err(ClientError::Other(
                response.message.unwrap_or_else(|| "Enregistrement échoué".to_string()),
            ));
        }

        // Vérifier que tous les certificats sont présents
        let client_cert = response.client_cert.ok_or_else(|| {
            ClientError::Other("Certificat client manquant dans la réponse".to_string())
        })?;
        let client_key = response.client_key.ok_or_else(|| {
            ClientError::Other("Clé privée manquante dans la réponse".to_string())
        })?;
        let ca_cert = response.ca_cert.ok_or_else(|| {
            ClientError::Other("Certificat CA manquant dans la réponse".to_string())
        })?;

        // Stocker les certificats
        let certs = ClientCertificates {
            client_cert,
            client_key,
            ca_cert,
        };
        self.store.store_certificates(&certs)?;

        let poste_info = PosteInfo {
            id: response.poste_id.unwrap_or(0),
            nom: response.poste_nom.unwrap_or_else(|| "Inconnu".to_string()),
        };

        tracing::info!(
            "✓ Client enregistré avec succès! Poste: {} (ID: {})",
            poste_info.nom,
            poste_info.id
        );

        Ok(poste_info)
    }

    /// Désenregistre le client (supprime les certificats locaux)
    pub fn unregister(&self) -> Result<()> {
        if !self.is_registered() {
            return Err(ClientError::Other("Ce client n'est pas enregistré.".to_string()));
        }

        self.store.remove_certificates()?;
        tracing::info!("✓ Client désenregistré avec succès");
        Ok(())
    }

    /// Obtient le nom d'hôte de la machine
    fn get_hostname() -> Result<String> {
        hostname::get()
            .map_err(|e| ClientError::Other(format!("Impossible d'obtenir le hostname: {}", e)))?
            .into_string()
            .map_err(|_| ClientError::Other("Hostname contient des caractères invalides".to_string()))
    }

    /// Obtient l'adresse MAC de la première interface réseau
    fn get_mac_address() -> Result<String> {
        mac_address::get_mac_address()
            .map_err(|e| ClientError::Other(format!("Impossible d'obtenir l'adresse MAC: {}", e)))?
            .map(|mac| mac.to_string())
            .ok_or_else(|| ClientError::Other("Aucune adresse MAC trouvée".to_string()))
    }

    /// Obtient le statut d'enregistrement
    pub fn status(&self) -> RegistrationStatus {
        if self.is_registered() {
            let info = self.store.certificate_info();
            RegistrationStatus::Registered { info }
        } else {
            RegistrationStatus::NotRegistered
        }
    }
}

/// Statut d'enregistrement du client
#[derive(Debug)]
pub enum RegistrationStatus {
    NotRegistered,
    Registered {
        info: Option<crate::certificate::CertificateInfo>,
    },
}

impl std::fmt::Display for RegistrationStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            RegistrationStatus::NotRegistered => {
                write!(f, "Non enregistré")
            }
            RegistrationStatus::Registered { info } => {
                write!(f, "Enregistré")?;
                if let Some(info) = info {
                    write!(f, "\n  Certificat: {:?}", info.cert_path)?;
                    write!(f, "\n  Clé: {:?}", info.key_path)?;
                    if let Some(cn) = &info.common_name {
                        write!(f, "\n  CN: {}", cn)?;
                    }
                    if let Some(exp) = &info.expires_at {
                        write!(f, "\n  Expire: {}", exp)?;
                    }
                }
                Ok(())
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_registration_request_serialize() {
        let request = RegistrationRequest {
            token: "ABC123".to_string(),
            hostname: "test-pc".to_string(),
            mac_address: "00:11:22:33:44:55".to_string(),
        };

        let json = serde_json::to_string(&request).unwrap();
        assert!(json.contains("ABC123"));
        assert!(json.contains("test-pc"));
        assert!(json.contains("00:11:22:33:44:55"));
    }

    #[test]
    fn test_registration_response_deserialize() {
        let json = r#"{
            "success": true,
            "message": "Enregistrement réussi",
            "client_cert": "-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----",
            "client_key": "-----BEGIN PRIVATE KEY-----\nTEST\n-----END PRIVATE KEY-----",
            "ca_cert": "-----BEGIN CERTIFICATE-----\nCA\n-----END CERTIFICATE-----",
            "poste_id": 1,
            "poste_nom": "PC-01"
        }"#;

        let response: RegistrationResponse = serde_json::from_str(json).unwrap();
        assert!(response.success);
        assert_eq!(response.poste_id, Some(1));
        assert_eq!(response.poste_nom, Some("PC-01".to_string()));
    }

    #[test]
    fn test_registration_response_error() {
        let json = r#"{
            "success": false,
            "message": "Token invalide"
        }"#;

        let response: RegistrationResponse = serde_json::from_str(json).unwrap();
        assert!(!response.success);
        assert_eq!(response.message, Some("Token invalide".to_string()));
        assert!(response.client_cert.is_none());
    }
}
