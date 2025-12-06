<template>
  <MainLayout>
    <!-- Actions bar -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex space-x-4">
        <!-- Filtre par type -->
        <div class="flex items-center space-x-1 mr-2 border-r pr-4">
          <button
            @click="filterType = 'all'"
            class="btn btn-sm"
            :class="filterType === 'all' ? 'btn-primary' : 'btn-secondary'"
          >
            Tous
          </button>
          <button
            @click="filterType = 'bureautique'"
            class="btn btn-sm"
            :class="filterType === 'bureautique' ? 'btn-primary' : 'btn-secondary'"
            title="Postes bureautique"
          >
            🖥️
          </button>
          <button
            @click="filterType = 'gaming'"
            class="btn btn-sm"
            :class="filterType === 'gaming' ? 'btn-primary' : 'btn-secondary'"
            title="Postes gaming"
          >
            🎮
          </button>
        </div>
        <!-- Filtre par statut -->
        <button
          @click="filterStatus = 'all'"
          class="btn"
          :class="filterStatus === 'all' ? 'btn-primary' : 'btn-secondary'"
        >
          Tous
        </button>
        <button
          @click="filterStatus = 'en_attente_validation'"
          class="btn relative"
          :class="filterStatus === 'en_attente_validation' ? 'btn-primary' : 'btn-secondary'"
        >
          En attente
          <span
            v-if="pendingCount > 0"
            class="absolute -top-2 -right-2 bg-red-500 text-white text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center"
          >
            {{ pendingCount }}
          </span>
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
            <span class="mr-2 text-lg" :title="poste.type_poste === 'gaming' ? 'Poste gaming' : 'Poste bureautique'">
              {{ poste.type_poste === 'gaming' ? '🎮' : '🖥️' }}
            </span>
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

          <!-- Infos découverte pour les postes en attente -->
          <div v-if="poste.statut === 'en_attente_validation'" class="mt-2 space-y-1">
            <div v-if="poste.mac_address" class="flex items-center text-sm text-gray-600">
              <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
              </svg>
              {{ poste.mac_address }}
            </div>
            <div v-if="poste.discovered_hostname" class="flex items-center text-sm text-gray-600">
              <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              {{ poste.discovered_hostname }}
            </div>
            <div v-if="poste.discovered_at" class="text-xs text-gray-500 mt-1">
              Découvert le {{ formatDate(poste.discovered_at) }}
            </div>
          </div>

          <div v-if="poste.session_active_code" class="mt-3 p-2 bg-green-50 rounded border border-green-200">
            <p class="text-xs text-green-700 mb-1">Session active</p>
            <p class="text-sm font-mono font-bold text-green-900">{{ poste.session_active_code }}</p>
          </div>
        </div>

        <!-- Actions pour postes en attente de validation -->
        <div v-if="poste.statut === 'en_attente_validation'" class="flex space-x-2 pt-4 border-t border-gray-200">
          <button
            @click="openValidateModal(poste)"
            class="flex-1 btn btn-primary text-sm"
          >
            <svg class="w-4 h-4 mr-1 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
            Valider
          </button>
          <button
            @click="rejectPoste(poste)"
            class="flex-1 btn btn-danger text-sm"
          >
            <svg class="w-4 h-4 mr-1 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
            Rejeter
          </button>
        </div>

        <!-- Actions pour postes normaux -->
        <div v-else class="flex space-x-2 pt-4 border-t border-gray-200">
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
            v-if="poste.est_en_ligne"
            @click="openCommandModal(poste)"
            class="btn btn-secondary text-sm"
            title="Commandes à distance"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </button>
          <button
            @click="openTokenModal(poste)"
            class="btn btn-secondary text-sm"
            title="Générer token d'enregistrement"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
            </svg>
          </button>
          <button
            @click="editPoste(poste)"
            class="btn btn-secondary text-sm"
            title="Modifier"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </button>
          <button
            @click="deletePoste(poste)"
            class="btn btn-danger text-sm"
            title="Supprimer"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
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
            <div class="grid grid-cols-2 gap-4">
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
                <label class="label">Type de poste</label>
                <select v-model="formData.type_poste" class="input">
                  <option value="bureautique">🖥️ Bureautique</option>
                  <option value="gaming">🎮 Gaming</option>
                </select>
              </div>
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
    <!-- Modal Validation -->
    <div
      v-if="showValidateModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="closeValidateModal"
    >
      <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div class="p-6">
          <div class="flex items-center justify-between mb-6">
            <h3 class="text-xl font-semibold text-gray-900">Valider le poste</h3>
            <button @click="closeValidateModal" class="text-gray-400 hover:text-gray-600">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div class="mb-4 p-3 bg-gray-50 rounded-lg">
            <p class="text-sm text-gray-600 mb-1">Hostname découvert :</p>
            <p class="font-mono text-gray-900">{{ validatingPoste?.discovered_hostname || 'N/A' }}</p>
            <p class="text-sm text-gray-600 mt-2 mb-1">Adresse MAC :</p>
            <p class="font-mono text-gray-900">{{ validatingPoste?.mac_address || 'N/A' }}</p>
          </div>

          <form @submit.prevent="handleValidate" class="space-y-4">
            <div>
              <label class="label">Nom du poste (optionnel)</label>
              <input
                v-model="validateFormData.nom"
                type="text"
                class="input"
                :placeholder="validatingPoste?.nom || 'Garder le nom actuel'"
              />
              <p class="text-xs text-gray-500 mt-1">Laissez vide pour conserver le nom généré automatiquement</p>
            </div>

            <div v-if="validateError" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              {{ validateError }}
            </div>

            <div class="flex justify-end space-x-3 pt-4 border-t">
              <button type="button" @click="closeValidateModal" class="btn btn-secondary">
                Annuler
              </button>
              <button type="submit" class="btn btn-primary" :disabled="validating">
                {{ validating ? 'Validation...' : 'Valider et générer token' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Modal Token -->
    <div
      v-if="showTokenModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="closeTokenModal"
    >
      <div class="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4">
        <div class="p-6">
          <div class="flex items-center justify-between mb-6">
            <h3 class="text-xl font-semibold text-gray-900">Token d'enregistrement</h3>
            <button @click="closeTokenModal" class="text-gray-400 hover:text-gray-600">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div class="mb-4">
            <p class="text-sm text-gray-600 mb-2">Poste : <span class="font-semibold">{{ tokenPoste?.nom }}</span></p>
          </div>

          <div v-if="generatedToken" class="mb-4">
            <label class="label">Token (valide 24h)</label>
            <div class="relative">
              <input
                :value="generatedToken"
                type="text"
                class="input font-mono text-sm pr-10"
                readonly
              />
              <button
                @click="copyToken"
                class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                title="Copier"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                </svg>
              </button>
            </div>
            <p class="text-xs text-gray-500 mt-2">
              Utilisez ce token avec la commande client pour enregistrer le poste.
            </p>
          </div>

          <div v-if="tokenError" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
            {{ tokenError }}
          </div>

          <div class="flex justify-end space-x-3 pt-4 border-t">
            <button type="button" @click="closeTokenModal" class="btn btn-secondary">
              Fermer
            </button>
            <button
              v-if="!generatedToken"
              @click="generateToken"
              class="btn btn-primary"
              :disabled="generatingToken"
            >
              {{ generatingToken ? 'Génération...' : 'Générer un nouveau token' }}
            </button>
            <button
              v-else
              @click="generateToken"
              class="btn btn-secondary"
              :disabled="generatingToken"
            >
              {{ generatingToken ? 'Génération...' : 'Regénérer' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal Commandes à distance -->
    <div
      v-if="showCommandModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="closeCommandModal"
    >
      <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div class="p-6">
          <div class="flex items-center justify-between mb-6">
            <h3 class="text-xl font-semibold text-gray-900">
              Commandes - {{ commandPoste?.nom }}
            </h3>
            <button @click="closeCommandModal" class="text-gray-400 hover:text-gray-600">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div class="grid grid-cols-2 gap-3 mb-4">
            <button
              @click="sendCommand('lock')"
              class="btn btn-secondary flex flex-col items-center py-4"
              :disabled="sendingCommand"
            >
              <svg class="w-8 h-8 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
              Verrouiller
            </button>
            <button
              @click="unlockKiosk"
              class="btn btn-secondary flex flex-col items-center py-4"
              :disabled="sendingCommand"
              title="Désactiver le mode kiosque sur ce poste"
            >
              <svg class="w-8 h-8 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 11V7a4 4 0 118 0m-4 8v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2z" />
              </svg>
              Déverrouiller
            </button>
            <button
              @click="openMessageInput"
              class="btn btn-secondary flex flex-col items-center py-4"
              :disabled="sendingCommand"
            >
              <svg class="w-8 h-8 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              Message
            </button>
            <button
              @click="confirmCommand('restart')"
              class="btn btn-warning flex flex-col items-center py-4"
              :disabled="sendingCommand"
            >
              <svg class="w-8 h-8 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Redémarrer
            </button>
            <button
              @click="confirmCommand('shutdown')"
              class="btn btn-danger flex flex-col items-center py-4"
              :disabled="sendingCommand"
            >
              <svg class="w-8 h-8 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 5.636a9 9 0 11-12.728 0M12 3v9" />
              </svg>
              Éteindre
            </button>
          </div>

          <!-- Input message -->
          <div v-if="showMessageInput" class="mb-4 p-3 bg-gray-50 rounded-lg">
            <label class="label">Message à afficher</label>
            <textarea
              v-model="messagePayload"
              class="input"
              rows="3"
              placeholder="Saisissez le message à afficher sur le poste..."
            ></textarea>
            <div class="flex justify-end mt-2 space-x-2">
              <button @click="showMessageInput = false" class="btn btn-secondary text-sm">
                Annuler
              </button>
              <button
                @click="sendCommand('message')"
                class="btn btn-primary text-sm"
                :disabled="!messagePayload || sendingCommand"
              >
                Envoyer
              </button>
            </div>
          </div>

          <div v-if="commandError" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
            {{ commandError }}
          </div>

          <div v-if="commandSuccess" class="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg mb-4">
            {{ commandSuccess }}
          </div>

          <div class="flex justify-end">
            <button @click="closeCommandModal" class="btn btn-secondary">
              Fermer
            </button>
          </div>
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
const filterType = ref('all')

const showModal = ref(false)
const isEditing = ref(false)
const currentPoste = ref(null)
const formData = ref(getEmptyForm())
const submitting = ref(false)
const submitError = ref(null)

// État pour la modal de validation
const showValidateModal = ref(false)
const validatingPoste = ref(null)
const validateFormData = ref({ nom: '' })
const validating = ref(false)
const validateError = ref(null)

// État pour la modal de token
const showTokenModal = ref(false)
const tokenPoste = ref(null)
const generatedToken = ref(null)
const generatingToken = ref(false)
const tokenError = ref(null)

// État pour la modal de commandes à distance
const showCommandModal = ref(false)
const commandPoste = ref(null)
const sendingCommand = ref(false)
const commandError = ref(null)
const commandSuccess = ref(null)
const showMessageInput = ref(false)
const messagePayload = ref('')

function getEmptyForm() {
  return {
    nom: '',
    type_poste: 'bureautique',
    ip_address: '',
    mac_address: '',
    emplacement: '',
    statut: 'disponible',
    notes: ''
  }
}

// Compte des postes en attente pour le badge
const pendingCount = computed(() => {
  return postes.value.filter(p => p.statut === 'en_attente_validation').length
})

const filteredPostes = computed(() => {
  let result = postes.value

  // Filtre par type
  if (filterType.value !== 'all') {
    result = result.filter(p => p.type_poste === filterType.value)
  }

  // Filtre par statut
  if (filterStatus.value !== 'all') {
    result = result.filter(p => p.statut === filterStatus.value)
  }

  return result
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

async function deletePoste(poste) {
  if (poste.session_active_code) {
    toastError('Impossible de supprimer un poste avec une session active')
    return
  }

  if (!confirm(`Êtes-vous sûr de vouloir supprimer le poste "${poste.nom}" ?\nCette action est irréversible.`)) {
    return
  }

  try {
    await postesService.delete(poste.id)
    success(`Le poste "${poste.nom}" a été supprimé`)
    loadPostes()
  } catch (err) {
    toastError(err.response?.data?.detail || 'Erreur lors de la suppression')
    console.error(err)
  }
}

function getStatusClass(statut) {
  const classes = {
    'en_attente_validation': 'bg-amber-100 text-amber-800',
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
    'en_attente_validation': 'En attente',
    'disponible': 'Disponible',
    'occupe': 'Occupé',
    'reserve': 'Réservé',
    'hors_ligne': 'Hors ligne',
    'maintenance': 'Maintenance'
  }
  return labels[statut] || statut
}

function formatDate(dateString) {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// ==================== Fonctions de validation ====================

function openValidateModal(poste) {
  validatingPoste.value = poste
  validateFormData.value = { nom: '' }
  validateError.value = null
  showValidateModal.value = true
}

function closeValidateModal() {
  showValidateModal.value = false
  validatingPoste.value = null
  validateError.value = null
}

async function handleValidate() {
  validating.value = true
  validateError.value = null

  try {
    const data = {}
    if (validateFormData.value.nom) {
      data.nom = validateFormData.value.nom
    }

    await postesService.validateDiscovery(validatingPoste.value.id, data)
    success(`Le poste "${validatingPoste.value.nom}" a été validé`)

    // Générer automatiquement un token après validation
    const tokenResponse = await postesService.generateRegistrationToken(validatingPoste.value.id)
    const token = tokenResponse.data.registration_token

    closeValidateModal()
    loadPostes()

    // Ouvrir la modal de token avec le token généré
    tokenPoste.value = validatingPoste.value
    generatedToken.value = token
    tokenError.value = null
    showTokenModal.value = true

  } catch (err) {
    validateError.value = err.response?.data?.error || err.response?.data?.detail || 'Erreur lors de la validation'
    toastError(validateError.value)
    console.error(err)
  } finally {
    validating.value = false
  }
}

async function rejectPoste(poste) {
  if (!confirm(`Êtes-vous sûr de vouloir rejeter le poste "${poste.nom}" ?\nCette action supprimera définitivement ce poste.`)) {
    return
  }

  try {
    await postesService.rejectDiscovery(poste.id)
    success(`Le poste "${poste.nom}" a été rejeté`)
    loadPostes()
  } catch (err) {
    toastError('Erreur lors du rejet du poste')
    console.error(err)
  }
}

// ==================== Fonctions de token ====================

function openTokenModal(poste) {
  tokenPoste.value = poste
  generatedToken.value = null
  tokenError.value = null
  showTokenModal.value = true
}

function closeTokenModal() {
  showTokenModal.value = false
  tokenPoste.value = null
  generatedToken.value = null
  tokenError.value = null
}

async function generateToken() {
  generatingToken.value = true
  tokenError.value = null

  try {
    const response = await postesService.generateRegistrationToken(tokenPoste.value.id)
    generatedToken.value = response.data.registration_token
    success('Token généré avec succès')
  } catch (err) {
    tokenError.value = err.response?.data?.error || err.response?.data?.detail || 'Erreur lors de la génération du token'
    toastError(tokenError.value)
    console.error(err)
  } finally {
    generatingToken.value = false
  }
}

async function copyToken() {
  try {
    await navigator.clipboard.writeText(generatedToken.value)
    success('Token copié dans le presse-papier')
  } catch (err) {
    toastError('Erreur lors de la copie')
    console.error(err)
  }
}

// ==================== Fonctions de commandes à distance ====================

function openCommandModal(poste) {
  commandPoste.value = poste
  commandError.value = null
  commandSuccess.value = null
  showMessageInput.value = false
  messagePayload.value = ''
  showCommandModal.value = true
}

function closeCommandModal() {
  showCommandModal.value = false
  commandPoste.value = null
  commandError.value = null
  commandSuccess.value = null
  showMessageInput.value = false
  messagePayload.value = ''
}

function openMessageInput() {
  showMessageInput.value = true
  commandError.value = null
  commandSuccess.value = null
}

function confirmCommand(command) {
  const labels = {
    shutdown: 'éteindre',
    restart: 'redémarrer'
  }
  const action = labels[command] || command

  if (!confirm(`Êtes-vous sûr de vouloir ${action} le poste "${commandPoste.value.nom}" ?`)) {
    return
  }

  sendCommand(command)
}

async function sendCommand(command) {
  sendingCommand.value = true
  commandError.value = null
  commandSuccess.value = null

  try {
    const payload = command === 'message' ? messagePayload.value : null
    await postesService.remoteCommand(commandPoste.value.id, command, payload)

    const labels = {
      lock: 'Verrouillage',
      message: 'Message',
      shutdown: 'Extinction',
      restart: 'Redémarrage'
    }

    commandSuccess.value = `${labels[command] || command} envoyé avec succès`
    success(commandSuccess.value)

    // Reset message input
    if (command === 'message') {
      showMessageInput.value = false
      messagePayload.value = ''
    }
  } catch (err) {
    commandError.value = err.response?.data?.error || err.response?.data?.detail || 'Erreur lors de l\'envoi de la commande'
    toastError(commandError.value)
    console.error(err)
  } finally {
    sendingCommand.value = false
  }
}

async function unlockKiosk() {
  if (!confirm(`Êtes-vous sûr de vouloir désactiver le mode kiosque sur "${commandPoste.value.nom}" ?\nCela permettra à l'utilisateur d'accéder au bureau.`)) {
    return
  }

  sendingCommand.value = true
  commandError.value = null
  commandSuccess.value = null

  try {
    await postesService.unlockKiosk(commandPoste.value.id)
    commandSuccess.value = 'Mode kiosque désactivé avec succès'
    success(commandSuccess.value)
  } catch (err) {
    commandError.value = err.response?.data?.error || err.response?.data?.detail || 'Erreur lors du déverrouillage'
    toastError(commandError.value)
    console.error(err)
  } finally {
    sendingCommand.value = false
  }
}

onMounted(() => {
  loadPostes()
  // Rafraîchissement automatique toutes les 10 secondes
  setInterval(loadPostes, 10000)
})
</script>
