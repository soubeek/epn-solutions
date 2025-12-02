/**
 * Mocks pour les services API
 */
import { vi } from 'vitest'

// Mock du service auth
export const mockAuthService = {
  login: vi.fn(),
  refreshToken: vi.fn(),
  logout: vi.fn()
}

// Mock du service sessions
export const mockSessionsService = {
  getAll: vi.fn(),
  create: vi.fn(),
  getById: vi.fn(),
  update: vi.fn(),
  delete: vi.fn(),
  validate_code: vi.fn(),
  start: vi.fn(),
  addTime: vi.fn(),
  terminate: vi.fn(),
  suspend: vi.fn(),
  resume: vi.fn()
}

// Mock du service utilisateurs
export const mockUtilisateursService = {
  getAll: vi.fn(),
  create: vi.fn(),
  getById: vi.fn(),
  update: vi.fn(),
  delete: vi.fn(),
  getStats: vi.fn(),
  canCreateSession: vi.fn()
}

// Mock du service postes
export const mockPostesService = {
  getAll: vi.fn(),
  create: vi.fn(),
  getById: vi.fn(),
  update: vi.fn(),
  delete: vi.fn(),
  getDisponibles: vi.fn(),
  marquerDisponible: vi.fn(),
  marquerMaintenance: vi.fn()
}

// Réponses mockées
export const mockResponses = {
  loginSuccess: {
    data: {
      access: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6InRlc3R1c2VyIiwiaXNfc3RhZmYiOnRydWUsImlzX3N1cGVydXNlciI6ZmFsc2UsImV4cCI6OTk5OTk5OTk5OX0.test',
      refresh: 'refresh_token_mock'
    }
  },
  loginError: {
    response: {
      status: 401,
      data: { detail: 'Invalid credentials' }
    }
  },
  refreshSuccess: {
    data: {
      access: 'new_access_token_mock'
    }
  }
}
