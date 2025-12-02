<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-500 to-primary-700">
    <div class="max-w-md w-full mx-4">
      <!-- Logo et titre -->
      <div class="text-center mb-8">
        <h1 class="text-4xl font-bold text-white mb-2">Poste Public Manager</h1>
        <p class="text-primary-100">Interface de gestion</p>
      </div>

      <!-- Formulaire de connexion -->
      <div class="card">
        <h2 class="text-2xl font-semibold text-gray-800 mb-6">Connexion</h2>

        <form @submit.prevent="handleLogin" class="space-y-4">
          <!-- Username -->
          <div>
            <label for="username" class="label">Nom d'utilisateur</label>
            <input
              id="username"
              v-model="credentials.username"
              type="text"
              class="input"
              placeholder="Entrez votre nom d'utilisateur"
              required
              :disabled="loading"
            />
          </div>

          <!-- Password -->
          <div>
            <label for="password" class="label">Mot de passe</label>
            <input
              id="password"
              v-model="credentials.password"
              type="password"
              class="input"
              placeholder="Entrez votre mot de passe"
              required
              :disabled="loading"
            />
          </div>

          <!-- Message d'erreur -->
          <div v-if="errorMessage" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
            {{ errorMessage }}
          </div>

          <!-- Bouton de connexion -->
          <button
            type="submit"
            class="w-full btn btn-primary"
            :disabled="loading"
          >
            <span v-if="!loading">Se connecter</span>
            <span v-else class="flex items-center justify-center">
              <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Connexion...
            </span>
          </button>
        </form>
      </div>

      <!-- Footer -->
      <div class="text-center mt-8 text-primary-100 text-sm">
        <p>&copy; 2025 Mairie - La Réunion</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const credentials = ref({
  username: '',
  password: ''
})

const loading = ref(false)
const errorMessage = ref('')

async function handleLogin() {
  loading.value = true
  errorMessage.value = ''

  const result = await authStore.login(credentials.value)

  if (result.success) {
    router.push({ name: 'dashboard' })
  } else {
    errorMessage.value = result.error
  }

  loading.value = false
}
</script>
