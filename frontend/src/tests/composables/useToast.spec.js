/**
 * Tests pour le composable useToast
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { useToast } from '@/composables/useToast'

describe('useToast', () => {
  let toast

  beforeEach(() => {
    vi.useFakeTimers()
    toast = useToast()
    toast.clear() // Nettoyer les toasts existants
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('addToast', () => {
    it('should add a toast with default values', () => {
      toast.addToast({ message: 'Test message' })

      expect(toast.toasts.value.length).toBe(1)
      expect(toast.toasts.value[0].message).toBe('Test message')
      expect(toast.toasts.value[0].type).toBe('info')
    })

    it('should add a toast with custom type', () => {
      toast.addToast({ type: 'error', message: 'Error message' })

      expect(toast.toasts.value[0].type).toBe('error')
    })

    it('should add a toast with title', () => {
      toast.addToast({ title: 'Title', message: 'Message' })

      expect(toast.toasts.value[0].title).toBe('Title')
    })

    it('should return toast id', () => {
      const id = toast.addToast({ message: 'Test' })

      expect(typeof id).toBe('number')
      expect(id).toBeGreaterThan(0)
    })

    it('should auto-remove toast after duration', () => {
      toast.addToast({ message: 'Test', duration: 1000 })

      expect(toast.toasts.value.length).toBe(1)

      vi.advanceTimersByTime(1000)

      expect(toast.toasts.value.length).toBe(0)
    })

    it('should not auto-remove if duration is 0', () => {
      toast.addToast({ message: 'Persistent', duration: 0 })

      vi.advanceTimersByTime(10000)

      expect(toast.toasts.value.length).toBe(1)
    })
  })

  describe('removeToast', () => {
    it('should remove toast by id', () => {
      const id = toast.addToast({ message: 'Test', duration: 0 })

      expect(toast.toasts.value.length).toBe(1)

      toast.removeToast(id)

      expect(toast.toasts.value.length).toBe(0)
    })

    it('should do nothing for non-existent id', () => {
      toast.addToast({ message: 'Test', duration: 0 })

      toast.removeToast(99999)

      expect(toast.toasts.value.length).toBe(1)
    })
  })

  describe('success', () => {
    it('should add a success toast', () => {
      toast.success('Success!')

      expect(toast.toasts.value[0].type).toBe('success')
      expect(toast.toasts.value[0].message).toBe('Success!')
    })

    it('should add a success toast with title', () => {
      toast.success('Message', 'Title')

      expect(toast.toasts.value[0].title).toBe('Title')
    })
  })

  describe('error', () => {
    it('should add an error toast', () => {
      toast.error('Error!')

      expect(toast.toasts.value[0].type).toBe('error')
      expect(toast.toasts.value[0].message).toBe('Error!')
    })

    it('should have default title "Erreur"', () => {
      toast.error('Something went wrong')

      expect(toast.toasts.value[0].title).toBe('Erreur')
    })

    it('should use custom title if provided', () => {
      toast.error('Message', 'Custom Title')

      expect(toast.toasts.value[0].title).toBe('Custom Title')
    })

    it('should have longer duration (8000ms)', () => {
      toast.error('Error')

      // Vérifie que le toast est toujours là après 5000ms
      vi.advanceTimersByTime(5000)
      expect(toast.toasts.value.length).toBe(1)

      // Doit disparaître après 8000ms
      vi.advanceTimersByTime(3000)
      expect(toast.toasts.value.length).toBe(0)
    })
  })

  describe('warning', () => {
    it('should add a warning toast', () => {
      toast.warning('Warning!')

      expect(toast.toasts.value[0].type).toBe('warning')
      expect(toast.toasts.value[0].message).toBe('Warning!')
    })

    it('should have default title "Attention"', () => {
      toast.warning('Be careful')

      expect(toast.toasts.value[0].title).toBe('Attention')
    })
  })

  describe('info', () => {
    it('should add an info toast', () => {
      toast.info('Information')

      expect(toast.toasts.value[0].type).toBe('info')
      expect(toast.toasts.value[0].message).toBe('Information')
    })
  })

  describe('clear', () => {
    it('should remove all toasts', () => {
      toast.addToast({ message: 'Toast 1', duration: 0 })
      toast.addToast({ message: 'Toast 2', duration: 0 })
      toast.addToast({ message: 'Toast 3', duration: 0 })

      expect(toast.toasts.value.length).toBe(3)

      toast.clear()

      expect(toast.toasts.value.length).toBe(0)
    })
  })

  describe('Multiple Toasts', () => {
    it('should handle multiple toasts', () => {
      toast.success('Success')
      toast.error('Error')
      toast.warning('Warning')
      toast.info('Info')

      expect(toast.toasts.value.length).toBe(4)
    })

    it('should assign unique ids to each toast', () => {
      const id1 = toast.addToast({ message: 'Toast 1', duration: 0 })
      const id2 = toast.addToast({ message: 'Toast 2', duration: 0 })
      const id3 = toast.addToast({ message: 'Toast 3', duration: 0 })

      expect(id1).not.toBe(id2)
      expect(id2).not.toBe(id3)
      expect(id1).not.toBe(id3)
    })
  })
})
