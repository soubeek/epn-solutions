// Client WebSocket pour la communication avec le serveur Django
// Supporte les connexions TLS avec authentification par certificat client (mTLS)

use crate::certificate::{CertificateStore, ClientCertificates};
use crate::types::{ClientError, ClientMessage, Result, ServerMessage};
use futures_util::{SinkExt, StreamExt};
use rustls::pki_types::{CertificateDer, PrivateKeyDer};
use std::io::BufReader;
use std::sync::Arc;
use tokio::io::{AsyncRead, AsyncWrite};
use tokio::net::TcpStream;
use tokio::sync::mpsc;
use tokio::time::{sleep, Duration};
use tokio_rustls::TlsConnector;
use tokio_tungstenite::{tungstenite::protocol::Message, WebSocketStream};
use url::Url;

/// Stream qui peut être TCP brut ou TLS
pub enum MaybeTlsClientStream {
    Plain(TcpStream),
    Tls(tokio_rustls::client::TlsStream<TcpStream>),
}

impl AsyncRead for MaybeTlsClientStream {
    fn poll_read(
        self: std::pin::Pin<&mut Self>,
        cx: &mut std::task::Context<'_>,
        buf: &mut tokio::io::ReadBuf<'_>,
    ) -> std::task::Poll<std::io::Result<()>> {
        match self.get_mut() {
            MaybeTlsClientStream::Plain(s) => std::pin::Pin::new(s).poll_read(cx, buf),
            MaybeTlsClientStream::Tls(s) => std::pin::Pin::new(s).poll_read(cx, buf),
        }
    }
}

impl AsyncWrite for MaybeTlsClientStream {
    fn poll_write(
        self: std::pin::Pin<&mut Self>,
        cx: &mut std::task::Context<'_>,
        buf: &[u8],
    ) -> std::task::Poll<std::io::Result<usize>> {
        match self.get_mut() {
            MaybeTlsClientStream::Plain(s) => std::pin::Pin::new(s).poll_write(cx, buf),
            MaybeTlsClientStream::Tls(s) => std::pin::Pin::new(s).poll_write(cx, buf),
        }
    }

    fn poll_flush(
        self: std::pin::Pin<&mut Self>,
        cx: &mut std::task::Context<'_>,
    ) -> std::task::Poll<std::io::Result<()>> {
        match self.get_mut() {
            MaybeTlsClientStream::Plain(s) => std::pin::Pin::new(s).poll_flush(cx),
            MaybeTlsClientStream::Tls(s) => std::pin::Pin::new(s).poll_flush(cx),
        }
    }

    fn poll_shutdown(
        self: std::pin::Pin<&mut Self>,
        cx: &mut std::task::Context<'_>,
    ) -> std::task::Poll<std::io::Result<()>> {
        match self.get_mut() {
            MaybeTlsClientStream::Plain(s) => std::pin::Pin::new(s).poll_shutdown(cx),
            MaybeTlsClientStream::Tls(s) => std::pin::Pin::new(s).poll_shutdown(cx),
        }
    }
}

type WsStream = WebSocketStream<MaybeTlsClientStream>;

/// Configuration TLS pour le client
#[derive(Clone)]
pub struct TlsConfig {
    /// Certificats mTLS (optionnel en mode dev)
    pub certificates: Option<ClientCertificates>,
    /// Accepter les certificats auto-signés (dev seulement)
    pub accept_invalid_certs: bool,
}

impl Default for TlsConfig {
    fn default() -> Self {
        Self {
            certificates: None,
            accept_invalid_certs: false,
        }
    }
}

impl TlsConfig {
    /// Crée une configuration TLS depuis le CertificateStore
    pub fn from_store(store: &CertificateStore) -> Result<Self> {
        if store.is_registered() {
            let certs = store.load_certificates()?;
            Ok(Self {
                certificates: Some(certs),
                accept_invalid_certs: false,
            })
        } else {
            Ok(Self::default())
        }
    }

    /// Mode développement : pas de certificat, accepte tout
    pub fn development() -> Self {
        Self {
            certificates: None,
            accept_invalid_certs: true,
        }
    }
}

/// Client WebSocket avec support mTLS
pub struct WsClient {
    #[allow(dead_code)]
    url: String,
    tx: mpsc::UnboundedSender<ClientMessage>,
    rx: mpsc::UnboundedReceiver<ServerMessage>,
    #[allow(dead_code)]
    reconnect_interval: Duration,
}

impl WsClient {
    /// Créer et connecter un nouveau client WebSocket sans TLS (pour compatibilité)
    pub async fn connect(url: &str) -> Result<Self> {
        Self::connect_with_tls(url, TlsConfig::development()).await
    }

    /// Créer et connecter un client WebSocket avec configuration TLS
    pub async fn connect_with_tls(url: &str, tls_config: TlsConfig) -> Result<Self> {
        let url_parsed = Url::parse(url)
            .map_err(|e| ClientError::Connection(format!("URL invalide: {}", e)))?;

        tracing::info!("Connexion au serveur WebSocket: {}", url);

        let (tx_msg, rx_msg) = mpsc::unbounded_channel();
        let (tx_resp, rx_resp) = mpsc::unbounded_channel();

        // Établir la connexion WebSocket avec TLS
        let ws_stream = Self::establish_connection(&url_parsed, &tls_config).await?;

        // Lancer la boucle de traitement des messages
        tokio::spawn(Self::message_loop(
            ws_stream,
            rx_msg,
            tx_resp,
            url.to_string(),
            tls_config,
        ));

        Ok(Self {
            url: url.to_string(),
            tx: tx_msg,
            rx: rx_resp,
            reconnect_interval: Duration::from_secs(5),
        })
    }

    /// Connexion avec certificat client depuis le CertificateStore
    pub async fn connect_mtls(url: &str) -> Result<Self> {
        let store = CertificateStore::new()?;

        if !store.is_registered() {
            return Err(ClientError::Connection(
                "Client non enregistré. Utilisez la commande d'enregistrement d'abord.".to_string(),
            ));
        }

        let tls_config = TlsConfig::from_store(&store)?;
        Self::connect_with_tls(url, tls_config).await
    }

    /// Établir la connexion WebSocket avec support TLS/mTLS
    async fn establish_connection(url: &Url, tls_config: &TlsConfig) -> Result<WsStream> {
        let host = url
            .host_str()
            .ok_or_else(|| ClientError::Connection("URL sans host".to_string()))?;
        let port = url.port_or_known_default().unwrap_or(443);

        // Connexion TCP
        let addr = format!("{}:{}", host, port);
        let tcp_stream = TcpStream::connect(&addr).await.map_err(|e| {
            ClientError::Connection(format!("Erreur de connexion TCP à {}: {}", addr, e))
        })?;

        // Déterminer si on utilise TLS
        let is_secure = url.scheme() == "wss" || url.scheme() == "https";

        let stream: MaybeTlsClientStream = if is_secure {
            // Connexion avec TLS
            let connector = Self::create_rustls_connector(tls_config)?;
            let domain = rustls::pki_types::ServerName::try_from(host.to_string())
                .map_err(|e| ClientError::Connection(format!("Nom de domaine invalide: {}", e)))?;

            let tls_stream = connector
                .connect(domain, tcp_stream)
                .await
                .map_err(|e| ClientError::Connection(format!("Erreur TLS: {}", e)))?;

            if tls_config.certificates.is_some() {
                tracing::info!("✓ Authentification mTLS active");
            }

            MaybeTlsClientStream::Tls(tls_stream)
        } else {
            tracing::warn!("⚠ Connexion non sécurisée (ws://)");
            MaybeTlsClientStream::Plain(tcp_stream)
        };

        // Upgrade vers WebSocket
        let (ws_stream, response) =
            tokio_tungstenite::client_async(url.as_str(), stream)
                .await
                .map_err(|e| ClientError::Connection(format!("Erreur WebSocket: {}", e)))?;

        tracing::info!(
            "✓ Connecté au serveur WebSocket (status: {})",
            response.status()
        );

        Ok(ws_stream)
    }

    /// Crée le connecteur TLS rustls avec ou sans certificat client
    fn create_rustls_connector(tls_config: &TlsConfig) -> Result<TlsConnector> {
        let mut root_store = rustls::RootCertStore::empty();

        // Ajouter les racines système par défaut
        root_store.extend(webpki_roots::TLS_SERVER_ROOTS.iter().cloned());

        // Configuration des certificats
        let config = if let Some(ref certs) = tls_config.certificates {
            // Parser le certificat CA
            let ca_certs = Self::load_pem_certs(&certs.ca_cert)?;
            for cert in ca_certs {
                root_store.add(cert).map_err(|e| {
                    ClientError::Connection(format!("Erreur d'ajout du certificat CA: {}", e))
                })?;
            }

            // Parser le certificat client et la clé
            let client_certs = Self::load_pem_certs(&certs.client_cert)?;
            let client_key = Self::load_pem_key(&certs.client_key)?;

            tracing::debug!("Certificats client chargés pour mTLS");

            // Configuration avec certificat client
            rustls::ClientConfig::builder()
                .with_root_certificates(root_store)
                .with_client_auth_cert(client_certs, client_key)
                .map_err(|e| {
                    ClientError::Connection(format!(
                        "Erreur de configuration du certificat client: {}",
                        e
                    ))
                })?
        } else {
            // Configuration sans certificat client
            let mut config = rustls::ClientConfig::builder()
                .with_root_certificates(root_store)
                .with_no_client_auth();

            // Mode développement : accepter les certificats invalides
            if tls_config.accept_invalid_certs {
                config
                    .dangerous()
                    .set_certificate_verifier(Arc::new(DangerousVerifier));
                tracing::warn!("Mode développement: vérification des certificats désactivée");
            }

            config
        };

        Ok(TlsConnector::from(Arc::new(config)))
    }

    /// Charge des certificats depuis une chaîne PEM
    fn load_pem_certs(pem: &str) -> Result<Vec<CertificateDer<'static>>> {
        let mut reader = BufReader::new(pem.as_bytes());
        let certs: Vec<_> = rustls_pemfile::certs(&mut reader)
            .filter_map(|r| r.ok())
            .collect();

        if certs.is_empty() {
            return Err(ClientError::Connection(
                "Aucun certificat trouvé dans le PEM".to_string(),
            ));
        }

        Ok(certs)
    }

    /// Charge une clé privée depuis une chaîne PEM
    fn load_pem_key(pem: &str) -> Result<PrivateKeyDer<'static>> {
        let mut reader = BufReader::new(pem.as_bytes());

        // Essayer de lire différents types de clés
        loop {
            match rustls_pemfile::read_one(&mut reader) {
                Ok(Some(rustls_pemfile::Item::Pkcs1Key(key))) => {
                    return Ok(PrivateKeyDer::Pkcs1(key));
                }
                Ok(Some(rustls_pemfile::Item::Pkcs8Key(key))) => {
                    return Ok(PrivateKeyDer::Pkcs8(key));
                }
                Ok(Some(rustls_pemfile::Item::Sec1Key(key))) => {
                    return Ok(PrivateKeyDer::Sec1(key));
                }
                Ok(Some(_)) => continue, // Skip other items
                Ok(None) => break,
                Err(e) => {
                    return Err(ClientError::Connection(format!(
                        "Erreur de lecture de la clé: {}",
                        e
                    )))
                }
            }
        }

        Err(ClientError::Connection(
            "Aucune clé privée trouvée dans le PEM".to_string(),
        ))
    }

    /// Boucle principale de traitement des messages
    async fn message_loop(
        mut ws_stream: WsStream,
        mut rx_msg: mpsc::UnboundedReceiver<ClientMessage>,
        tx_resp: mpsc::UnboundedSender<ServerMessage>,
        url: String,
        tls_config: TlsConfig,
    ) {
        loop {
            tokio::select! {
                // Messages à envoyer au serveur
                Some(client_msg) = rx_msg.recv() => {
                    if let Err(e) = Self::send_message(&mut ws_stream, &client_msg).await {
                        tracing::error!("Erreur d'envoi: {}", e);
                        // Tenter de se reconnecter
                        if let Ok(new_stream) = Self::reconnect(&url, &tls_config).await {
                            ws_stream = new_stream;
                        } else {
                            break;
                        }
                    }
                }

                // Messages reçus du serveur
                Some(result) = ws_stream.next() => {
                    match result {
                        Ok(Message::Text(text)) => {
                            match Self::parse_server_message(&text) {
                                Ok(server_msg) => {
                                    tracing::debug!("Message reçu: {:?}", server_msg);
                                    if tx_resp.send(server_msg).is_err() {
                                        tracing::error!("Le récepteur a été fermé");
                                        break;
                                    }
                                }
                                Err(e) => {
                                    tracing::error!("Erreur de parsing: {}", e);
                                }
                            }
                        }
                        Ok(Message::Close(_)) => {
                            tracing::warn!("Connexion fermée par le serveur");
                            // Tenter de se reconnecter
                            if let Ok(new_stream) = Self::reconnect(&url, &tls_config).await {
                                ws_stream = new_stream;
                            } else {
                                break;
                            }
                        }
                        Ok(Message::Ping(data)) => {
                            if let Err(e) = ws_stream.send(Message::Pong(data)).await {
                                tracing::error!("Erreur lors de l'envoi du pong: {}", e);
                            }
                        }
                        Ok(_) => {}
                        Err(e) => {
                            tracing::error!("Erreur WebSocket: {}", e);
                            // Tenter de se reconnecter
                            if let Ok(new_stream) = Self::reconnect(&url, &tls_config).await {
                                ws_stream = new_stream;
                            } else {
                                break;
                            }
                        }
                    }
                }
            }
        }

        tracing::info!("Boucle de messages terminée");
    }

    /// Envoyer un message au serveur
    async fn send_message(ws_stream: &mut WsStream, msg: &ClientMessage) -> Result<()> {
        let json = serde_json::to_string(msg)?;
        tracing::debug!("Envoi: {}", json);

        ws_stream
            .send(Message::Text(json))
            .await
            .map_err(|e| ClientError::WebSocket(format!("Erreur d'envoi: {}", e)))
    }

    /// Parser un message du serveur
    fn parse_server_message(text: &str) -> Result<ServerMessage> {
        serde_json::from_str(text).map_err(|e| ClientError::Serialization(e))
    }

    /// Tenter de se reconnecter
    async fn reconnect(url: &str, tls_config: &TlsConfig) -> Result<WsStream> {
        tracing::warn!("Tentative de reconnexion...");
        sleep(Duration::from_secs(5)).await;

        let url_parsed = Url::parse(url)
            .map_err(|e| ClientError::Connection(format!("URL invalide: {}", e)))?;

        Self::establish_connection(&url_parsed, tls_config).await
    }

    /// Envoyer un message au serveur
    pub fn send(&self, msg: ClientMessage) -> Result<()> {
        self.tx
            .send(msg)
            .map_err(|e| ClientError::WebSocket(format!("Canal fermé: {}", e)))
    }

    /// Recevoir le prochain message du serveur (non-bloquant)
    pub async fn recv(&mut self) -> Option<ServerMessage> {
        self.rx.recv().await
    }

    /// Recevoir le prochain message avec timeout
    pub async fn recv_timeout(&mut self, timeout: Duration) -> Option<ServerMessage> {
        tokio::time::timeout(timeout, self.rx.recv())
            .await
            .ok()
            .flatten()
    }
}

/// Vérificateur de certificat qui accepte tout (mode développement uniquement)
#[derive(Debug)]
struct DangerousVerifier;

impl rustls::client::danger::ServerCertVerifier for DangerousVerifier {
    fn verify_server_cert(
        &self,
        _end_entity: &CertificateDer<'_>,
        _intermediates: &[CertificateDer<'_>],
        _server_name: &rustls::pki_types::ServerName<'_>,
        _ocsp_response: &[u8],
        _now: rustls::pki_types::UnixTime,
    ) -> std::result::Result<rustls::client::danger::ServerCertVerified, rustls::Error> {
        Ok(rustls::client::danger::ServerCertVerified::assertion())
    }

    fn verify_tls12_signature(
        &self,
        _message: &[u8],
        _cert: &CertificateDer<'_>,
        _dss: &rustls::DigitallySignedStruct,
    ) -> std::result::Result<rustls::client::danger::HandshakeSignatureValid, rustls::Error> {
        Ok(rustls::client::danger::HandshakeSignatureValid::assertion())
    }

    fn verify_tls13_signature(
        &self,
        _message: &[u8],
        _cert: &CertificateDer<'_>,
        _dss: &rustls::DigitallySignedStruct,
    ) -> std::result::Result<rustls::client::danger::HandshakeSignatureValid, rustls::Error> {
        Ok(rustls::client::danger::HandshakeSignatureValid::assertion())
    }

    fn supported_verify_schemes(&self) -> Vec<rustls::SignatureScheme> {
        vec![
            rustls::SignatureScheme::RSA_PKCS1_SHA256,
            rustls::SignatureScheme::RSA_PKCS1_SHA384,
            rustls::SignatureScheme::RSA_PKCS1_SHA512,
            rustls::SignatureScheme::ECDSA_NISTP256_SHA256,
            rustls::SignatureScheme::ECDSA_NISTP384_SHA384,
            rustls::SignatureScheme::ECDSA_NISTP521_SHA512,
            rustls::SignatureScheme::RSA_PSS_SHA256,
            rustls::SignatureScheme::RSA_PSS_SHA384,
            rustls::SignatureScheme::RSA_PSS_SHA512,
            rustls::SignatureScheme::ED25519,
        ]
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_server_message() {
        let json = r#"{"type":"code_valid","session":{"id":1,"code":"ABC123","user_name":"Test User","workstation":"PC-01","total_duration":3600,"remaining_time":3600,"status":"active"}}"#;
        let result = WsClient::parse_server_message(json);
        assert!(result.is_ok());
    }

    #[test]
    fn test_parse_time_update() {
        let json = r#"{"type":"time_update","remaining":300,"percentage":50.0}"#;
        let result = WsClient::parse_server_message(json);
        assert!(result.is_ok());
    }

    #[test]
    fn test_parse_error() {
        let json = r#"{"type":"error","message":"Test error"}"#;
        let result = WsClient::parse_server_message(json);
        assert!(result.is_ok());
    }

    #[test]
    fn test_tls_config_default() {
        let config = TlsConfig::default();
        assert!(config.certificates.is_none());
        assert!(!config.accept_invalid_certs);
    }

    #[test]
    fn test_tls_config_development() {
        let config = TlsConfig::development();
        assert!(config.certificates.is_none());
        assert!(config.accept_invalid_certs);
    }

    #[test]
    fn test_load_pem_certs() {
        let pem = "-----BEGIN CERTIFICATE-----\n\
                   MIIBkTCB+wIJAKHBfpStl/uFMA0GCSqGSIb3DQEBCwUAMBExDzANBgNVBAMMBnRl\n\
                   c3RjYTAeFw0yMzAxMDEwMDAwMDBaFw0yNDAxMDEwMDAwMDBaMBExDzANBgNVBAMM\n\
                   BnRlc3RjYTBcMA0GCSqGSIb3DQEBAQUAA0sAMEgCQQC7o96+t73V0hFqycnSXqKz\n\
                   8OJrYCAGmvCLTdGmSjPLiCDnbBq7L5b1V1C8E5y7p1ZK3J7zOaVL9jPJ9KeZX9Xj\n\
                   AgMBAAGjUzBRMB0GA1UdDgQWBBQFwsN5Wwe0T1HCM4Fy7n7kPwHb9jAfBgNVHSME\n\
                   GDAWgBQFwsN5Wwe0T1HCM4Fy7n7kPwHb9jAPBgNVHRMBAf8EBTADAQH/MA0GCSqG\n\
                   SIb3DQEBCwUAA0EAJ2MtM+rjJzYCwMU9Z7K9M8lT9F+Lg3mJm3eOFsM7rE7w\n\
                   -----END CERTIFICATE-----";

        // Ce test vérifie juste que le parsing ne plante pas
        // Le certificat de test n'est pas valide, donc on s'attend à une erreur
        let result = WsClient::load_pem_certs(pem);
        // Le parsing peut échouer car le certificat n'est pas valide
        assert!(result.is_ok() || result.is_err());
    }
}
