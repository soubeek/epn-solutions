# Frontend - Poste Public Manager

Interface web d'administration pour la gestion des postes informatiques publics.

## 🚀 Technologies

- **Vue 3** - Framework JavaScript progressif
- **Vite 5** - Build tool ultra-rapide
- **Tailwind CSS 3** - Framework CSS utility-first
- **Pinia** - State management
- **Vue Router** - Routing
- **Axios** - HTTP client
- **Socket.io** - WebSocket temps réel

## 📦 Installation

```bash
# Installer les dépendances
npm install

# Lancer en mode développement
npm run dev

# Build pour la production
npm run build

# Preview du build de production
npm run preview
```

## 🏗️ Structure du Projet

```
frontend/
├── public/              # Fichiers statiques
├── src/
│   ├── assets/          # CSS, images, etc.
│   │   └── main.css     # Styles globaux Tailwind
│   ├── components/      # Composants réutilisables
│   │   └── Layout/
│   │       └── MainLayout.vue
│   ├── router/          # Configuration Vue Router
│   │   └── index.js
│   ├── services/        # Services API
│   │   └── api.js       # Client Axios + endpoints
│   ├── stores/          # Stores Pinia
│   │   ├── auth.js      # Authentification
│   │   └── dashboard.js # Dashboard
│   ├── views/           # Pages/Vues
│   │   ├── LoginView.vue
│   │   ├── DashboardView.vue
│   │   ├── UtilisateursView.vue
│   │   ├── SessionsView.vue
│   │   ├── PostesView.vue
│   │   └── LogsView.vue
│   ├── App.vue          # Composant racine
│   └── main.js          # Point d'entrée
├── index.html
├── package.json
├── vite.config.js
├── tailwind.config.js
└── postcss.config.js
```

## 🎯 Fonctionnalités

### ✅ Authentification
- Connexion JWT
- Auto-refresh token
- Protection des routes
- Déconnexion

### ✅ Dashboard
- Statistiques en temps réel
- Utilisateurs actifs
- Sessions en cours
- Postes disponibles
- Graphiques

### ✅ Gestion Utilisateurs
- Liste avec recherche
- Création (+ photo)
- Modification
- Suppression
- Conformité RGPD
- Historique sessions

### ✅ Gestion Sessions
- Liste filtrée par statut
- Création avec code généré
- Ajout de temps
- Terminaison
- Monitoring temps réel
- Statistiques

### ✅ Gestion Postes
- Vue en grille
- Statut temps réel (en ligne/hors ligne)
- Changement de statut
- Session active affichée
- Création/modification

### ✅ Logs & Audit
- Liste complète
- Filtres avancés (action, opérateur, période)
- Recherche
- Rafraîchissement automatique

## 🔌 API Backend

L'application se connecte au backend Django via Axios.

### Configuration

Créer un fichier `.env` :

```env
VITE_API_URL=http://localhost:8000/api
```

### Endpoints Utilisés

```
POST   /api/token/                          - Login
POST   /api/token/refresh/                  - Refresh token
GET    /api/utilisateurs/                   - Liste utilisateurs
POST   /api/utilisateurs/                   - Créer utilisateur
GET    /api/sessions/                       - Liste sessions
POST   /api/sessions/                       - Créer session
POST   /api/sessions/{id}/add_time/         - Ajouter temps
POST   /api/sessions/{id}/terminate/        - Terminer session
GET    /api/postes/                         - Liste postes
POST   /api/postes/{id}/marquer_disponible/ - Changer statut
GET    /api/logs/                           - Liste logs
POST   /api/logs/search/                    - Recherche logs
```

## 🎨 Styles

Utilise **Tailwind CSS** avec des classes utilitaires personnalisées :

```css
/* Classes globales */
.btn             - Bouton de base
.btn-primary     - Bouton principal (bleu)
.btn-secondary   - Bouton secondaire (gris)
.btn-danger      - Bouton danger (rouge)
.card            - Carte avec ombre
.input           - Input stylisé
.label           - Label de formulaire
```

### Couleurs Personnalisées

```javascript
// tailwind.config.js
colors: {
  primary: {
    50: '#eff6ff',
    ...
    600: '#2563eb',  // Couleur principale
    ...
    900: '#1e3a8a',
  }
}
```

## 🔐 Authentification

### Store Auth (Pinia)

```javascript
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

// Login
await authStore.login({ username, password })

// Logout
authStore.logout()

// Vérifier si authentifié
authStore.isAuthenticated
```

### Protection des Routes

```javascript
// router/index.js
{
  path: '/dashboard',
  meta: { requiresAuth: true }  // Nécessite authentification
}
```

## 📡 Services API

### Utilisation

```javascript
import { utilisateursService, sessionsService } from '@/services/api'

// Récupérer tous les utilisateurs
const response = await utilisateursService.getAll()
const utilisateurs = response.data

// Créer une session
const response = await sessionsService.create({
  utilisateur: 1,
  poste: 1,
  duree_minutes: 60,
  operateur: 'admin'
})
```

## 🔄 Rafraîchissement Automatique

Plusieurs vues rafraîchissent automatiquement les données :

- **Dashboard** : 30 secondes
- **Sessions** : 5 secondes
- **Postes** : 10 secondes
- **Logs** : 30 secondes

## 🚧 TODO / Améliorations Futures

- [ ] WebSocket temps réel (Socket.io)
- [ ] Graphiques avec Chart.js
- [ ] Export PDF/Excel
- [ ] Notifications toast
- [ ] Mode sombre
- [ ] Responsive mobile optimisé
- [ ] Tests unitaires (Vitest)
- [ ] Tests E2E (Cypress)
- [ ] PWA (Progressive Web App)

## 📝 Notes de Développement

### Proxy Vite

Le fichier `vite.config.js` configure un proxy pour le développement :

```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    }
  }
}
```

Cela permet d'éviter les problèmes CORS en développement.

### Build de Production

```bash
npm run build
```

Génère les fichiers optimisés dans `dist/` prêts pour le déploiement.

### Déploiement

Les fichiers statiques peuvent être servis par :
- Nginx
- Apache
- Netlify
- Vercel
- GitHub Pages

## 🐛 Debugging

### Vue Devtools

Installer l'extension navigateur **Vue Devtools** pour déboguer :
- Composants
- Routes
- Pinia stores
- Timeline

### Console Réseau

Vérifier les appels API dans l'onglet Network des DevTools.

## 📚 Documentation

- [Vue 3](https://vuejs.org/)
- [Vite](https://vitejs.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Pinia](https://pinia.vuejs.org/)
- [Vue Router](https://router.vuejs.org/)

## 👥 Support

Pour toute question ou problème, contacter l'équipe de développement.

---

**Statut** : ✅ Frontend fonctionnel à ~80%
**Dernière mise à jour** : 2025-01-19
