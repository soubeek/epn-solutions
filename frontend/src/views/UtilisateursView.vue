<template>
  <MainLayout>
    <!-- Actions bar -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex-1 max-w-lg">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Rechercher un utilisateur..."
          class="input"
          @input="handleSearch"
        />
      </div>
      <button @click="openCreateModal" class="btn btn-primary">
        <svg class="w-5 h-5 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        Nouvel utilisateur
      </button>
    </div>

    <!-- Utilisateurs list -->
    <div class="card">
      <div v-if="loading" class="text-center py-12">
        <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>

      <div v-else-if="error" class="text-center py-12 text-red-600">
        {{ error }}
      </div>

      <div v-else-if="utilisateurs.length === 0" class="text-center py-12 text-gray-500">
        Aucun utilisateur trouvé
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Utilisateur
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Contact
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                RGPD
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Sessions
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="user in utilisateurs" :key="user.id" class="hover:bg-gray-50">
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                  <div class="flex-shrink-0 h-10 w-10">
                    <img
                      v-if="user.photo"
                      :src="user.photo"
                      :alt="user.full_name"
                      class="h-10 w-10 rounded-full object-cover"
                    />
                    <div
                      v-else
                      class="h-10 w-10 rounded-full bg-primary-100 flex items-center justify-center"
                    >
                      <span class="text-primary-600 font-medium">
                        {{ getUserInitials(user.full_name) }}
                      </span>
                    </div>
                  </div>
                  <div class="ml-4">
                    <div class="text-sm font-medium text-gray-900">{{ user.full_name }}</div>
                    <div class="text-sm text-gray-500">ID: {{ user.carte_identite || 'N/A' }}</div>
                  </div>
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-gray-900">{{ user.email || '-' }}</div>
                <div class="text-sm text-gray-500">{{ user.telephone || '-' }}</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span
                  class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full"
                  :class="user.consentement_rgpd
                    ? 'bg-green-100 text-green-800'
                    : 'bg-red-100 text-red-800'"
                >
                  {{ user.consentement_rgpd ? 'Accepté' : 'Refusé' }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {{ user.sessions_count || 0 }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                <button
                  @click="viewUser(user)"
                  class="text-primary-600 hover:text-primary-900"
                >
                  Voir
                </button>
                <button
                  @click="editUser(user)"
                  class="text-blue-600 hover:text-blue-900"
                >
                  Modifier
                </button>
                <button
                  @click="deleteUser(user)"
                  class="text-red-600 hover:text-red-900"
                >
                  Supprimer
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div v-if="!loading && utilisateurs.length > 0" class="px-6 py-4 border-t border-gray-200">
        <div class="flex items-center justify-between">
          <p class="text-sm text-gray-700">
            Affichage de <span class="font-medium">{{ utilisateurs.length }}</span> utilisateurs
          </p>
          <div class="flex space-x-2">
            <button class="btn btn-secondary" disabled>Précédent</button>
            <button class="btn btn-secondary" disabled>Suivant</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal Create/Edit -->
    <div
      v-if="showModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="closeModal"
    >
      <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div class="p-6">
          <div class="flex items-center justify-between mb-6">
            <h3 class="text-2xl font-semibold text-gray-900">
              {{ isEditing ? 'Modifier l\'utilisateur' : 'Nouvel utilisateur' }}
            </h3>
            <button @click="closeModal" class="text-gray-400 hover:text-gray-600">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <form @submit.prevent="handleSubmit" class="space-y-4">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="label">Nom *</label>
                <input v-model="formData.nom" type="text" class="input" required />
              </div>
              <div>
                <label class="label">Prénom *</label>
                <input v-model="formData.prenom" type="text" class="input" required />
              </div>
            </div>

            <div>
              <label class="label">Email</label>
              <input v-model="formData.email" type="email" class="input" />
            </div>

            <div>
              <label class="label">Téléphone</label>
              <input v-model="formData.telephone" type="tel" class="input" />
            </div>

            <div>
              <label class="label">Carte d'identité</label>
              <input v-model="formData.carte_identite" type="text" class="input" />
            </div>

            <div>
              <label class="label">Adresse</label>
              <textarea v-model="formData.adresse" class="input" rows="2"></textarea>
            </div>

            <div>
              <label class="label">Date de naissance</label>
              <input v-model="formData.date_naissance" type="date" class="input" />
            </div>

            <div>
              <label class="label">Photo</label>
              <input
                @change="handlePhotoChange"
                type="file"
                accept="image/jpeg,image/png"
                class="input"
              />
              <p class="text-xs text-gray-500 mt-1">Max 5MB - JPEG ou PNG</p>
            </div>

            <div class="flex items-center">
              <input
                v-model="formData.consentement_rgpd"
                type="checkbox"
                class="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
              />
              <label class="ml-2 text-sm text-gray-700">
                Consentement RGPD (obligatoire) *
              </label>
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

    <!-- Confirm Delete Modal -->
    <ConfirmModal
      v-model="showConfirmModal"
      :title="confirmModalConfig.title"
      :message="confirmModalConfig.message"
      :type="confirmModalConfig.type"
      :confirm-text="confirmModalConfig.confirmText"
      :cancel-text="confirmModalConfig.cancelText"
      @confirm="confirmDeleteUser"
    />

    <!-- User Detail Modal -->
    <UserDetailModal
      v-model="showDetailModal"
      :user="selectedUser"
      @edit="editUser"
    />
  </MainLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import MainLayout from '@/components/Layout/MainLayout.vue'
import ConfirmModal from '@/components/common/ConfirmModal.vue'
import UserDetailModal from '@/components/utilisateurs/UserDetailModal.vue'
import { utilisateursService } from '@/services/api'
import { useToast } from '@/composables/useToast'

const { success, error: toastError } = useToast()

const utilisateurs = ref([])
const loading = ref(true)
const error = ref(null)
const searchQuery = ref('')

const showModal = ref(false)
const isEditing = ref(false)
const currentUser = ref(null)
const formData = ref(getEmptyForm())
const photoFile = ref(null)
const submitting = ref(false)
const submitError = ref(null)

// Confirm Modal
const showConfirmModal = ref(false)
const confirmModalConfig = ref({
  title: '',
  message: '',
  type: 'danger',
  confirmText: 'Supprimer',
  cancelText: 'Annuler'
})
const userToDelete = ref(null)

// Detail Modal
const showDetailModal = ref(false)
const selectedUser = ref(null)

function getEmptyForm() {
  return {
    nom: '',
    prenom: '',
    email: '',
    telephone: '',
    carte_identite: '',
    adresse: '',
    date_naissance: '',
    consentement_rgpd: true,
    notes: ''
  }
}

async function loadUtilisateurs() {
  loading.value = true
  error.value = null

  try {
    const response = await utilisateursService.getAll({ search: searchQuery.value })
    // Handle both array and paginated response
    utilisateurs.value = Array.isArray(response.data) ? response.data : (response.data.results || [])
  } catch (err) {
    error.value = 'Erreur lors du chargement des utilisateurs'
    console.error(err)
  } finally {
    loading.value = false
  }
}

// Debounce pour la recherche
let searchTimeout = null
function handleSearch() {
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }
  searchTimeout = setTimeout(() => {
    loadUtilisateurs()
  }, 300) // 300ms debounce
}

function openCreateModal() {
  isEditing.value = false
  currentUser.value = null
  formData.value = getEmptyForm()
  photoFile.value = null
  showModal.value = true
}

function editUser(user) {
  isEditing.value = true
  currentUser.value = user
  formData.value = { ...user }
  photoFile.value = null
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  submitError.value = null
}

function handlePhotoChange(event) {
  const file = event.target.files[0]
  if (file) {
    photoFile.value = file
  }
}

async function handleSubmit() {
  submitting.value = true
  submitError.value = null

  try {
    const data = new FormData()

    // Ajouter tous les champs
    Object.keys(formData.value).forEach(key => {
      if (formData.value[key] !== null && formData.value[key] !== '') {
        data.append(key, formData.value[key])
      }
    })

    // Ajouter la photo si présente
    if (photoFile.value) {
      data.append('photo', photoFile.value)
    }

    // L'opérateur est maintenant récupéré côté backend depuis request.user

    if (isEditing.value) {
      await utilisateursService.update(currentUser.value.id, data)
      success('Utilisateur modifié avec succès')
    } else {
      await utilisateursService.create(data)
      success('Utilisateur créé avec succès')
    }

    closeModal()
    loadUtilisateurs()
  } catch (err) {
    submitError.value = err.response?.data?.detail || 'Erreur lors de l\'enregistrement'
    toastError(submitError.value)
    console.error(err)
  } finally {
    submitting.value = false
  }
}

function deleteUser(user) {
  userToDelete.value = user
  confirmModalConfig.value = {
    title: 'Supprimer l\'utilisateur',
    message: `Êtes-vous sûr de vouloir supprimer l'utilisateur "${user.full_name}" ? Cette action est irréversible.`,
    type: 'danger',
    confirmText: 'Supprimer',
    cancelText: 'Annuler'
  }
  showConfirmModal.value = true
}

async function confirmDeleteUser() {
  if (!userToDelete.value) return

  try {
    await utilisateursService.delete(userToDelete.value.id)
    success(`L'utilisateur "${userToDelete.value.full_name}" a été supprimé`)
    loadUtilisateurs()
  } catch (err) {
    toastError('Erreur lors de la suppression de l\'utilisateur')
    console.error(err)
  } finally {
    showConfirmModal.value = false
    userToDelete.value = null
  }
}

function viewUser(user) {
  selectedUser.value = user
  showDetailModal.value = true
}

function getUserInitials(fullName) {
  if (!fullName) return '??'
  return fullName
    .split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

onMounted(() => {
  loadUtilisateurs()
})
</script>
