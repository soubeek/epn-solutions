<template>
  <MainLayout>
    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      <!-- Utilisateurs -->
      <div class="card">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-gray-600">Utilisateurs</p>
            <p class="text-3xl font-bold text-gray-900 mt-2">
              {{ stats.utilisateurs.total }}
            </p>
            <p class="text-sm text-green-600 mt-1">
              {{ stats.utilisateurs.actifs_30_jours }} actifs (30j)
            </p>
          </div>
          <div class="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
            <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          </div>
        </div>
      </div>

      <!-- Postes -->
      <div class="card">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-gray-600">Postes</p>
            <p class="text-3xl font-bold text-gray-900 mt-2">
              {{ stats.postes.total }}
            </p>
            <p class="text-sm mt-1">
              <span class="text-green-600">{{ stats.postes.en_ligne }} en ligne</span>
            </p>
          </div>
          <div class="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
            <svg class="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
        </div>
      </div>

      <!-- Sessions Actives -->
      <div class="card">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-gray-600">Sessions Actives</p>
            <p class="text-3xl font-bold text-gray-900 mt-2">
              {{ sessionStats.actives || 0 }}
            </p>
            <p class="text-sm text-gray-500 mt-1">
              {{ sessionStats.sessions_aujourdhui || 0 }} aujourd'hui
            </p>
          </div>
          <div class="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
            <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </div>
      </div>

      <!-- Durée Moyenne -->
      <div class="card">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-gray-600">Durée Moyenne</p>
            <p class="text-3xl font-bold text-gray-900 mt-2">
              {{ sessionStats.duree_moyenne_minutes || 0 }} min
            </p>
            <p class="text-sm text-gray-500 mt-1">Par session</p>
          </div>
          <div class="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
            <svg class="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
          </div>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Sessions Actives -->
      <div class="card">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-gray-900">Sessions Actives</h3>
          <router-link :to="{ name: 'sessions' }" class="text-sm text-primary-600 hover:text-primary-700">
            Voir tout →
          </router-link>
        </div>

        <div v-if="loading" class="text-center py-8">
          <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>

        <div v-else-if="sessionsActives.length === 0" class="text-center py-8 text-gray-500">
          Aucune session active
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="session in sessionsActives.slice(0, 5)"
            :key="session.id"
            class="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
          >
            <div class="flex-1">
              <p class="font-medium text-gray-900">{{ session.utilisateur_nom }}</p>
              <p class="text-sm text-gray-500">{{ session.poste_nom }}</p>
            </div>
            <div class="text-right">
              <p class="text-sm font-medium text-gray-900">{{ session.minutes_restantes }} min</p>
              <span class="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">
                Active
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Postes Disponibles -->
      <div class="card">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-gray-900">Postes Disponibles</h3>
          <router-link :to="{ name: 'postes' }" class="text-sm text-primary-600 hover:text-primary-700">
            Voir tout →
          </router-link>
        </div>

        <div v-if="loading" class="text-center py-8">
          <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>

        <div v-else-if="postesDisponibles.length === 0" class="text-center py-8 text-gray-500">
          Aucun poste disponible
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="poste in postesDisponibles.slice(0, 5)"
            :key="poste.id"
            class="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
          >
            <div class="flex-1">
              <p class="font-medium text-gray-900">{{ poste.nom }}</p>
              <p class="text-sm text-gray-500">{{ poste.emplacement || 'Sans emplacement' }}</p>
            </div>
            <div class="flex items-center space-x-2">
              <div class="w-2 h-2 bg-green-500 rounded-full"></div>
              <span class="text-sm text-gray-600">Disponible</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </MainLayout>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import MainLayout from '@/components/Layout/MainLayout.vue'
import { useDashboardStore } from '@/stores/dashboard'
import { sessionsService, postesService } from '@/services/api'
import { useDashboardWebSocket } from '@/composables/useWebSocket'

const dashboardStore = useDashboardStore()
const { stats: wsStats, isConnected, error: wsError, connect, disconnect } = useDashboardWebSocket()

const sessionsActives = ref([])
const postesDisponibles = ref([])
const loading = ref(true)
const useWebSocket = ref(true) // Toggle pour activer/désactiver WebSocket
let refreshInterval = null

const stats = computed(() => wsStats.value || dashboardStore.stats)
const sessionStats = computed(() => stats.value?.sessions || dashboardStore.stats.sessions)

async function loadData() {
  loading.value = true

  try {
    // Charger les stats via HTTP (fallback si WebSocket désactivé)
    if (!useWebSocket.value) {
      await dashboardStore.fetchStats()
    }

    const [sessions, postes] = await Promise.all([
      sessionsService.getActives(),
      postesService.getDisponibles()
    ])

    sessionsActives.value = sessions.data
    postesDisponibles.value = postes.data
  } catch (error) {
    console.error('Erreur chargement dashboard:', error)
  } finally {
    loading.value = false
  }
}

// Observer les changements de stats WebSocket
watch(wsStats, (newStats) => {
  if (newStats) {
    // Mettre à jour le store avec les stats WebSocket
    dashboardStore.stats = {
      utilisateurs: newStats.utilisateurs || {},
      sessions: newStats.sessions || {},
      postes: newStats.postes || {}
    }
    loading.value = false
  }
})

// Observer l'état de connexion WebSocket
watch(isConnected, (connected) => {
  if (!connected && wsError.value) {
    console.warn('WebSocket disconnected, falling back to HTTP polling')
    // Fallback vers HTTP polling si WebSocket échoue
    if (!refreshInterval) {
      refreshInterval = setInterval(loadData, 30000)
    }
  } else if (connected) {
    // Arrêter le polling HTTP si WebSocket connecté
    if (refreshInterval) {
      clearInterval(refreshInterval)
      refreshInterval = null
    }
  }
})

onMounted(() => {
  // Charger les données initiales
  loadData()

  // Tenter de se connecter au WebSocket
  if (useWebSocket.value) {
    connect()
  } else {
    // Si WebSocket désactivé, utiliser le polling HTTP
    refreshInterval = setInterval(loadData, 30000)
  }
})

onUnmounted(() => {
  // Nettoyer la connexion WebSocket
  disconnect()

  // Nettoyer l'intervalle HTTP
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>
