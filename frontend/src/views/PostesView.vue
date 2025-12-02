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
          Tous
        </button>
        <button
          @click="filterStatus = 'disponible'"
          class="btn"
          :class="filterStatus === 'disponible' ? 'btn-primary' : 'btn-secondary'"
        >
          Disponibles
        </button>
        <button
          @click="filterStatus = 'occupe'"
          class="btn"
          :class="filterStatus === 'occupe' ? 'btn-primary' : 'btn-secondary'"
        >
          Occupés
        </button>
      </div>
      <button @click="openCreateModal" class="btn btn-primary">
        <svg class="w-5 h-5 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        Nouveau poste
      </button>
    </div>

    <!-- Postes grid -->
    <div v-if="loading" class="text-center py-12">
      <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
    </div>

    <div v-else-if="filteredPostes.length === 0" class="card text-center py-12 text-gray-500">
      Aucun poste trouvé
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div
        v-for="poste in filteredPostes"
        :key="poste.id"
        class="card hover:shadow-md transition-shadow"
      >
        <!-- Header -->
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center">
            <div
              class="w-3 h-3 rounded-full mr-2"
              :class="poste.est_en_ligne ? 'bg-green-500 animate-pulse' : 'bg-gray-300'"
            ></div>
            <h3 class="text-lg font-semibold text-gray-900">{{ poste.nom }}</h3>
          </div>
          <span
            class="px-2 py-1 text-xs font-semibold rounded-full"
            :class="getStatusClass(poste.statut)"
          >
            {{ getStatusLabel(poste.statut) }}
          </span>
        </div>

        <!-- Info -->
        <div class="space-y-2 mb-4">
          <div class="flex items-center text-sm text-gray-600">
            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            {{ poste.emplacement || 'Sans emplacement' }}
          </div>

          <div class="flex items-center text-sm text-gray-600">
            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
            </svg>
            {{ poste.ip_address }}
          </div>

          <div v-if="poste.session_active_code" class="mt-3 p-2 bg-green-50 rounded border border-green-200">
            <p class="text-xs text-green-700 mb-1">Session active</p>
            <p class="text-sm font-mono font-bold text-green-900">{{ poste.session_active_code }}</p>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex space-x-2 pt-4 border-t border-gray-200">
          <button
            v-if="poste.statut !== 'disponible'"
            @click="marquerDisponible(poste)"
            class="flex-1 btn btn-secondary text-sm"
          >
            Disponible
          </button>
          <button
            v-if="poste.statut !== 'maintenance'"
            @click="marquerMaintenance(poste)"
            class="flex-1 btn btn-secondary text-sm"
          >
            Maintenance
          </button>
          <button
            @click="editPoste(poste)"
            class="btn btn-secondary text-sm"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Modal Create/Edit -->
    <div
      v-if="showModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="closeModal"
    >
      <div class="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4">
        <div class="p-6">
          <div class="flex items-center justify-between mb-6">
            <h3 class="text-2xl font-semibold text-gray-900">
              {{ isEditing ? 'Modifier le poste' : 'Nouveau poste' }}
            </h3>
            <button @click="closeModal" class="text-gray-400 hover:text-gray-600">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <form @submit.prevent="handleSubmit" class="space-y-4">
            <div>
              <label class="label">Nom du poste *</label>
              <input
                v-model="formData.nom"
                type="text"
                class="input"
                placeholder="Ex: Poste-01"
                required
              />
            </div>

            <div>
              <label class="label">Adresse IP *</label>
              <input
                v-model="formData.ip_address"
                type="text"
                class="input"
                placeholder="Ex: 192.168.1.100"
                pattern="^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
                required
              />
            </div>

            <div>
              <label class="label">Adresse MAC</label>
              <input
                v-model="formData.mac_address"
                type="text"
                class="input"
                placeholder="Ex: AA:BB:CC:DD:EE:FF"
                pattern="^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$"
              />
            </div>

            <div>
              <label class="label">Emplacement</label>
              <input
                v-model="formData.emplacement"
                type="text"
                class="input"
                placeholder="Ex: Salle principale"
              />
            </div>

            <div>
              <label class="label">Statut</label>
              <select v-model="formData.statut" class="input">
                <option value="disponible">Disponible</option>
                <option value="maintenance">Maintenance</option>
                <option value="hors_ligne">Hors ligne</option>
              </select>
            </div>

            <div>
              <label class="label">Notes</label>
              <textarea v-model="formData.notes" class="input" rows="3"></textarea>
            </div>

            <div v-if="submitError" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              {{ submitError }}
            </div>

            <div class="flex justify-end space-x-3 pt-4 border-t">
              <button type="button" @click="closeModal" class="btn btn-secondary">
                Annuler
              </button>
              <button type="submit" class="btn btn-primary" :disabled="submitting">
                {{ submitting ? 'Enregistrement...' : 'Enregistrer' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </MainLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import MainLayout from '@/components/Layout/MainLayout.vue'
import { postesService } from '@/services/api'
import { useToast } from '@/composables/useToast'

const { success, error: toastError } = useToast()

const postes = ref([])
const loading = ref(true)
const filterStatus = ref('all')

const showModal = ref(false)
const isEditing = ref(false)
const currentPoste = ref(null)
const formData = ref(getEmptyForm())
const submitting = ref(false)
const submitError = ref(null)

function getEmptyForm() {
  return {
    nom: '',
    ip_address: '',
    mac_address: '',
    emplacement: '',
    statut: 'disponible',
    notes: ''
  }
}

const filteredPostes = computed(() => {
  if (filterStatus.value === 'all') {
    return postes.value
  }
  return postes.value.filter(p => p.statut === filterStatus.value)
})

async function loadPostes() {
  loading.value = true
  try {
    const response = await postesService.getAll()
    // Handle both array and paginated response
    postes.value = Array.isArray(response.data) ? response.data : (response.data.results || [])
  } catch (err) {
    console.error('Erreur chargement postes:', err)
  } finally {
    loading.value = false
  }
}

function openCreateModal() {
  isEditing.value = false
  currentPoste.value = null
  formData.value = getEmptyForm()
  showModal.value = true
}

function editPoste(poste) {
  isEditing.value = true
  currentPoste.value = poste
  formData.value = { ...poste }
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  submitError.value = null
}

async function handleSubmit() {
  submitting.value = true
  submitError.value = null

  try {
    if (isEditing.value) {
      await postesService.update(currentPoste.value.id, formData.value)
      success('Poste modifié avec succès')
    } else {
      await postesService.create(formData.value)
      success('Poste créé avec succès')
    }

    closeModal()
    loadPostes()
  } catch (err) {
    submitError.value = err.response?.data?.detail || 'Erreur lors de l\'enregistrement'
    toastError(submitError.value)
    console.error(err)
  } finally {
    submitting.value = false
  }
}

async function marquerDisponible(poste) {
  try {
    await postesService.marquerDisponible(poste.id)
    success(`Le poste "${poste.nom}" est maintenant disponible`)
    loadPostes()
  } catch (err) {
    toastError('Erreur lors du changement de statut')
    console.error(err)
  }
}

async function marquerMaintenance(poste) {
  try {
    await postesService.marquerMaintenance(poste.id)
    success(`Le poste "${poste.nom}" est en maintenance`)
    loadPostes()
  } catch (err) {
    toastError('Erreur lors du changement de statut')
    console.error(err)
  }
}

function getStatusClass(statut) {
  const classes = {
    'disponible': 'bg-green-100 text-green-800',
    'occupe': 'bg-blue-100 text-blue-800',
    'reserve': 'bg-yellow-100 text-yellow-800',
    'hors_ligne': 'bg-gray-100 text-gray-800',
    'maintenance': 'bg-orange-100 text-orange-800'
  }
  return classes[statut] || 'bg-gray-100 text-gray-800'
}

function getStatusLabel(statut) {
  const labels = {
    'disponible': 'Disponible',
    'occupe': 'Occupé',
    'reserve': 'Réservé',
    'hors_ligne': 'Hors ligne',
    'maintenance': 'Maintenance'
  }
  return labels[statut] || statut
}

onMounted(() => {
  loadPostes()
  // Rafraîchissement automatique toutes les 10 secondes
  setInterval(loadPostes, 10000)
})
</script>
