<template>
  <div class="flex h-screen bg-gray-50">
    <!-- Sidebar -->
    <aside class="w-64 bg-white border-r border-gray-200">
      <div class="flex flex-col h-full">
        <!-- Logo -->
        <div class="p-6 border-b border-gray-200">
          <h1 class="text-xl font-bold text-primary-600">Poste Public</h1>
          <p class="text-sm text-gray-500">Manager</p>
        </div>

        <!-- Navigation -->
        <nav class="flex-1 p-4 space-y-2">
          <router-link
            v-for="item in menuItems"
            :key="item.name"
            :to="{ name: item.route }"
            class="flex items-center px-4 py-3 rounded-lg transition-colors"
            :class="isActive(item.route)
              ? 'bg-primary-50 text-primary-600 font-medium'
              : 'text-gray-600 hover:bg-gray-50'"
          >
            <component :is="item.icon" class="w-5 h-5 mr-3" />
            {{ item.label }}
          </router-link>
        </nav>

        <!-- User info -->
        <div class="p-4 border-t border-gray-200">
          <div class="flex items-center justify-between">
            <div class="flex items-center">
              <div class="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center">
                <span class="text-primary-600 font-medium">{{ userInitials }}</span>
              </div>
              <div class="ml-3">
                <p class="text-sm font-medium text-gray-700">{{ authStore.user?.username || 'Admin' }}</p>
                <p class="text-xs text-gray-500">Opérateur</p>
              </div>
            </div>
            <button
              @click="handleLogout"
              class="text-gray-400 hover:text-red-600 transition-colors"
              title="Déconnexion"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </aside>

    <!-- Main content -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- Header -->
      <header class="bg-white border-b border-gray-200 px-6 py-4">
        <div class="flex items-center justify-between">
          <h2 class="text-2xl font-semibold text-gray-800">{{ currentPageTitle }}</h2>
          <div class="flex items-center space-x-4">
            <!-- Indicateur temps réel -->
            <div class="flex items-center text-sm text-gray-600">
              <div class="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></div>
              Temps réel
            </div>
          </div>
        </div>
      </header>

      <!-- Page content -->
      <main class="flex-1 overflow-y-auto p-6">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

// Menu items avec icônes SVG inline
const menuItems = [
  {
    name: 'dashboard',
    route: 'dashboard',
    label: 'Tableau de bord',
    icon: 'IconDashboard'
  },
  {
    name: 'utilisateurs',
    route: 'utilisateurs',
    label: 'Utilisateurs',
    icon: 'IconUsers'
  },
  {
    name: 'sessions',
    route: 'sessions',
    label: 'Sessions',
    icon: 'IconClock'
  },
  {
    name: 'postes',
    route: 'postes',
    label: 'Postes',
    icon: 'IconComputer'
  },
  {
    name: 'logs',
    route: 'logs',
    label: 'Logs',
    icon: 'IconList'
  },
]

const currentPageTitle = computed(() => {
  const item = menuItems.find(m => m.route === route.name)
  return item?.label || 'Tableau de bord'
})

const userInitials = computed(() => {
  const username = authStore.user?.username || 'A'
  return username.substring(0, 2).toUpperCase()
})

function isActive(routeName) {
  return route.name === routeName
}

function handleLogout() {
  if (confirm('Voulez-vous vraiment vous déconnecter ?')) {
    authStore.logout()
    router.push({ name: 'login' })
  }
}
</script>

<script>
// Composants d'icônes simples
export const IconDashboard = {
  template: `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" /></svg>`
}

export const IconUsers = {
  template: `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>`
}

export const IconClock = {
  template: `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>`
}

export const IconComputer = {
  template: `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>`
}

export const IconList = {
  template: `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" /></svg>`
}
</script>
