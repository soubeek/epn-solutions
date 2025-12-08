import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authService } from '@/services/api'
import { logger } from '@/utils/logger'

/**
 * Décode un token JWT et retourne son payload
 * @param {string} token - Le token JWT
 * @returns {object|null} Le payload décodé ou null si invalide
 */
function decodeJWT(token) {
  try {
    const base64Url = token.split('.')[1]
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    )
    return JSON.parse(jsonPayload)
  } catch (e) {
    logger.error('Erreur lors du décodage du JWT:', e)
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  // State
  const accessToken = ref(localStorage.getItem('accessToken') || null)
  const refreshToken = ref(localStorage.getItem('refreshToken') || null)
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  // Getters
  const isAuthenticated = computed(() => !!accessToken.value)
  const username = computed(() => user.value?.username || 'anonymous')
  const isAdmin = computed(() => user.value?.is_staff || user.value?.is_superuser || false)

  // Actions
  async function login(credentials) {
    try {
      const response = await authService.login(credentials)
      const { access, refresh } = response.data

      accessToken.value = access
      refreshToken.value = refresh

      // Sauvegarder dans localStorage
      localStorage.setItem('accessToken', access)
      localStorage.setItem('refreshToken', refresh)

      // Décoder le JWT pour récupérer les infos utilisateur
      const payload = decodeJWT(access)
      if (payload) {
        user.value = {
          username: payload.username || credentials.username,
          user_id: payload.user_id,
          email: payload.email || '',
          is_staff: payload.is_staff || false,
          is_superuser: payload.is_superuser || false,
          exp: payload.exp
        }
      } else {
        // Fallback si le décodage échoue
        user.value = { username: credentials.username }
      }
      localStorage.setItem('user', JSON.stringify(user.value))

      return { success: true }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Erreur de connexion'
      }
    }
  }

  async function refreshTokenAction() {
    if (!refreshToken.value) {
      throw new Error('No refresh token available')
    }

    try {
      const response = await authService.refreshToken(refreshToken.value)
      const { access } = response.data

      accessToken.value = access
      localStorage.setItem('accessToken', access)

      return access
    } catch (error) {
      logout()
      throw error
    }
  }

  function logout() {
    accessToken.value = null
    refreshToken.value = null
    user.value = null

    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
    localStorage.removeItem('user')
  }

  return {
    accessToken,
    refreshToken,
    user,
    isAuthenticated,
    username,
    isAdmin,
    login,
    refreshAccessToken: refreshTokenAction,
    logout
  }
})
