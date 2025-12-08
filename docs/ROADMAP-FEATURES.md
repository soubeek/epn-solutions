# Roadmap des fonctionnalites futures EPN Solutions

*Analyse comparative avec Libki - A implementer plus tard*

## Comparaison EPN vs Libki

| Fonctionnalite | EPN Solutions | Libki | Priorite |
|----------------|:-------------:|:-----:|:--------:|
| Gestion sessions avec codes | OK | OK | - |
| Compteur de temps | OK | OK | - |
| Nettoyage automatique | OK | Non | - |
| Mode kiosque | OK | OK | - |
| Demande d'extension | OK | Non | - |
| Gaming (Steam, Epic...) | OK | Non | - |
| **Reservations** | Non | OK | Haute |
| **Integration SIP2/ILS** | Non | OK | Moyenne |
| **Gestion d'impression** | Non | OK | Haute |
| **Interface publique** | Non | OK | Moyenne |
| **LDAP/SSO** | Non | OK | Moyenne |
| **Rapports avances** | Partiel | OK | Moyenne |
| **Multi-sites** | Non | OK | Basse |
| Portabilite du credit temps | Non | OK | Basse |

---

## Fonctionnalites a implementer

### Priorite Haute

#### 1. Systeme de reservation

**Description:** Utilisateur peut reserver un poste a l'avance via interface web

**Fonctionnalites:**
- Calendrier de disponibilite des postes
- Creneaux horaires configurables
- Notification rappel avant reservation
- Annulation automatique si non-presentation (5-10 min)
- Vue tableau de bord des reservations du jour

**Valeur ajoutee:** Evite les files d'attente, meilleure planification pour les usagers

**Fichiers a creer:**
- `backend/apps/reservations/` - Nouvelle app Django
- `frontend/src/views/ReservationsView.vue`
- `frontend/src/components/Calendar.vue`

---

#### 2. Gestion d'impression

**Description:** Controle des impressions avec quotas et validation

**Fonctionnalites:**
- Quota d'impression par utilisateur/session
- Cout par page configurable
- File d'impression avec validation
- Impression depuis le client EPN
- Rapports d'utilisation papier
- Liberation des impressions par l'admin ou l'usager

**Valeur ajoutee:** Controle des couts, evite le gaspillage papier

**Integration:** CUPS sur Linux, Windows Print Spooler

---

### Priorite Moyenne

#### 3. Interface publique (kiosque info)

**Description:** Page web publique pour les usagers

**Fonctionnalites:**
- Postes disponibles en temps reel
- Temps d'attente estime
- Possibilite de reserver
- Affichage sur ecran dans l'espace

**Fichiers a creer:**
- `frontend/src/views/PublicView.vue`
- Nouvelle route publique sans authentification

---

#### 4. Integration LDAP/Active Directory

**Description:** Authentification centralisee

**Fonctionnalites:**
- Authentification SSO
- Import automatique des utilisateurs
- Synchronisation des groupes
- Pas de double gestion des comptes

**Valeur ajoutee:** Integration SI existant, simplification administration

---

#### 5. Integration SIP2 (bibliotheques)

**Description:** Connexion aux systemes de bibliotheque

**Fonctionnalites:**
- Connexion au SIGB (Koha, PMB, etc.)
- Verification carte de bibliotheque
- Restrictions basees sur le statut usager
- Blocage si amendes impayees

**Valeur ajoutee:** Integration native avec les systemes de bibliotheque

---

#### 6. Rapports avances et exports

**Description:** Statistiques detaillees et exports

**Fonctionnalites:**
- Statistiques d'utilisation par periode
- Taux d'occupation des postes
- Duree moyenne des sessions
- Export CSV/PDF
- Graphiques de tendances
- Rapport RGPD (donnees utilisateur)

**Valeur ajoutee:** Aide a la decision, justification budgetaire

---

### Priorite Basse

#### 7. Multi-sites / Multi-espaces

- Gestion de plusieurs lieux
- Configuration par site
- Statistiques consolidees
- Horaires par site

#### 8. Portabilite du credit temps

- Minutes non utilisees reportables
- Utilisation sur differents postes
- Cumul de temps entre sessions

#### 9. File d'attente virtuelle

- Inscription en file d'attente
- Notification quand poste disponible
- Estimation du temps d'attente

#### 10. Horaires et fermetures

- Horaires d'ouverture par jour
- Jours feries automatiques
- Fermeture programmee des postes
- Avertissement avant fermeture

---

## Avantages uniques d'EPN Solutions

Fonctionnalites que Libki n'a **pas** :

| Fonctionnalite | Description |
|----------------|-------------|
| **Nettoyage complet** | Suppression traces Firefox, documents, historique |
| **Template Firefox** | Restauration profil propre avec extensions |
| **Support Gaming** | Steam, Epic, GOG, Ubisoft, EA App |
| **Mode kiosque avance** | Plein ecran force, blocage raccourcis |
| **Demande d'extension** | L'usager peut demander plus de temps |
| **Client Rust natif** | Performance, securite, cross-platform |
| **mTLS** | Authentification mutuelle par certificats |

---

## Ordre d'implementation suggere

### Phase 0 (Immediat) - Verrouillage Systeme
0. **System Lockdown** - Restrictions OS integrees au client

### Phase 1 (Court terme)
1. Systeme de reservation
2. Interface publique

### Phase 2 (Moyen terme)
3. Gestion d'impression
4. Rapports avances

### Phase 3 (Long terme)
5. LDAP/SSO
6. SIP2
7. Multi-sites

---

## Feature: System Lockdown (Verrouillage Systeme)

**Statut:** En cours d'implementation

### Objectif

Permettre au client EPN de configurer automatiquement les restrictions systeme lors de l'installation, avec possibilite de personnalisation. Actuellement, l'application gere la session utilisateur et le nettoyage, mais le verrouillage OS (bloquer applications, acces fichiers) doit etre configure manuellement.

### Architecture

```
+-----------------------------------------------------+
|                  Dashboard Admin                     |
|  +-----------+  +-----------+  +-----------+        |
|  |  Profils  |  |  Postes   |  | Appliquer |        |
|  |restriction|  |  groupes  |  |  config   |        |
|  +-----------+  +-----------+  +-----------+        |
+------------------------+----------------------------+
                         | API/WebSocket
                         v
+-----------------------------------------------------+
|                   Client Rust                        |
|  +-----------------------------------------------+  |
|  |           Module System Lockdown              |  |
|  |  +---------+  +---------+  +---------+        |  |
|  |  |  Linux  |  | Windows |  |  macOS  |        |  |
|  |  | (dconf) |  |(registry)|  | (future)|        |  |
|  |  +---------+  +---------+  +---------+        |  |
|  +-----------------------------------------------+  |
+-----------------------------------------------------+
```

### Phase 1: Linux (GNOME/GTK) - Priorite Haute

#### 1.1 Restrictions bureau GNOME via dconf

**Fichier:** `rust-client/crates/epn-core/src/lockdown/linux.rs`

Restrictions implementees:
- Desactiver le clic droit sur le bureau
- Cacher le menu Activites
- Desactiver les raccourcis systeme (Super, Alt+F2)
- Verrouiller le fond d'ecran
- Masquer les notifications systeme
- Bloquer l'acces aux parametres systeme

**Commandes dconf:**
```bash
# Desktop restrictions
dconf write /org/gnome/desktop/lockdown/disable-command-line true
dconf write /org/gnome/desktop/lockdown/disable-log-out true
dconf write /org/gnome/desktop/lockdown/disable-print-setup true
dconf write /org/gnome/desktop/lockdown/disable-user-switching true

# Shell restrictions
dconf write /org/gnome/shell/disable-user-extensions true
dconf write /org/gnome/mutter/overlay-key "''"
```

#### 1.2 Restrictions applications

**Fichier:** `rust-client/crates/epn-core/src/lockdown/apps.rs`

- Whitelist d'applications autorisees
- Bloquer: terminal, nautilus, parametres, etc.
- Configurer PolicyKit pour bloquer les actions admin
- Creer des fichiers `.desktop` modifies

#### 1.3 Session automatique

**Fichier:** `rust-client/scripts/configure-autologin.sh`

- Configuration GDM pour auto-login utilisateur `epn`
- Lancement automatique du client au demarrage (autostart)
- Redemarrage automatique si le client plante (systemd)

### Phase 2: Windows - Priorite Moyenne

#### 2.1 Restrictions via registre

**Fichier:** `rust-client/crates/epn-core/src/lockdown/windows.rs`

Cles registre:
```
HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer
- NoDesktop = 1
- NoRun = 1
- NoControlPanel = 1
- DisableTaskMgr = 1

HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\System
- DisableTaskMgr = 1
- DisableChangePassword = 1
```

#### 2.2 Shell personnalise

- Option: Remplacer explorer.exe par le client EPN
- Alternative: Utiliser Assigned Access (Windows 10/11 Pro)

#### 2.3 Session automatique

- Auto-login utilisateur kiosque via registre
- Demarrage automatique du client

### Phase 3: Interface administration (Future)

#### 3.1 Profils de restriction

| Profil | Applications autorisees |
|--------|------------------------|
| Strict | Firefox uniquement |
| Standard | Firefox + LibreOffice |
| Permissif | Applications selectionnees |
| Gaming | Firefox + Steam + Epic + autres |
| Personnalise | Configuration manuelle |

#### 3.2 Gestion depuis le dashboard

- Appliquer un profil a un poste ou groupe
- Voir le statut des restrictions par poste
- Forcer la reapplication des restrictions a distance

### Phase 4: Fonctionnalites avancees (Future)

#### 4.1 Controle USB (optionnel)
- Bloquer les peripheriques de stockage USB
- Autoriser clavier/souris uniquement
- udev rules sur Linux, GPO sur Windows

#### 4.2 Filtrage reseau (optionnel)
- Integration avec Pi-hole existant
- Whitelist/blacklist de sites par profil

#### 4.3 Restrictions par horaire
- Profils differents selon l'heure
- Restrictions differentes gaming vs bureautique

### Priorite implementation

| Phase | Priorite | Complexite | Impact |
|-------|----------|------------|--------|
| 1.1 Restrictions GNOME | Haute | Moyenne | Fort |
| 1.2 Restrictions apps | Haute | Moyenne | Fort |
| 1.3 Session auto | Haute | Faible | Fort |
| 2.1-2.3 Windows | Moyenne | Haute | Moyen |
| 3.1-3.2 Interface admin | Moyenne | Moyenne | Fort |
| 4.x Avance | Basse | Haute | Moyen |

### Fichiers a creer

```
rust-client/crates/epn-core/src/lockdown/
├── mod.rs              # Module principal
├── linux.rs            # Implementation Linux (dconf, PolicyKit)
├── windows.rs          # Implementation Windows (registre)
├── apps.rs             # Gestion whitelist applications
└── profiles.rs         # Profils de restriction

rust-client/scripts/
├── configure-lockdown.sh      # Script installation Linux
├── configure-lockdown.ps1     # Script installation Windows
└── configure-autologin.sh     # Auto-login Linux
```

---

## Sources

- [Libki.org](https://libki.org/)
- [Libki Manual](https://manual.libki.org/master/libki-manual.html)
- [Opensource.com - Libki Guide](https://opensource.com/article/19/5/libki-computer-access)
