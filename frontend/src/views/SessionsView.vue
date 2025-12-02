<template>
  <MainLayout>
    <!-- Actions bar -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex space-x-4">
        <button
          @click="filterStatus = 'all'"
          class="btn"
          :class="filterStatus === 'all' ? 'btn-primary' : 'btn-secondary'"
        >
          Toutes
        </button>
        <button
          @click="filterStatus = 'active'"
          class="btn"
          :class="filterStatus === 'active' ? 'btn-primary' : 'btn-secondary'"
        >
          Actives ({{ sessionsActives.length }})
        </button>
        <button
          @click="filterStatus = 'en_attente'"
          class="btn"
          :class="filterStatus === 'en_attente' ? 'btn-primary' : 'btn-secondary'"
        >
          En attente
        </button>
      </div>
      <button @click="openCreateModal" class="btn btn-primary">
        <svg class="w-5 h-5 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        Nouvelle session
      </button>
    </div>

    <!-- Sessions list -->
    <div class="card">
      <div v-if="loading" class="text-center py-12">
        <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>

      <div v-else-if="filteredSessions.length === 0" class="text-center py-12 text-gray-500">
        Aucune session trouvée
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Code
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Utilisateur
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Poste
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Temps
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Statut
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="session in filteredSessions" :key="session.id" class="hover:bg-gray-50">
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-lg font-mono font-bold text-primary-600">
                  {{ session.code_acces }}
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium text-gray-900">{{ session.utilisateur_nom }}</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-gray-900">{{ session.poste_nom }}</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium" :class="getTimeColor(session.temps_restant)">
                  {{ formatTime(session.temps_restant) }}
                </div>
                <div class="text-xs text-gray-500">
                  {{ session.pourcentage_utilise }}% utilisé
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span
                  class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full"
                  :class="getStatusClass(session.statut)"
                >
                  {{ getStatusLabel(session.statut) }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                <button
                  v-if="session.statut === 'active'"
                  @click="addTime(session)"
                  class="text-blue-600 hover:text-blue-900"
                >
                  + Temps
                </button>
                <button
                  v-if="session.statut === 'active'"
                  @click="terminateSession(session)"
                  class="text-red-600 hover:text-red-900"
                >
                  Terminer
                </button>
                <button
                  @click="viewDetails(session)"
                  class="text-primary-600 hover:text-primary-900"
                >
                  Détails
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modal Create Session -->
    <div
      v-if="showCreateModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="closeCreateModal"
    >
      <div class="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4">
        <div class="p-6">
          <div class="flex items-center justify-between mb-6">
            <h3 class="text-2xl font-semibold text-gray-900">Nouvelle session</h3>
            <button @click="closeCreateModal" class="text-gray-400 hover:text-gray-600">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <form @submit.prevent="handleCreateSession" class="space-y-4">
            <div>
              <label class="label">Utilisateur *</label>
              <select v-model="createForm.utilisateur" class="input" required>
                <option value="">Sélectionner un utilisateur</option>
                <option v-for="user in availableUsers" :key="user.id" :value="user.id">
                  {{ user.full_name }}
                </option>
              </select>
            </div>

            <div>
              <label class="label">Poste *</label>
              <select v-model="createForm.poste" class="input" required>
                <option value="">Sélectionner un poste</option>
                <option v-for="poste in availablePostes" :key="poste.id" :value="poste.id">
                  {{ poste.nom }} ({{ poste.emplacement || 'Sans emplacement' }})
                </option>
              </select>
            </div>

            <div>
              <label class="label">Durée (minutes) *</label>
              <input
                v-model.number="createForm.duree_minutes"
                type="number"
                min="1"
                max="240"
                class="input"
                required
              />
              <p class="text-xs text-gray-500 mt-1">Max 240 minutes (4 heures)</p>
            </div>

            <div>
              <label class="label">Notes</label>
              <textarea v-model="createForm.notes" class="input" rows="3"></textarea>
            </div>

            <div v-if="createError" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              {{ createError }}
            </div>

            <div v-if="createdCode" class="bg-green-50 border border-green-200 p-4 rounded-lg">
              <p class="text-sm text-green-700 mb-2">Session créée avec succès !</p>
              <p class="text-2xl font-mono font-bold text-green-900 text-center">
                {{ createdCode }}
              </p>
              <p class="text-xs text-green-600 mt-2 text-center">
                Communiquez ce code à l'utilisateur
              </p>
            </div>

            <div class="flex justify-end space-x-3 pt-4 border-t">
              <button type="button" @click="closeCreateModal" class="btn btn-secondary">
                {{ createdCode ? 'Fermer' : 'Annuler' }}
              </button>
              <button
                v-if="!createdCode"
                type="submit"
                class="btn btn-primary"
                :disabled="creating"
              >
                {{ creating ? 'Création...' : 'Créer la session' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Modal Add Time -->
    <div
      v-if="showAddTimeModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="showAddTimeModal = false"
    >
      <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div class="p-6">
          <h3 class="text-xl font-semibold text-gray-900 mb-4">Ajouter du temps</h3>
          <form @submit.prevent="handleAddTime" class="space-y-4">
            <div>
              <label class="label">Minutes à ajouter</label>
              <div class="grid grid-cols-3 gap-2 mb-2">
                <button
                  type="button"
                  @click="addTimeMinutes = 15"
                  class="btn btn-secondary"
                >
                  15 min
                </button>
                <button
                  type="button"
                  @click="addTimeMinutes = 30"
                  class="btn btn-secondary"
                >
                  30 min
                </button>
                <button
                  type="button"
                  @click="addTimeMinutes = 60"
                  class="btn btn-secondary"
                >
                  60 min
                </button>
              </div>
              <input
                v-model.number="addTimeMinutes"
                type="number"
                min="1"
                max="120"
                class="input"
                required
              />
            </div>

            <div class="flex justify-end space-x-3">
              <button type="button" @click="showAddTimeModal = false" class="btn btn-secondary">
                Annuler
              </button>
              <button type="submit" class="btn btn-primary">
                Ajouter
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Session Detail Modal -->
    <SessionDetailModal
      v-model="showDetailModal"
      :session="detailSession"
      @add-time="handleDetailAddTime"
      @terminate="handleDetailTerminate"
    />

    <!-- Confirm Terminate Modal -->
    <ConfirmModal
      v-model="showConfirmModal"
      :title="confirmModalConfig.title"
      :message="confirmModalConfig.message"
      :type="confirmModalConfig.type"
      :confirm-text="confirmModalConfig.confirmText"
      :cancel-text="confirmModalConfig.cancelText"
      @confirm="confirmTerminateSession"
    />
  </MainLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import MainLayout from '@/components/Layout/MainLayout.vue'
import ConfirmModal from '@/components/common/ConfirmModal.vue'
import SessionDetailModal from '@/components/sessions/SessionDetailModal.vue'
import { sessionsService, utilisateursService, postesService } from '@/services/api'
import { useToast } from '@/composables/useToast'

const { success, error: toastError } = useToast()

const sessions = ref([])
const loading = ref(true)
const filterStatus = ref('all')

const showCreateModal = ref(false)
const createForm = ref({
  utilisateur: '',
  poste: '',
  duree_minutes: 60,
  notes: ''
})
// L'opérateur est maintenant récupéré côté backend depuis request.user
const availableUsers = ref([])
const availablePostes = ref([])
const creating = ref(false)
const createError = ref(null)
const createdCode = ref(null)

const showAddTimeModal = ref(false)
const selectedSession = ref(null)
const addTimeMinutes = ref(15)

// Detail Modal
const showDetailModal = ref(false)
const detailSession = ref(null)

// Confirm Modal
const showConfirmModal = ref(false)
const confirmModalConfig = ref({
  title: '',
  message: '',
  type: 'warning',
  confirmText: 'Confirmer',
  cancelText: 'Annuler'
})
const sessionToTerminate = ref(null)

const sessionsActives = computed(() => {
  return sessions.value.filter(s => s.statut === 'active')
})

const filteredSessions = computed(() => {
  if (filterStatus.value === 'all') {
    return sessions.value
  }
  return sessions.value.filter(s => s.statut === filterStatus.value)
})

async function loadSessions() {
  loading.value = true
  try {
    const response = await sessionsService.getAll()
    // Handle both array and paginated response
    sessions.value = Array.isArray(response.data) ? response.data : (response.data.results || [])
  } catch (err) {
    console.error('Erreur chargement sessions:', err)
  } finally {
    loading.value = false
  }
}

async function openCreateModal() {
  showCreateModal.value = true
  createdCode.value = null
  createError.value = null

  try {
    const [users, postes] = await Promise.all([
      utilisateursService.getAll(),
      postesService.getDisponibles()
    ])
    availableUsers.value = users.data
    availablePostes.value = postes.data
  } catch (err) {
    console.error('Erreur chargement données:', err)
  }
}

function closeCreateModal() {
  showCreateModal.value = false
  createForm.value = {
    utilisateur: '',
    poste: '',
    duree_minutes: 60,
    operateur: 'admin',
    notes: ''
  }
}

async function handleCreateSession() {
  creating.value = true
  createError.value = null

  try {
    const response = await sessionsService.create(createForm.value)
    createdCode.value = response.data.code_acces
    success('Session créée avec succès')
    loadSessions()
  } catch (err) {
    createError.value = err.response?.data?.detail || 'Erreur lors de la création'
    toastError(createError.value)
  } finally {
    creating.value = false
  }
}

function addTime(session) {
  selectedSession.value = session
  addTimeMinutes.value = 15
  showAddTimeModal.value = true
}

async function handleAddTime() {
  try {
    await sessionsService.addTime(selectedSession.value.id, {
      minutes: addTimeMinutes.value
    })
    success(`${addTimeMinutes.value} minutes ajoutées à la session`)
    showAddTimeModal.value = false
    loadSessions()
  } catch (err) {
    toastError('Erreur lors de l\'ajout de temps')
    console.error(err)
  }
}

function terminateSession(session) {
  sessionToTerminate.value = session
  confirmModalConfig.value = {
    title: 'Terminer la session',
    message: `Êtes-vous sûr de vouloir terminer la session "${session.code_acces}" ? L'utilisateur sera déconnecté.`,
    type: 'warning',
    confirmText: 'Terminer',
    cancelText: 'Annuler'
  }
  showConfirmModal.value = true
}

async function confirmTerminateSession() {
  if (!sessionToTerminate.value) return

  try {
    await sessionsService.terminate(sessionToTerminate.value.id, {
      raison: 'fermeture_normale'
    })
    success(`Session "${sessionToTerminate.value.code_acces}" terminée`)
    loadSessions()
  } catch (err) {
    toastError('Erreur lors de la terminaison de la session')
    console.error(err)
  } finally {
    showConfirmModal.value = false
    sessionToTerminate.value = null
  }
}

function viewDetails(session) {
  detailSession.value = session
  showDetailModal.value = true
}

function handleDetailAddTime(session) {
  showDetailModal.value = false
  addTime(session)
}

function handleDetailTerminate(session) {
  showDetailModal.value = false
  terminateSession(session)
}

function formatTime(seconds) {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function getTimeColor(seconds) {
  if (seconds <= 300) return 'text-red-600'
  if (seconds <= 600) return 'text-orange-600'
  return 'text-green-600'
}

function getStatusClass(statut) {
  const classes = {
    'en_attente': 'bg-yellow-100 text-yellow-800',
    'active': 'bg-green-100 text-green-800',
    'terminee': 'bg-gray-100 text-gray-800',
    'suspendue': 'bg-orange-100 text-orange-800',
    'expiree': 'bg-red-100 text-red-800'
  }
  return classes[statut] || 'bg-gray-100 text-gray-800'
}

function getStatusLabel(statut) {
  const labels = {
    'en_attente': 'En attente',
    'active': 'Active',
    'terminee': 'Terminée',
    'suspendue': 'Suspendue',
    'expiree': 'Expirée'
  }
  return labels[statut] || statut
}

onMounted(() => {
  loadSessions()
  // Rafraîchissement automatique toutes les 5 secondes
  setInterval(loadSessions, 5000)
})
</script>
