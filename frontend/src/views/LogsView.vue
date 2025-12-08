<template>
  <MainLayout>
    <!-- Filtres -->
    <div class="card mb-6">
      <h3 class="text-lg font-semibold text-gray-900 mb-4">Filtres</h3>
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label class="label">Type d'action</label>
          <select v-model="filters.action" @change="applyFilters" class="input">
            <option value="">Tous</option>
            <option value="creation_utilisateur">Création utilisateur</option>
            <option value="generation_code">Génération code</option>
            <option value="demarrage_session">Démarrage session</option>
            <option value="ajout_temps">Ajout de temps</option>
            <option value="fermeture">Fermeture session</option>
            <option value="expiration">Expiration session</option>
            <option value="erreur">Erreur</option>
            <option value="warning">Avertissement</option>
          </select>
        </div>

        <div>
          <label class="label">Opérateur</label>
          <input
            v-model="filters.operateur"
            @input="applyFilters"
            type="text"
            class="input"
            placeholder="Nom de l'opérateur"
          />
        </div>

        <div>
          <label class="label">Période</label>
          <select v-model="period" @change="setPeriod" class="input">
            <option value="1h">Dernière heure</option>
            <option value="24h">Dernières 24h</option>
            <option value="7d">7 derniers jours</option>
            <option value="30d">30 derniers jours</option>
          </select>
        </div>

        <div class="flex items-end">
          <button @click="resetFilters" class="btn btn-secondary w-full">
            Réinitialiser
          </button>
        </div>
      </div>
    </div>

    <!-- Logs table -->
    <div class="card">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-semibold text-gray-900">
          Logs ({{ logs.length }})
        </h3>
        <div class="flex space-x-2">
          <button @click="loadLogs" class="btn btn-secondary">
            <svg class="w-4 h-4 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Actualiser
          </button>
        </div>
      </div>

      <div v-if="loading" class="text-center py-12">
        <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>

      <div v-else-if="logs.length === 0" class="text-center py-12 text-gray-500">
        Aucun log trouvé
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Date
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Action
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Opérateur
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Détails
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Session
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="log in logs" :key="log.id" class="hover:bg-gray-50">
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {{ formatDate(log.created_at) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span
                  class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full"
                  :class="getActionClass(log.action)"
                >
                  {{ log.action_display }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {{ log.operateur || '-' }}
              </td>
              <td class="px-6 py-4 text-sm text-gray-600">
                <div class="max-w-md truncate" :title="log.details">
                  {{ log.details }}
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm">
                <span
                  v-if="log.session_code"
                  class="font-mono text-primary-600 font-medium"
                >
                  {{ log.session_code }}
                </span>
                <span v-else class="text-gray-400">-</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div v-if="!loading && logs.length > 0" class="px-6 py-4 border-t border-gray-200">
        <div class="flex items-center justify-between">
          <p class="text-sm text-gray-700">
            Affichage de <span class="font-medium">{{ logs.length }}</span> logs
          </p>
        </div>
      </div>
    </div>
  </MainLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import MainLayout from '@/components/Layout/MainLayout.vue'
import { logsService } from '@/services/api'
import { logger } from '@/utils/logger'

const logs = ref([])
const loading = ref(true)
const period = ref('24h')

const filters = ref({
  action: '',
  operateur: '',
  date_debut: null,
  date_fin: null
})

async function loadLogs() {
  loading.value = true

  try {
    let response

    if (hasActiveFilters()) {
      // Recherche avec filtres
      const searchFilters = {}
      if (filters.value.action) searchFilters.action = filters.value.action
      if (filters.value.operateur) searchFilters.operateur = filters.value.operateur
      if (filters.value.date_debut) searchFilters.date_debut = filters.value.date_debut
      if (filters.value.date_fin) searchFilters.date_fin = filters.value.date_fin

      response = await logsService.search(searchFilters)
    } else {
      // Logs récents par défaut
      const hours = period.value === '1h' ? 1 : period.value === '24h' ? 24 : period.value === '7d' ? 168 : 720
      response = await logsService.getRecent(hours, 1000)
      logs.value = response.data.logs || response.data
    }

    if (response.data.logs) {
      logs.value = response.data.logs
    } else {
      logs.value = response.data
    }
  } catch (err) {
    logger.error('Erreur chargement logs:', err)
  } finally {
    loading.value = false
  }
}

function hasActiveFilters() {
  return filters.value.action || filters.value.operateur || filters.value.date_debut || filters.value.date_fin
}

function setPeriod() {
  // Calculer les dates selon la période
  const now = new Date()
  const hours = period.value === '1h' ? 1 : period.value === '24h' ? 24 : period.value === '7d' ? 168 : 720

  filters.value.date_fin = now.toISOString()
  filters.value.date_debut = new Date(now.getTime() - hours * 60 * 60 * 1000).toISOString()

  loadLogs()
}

function applyFilters() {
  loadLogs()
}

function resetFilters() {
  filters.value = {
    action: '',
    operateur: '',
    date_debut: null,
    date_fin: null
  }
  period.value = '24h'
  loadLogs()
}

function formatDate(dateString) {
  const date = new Date(dateString)
  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  }).format(date)
}

function getActionClass(action) {
  const classes = {
    'creation_utilisateur': 'bg-blue-100 text-blue-800',
    'generation_code': 'bg-blue-100 text-blue-800',
    'demarrage_session': 'bg-green-100 text-green-800',
    'ajout_temps': 'bg-yellow-100 text-yellow-800',
    'fermeture': 'bg-gray-100 text-gray-800',
    'expiration': 'bg-red-100 text-red-800',
    'erreur': 'bg-red-100 text-red-800',
    'warning': 'bg-orange-100 text-orange-800',
    'info': 'bg-blue-100 text-blue-800'
  }
  return classes[action] || 'bg-gray-100 text-gray-800'
}

onMounted(() => {
  setPeriod()
  // Rafraîchissement automatique toutes les 30 secondes
  setInterval(loadLogs, 30000)
})
</script>
