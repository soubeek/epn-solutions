import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

const API_URL = import.meta.env.VITE_API_URL || '/api'

// Instance Axios configurée
const api = axios.create({
  baseURL: API_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Intercepteur pour ajouter le token JWT
api.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore()
    if (authStore.accessToken) {
      config.headers.Authorization = `Bearer ${authStore.accessToken}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Intercepteur pour gérer le refresh token
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // Si erreur 401 et pas déjà tenté de refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      const authStore = useAuthStore()

      try {
        await authStore.refreshAccessToken()
        return api(originalRequest)
      } catch (refreshError) {
        authStore.logout()
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

// Services API
export const authService = {
  login(credentials) {
    return api.post('/token/', credentials)
  },
  refreshToken(refresh) {
    return api.post('/token/refresh/', { refresh })
  },
  verifyToken(token) {
    return api.post('/token/verify/', { token })
  },
}

export const utilisateursService = {
  getAll(params) {
    return api.get('/utilisateurs/', { params })
  },
  getById(id) {
    return api.get(`/utilisateurs/${id}/`)
  },
  create(data) {
    return api.post('/utilisateurs/', data, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  update(id, data) {
    return api.put(`/utilisateurs/${id}/`, data, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  delete(id) {
    return api.delete(`/utilisateurs/${id}/`)
  },
  getStats() {
    return api.get('/utilisateurs/stats/')
  },
  getSessions(id) {
    return api.get(`/utilisateurs/${id}/sessions/`)
  },
  canCreateSession(id) {
    return api.get(`/utilisateurs/${id}/can_create_session/`)
  },
  revokeConsent(id) {
    return api.post(`/utilisateurs/${id}/revoke_consent/`)
  },
}

export const postesService = {
  getAll(params) {
    return api.get('/postes/', { params })
  },
  getById(id) {
    return api.get(`/postes/${id}/`)
  },
  create(data) {
    return api.post('/postes/', data)
  },
  update(id, data) {
    return api.put(`/postes/${id}/`, data)
  },
  delete(id) {
    return api.delete(`/postes/${id}/`)
  },
  getDisponibles() {
    return api.get('/postes/disponibles/')
  },
  getStats() {
    return api.get('/postes/stats/')
  },
  heartbeat(id, data) {
    return api.post(`/postes/${id}/heartbeat/`, data)
  },
  marquerDisponible(id) {
    return api.post(`/postes/${id}/marquer_disponible/`)
  },
  marquerMaintenance(id) {
    return api.post(`/postes/${id}/marquer_maintenance/`)
  },
  marquerHorsLigne(id) {
    return api.post(`/postes/${id}/marquer_hors_ligne/`)
  },
  getSessionActive(id) {
    return api.get(`/postes/${id}/session_active/`)
  },
  // ==================== Méthodes de découverte automatique ====================
  /**
   * Récupère les postes en attente de validation
   */
  getPendingValidation() {
    return api.get('/postes/pending_validation/')
  },
  /**
   * Valide un poste découvert
   * @param {number} id - ID du poste
   * @param {object} data - Données optionnelles (nom personnalisé)
   */
  validateDiscovery(id, data = {}) {
    return api.post(`/postes/${id}/validate_discovery/`, data)
  },
  /**
   * Génère un token d'enregistrement pour un poste validé
   * @param {number} id - ID du poste
   */
  generateRegistrationToken(id) {
    return api.post(`/postes/${id}/generate_registration_token/`)
  },
  /**
   * Rejette/supprime un poste en attente de validation
   * @param {number} id - ID du poste
   */
  rejectDiscovery(id) {
    return api.delete(`/postes/${id}/`)
  },
  // ==================== Commandes à distance ====================
  /**
   * Envoie une commande à distance à un poste
   * @param {number} id - ID du poste
   * @param {string} command - Commande: 'lock', 'message', 'shutdown', 'restart'
   * @param {string} payload - Payload optionnel (requis pour 'message')
   */
  remoteCommand(id, command, payload = null) {
    return api.post(`/postes/${id}/remote_command/`, { command, payload })
  },
  /**
   * Déverrouille le mode kiosque sur un poste
   * @param {number} id - ID du poste
   */
  unlockKiosk(id) {
    return api.post(`/postes/${id}/unlock_kiosk/`)
  },
}

export const sessionsService = {
  getAll(params) {
    return api.get('/sessions/', { params })
  },
  getById(id) {
    return api.get(`/sessions/${id}/`)
  },
  create(data) {
    return api.post('/sessions/', data)
  },
  createGuest(data) {
    return api.post('/sessions/create_guest/', data)
  },
  update(id, data) {
    return api.put(`/sessions/${id}/`, data)
  },
  delete(id) {
    return api.delete(`/sessions/${id}/`)
  },
  getActives() {
    return api.get('/sessions/actives/')
  },
  getStats() {
    return api.get('/sessions/stats/')
  },
  validateCode(data) {
    return api.post('/sessions/validate_code/', data)
  },
  start(id) {
    return api.post(`/sessions/${id}/start/`)
  },
  addTime(id, data) {
    return api.post(`/sessions/${id}/add_time/`, data)
  },
  terminate(id, data) {
    return api.post(`/sessions/${id}/terminate/`, data)
  },
  suspend(id, data) {
    return api.post(`/sessions/${id}/suspend/`, data)
  },
  resume(id, data) {
    return api.post(`/sessions/${id}/resume/`, data)
  },
  getTimeRemaining(id) {
    return api.get(`/sessions/${id}/time_remaining/`)
  },
}

export const extensionRequestsService = {
  /**
   * Récupère les demandes de prolongation en attente
   */
  getPending() {
    return api.get('/sessions/pending_extensions/')
  },
  /**
   * Récupère toutes les demandes de prolongation
   */
  getAll(params) {
    return api.get('/extension-requests/', { params })
  },
  /**
   * Répond à une demande de prolongation
   * @param {number} id - ID de la demande
   * @param {boolean} approve - Approuver ou refuser
   * @param {string} message - Message optionnel
   */
  respond(id, approve, message = null) {
    return api.post(`/extension-requests/${id}/respond/`, { approve, message })
  },
}

export const logsService = {
  getAll(params) {
    return api.get('/logs/', { params })
  },
  getById(id) {
    return api.get(`/logs/${id}/`)
  },
  getStats() {
    return api.get('/logs/stats/')
  },
  getRecent(hours = 24, limit = 100) {
    return api.get('/logs/recent/', { params: { hours, limit } })
  },
  search(filters) {
    return api.post('/logs/search/', filters)
  },
  getBySession(sessionId) {
    return api.get('/logs/by_session/', { params: { session_id: sessionId } })
  },
  getErrors(hours = 24) {
    return api.get('/logs/errors/', { params: { hours } })
  },
}

export default api
