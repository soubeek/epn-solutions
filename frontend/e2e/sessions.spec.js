/**
 * Tests E2E pour la gestion des sessions
 */
import { test, expect } from '@playwright/test'
import { testCredentials, login } from './fixtures/auth.js'

test.describe('Sessions Management', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, testCredentials.admin)
    await page.goto('/sessions')
  })

  test.describe('Sessions List', () => {
    test('should display sessions page', async ({ page }) => {
      await expect(page).toHaveURL(/.*sessions/)

      // Vérifier les éléments de la page
      await expect(page.locator('h1, h2, .page-title').filter({ hasText: /session/i })).toBeVisible({ timeout: 10000 })
    })

    test('should have filter buttons', async ({ page }) => {
      // Vérifier les boutons de filtres
      await expect(page.locator('button:has-text("Toutes"), button:has-text("All")')).toBeVisible()
      await expect(page.locator('button:has-text("Actives"), button:has-text("Active")')).toBeVisible()
    })

    test('should have create button', async ({ page }) => {
      // Vérifier le bouton de création
      await expect(page.locator('button:has-text("Nouvelle session"), button:has-text("New")')).toBeVisible()
    })

    test('should filter sessions by status', async ({ page }) => {
      // Cliquer sur le filtre "Actives"
      await page.click('button:has-text("Actives")')

      // Le bouton devrait être sélectionné (class active ou primary)
      const activeButton = page.locator('button:has-text("Actives")')
      await expect(activeButton).toHaveClass(/primary|active|selected/)
    })
  })

  test.describe('Create Session', () => {
    test('should open create modal', async ({ page }) => {
      await page.click('button:has-text("Nouvelle session")')

      // Vérifier que le modal est ouvert
      await expect(page.locator('.modal, [role="dialog"], .fixed.inset-0')).toBeVisible()
      await expect(page.locator('h3:has-text("Nouvelle session")')).toBeVisible()
    })

    test('should have required form fields', async ({ page }) => {
      await page.click('button:has-text("Nouvelle session")')

      // Vérifier les champs du formulaire
      await expect(page.locator('select, input').filter({ hasText: /utilisateur/i }).or(page.locator('label:has-text("Utilisateur") + select, label:has-text("Utilisateur") ~ select'))).toBeVisible()
      await expect(page.locator('select, input').filter({ hasText: /poste/i }).or(page.locator('label:has-text("Poste") + select, label:has-text("Poste") ~ select'))).toBeVisible()
      await expect(page.locator('input[type="number"]')).toBeVisible() // Durée
    })

    test('should close modal on cancel', async ({ page }) => {
      await page.click('button:has-text("Nouvelle session")')

      // Cliquer sur Annuler
      await page.click('button:has-text("Annuler")')

      // Vérifier que le modal est fermé
      await expect(page.locator('.modal, [role="dialog"]').filter({ hasText: 'Nouvelle session' })).not.toBeVisible()
    })
  })

  test.describe('Session Actions', () => {
    test('should show session details on click', async ({ page }) => {
      // Attendre que les sessions soient chargées
      await page.waitForTimeout(1000)

      // Chercher un bouton "Détails"
      const detailsButton = page.locator('button:has-text("Détails")').first()

      if (await detailsButton.isVisible()) {
        await detailsButton.click()

        // Vérifier que le modal de détails s'ouvre
        await expect(page.locator('.modal, [role="dialog"]')).toBeVisible({ timeout: 5000 })
      }
    })

    test('should show add time modal for active session', async ({ page }) => {
      // Cliquer sur filtre Actives
      await page.click('button:has-text("Actives")')
      await page.waitForTimeout(500)

      // Chercher un bouton "+ Temps"
      const addTimeButton = page.locator('button:has-text("Temps")').first()

      if (await addTimeButton.isVisible()) {
        await addTimeButton.click()

        // Vérifier que le modal s'ouvre
        await expect(page.locator('.modal:has-text("Ajouter du temps"), [role="dialog"]:has-text("Ajouter")')).toBeVisible({ timeout: 5000 })
      }
    })
  })
})

test.describe('Session Detail Modal', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, testCredentials.admin)
    await page.goto('/sessions')
  })

  test('should display session code prominently', async ({ page }) => {
    // Ouvrir le détail d'une session
    const detailsButton = page.locator('button:has-text("Détails")').first()

    if (await detailsButton.isVisible({ timeout: 5000 })) {
      await detailsButton.click()

      // Vérifier que le code est affiché
      await expect(page.locator('.font-mono, .code-acces')).toBeVisible({ timeout: 5000 })
    }
  })
})
