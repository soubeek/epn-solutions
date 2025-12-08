/**
 * Logger conditionnel pour le frontend
 * N'affiche les logs qu'en mode développement
 */

const isDev = import.meta.env.DEV

export const logger = {
  log: (...args) => isDev && console.log(...args),
  info: (...args) => isDev && console.info(...args),
  warn: (...args) => isDev && console.warn(...args),
  error: (...args) => isDev && console.error(...args),
  debug: (...args) => isDev && console.debug(...args),

  // Logger avec préfixe pour les modules
  withPrefix: (prefix) => ({
    log: (...args) => isDev && console.log(`[${prefix}]`, ...args),
    info: (...args) => isDev && console.info(`[${prefix}]`, ...args),
    warn: (...args) => isDev && console.warn(`[${prefix}]`, ...args),
    error: (...args) => isDev && console.error(`[${prefix}]`, ...args),
    debug: (...args) => isDev && console.debug(`[${prefix}]`, ...args)
  })
}

export default logger
