/**
 * Fixtures d'authentification pour les tests E2E
 */

export const testCredentials = {
  admin: {
    username: 'admin',
    password: 'admin123'
  },
  operator: {
    username: 'operator',
    password: 'operator123'
  }
}

/**
 * Helper pour se connecter
 * @param {import('@playwright/test').Page} page
 * @param {Object} credentials
 */
export async function login(page, credentials = testCredentials.admin) {
  await page.goto('/login')
  await page.fill('input[name="username"], input[type="text"]', credentials.username)
  await page.fill('input[name="password"], input[type="password"]', credentials.password)
  await page.click('button[type="submit"]')

  // Attendre la redirection après login
  await page.waitForURL('**/*', { timeout: 10000 })
}

/**
 * Helper pour se déconnecter
 * @param {import('@playwright/test').Page} page
 */
export async function logout(page) {
  // Trouver et cliquer sur le bouton de déconnexion
  const logoutButton = page.locator('button:has-text("Déconnexion"), a:has-text("Déconnexion")')
  if (await logoutButton.isVisible()) {
    await logoutButton.click()
  }
}

/**
 * Helper pour vérifier si connecté
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<boolean>}
 */
export async function isLoggedIn(page) {
  // Vérifier la présence d'éléments qui n'apparaissent qu'une fois connecté
  const dashboardElement = page.locator('[data-testid="dashboard"], nav, .main-layout')
  return await dashboardElement.isVisible({ timeout: 5000 }).catch(() => false)
}
