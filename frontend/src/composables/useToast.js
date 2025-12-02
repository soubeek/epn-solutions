/**
 * Composable pour gérer les notifications toast globalement
 */

import { ref } from 'vue'

const toasts = ref([])
let toastId = 0

export function useToast() {
  function addToast({ type = 'info', title = '', message = '', duration = 5000 }) {
    const id = ++toastId
    toasts.value.push({ id, type, title, message })

    if (duration > 0) {
      setTimeout(() => {
        removeToast(id)
      }, duration)
    }

    return id
  }

  function removeToast(id) {
    const index = toasts.value.findIndex((t) => t.id === id)
    if (index > -1) {
      toasts.value.splice(index, 1)
    }
  }

  function success(message, title = '') {
    return addToast({ type: 'success', title, message })
  }

  function error(message, title = 'Erreur') {
    return addToast({ type: 'error', title, message, duration: 8000 })
  }

  function warning(message, title = 'Attention') {
    return addToast({ type: 'warning', title, message })
  }

  function info(message, title = '') {
    return addToast({ type: 'info', title, message })
  }

  function clear() {
    toasts.value = []
  }

  return {
    toasts,
    addToast,
    removeToast,
    success,
    error,
    warning,
    info,
    clear
  }
}
