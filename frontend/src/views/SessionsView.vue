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

    <!-- Demandes de prolongation en attente -->
    <div v-if="pendingExtensions.length > 0" class="mb-6">
      <h2 class="text-lg font-semibold text-gray-900 mb-3 flex items-center">
        <span class="relative flex h-3 w-3 mr-2">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
          <span class="relative inline-flex rounded-full h-3 w-3 bg-amber-500"></span>
        </span>
        Demandes de prolongation ({{ pendingExtensions.length }})
      </h2>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="ext in pendingExtensions"
          :key="ext.id"
          class="card border-2 border-amber-200 bg-amber-50"
        >
          <div class="flex justify-between items-start mb-3">
            <div>
              <div class="text-lg font-mono font-bold text-amber-700">
                {{ ext.session_code }}
              </div>
              <div class="text-sm text-gray-600">
                {{ ext.utilisateur_nom }}
              </div>
              <div class="text-sm text-gray-500">
                {{ ext.poste_nom }}
              </div>
            </div>
            <div class="text-right">
              <div class="text-2xl font-bold text-amber-600">
                +{{ ext.minutes_requested }} min
              </div>
              <div class="text-xs text-gray-500">
                {{ formatTimeAgo(ext.created_at) }}
              </div>
            </div>
          </div>
          <div class="text-sm text-gray-600 mb-3">
            Temps restant actuel: <span class="font-medium">{{ formatTime(ext.temps_restant) }}</span>
          </div>
          <div class="flex space-x-2">
            <button
              @click="respondToExtension(ext.id, true)"
              class="flex-1 btn btn-primary text-sm"
              :disabled="respondingExtension === ext.id"
            >
              <svg class="w-4 h-4 mr-1 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
              Approuver
            </button>
            <button
              @click="respondToExtension(ext.id, false)"
              class="flex-1 btn btn-danger text-sm"
              :disabled="respondingExtension === ext.id"
            >
              <svg class="w-4 h-4 mr-1 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
              Refuser
            </button>
          </div>
        </div>
      </div>
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
                Temps restant
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Temps écoulé
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
                <div class="text-sm font-medium text-gray-900">
                  {{ session.utilisateur_nom }}
                  <span v-if="session.is_guest" class="ml-2 px-2 py-0.5 text-xs bg-purple-100 text-purple-800 rounded-full">
                    Invité
                  </span>
                </div>
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
                <div class="text-sm text-gray-900">
                  {{ formatTime(session.temps_ecoule || 0) }}
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
                  v-if="['active', 'en_attente', 'suspendue'].includes(session.statut)"
                  @click="addTime(session)"
                  class="text-blue-600 hover:text-blue-900"
                >
                  + Temps
                </button>
                <button
                  v-if="['active', 'en_attente', 'suspendue'].includes(session.statut)"
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
            <!-- Toggle Guest/Normal -->
            <div class="flex space-x-2 mb-4">
              <button
                type="button"
                @click="isGuestSession = false"
                class="flex-1 px-4 py-2 rounded-lg font-medium transition-colors"
                :class="!isGuestSession ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'"
              >
                Utilisateur enregistré
              </button>
              <button
                type="button"
                @click="isGuestSession = true"
                class="flex-1 px-4 py-2 rounded-lg font-medium transition-colors"
                :class="isGuestSession ? 'bg-purple-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'"
              >
                Session invité
              </button>
            </div>

            <!-- Sélection utilisateur (uniquement si pas guest) -->
            <div v-if="!isGuestSession">
              <label class="label">Utilisateur *</label>
              <select v-model="createForm.utilisateur" class="input" required>
                <option value="">Sélectionner un utilisateur</option>
                <option v-for="user in availableUsers.filter(u => u && u.id)" :key="user.id" :value="user.id">
                  {{ user.full_name || user.nom || 'Utilisateur' }}
                </option>
              </select>
            </div>

            <!-- Info guest -->
            <div v-else class="bg-purple-50 border border-purple-200 p-4 rounded-lg">
              <div class="flex items-center">
                <svg class="w-5 h-5 text-purple-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                <span class="text-sm text-purple-700 font-medium">Session invité anonyme</span>
              </div>
              <p class="text-xs text-purple-600 mt-2">
                Un identifiant unique sera généré automatiquement (ex: GUEST-ABC123)
              </p>
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
              <p v-if="guestIdentifier" class="text-sm text-purple-600 mb-2 text-center">
                Identifiant invité : <span class="font-mono font-bold">{{ guestIdentifier }}</span>
              </p>
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
import { sessionsService, utilisateursService, postesService, extensionRequestsService } from '@/services/api'
import { useToast } from '@/composables/useToast'
import { logger } from '@/utils/logger'

const { success, error: toastError } = useToast()

const sessions = ref([])
const loading = ref(true)
const filterStatus = ref('all')

const showCreateModal = ref(false)
const isGuestSession = ref(false)
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
const guestIdentifier = ref(null)

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

// Extension requests (demandes de prolongation)
const pendingExtensions = ref([])
const respondingExtension = ref(null)

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
    logger.error('Erreur chargement sessions:', err)
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
    // Handle both array and paginated response
    availableUsers.value = Array.isArray(users.data) ? users.data : (users.data?.results || [])
    availablePostes.value = Array.isArray(postes.data) ? postes.data : (postes.data?.results || [])
  } catch (err) {
    logger.error('Erreur chargement données:', err)
    availableUsers.value = []
    availablePostes.value = []
  }
}

function closeCreateModal() {
  showCreateModal.value = false
  isGuestSession.value = false
  guestIdentifier.value = null
  createForm.value = {
    utilisateur: '',
    poste: '',
    duree_minutes: 60,
    notes: ''
  }
}

async function handleCreateSession() {
  creating.value = true
  createError.value = null

  try {
    let response
    if (isGuestSession.value) {
      // Création d'une session invité
      response = await sessionsService.createGuest({
        poste: createForm.value.poste,
        duree_minutes: createForm.value.duree_minutes,
        notes: createForm.value.notes
      })
      createdCode.value = response.data.code_acces
      guestIdentifier.value = response.data.guest_identifier
      success(`Session invité créée (${response.data.guest_identifier})`)
    } else {
      // Création d'une session normale
      response = await sessionsService.create(createForm.value)
      createdCode.value = response.data.code_acces
      success('Session créée avec succès')
    }
    loadSessions()
  } catch (err) {
    createError.value = err.response?.data?.detail || err.response?.data?.poste?.[0] || 'Erreur lors de la création'
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
    logger.error(err)
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
    logger.error(err)
  } finally {
    showConfirmModal.value = false
    sessionToTerminate.value = null
  }
}

async function viewDetails(session) {
  // Charger les détails complets de la session
  showDetailModal.value = true
  detailSession.value = null  // Afficher le loading

  try {
    const response = await sessionsService.getById(session.id)
    detailSession.value = response.data
  } catch (err) {
    logger.error('Erreur chargement détails session:', err)
    toastError('Erreur lors du chargement des détails')
    showDetailModal.value = false
  }
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

// Extension requests functions
async function loadPendingExtensions() {
  try {
    const response = await extensionRequestsService.getPending()
    pendingExtensions.value = Array.isArray(response.data) ? response.data : (response.data.results || [])
  } catch (err) {
    logger.error('Erreur chargement demandes prolongation:', err)
  }
}

async function respondToExtension(id, approve) {
  respondingExtension.value = id
  try {
    await extensionRequestsService.respond(id, approve)
    if (approve) {
      success('Prolongation approuvée')
    } else {
      success('Prolongation refusée')
    }
    // Recharger les listes
    await Promise.all([loadPendingExtensions(), loadSessions()])
  } catch (err) {
    toastError('Erreur lors de la réponse')
    logger.error(err)
  } finally {
    respondingExtension.value = null
  }
}

function formatTimeAgo(dateString) {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now - date
  const diffSecs = Math.floor(diffMs / 1000)
  const diffMins = Math.floor(diffSecs / 60)
  const diffHours = Math.floor(diffMins / 60)

  if (diffSecs < 60) {
    return 'à l\'instant'
  } else if (diffMins < 60) {
    return `il y a ${diffMins} min`
  } else if (diffHours < 24) {
    return `il y a ${diffHours}h`
  } else {
    return date.toLocaleDateString('fr-FR')
  }
}

onMounted(() => {
  loadSessions()
  loadPendingExtensions()
  // Rafraîchissement automatique toutes les 5 secondes
  setInterval(() => {
    loadSessions()
    loadPendingExtensions()
  }, 5000)
})
</script>
