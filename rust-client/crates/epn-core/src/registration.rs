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

// ==================== Types pour la découverte automatique ====================

/// Requête de découverte envoyée au serveur
#[derive(Debug, Serialize)]
pub struct DiscoveryRequest {
    pub discovery_token: String,
    pub hostname: String,
    pub mac_address: String,
}

/// Réponse du serveur pour la découverte
#[derive(Debug, Deserialize)]
pub struct DiscoveryResponse {
    pub status: String,
    pub poste_id: u64,
    pub message: String,
}

/// Requête de vérification du statut de découverte
#[derive(Debug, Serialize)]
pub struct DiscoveryStatusRequest {
    pub mac_address: String,
}

/// Réponse du serveur pour le statut de découverte
#[derive(Debug, Deserialize)]
pub struct DiscoveryStatusResponse {
    pub status: String,           // "pending_validation" | "validated" | "registered" | "unknown"
    pub poste_id: Option<u64>,
    pub poste_nom: Option<String>,
    pub registration_token: Option<String>,
    pub message: Option<String>,
}

/// Réponse de succès du serveur
#[derive(Debug, Deserialize)]
pub struct RegistrationSuccessResponse {
    pub client_cert: String,
    pub client_key: String,
    pub ca_cert: String,
    pub poste_id: u64,
    pub poste_nom: String,
    pub certificate_cn: String,
    pub expires_at: String,
}

/// Réponse d'erreur du serveur
#[derive(Debug, Deserialize)]
pub struct RegistrationErrorResponse {
    pub error: String,
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
            if let Ok(error_response) = serde_json::from_str::<RegistrationErrorResponse>(&body) {
                return Err(ClientError::Other(error_response.error));
            }
            return Err(ClientError::Connection(format!(
                "Erreur du serveur: {} - {}",
                status, body
            )));
        }

        // Parser la réponse de succès
        let response: RegistrationSuccessResponse = serde_json::from_str(&body)
            .map_err(|e| ClientError::Other(format!("Erreur de parsing de la réponse: {}", e)))?;

        // Stocker les certificats
        let certs = ClientCertificates {
            client_cert: response.client_cert,
            client_key: response.client_key,
            ca_cert: response.ca_cert,
        };
        self.store.store_certificates(&certs)?;

        let poste_info = PosteInfo {
            id: response.poste_id,
            nom: response.poste_nom,
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

    // ==================== Méthodes de découverte automatique ====================

    /// Envoie une demande de découverte au serveur
    ///
    /// Le client s'annonce au serveur avec le token de découverte partagé.
    /// Le serveur crée un poste en attente de validation par l'admin.
    ///
    /// # Arguments
    /// * `discovery_token` - Token partagé configuré sur le serveur
    ///
    /// # Returns
    /// Réponse de découverte indiquant le statut
    pub async fn discover(&self, discovery_token: &str) -> Result<DiscoveryResponse> {
        let hostname = Self::get_hostname()?;
        let mac_address = Self::get_mac_address()?;

        tracing::info!("Envoi de la demande de découverte au serveur...");
        tracing::debug!("Hostname: {}, MAC: {}", hostname, mac_address);

        let request = DiscoveryRequest {
            discovery_token: discovery_token.to_string(),
            hostname,
            mac_address,
        };

        let url = format!("{}/api/postes/discover/", self.server_url);
        tracing::debug!("URL de découverte: {}", url);

        let client = reqwest::Client::builder()
            .danger_accept_invalid_certs(true)
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
            if let Ok(error_response) = serde_json::from_str::<RegistrationErrorResponse>(&body) {
                return Err(ClientError::Other(error_response.error));
            }
            return Err(ClientError::Connection(format!(
                "Erreur du serveur: {} - {}",
                status, body
            )));
        }

        let response: DiscoveryResponse = serde_json::from_str(&body)
            .map_err(|e| ClientError::Other(format!("Erreur de parsing de la réponse: {}", e)))?;

        tracing::info!("✓ Découverte envoyée: {} (poste_id: {})", response.message, response.poste_id);

        Ok(response)
    }

    /// Vérifie le statut de découverte et récupère le token si disponible
    ///
    /// Cette méthode est appelée en boucle (polling) pour vérifier si l'admin
    /// a validé le poste et généré un token d'enregistrement.
    ///
    /// # Returns
    /// Statut de découverte avec éventuellement le token d'enregistrement
    pub async fn check_discovery_status(&self) -> Result<DiscoveryStatusResponse> {
        let mac_address = Self::get_mac_address()?;

        let request = DiscoveryStatusRequest { mac_address };

        let url = format!("{}/api/postes/check_discovery_status/", self.server_url);

        let client = reqwest::Client::builder()
            .danger_accept_invalid_certs(true)
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

        if !status.is_success() {
            if let Ok(error_response) = serde_json::from_str::<RegistrationErrorResponse>(&body) {
                return Err(ClientError::Other(error_response.error));
            }
            return Err(ClientError::Connection(format!(
                "Erreur du serveur: {} - {}",
                status, body
            )));
        }

        let response: DiscoveryStatusResponse = serde_json::from_str(&body)
            .map_err(|e| ClientError::Other(format!("Erreur de parsing de la réponse: {}", e)))?;

        Ok(response)
    }

    /// Flux complet de découverte automatique et enregistrement
    ///
    /// Cette méthode gère le flux complet :
    /// 1. Envoie la demande de découverte
    /// 2. Poll le serveur jusqu'à validation par l'admin
    /// 3. Récupère le token d'enregistrement
    /// 4. S'enregistre et obtient les certificats mTLS
    ///
    /// # Arguments
    /// * `discovery_token` - Token partagé configuré sur le serveur
    /// * `poll_interval_secs` - Intervalle entre les vérifications (secondes)
    /// * `max_wait_secs` - Temps maximum d'attente (secondes)
    ///
    /// # Returns
    /// Informations sur le poste après enregistrement complet
    pub async fn auto_discover_and_register(
        &self,
        discovery_token: &str,
        poll_interval_secs: u64,
        max_wait_secs: u64,
    ) -> Result<PosteInfo> {
        // Si déjà enregistré, retourner une erreur
        if self.is_registered() {
            return Err(ClientError::Other(
                "Ce client est déjà enregistré. Utilisez unregister d'abord.".to_string(),
            ));
        }

        // Étape 1: Envoyer la demande de découverte
        tracing::info!("=== Étape 1/4: Envoi de la demande de découverte ===");
        let discovery_response = self.discover(discovery_token).await?;
        tracing::info!(
            "Poste créé en attente de validation (ID: {})",
            discovery_response.poste_id
        );

        // Étape 2: Polling pour attendre la validation
        tracing::info!("=== Étape 2/4: Attente de validation par l'administrateur ===");
        tracing::info!(
            "Vérification toutes les {}s, timeout: {}s",
            poll_interval_secs,
            max_wait_secs
        );

        let start_time = std::time::Instant::now();
        let poll_interval = std::time::Duration::from_secs(poll_interval_secs);
        let max_wait = std::time::Duration::from_secs(max_wait_secs);

        let registration_token = loop {
            // Vérifier le timeout
            if start_time.elapsed() > max_wait {
                return Err(ClientError::Other(format!(
                    "Timeout: pas de validation après {}s d'attente",
                    max_wait_secs
                )));
            }

            // Vérifier le statut
            let status = self.check_discovery_status().await?;

            match status.status.as_str() {
                "pending_validation" => {
                    tracing::debug!("En attente de validation...");
                }
                "validated" => {
                    if let Some(token) = status.registration_token {
                        tracing::info!("✓ Poste validé! Token d'enregistrement reçu.");
                        break token;
                    } else {
                        tracing::debug!("Validé mais token pas encore généré...");
                    }
                }
                "registered" => {
                    return Err(ClientError::Other(
                        "Ce poste est déjà enregistré sur le serveur".to_string(),
                    ));
                }
                "unknown" => {
                    return Err(ClientError::Other(
                        "Poste non trouvé sur le serveur. Réessayez la découverte.".to_string(),
                    ));
                }
                other => {
                    tracing::warn!("Statut inattendu: {}", other);
                }
            }

            // Attendre avant le prochain poll
            tokio::time::sleep(poll_interval).await;
        };

        // Étape 3: Enregistrement avec le token
        tracing::info!("=== Étape 3/4: Enregistrement avec le token ===");
        let poste_info = self.register(&registration_token).await?;

        // Étape 4: Confirmation
        tracing::info!("=== Étape 4/4: Enregistrement complet ===");
        tracing::info!(
            "✓ Client enregistré avec succès! Poste: {} (ID: {})",
            poste_info.nom,
            poste_info.id
        );

        Ok(poste_info)
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
    fn test_registration_success_response_deserialize() {
        let json = r#"{
            "client_cert": "-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----",
            "client_key": "-----BEGIN PRIVATE KEY-----\nTEST\n-----END PRIVATE KEY-----",
            "ca_cert": "-----BEGIN CERTIFICATE-----\nCA\n-----END CERTIFICATE-----",
            "poste_id": 1,
            "poste_nom": "PC-01",
            "certificate_cn": "poste-1-pc01",
            "expires_at": "2026-12-04T10:00:00Z"
        }"#;

        let response: RegistrationSuccessResponse = serde_json::from_str(json).unwrap();
        assert_eq!(response.poste_id, 1);
        assert_eq!(response.poste_nom, "PC-01".to_string());
        assert_eq!(response.certificate_cn, "poste-1-pc01");
    }

    #[test]
    fn test_registration_error_response() {
        let json = r#"{
            "error": "Token invalide ou expiré"
        }"#;

        let response: RegistrationErrorResponse = serde_json::from_str(json).unwrap();
        assert_eq!(response.error, "Token invalide ou expiré");
    }

    #[test]
    fn test_discovery_request_serialize() {
        let request = DiscoveryRequest {
            discovery_token: "shared-secret-token".to_string(),
            hostname: "test-pc".to_string(),
            mac_address: "00:11:22:33:44:55".to_string(),
        };

        let json = serde_json::to_string(&request).unwrap();
        assert!(json.contains("shared-secret-token"));
        assert!(json.contains("test-pc"));
        assert!(json.contains("00:11:22:33:44:55"));
    }

    #[test]
    fn test_discovery_response_deserialize() {
        let json = r#"{
            "status": "pending_validation",
            "poste_id": 123,
            "message": "Poste découvert, en attente de validation"
        }"#;

        let response: DiscoveryResponse = serde_json::from_str(json).unwrap();
        assert_eq!(response.status, "pending_validation");
        assert_eq!(response.poste_id, 123);
        assert!(response.message.contains("attente de validation"));
    }

    #[test]
    fn test_discovery_status_response_validated() {
        let json = r#"{
            "status": "validated",
            "poste_id": 123,
            "poste_nom": "PC-01",
            "registration_token": "abc123token",
            "message": "Poste validé"
        }"#;

        let response: DiscoveryStatusResponse = serde_json::from_str(json).unwrap();
        assert_eq!(response.status, "validated");
        assert_eq!(response.poste_id, Some(123));
        assert_eq!(response.poste_nom, Some("PC-01".to_string()));
        assert_eq!(response.registration_token, Some("abc123token".to_string()));
    }

    #[test]
    fn test_discovery_status_response_pending() {
        let json = r#"{
            "status": "pending_validation",
            "poste_id": 123,
            "poste_nom": "AUTO-334455",
            "message": "En attente de validation par l'administrateur"
        }"#;

        let response: DiscoveryStatusResponse = serde_json::from_str(json).unwrap();
        assert_eq!(response.status, "pending_validation");
        assert!(response.registration_token.is_none());
    }
}
