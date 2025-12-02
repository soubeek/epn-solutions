<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div
        v-if="modelValue"
        class="fixed inset-0 z-50 overflow-y-auto"
        @click.self="handleCancel"
      >
        <!-- Overlay -->
        <div class="fixed inset-0 bg-black bg-opacity-50 transition-opacity"></div>

        <!-- Modal container -->
        <div class="flex min-h-screen items-center justify-center p-4">
          <div
            class="relative bg-white rounded-lg shadow-xl w-full max-w-md transform transition-all"
            @click.stop
          >
            <!-- Header -->
            <div class="flex items-center p-4 border-b" :class="headerClass">
              <div class="flex-shrink-0 mr-3">
                <!-- Warning Icon -->
                <svg
                  v-if="type === 'warning'"
                  class="h-6 w-6 text-yellow-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
                <!-- Danger Icon -->
                <svg
                  v-else-if="type === 'danger'"
                  class="h-6 w-6 text-red-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
                <!-- Info Icon -->
                <svg
                  v-else
                  class="h-6 w-6 text-blue-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <h3 class="text-lg font-medium text-gray-900">{{ title }}</h3>
            </div>

            <!-- Body -->
            <div class="p-4">
              <p class="text-sm text-gray-600">{{ message }}</p>
              <slot></slot>
            </div>

            <!-- Footer -->
            <div class="flex justify-end gap-3 p-4 border-t bg-gray-50">
              <button
                type="button"
                class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                @click="handleCancel"
                :disabled="loading"
              >
                {{ cancelText }}
              </button>
              <button
                type="button"
                :class="confirmButtonClass"
                @click="handleConfirm"
                :disabled="loading"
              >
                <svg
                  v-if="loading"
                  class="animate-spin -ml-1 mr-2 h-4 w-4"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    class="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    stroke-width="4"
                  ></circle>
                  <path
                    class="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                {{ confirmText }}
              </button>
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
  title: {
    type: String,
    default: 'Confirmation'
  },
  message: {
    type: String,
    default: 'Voulez-vous vraiment effectuer cette action ?'
  },
  type: {
    type: String,
    default: 'warning',
    validator: (value) => ['info', 'warning', 'danger'].includes(value)
  },
  confirmText: {
    type: String,
    default: 'Confirmer'
  },
  cancelText: {
    type: String,
    default: 'Annuler'
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'confirm', 'cancel'])

const headerClass = computed(() => {
  switch (props.type) {
    case 'danger':
      return 'bg-red-50'
    case 'warning':
      return 'bg-yellow-50'
    default:
      return 'bg-blue-50'
  }
})

const confirmButtonClass = computed(() => {
  const base = 'inline-flex items-center px-4 py-2 text-sm font-medium text-white rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2'
  switch (props.type) {
    case 'danger':
      return `${base} bg-red-600 hover:bg-red-700 focus:ring-red-500`
    case 'warning':
      return `${base} bg-yellow-600 hover:bg-yellow-700 focus:ring-yellow-500`
    default:
      return `${base} bg-blue-600 hover:bg-blue-700 focus:ring-blue-500`
  }
})

function handleConfirm() {
  emit('confirm')
}

function handleCancel() {
  emit('update:modelValue', false)
  emit('cancel')
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
