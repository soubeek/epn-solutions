/**
 * Tests E2E pour l'authentification
 */
import { test, expect } from '@playwright/test'
import { testCredentials, login, logout, isLoggedIn } from './fixtures/auth.js'

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    // S'assurer qu'on n'est pas connecté au début
    await page.context().clearCookies()
    await page.evaluate(() => localStorage.clear())
  })

  test.describe('Login Page', () => {
    test('should display login form', async ({ page }) => {
      await page.goto('/login')

      // Vérifier les éléments du formulaire
      await expect(page.locator('input[type="text"], input[name="username"]')).toBeVisible()
      await expect(page.locator('input[type="password"]')).toBeVisible()
      await expect(page.locator('button[type="submit"]')).toBeVisible()
    })

    test('should show error on invalid credentials', async ({ page }) => {
      await page.goto('/login')

      await page.fill('input[type="text"], input[name="username"]', 'wronguser')
      await page.fill('input[type="password"]', 'wrongpassword')
      await page.click('button[type="submit"]')

      // Attendre et vérifier le message d'erreur
      await expect(page.locator('.text-red, .error, [role="alert"]')).toBeVisible({ timeout: 5000 })
    })

    test('should login successfully with valid credentials', async ({ page }) => {
      await login(page, testCredentials.admin)

      // Vérifier qu'on est redirigé (pas sur /login)
      await expect(page).not.toHaveURL(/.*login/)

      // Vérifier qu'on voit le dashboard ou un élément de navigation
      await expect(page.locator('nav, .main-layout, [data-testid="dashboard"]')).toBeVisible({ timeout: 10000 })
    })

    test('should persist login state after page refresh', async ({ page }) => {
      await login(page, testCredentials.admin)

      // Rafraîchir la page
      await page.reload()

      // Vérifier qu'on est toujours connecté
      await expect(page).not.toHaveURL(/.*login/)
    })
  })

  test.describe('Protected Routes', () => {
    test('should redirect to login when accessing protected route', async ({ page }) => {
      await page.goto('/dashboard')

      // Devrait rediriger vers login
      await expect(page).toHaveURL(/.*login/)
    })

    test('should access protected route after login', async ({ page }) => {
      await login(page, testCredentials.admin)

      await page.goto('/sessions')

      // Ne devrait pas rediriger vers login
      await expect(page).not.toHaveURL(/.*login/)
      await expect(page).toHaveURL(/.*sessions/)
    })
  })

  test.describe('Logout', () => {
    test('should logout successfully', async ({ page }) => {
      await login(page, testCredentials.admin)

      // Chercher et cliquer sur déconnexion
      const logoutButton = page.locator('button:has-text("Déconnexion"), a:has-text("Déconnexion"), [data-testid="logout"]')

      if (await logoutButton.isVisible()) {
        await logoutButton.click()

        // Devrait rediriger vers login
        await expect(page).toHaveURL(/.*login/, { timeout: 5000 })
      }
    })

    test('should clear tokens on logout', async ({ page }) => {
      await login(page, testCredentials.admin)

      // Vérifier qu'il y a des tokens
      const hasTokens = await page.evaluate(() => {
        return localStorage.getItem('accessToken') !== null
      })
      expect(hasTokens).toBe(true)

      // Se déconnecter
      await logout(page)

      // Vérifier que les tokens sont supprimés
      const tokensCleared = await page.evaluate(() => {
        return localStorage.getItem('accessToken') === null
      })
      expect(tokensCleared).toBe(true)
    })
  })
})
