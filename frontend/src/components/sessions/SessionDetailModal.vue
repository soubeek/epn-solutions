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
            <div class="flex items-center justify-between p-4 border-b" :class="headerBgClass">
              <div class="flex items-center gap-3">
                <span
                  class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium"
                  :class="statusClass"
                >
                  {{ statusLabel }}
                </span>
                <h3 class="text-lg font-medium text-gray-900">
                  Session #{{ session?.id }}
                </h3>
              </div>
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
            <div v-if="session" class="p-6">
              <!-- Code d'accès (prominent) -->
              <div class="bg-gray-100 rounded-lg p-4 mb-6 text-center">
                <p class="text-xs text-gray-500 uppercase tracking-wide mb-1">Code d'accès</p>
                <p class="text-3xl font-mono font-bold text-gray-900 tracking-widest">
                  {{ session.code_acces }}
                </p>
              </div>

              <!-- Temps restant (si active) -->
              <div
                v-if="session.statut === 'active'"
                class="bg-blue-50 rounded-lg p-4 mb-6"
              >
                <div class="flex items-center justify-between">
                  <div>
                    <p class="text-sm text-blue-600 font-medium">Temps restant</p>
                    <p class="text-2xl font-bold text-blue-900">
                      {{ formatTime(session.temps_restant) }}
                    </p>
                  </div>
                  <div class="text-right">
                    <p class="text-sm text-blue-600 font-medium">Utilisation</p>
                    <p class="text-2xl font-bold text-blue-900">
                      {{ session.pourcentage_utilise || 0 }}%
                    </p>
                  </div>
                </div>
                <!-- Barre de progression -->
                <div class="mt-3 h-2 bg-blue-200 rounded-full overflow-hidden">
                  <div
                    class="h-full bg-blue-600 transition-all duration-300"
                    :style="{ width: `${session.pourcentage_utilise || 0}%` }"
                  ></div>
                </div>
              </div>

              <!-- Informations détaillées -->
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <!-- Utilisateur -->
                <div class="bg-gray-50 rounded-lg p-4">
                  <h5 class="text-sm font-medium text-gray-900 mb-3 flex items-center gap-2">
                    <svg class="h-4 w-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                    Utilisateur
                    <span
                      v-if="session.is_guest_session"
                      class="px-2 py-0.5 text-xs bg-purple-100 text-purple-800 rounded-full"
                    >
                      Invité
                    </span>
                  </h5>
                  <dl class="space-y-1">
                    <dd class="text-sm font-medium text-gray-900">
                      {{ session.utilisateur_nom || session.utilisateur?.full_name || 'N/A' }}
                    </dd>
                  </dl>
                </div>

                <!-- Poste -->
                <div class="bg-gray-50 rounded-lg p-4">
                  <h5 class="text-sm font-medium text-gray-900 mb-3 flex items-center gap-2">
                    <svg class="h-4 w-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                    Poste
                  </h5>
                  <dl class="space-y-1">
                    <dd class="text-sm font-medium text-gray-900">
                      {{ session.poste_nom || session.poste?.nom || 'N/A' }}
                    </dd>
                  </dl>
                </div>

                <!-- Durée -->
                <div class="bg-gray-50 rounded-lg p-4">
                  <h5 class="text-sm font-medium text-gray-900 mb-3 flex items-center gap-2">
                    <svg class="h-4 w-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Durée
                  </h5>
                  <dl class="space-y-2">
                    <div>
                      <dt class="text-xs text-gray-500">Durée initiale</dt>
                      <dd class="text-sm text-gray-900">{{ formatMinutes(session.duree_initiale) }}</dd>
                    </div>
                    <div v-if="session.temps_ajoute > 0">
                      <dt class="text-xs text-gray-500">Temps ajouté</dt>
                      <dd class="text-sm text-green-600">+{{ formatMinutes(session.temps_ajoute) }}</dd>
                    </div>
                    <div v-if="session.temps_ecoule > 0">
                      <dt class="text-xs text-gray-500">Temps écoulé</dt>
                      <dd class="text-sm text-gray-900">{{ formatMinutes(session.temps_ecoule) }}</dd>
                    </div>
                  </dl>
                </div>

                <!-- Dates -->
                <div class="bg-gray-50 rounded-lg p-4">
                  <h5 class="text-sm font-medium text-gray-900 mb-3 flex items-center gap-2">
                    <svg class="h-4 w-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    Dates
                  </h5>
                  <dl class="space-y-2">
                    <div>
                      <dt class="text-xs text-gray-500">Créée le</dt>
                      <dd class="text-sm text-gray-900">{{ formatDateTime(session.created_at) }}</dd>
                    </div>
                    <div v-if="session.debut_session">
                      <dt class="text-xs text-gray-500">Démarrée le</dt>
                      <dd class="text-sm text-gray-900">{{ formatDateTime(session.debut_session) }}</dd>
                    </div>
                    <div v-if="session.fin_session">
                      <dt class="text-xs text-gray-500">Terminée le</dt>
                      <dd class="text-sm text-gray-900">{{ formatDateTime(session.fin_session) }}</dd>
                    </div>
                  </dl>
                </div>
              </div>

              <!-- Notes -->
              <div v-if="session.notes" class="mt-4 bg-yellow-50 rounded-lg p-4">
                <h5 class="text-sm font-medium text-gray-900 mb-2">Notes</h5>
                <p class="text-sm text-gray-700 whitespace-pre-wrap">{{ session.notes }}</p>
              </div>

              <!-- Métadonnées -->
              <div class="mt-4 pt-4 border-t text-xs text-gray-500">
                <p>Opérateur : {{ session.operateur || 'N/A' }}</p>
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
            <div class="flex justify-between gap-3 p-4 border-t bg-gray-50">
              <div>
                <button
                  v-if="canModifySession"
                  type="button"
                  class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700"
                  @click="$emit('terminate', session)"
                >
                  Terminer
                </button>
              </div>
              <div class="flex gap-3">
                <button
                  v-if="canModifySession"
                  type="button"
                  class="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700"
                  @click="$emit('addTime', session)"
                >
                  Ajouter du temps
                </button>
                <button
                  type="button"
                  class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                  @click="close"
                >
                  Fermer
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  session: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'terminate', 'addTime'])

const statusConfig = {
  en_attente: { label: 'En attente', class: 'bg-yellow-100 text-yellow-800', headerBg: 'bg-yellow-50' },
  active: { label: 'Active', class: 'bg-green-100 text-green-800', headerBg: 'bg-green-50' },
  suspendue: { label: 'Suspendue', class: 'bg-orange-100 text-orange-800', headerBg: 'bg-orange-50' },
  terminee: { label: 'Terminée', class: 'bg-gray-100 text-gray-800', headerBg: 'bg-gray-50' },
  expiree: { label: 'Expirée', class: 'bg-red-100 text-red-800', headerBg: 'bg-red-50' }
}

const statusClass = computed(() => {
  return statusConfig[props.session?.statut]?.class || 'bg-gray-100 text-gray-800'
})

const statusLabel = computed(() => {
  return statusConfig[props.session?.statut]?.label || props.session?.statut
})

const headerBgClass = computed(() => {
  return statusConfig[props.session?.statut]?.headerBg || 'bg-gray-50'
})

const canModifySession = computed(() => {
  return ['active', 'en_attente', 'suspendue'].includes(props.session?.statut)
})

function close() {
  emit('update:modelValue', false)
}

function formatTime(seconds) {
  if (!seconds && seconds !== 0) return 'N/A'
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function formatMinutes(seconds) {
  if (!seconds && seconds !== 0) return 'N/A'
  const mins = Math.floor(seconds / 60)
  return `${mins} min`
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
