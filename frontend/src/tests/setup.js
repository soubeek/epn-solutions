/**
 * Setup file for Vitest
 * Configuration globale des tests
 */

import { vi } from 'vitest'
import { config } from '@vue/test-utils'

// Mock de localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn()
}
global.localStorage = localStorageMock

// Mock de window.location
delete window.location
window.location = {
  href: 'http://localhost:3000',
  hostname: 'localhost',
  protocol: 'http:',
  port: '3000',
  pathname: '/',
  search: '',
  hash: '',
  assign: vi.fn(),
  reload: vi.fn(),
  replace: vi.fn()
}

// Mock de navigator.clipboard
Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn().mockResolvedValue(undefined),
    readText: vi.fn().mockResolvedValue('')
  }
})

// Configuration globale de Vue Test Utils
config.global.mocks = {
  $t: (msg) => msg, // Mock pour i18n si utilisé
  $router: {
    push: vi.fn(),
    replace: vi.fn(),
    go: vi.fn()
  },
  $route: {
    path: '/',
    params: {},
    query: {}
  }
}

// Configuration des stubs globaux
config.global.stubs = {
  Teleport: true,
  Transition: false,
  TransitionGroup: false
}

// Reset tous les mocks avant chaque test
beforeEach(() => {
  vi.clearAllMocks()
  localStorage.getItem.mockReturnValue(null)
})
