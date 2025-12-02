/**
 * Composable pour gérer les connexions WebSocket
 */

import { ref, onUnmounted } from 'vue'

/**
 * Construit l'URL WebSocket complète
 * Utilise les variables d'environnement ou détecte automatiquement
 */
function buildWebSocketUrl(path) {
  // Si le path est déjà une URL complète, l'utiliser
  if (path.startsWith('ws://') || path.startsWith('wss://')) {
    return path
  }

  // Utiliser la variable d'environnement si disponible
  const wsBaseUrl = import.meta.env.VITE_WS_URL

  if (wsBaseUrl) {
    // S'assurer que l'URL de base ne se termine pas par /
    const base = wsBaseUrl.replace(/\/$/, '')
    return `${base}${path}`
  }

  // Détection automatique basée sur l'URL courante
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host

  // En développement, utiliser le port du backend (8000)
  if (window.location.port === '3000' || window.location.port === '5173') {
    // Mode dev avec Vite - connecter au backend sur le même host mais port différent
    const devHost = window.location.hostname
    return `${protocol}//${devHost}:8000${path}`
  }

  // En production, utiliser le même host
  return `${protocol}//${host}${path}`
}

export function useWebSocket(url) {
  const ws = ref(null)
  const isConnected = ref(false)
  const error = ref(null)
  const reconnectAttempts = ref(0)
  const maxReconnectAttempts = 5
  const reconnectDelay = 3000

  const connect = () => {
    try {
      // Construire l'URL WebSocket dynamiquement
      const wsUrl = buildWebSocketUrl(url)

      ws.value = new WebSocket(wsUrl)

      ws.value.onopen = () => {
        console.log(`WebSocket connected: ${url}`)
        isConnected.value = true
        error.value = null
        reconnectAttempts.value = 0
      }

      ws.value.onclose = (event) => {
        console.log(`WebSocket closed: ${url}`, event)
        isConnected.value = false

        // Tentative de reconnexion automatique
        if (reconnectAttempts.value < maxReconnectAttempts) {
          console.log(`Reconnection attempt ${reconnectAttempts.value + 1}/${maxReconnectAttempts}`)
          reconnectAttempts.value++
          setTimeout(connect, reconnectDelay)
        } else {
          error.value = 'Connexion WebSocket perdue. Impossible de reconnecter.'
        }
      }

      ws.value.onerror = (err) => {
        console.error(`WebSocket error: ${url}`, err)
        error.value = 'Erreur de connexion WebSocket'
      }

    } catch (err) {
      console.error('Error creating WebSocket:', err)
      error.value = err.message
    }
  }

  const disconnect = () => {
    if (ws.value) {
      reconnectAttempts.value = maxReconnectAttempts // Empêcher la reconnexion automatique
      ws.value.close()
      ws.value = null
      isConnected.value = false
    }
  }

  const send = (data) => {
    if (ws.value && isConnected.value) {
      ws.value.send(JSON.stringify(data))
    } else {
      console.warn('WebSocket not connected. Cannot send:', data)
    }
  }

  const onMessage = (callback) => {
    if (ws.value) {
      ws.value.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          callback(data)
        } catch (err) {
          console.error('Error parsing WebSocket message:', err)
        }
      }
    }
  }

  // Nettoyer la connexion lors de la destruction du composant
  onUnmounted(() => {
    disconnect()
  })

  return {
    ws,
    isConnected,
    error,
    connect,
    disconnect,
    send,
    onMessage
  }
}

/**
 * Composable spécialisé pour le Dashboard WebSocket
 */
export function useDashboardWebSocket() {
  const { ws, isConnected, error, connect, disconnect, send, onMessage } = useWebSocket('/ws/dashboard/')
  const stats = ref(null)

  const handleMessage = (data) => {
    if (data.type === 'stats_update') {
      stats.value = data.data
    }
  }

  const requestStats = () => {
    send({ type: 'get_stats' })
  }

  const connectDashboard = () => {
    connect()
    onMessage(handleMessage)
  }

  return {
    stats,
    isConnected,
    error,
    connect: connectDashboard,
    disconnect,
    requestStats
  }
}

/**
 * Composable spécialisé pour les Sessions WebSocket
 */
export function useSessionWebSocket(sessionId = null) {
  const url = sessionId ? `/ws/sessions/${sessionId}/` : '/ws/sessions/'
  const { ws, isConnected, error, connect, disconnect, send, onMessage } = useWebSocket(url)

  const sessions = ref([])
  const currentSession = ref(null)

  const handleMessage = (data) => {
    switch (data.type) {
      case 'sessions_update':
        sessions.value = data.data
        break
      case 'session_update':
        // Mettre à jour une session spécifique
        const index = sessions.value.findIndex(s => s.id === data.data.id)
        if (index !== -1) {
          sessions.value[index] = data.data
        }
        break
      case 'session_created':
        sessions.value.push(data.data)
        break
      case 'session_ended':
        sessions.value = sessions.value.filter(s => s.id !== data.data.id)
        break
      case 'time_update':
        if (currentSession.value && currentSession.value.id === data.session_id) {
          currentSession.value.temps_restant = data.temps_restant
          currentSession.value.pourcentage_utilise = data.pourcentage_utilise
        }
        break
      case 'connection_established':
        console.log('Session WebSocket connected:', data.message)
        break
      case 'error':
        console.error('Session WebSocket error:', data.message)
        break
    }
  }

  const requestSessions = () => {
    send({ type: 'get_sessions' })
  }

  const validateCode = (code, ipAddress = null) => {
    send({
      type: 'validate_code',
      code,
      ip_address: ipAddress
    })
  }

  const startSession = (sessionId) => {
    send({
      type: 'start_session',
      session_id: sessionId
    })
  }

  const getTime = (sessionId) => {
    send({
      type: 'get_time',
      session_id: sessionId
    })
  }

  const heartbeat = () => {
    send({ type: 'heartbeat' })
  }

  const connectSession = () => {
    connect()
    onMessage(handleMessage)
  }

  return {
    sessions,
    currentSession,
    isConnected,
    error,
    connect: connectSession,
    disconnect,
    requestSessions,
    validateCode,
    startSession,
    getTime,
    heartbeat
  }
}
