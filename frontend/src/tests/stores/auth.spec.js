/**
 * Tests pour le store auth
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'

// Mock du module api
vi.mock('@/services/api', () => ({
  authService: {
    login: vi.fn(),
    refreshToken: vi.fn()
  }
}))

import { authService } from '@/services/api'

describe('Auth Store', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useAuthStore()
    vi.clearAllMocks()
    localStorage.clear()
  })

  describe('Initial State', () => {
    it('should have null tokens initially', () => {
      expect(store.accessToken).toBeNull()
      expect(store.refreshToken).toBeNull()
    })

    it('should have null user initially', () => {
      expect(store.user).toBeNull()
    })

    it('should not be authenticated initially', () => {
      expect(store.isAuthenticated).toBe(false)
    })

    it('should return anonymous as username when not logged in', () => {
      expect(store.username).toBe('anonymous')
    })

    it('should not be admin initially', () => {
      expect(store.isAdmin).toBe(false)
    })
  })

  describe('Login', () => {
    const mockJWT = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6InRlc3R1c2VyIiwiaXNfc3RhZmYiOnRydWUsImlzX3N1cGVydXNlciI6ZmFsc2UsImV4cCI6OTk5OTk5OTk5OX0.test'

    it('should login successfully', async () => {
      authService.login.mockResolvedValueOnce({
        data: {
          access: mockJWT,
          refresh: 'refresh_token'
        }
      })

      const result = await store.login({ username: 'testuser', password: 'password' })

      expect(result.success).toBe(true)
      expect(store.accessToken).toBe(mockJWT)
      expect(localStorage.setItem).toHaveBeenCalledWith('refreshToken', 'refresh_token')
      expect(store.isAuthenticated).toBe(true)
    })

    it('should store tokens in localStorage', async () => {
      authService.login.mockResolvedValueOnce({
        data: {
          access: mockJWT,
          refresh: 'refresh_token_value'
        }
      })

      await store.login({ username: 'testuser', password: 'password' })

      expect(localStorage.setItem).toHaveBeenCalledWith('accessToken', mockJWT)
      expect(localStorage.setItem).toHaveBeenCalledWith('refreshToken', 'refresh_token_value')
    })

    it('should decode JWT and set user info', async () => {
      authService.login.mockResolvedValueOnce({
        data: {
          access: mockJWT,
          refresh: 'refresh_token'
        }
      })

      await store.login({ username: 'testuser', password: 'password' })

      expect(store.user).not.toBeNull()
      expect(store.user.username).toBe('testuser')
      expect(store.user.is_staff).toBe(true)
    })

    it('should return error on failed login', async () => {
      authService.login.mockRejectedValueOnce({
        response: {
          data: { detail: 'Invalid credentials' }
        }
      })

      const result = await store.login({ username: 'wrong', password: 'wrong' })

      expect(result.success).toBe(false)
      expect(result.error).toBe('Invalid credentials')
      expect(store.isAuthenticated).toBe(false)
    })

    it('should return generic error message when no detail provided', async () => {
      authService.login.mockRejectedValueOnce(new Error('Network error'))

      const result = await store.login({ username: 'user', password: 'pass' })

      expect(result.success).toBe(false)
      expect(result.error).toBe('Erreur de connexion')
    })
  })

  describe('Logout', () => {
    beforeEach(async () => {
      // Setup logged in state
      store.accessToken = 'token'
      store.refreshToken = 'refresh'
      store.user = { username: 'testuser' }
    })

    it('should clear all tokens', () => {
      store.logout()

      expect(store.accessToken).toBeNull()
      expect(store.user).toBeNull()
      expect(localStorage.removeItem).toHaveBeenCalledWith('refreshToken')
    })

    it('should remove tokens from localStorage', () => {
      store.logout()

      expect(localStorage.removeItem).toHaveBeenCalledWith('accessToken')
      expect(localStorage.removeItem).toHaveBeenCalledWith('refreshToken')
      expect(localStorage.removeItem).toHaveBeenCalledWith('user')
    })

    it('should set isAuthenticated to false', () => {
      store.logout()

      expect(store.isAuthenticated).toBe(false)
    })
  })

  describe('Refresh Token', () => {
    it('should refresh token successfully', async () => {
      store.refreshToken = 'old_refresh_token'
      authService.refreshToken.mockResolvedValueOnce({
        data: { access: 'new_access_token' }
      })

      const result = await store.refreshAccessToken()

      expect(result).toBe('new_access_token')
      expect(store.accessToken).toBe('new_access_token')
    })

    it('should throw error when no refresh token', async () => {
      store.refreshToken = null

      await expect(store.refreshAccessToken()).rejects.toThrow('No refresh token available')
    })

    it('should logout on refresh failure', async () => {
      store.refreshToken = 'old_refresh_token'
      store.accessToken = 'old_access_token'
      authService.refreshToken.mockRejectedValueOnce(new Error('Expired'))

      await expect(store.refreshAccessToken()).rejects.toThrow()
      expect(store.accessToken).toBeNull()
    })
  })

  describe('Computed Properties', () => {
    it('isAdmin should be true for staff user', async () => {
      store.user = { username: 'admin', is_staff: true, is_superuser: false }

      expect(store.isAdmin).toBe(true)
    })

    it('isAdmin should be true for superuser', async () => {
      store.user = { username: 'superadmin', is_staff: false, is_superuser: true }

      expect(store.isAdmin).toBe(true)
    })

    it('isAdmin should be false for regular user', async () => {
      store.user = { username: 'user', is_staff: false, is_superuser: false }

      expect(store.isAdmin).toBe(false)
    })

    it('username should return user.username when logged in', async () => {
      store.user = { username: 'johndoe' }

      expect(store.username).toBe('johndoe')
    })
  })
})
