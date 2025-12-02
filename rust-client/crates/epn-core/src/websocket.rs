// Client WebSocket pour la communication avec le serveur Django
use crate::types::{ClientError, ClientMessage, Result, ServerMessage};
use futures_util::{SinkExt, StreamExt};
use tokio::net::TcpStream;
use tokio::sync::mpsc;
use tokio::time::{sleep, Duration};
use tokio_tungstenite::{
    connect_async, tungstenite::protocol::Message, MaybeTlsStream, WebSocketStream,
};
use url::Url;

type WsStream = WebSocketStream<MaybeTlsStream<TcpStream>>;

/// Client WebSocket
pub struct WsClient {
    url: String,
    tx: mpsc::UnboundedSender<ClientMessage>,
    rx: mpsc::UnboundedReceiver<ServerMessage>,
    reconnect_interval: Duration,
}

impl WsClient {
    /// Créer et connecter un nouveau client WebSocket
    pub async fn connect(url: &str) -> Result<Self> {
        let url_parsed = Url::parse(url)
            .map_err(|e| ClientError::Connection(format!("URL invalide: {}", e)))?;

        tracing::info!("Connexion au serveur WebSocket: {}", url);

        let (tx_msg, rx_msg) = mpsc::unbounded_channel();
        let (tx_resp, rx_resp) = mpsc::unbounded_channel();

        // Établir la connexion WebSocket
        let ws_stream = Self::establish_connection(&url_parsed).await?;

        // Lancer la boucle de traitement des messages
        tokio::spawn(Self::message_loop(ws_stream, rx_msg, tx_resp, url.to_string()));

        Ok(Self {
            url: url.to_string(),
            tx: tx_msg,
            rx: rx_resp,
            reconnect_interval: Duration::from_secs(5),
        })
    }

    /// Établir la connexion WebSocket
    async fn establish_connection(url: &Url) -> Result<WsStream> {
        match connect_async(url).await {
            Ok((ws_stream, _)) => {
                tracing::info!("✓ Connecté au serveur WebSocket");
                Ok(ws_stream)
            }
            Err(e) => {
                let err_msg = format!("Impossible de se connecter: {}", e);
                tracing::error!("{}", err_msg);
                Err(ClientError::Connection(err_msg))
            }
        }
    }

    /// Boucle principale de traitement des messages
    async fn message_loop(
        mut ws_stream: WsStream,
        mut rx_msg: mpsc::UnboundedReceiver<ClientMessage>,
        tx_resp: mpsc::UnboundedSender<ServerMessage>,
        url: String,
    ) {
        loop {
            tokio::select! {
                // Messages à envoyer au serveur
                Some(client_msg) = rx_msg.recv() => {
                    if let Err(e) = Self::send_message(&mut ws_stream, &client_msg).await {
                        tracing::error!("Erreur d'envoi: {}", e);
                        // Tenter de se reconnecter
                        if let Ok(new_stream) = Self::reconnect(&url).await {
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
                            if let Ok(new_stream) = Self::reconnect(&url).await {
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
                            if let Ok(new_stream) = Self::reconnect(&url).await {
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
        serde_json::from_str(text).map_err(|e| {
            ClientError::Serialization(e)
        })
    }

    /// Tenter de se reconnecter
    async fn reconnect(url: &str) -> Result<WsStream> {
        tracing::warn!("Tentative de reconnexion...");
        sleep(Duration::from_secs(5)).await;

        let url_parsed = Url::parse(url)
            .map_err(|e| ClientError::Connection(format!("URL invalide: {}", e)))?;

        Self::establish_connection(&url_parsed).await
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
}
