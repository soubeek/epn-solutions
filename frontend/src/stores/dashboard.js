import { defineStore } from 'pinia'
import { ref } from 'vue'
import { utilisateursService, postesService, sessionsService } from '@/services/api'

export const useDashboardStore = defineStore('dashboard', () => {
  // State
  const stats = ref({
    utilisateurs: {
      total: 0,
      avec_consentement: 0,
      actifs_30_jours: 0
    },
    postes: {
      total: 0,
      en_ligne: 0,
      disponibles: 0,
      occupes: 0
    },
    sessions: {
      total: 0,
      actives: 0,
      sessions_aujourdhui: 0,
      duree_moyenne_minutes: 0
    }
  })

  const loading = ref(false)
  const error = ref(null)

  // Actions
  async function fetchStats() {
    loading.value = true
    error.value = null

    try {
      const [utilisateurs, postes, sessions] = await Promise.all([
        utilisateursService.getStats(),
        postesService.getStats(),
        sessionsService.getStats()
      ])

      stats.value = {
        utilisateurs: utilisateurs.data,
        postes: postes.data,
        sessions: sessions.data
      }
    } catch (err) {
      error.value = err.message || 'Erreur lors du chargement des statistiques'
      console.error('Erreur stats:', err)
    } finally {
      loading.value = false
    }
  }

  return {
    stats,
    loading,
    error,
    fetchStats
  }
})
