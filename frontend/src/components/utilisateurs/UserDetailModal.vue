<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div
        v-if="modelValue"
        class="fixed inset-0 z-50 overflow-y-auto"
        @click.self="close"
      >
        <!-- Overlay -->
        <div class="fixed inset-0 bg-black bg-opacity-50 transition-opacity"></div>

        <!-- Modal container -->
        <div class="flex min-h-screen items-center justify-center p-4">
          <div
            class="relative bg-white rounded-lg shadow-xl w-full max-w-2xl transform transition-all"
            @click.stop
          >
            <!-- Header -->
            <div class="flex items-center justify-between p-4 border-b bg-gray-50">
              <h3 class="text-lg font-medium text-gray-900">
                Détails de l'utilisateur
              </h3>
              <button
                type="button"
                class="text-gray-400 hover:text-gray-600"
                @click="close"
              >
                <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <!-- Body -->
            <div v-if="user" class="p-6">
              <!-- Photo et info principale -->
              <div class="flex items-start gap-6 mb-6">
                <div class="flex-shrink-0">
                  <img
                    v-if="user.photo"
                    :src="user.photo"
                    :alt="user.full_name"
                    class="h-24 w-24 rounded-full object-cover border-2 border-gray-200"
                  />
                  <div
                    v-else
                    class="h-24 w-24 rounded-full bg-blue-100 flex items-center justify-center"
                  >
                    <span class="text-2xl font-medium text-blue-600">
                      {{ getInitials(user) }}
                    </span>
                  </div>
                </div>
                <div>
                  <h4 class="text-xl font-semibold text-gray-900">
                    {{ user.full_name || `${user.prenom} ${user.nom}` }}
                  </h4>
                  <p class="text-sm text-gray-500 mt-1">
                    Inscrit le {{ formatDate(user.created_at) }}
                  </p>
                  <div class="mt-2">
                    <span
                      v-if="user.consentement_rgpd"
                      class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800"
                    >
                      Consentement RGPD
                    </span>
                    <span
                      v-else
                      class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800"
                    >
                      Sans consentement
                    </span>
                  </div>
                </div>
              </div>

              <!-- Informations détaillées -->
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <!-- Contact -->
                <div class="bg-gray-50 rounded-lg p-4">
                  <h5 class="text-sm font-medium text-gray-900 mb-3">Contact</h5>
                  <dl class="space-y-2">
                    <div v-if="user.email">
                      <dt class="text-xs text-gray-500">Email</dt>
                      <dd class="text-sm text-gray-900">{{ user.email }}</dd>
                    </div>
                    <div v-if="user.telephone">
                      <dt class="text-xs text-gray-500">Téléphone</dt>
                      <dd class="text-sm text-gray-900">{{ user.telephone }}</dd>
                    </div>
                    <div v-if="user.adresse">
                      <dt class="text-xs text-gray-500">Adresse</dt>
                      <dd class="text-sm text-gray-900">{{ user.adresse }}</dd>
                    </div>
                  </dl>
                </div>

                <!-- Identité -->
                <div class="bg-gray-50 rounded-lg p-4">
                  <h5 class="text-sm font-medium text-gray-900 mb-3">Identité</h5>
                  <dl class="space-y-2">
                    <div v-if="user.carte_identite">
                      <dt class="text-xs text-gray-500">N° Carte d'identité</dt>
                      <dd class="text-sm text-gray-900 font-mono">{{ user.carte_identite }}</dd>
                    </div>
                    <div v-if="user.date_naissance">
                      <dt class="text-xs text-gray-500">Date de naissance</dt>
                      <dd class="text-sm text-gray-900">{{ formatDate(user.date_naissance) }}</dd>
                    </div>
                  </dl>
                </div>

                <!-- Statistiques -->
                <div class="bg-blue-50 rounded-lg p-4">
                  <h5 class="text-sm font-medium text-gray-900 mb-3">Statistiques</h5>
                  <dl class="space-y-2">
                    <div>
                      <dt class="text-xs text-gray-500">Sessions totales</dt>
                      <dd class="text-lg font-semibold text-blue-600">
                        {{ user.nombre_sessions_total || 0 }}
                      </dd>
                    </div>
                    <div v-if="user.derniere_session">
                      <dt class="text-xs text-gray-500">Dernière session</dt>
                      <dd class="text-sm text-gray-900">{{ formatDateTime(user.derniere_session) }}</dd>
                    </div>
                  </dl>
                </div>

                <!-- Notes -->
                <div v-if="user.notes" class="bg-yellow-50 rounded-lg p-4">
                  <h5 class="text-sm font-medium text-gray-900 mb-3">Notes</h5>
                  <p class="text-sm text-gray-700 whitespace-pre-wrap">{{ user.notes }}</p>
                </div>
              </div>

              <!-- Métadonnées -->
              <div class="mt-4 pt-4 border-t text-xs text-gray-500">
                <p>Créé par : {{ user.created_by || 'N/A' }}</p>
                <p v-if="user.date_consentement">
                  Consentement le : {{ formatDateTime(user.date_consentement) }}
                </p>
              </div>
            </div>

            <!-- Loading -->
            <div v-else class="p-6 flex justify-center">
              <svg class="animate-spin h-8 w-8 text-blue-500" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </div>

            <!-- Footer -->
            <div class="flex justify-end gap-3 p-4 border-t bg-gray-50">
              <button
                type="button"
                class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                @click="close"
              >
                Fermer
              </button>
              <button
                v-if="user"
                type="button"
                class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
                @click="$emit('edit', user)"
              >
                Modifier
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  user: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'edit'])

function close() {
  emit('update:modelValue', false)
}

function getInitials(user) {
  if (!user) return '?'
  const prenom = user.prenom || ''
  const nom = user.nom || ''
  return `${prenom.charAt(0)}${nom.charAt(0)}`.toUpperCase()
}

function formatDate(dateString) {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleDateString('fr-FR')
}

function formatDateTime(dateString) {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleString('fr-FR')
}
</script>

<style scoped>
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
</style>
