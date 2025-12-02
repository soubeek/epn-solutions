/**
 * Tests pour le composant ConfirmModal
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ConfirmModal from '@/components/common/ConfirmModal.vue'

describe('ConfirmModal', () => {
  const defaultProps = {
    modelValue: true,
    title: 'Test Title',
    message: 'Test Message'
  }

  describe('Rendering', () => {
    it('should render when modelValue is true', () => {
      const wrapper = mount(ConfirmModal, {
        props: defaultProps
      })

      expect(wrapper.text()).toContain('Test Title')
      expect(wrapper.text()).toContain('Test Message')
    })

    it('should not render when modelValue is false', () => {
      const wrapper = mount(ConfirmModal, {
        props: {
          ...defaultProps,
          modelValue: false
        }
      })

      expect(wrapper.find('.fixed').exists()).toBe(false)
    })

    it('should render default button texts', () => {
      const wrapper = mount(ConfirmModal, {
        props: defaultProps
      })

      expect(wrapper.text()).toContain('Confirmer')
      expect(wrapper.text()).toContain('Annuler')
    })

    it('should render custom button texts', () => {
      const wrapper = mount(ConfirmModal, {
        props: {
          ...defaultProps,
          confirmText: 'Yes',
          cancelText: 'No'
        }
      })

      expect(wrapper.text()).toContain('Yes')
      expect(wrapper.text()).toContain('No')
    })
  })

  describe('Events', () => {
    it('should emit confirm when confirm button clicked', async () => {
      const wrapper = mount(ConfirmModal, {
        props: defaultProps
      })

      const confirmButton = wrapper.findAll('button').find(btn =>
        btn.text().includes('Confirmer')
      )
      await confirmButton.trigger('click')

      expect(wrapper.emitted('confirm')).toBeTruthy()
      // Note: handleConfirm only emits 'confirm', not 'update:modelValue'
      // The parent component is responsible for closing the modal after confirmation
    })

    it('should emit cancel when cancel button clicked', async () => {
      const wrapper = mount(ConfirmModal, {
        props: defaultProps
      })

      const cancelButton = wrapper.findAll('button').find(btn =>
        btn.text().includes('Annuler')
      )
      await cancelButton.trigger('click')

      expect(wrapper.emitted('cancel')).toBeTruthy()
      expect(wrapper.emitted('update:modelValue')).toBeTruthy()
      expect(wrapper.emitted('update:modelValue')[0]).toEqual([false])
    })

    it('should close when clicking overlay', async () => {
      const wrapper = mount(ConfirmModal, {
        props: defaultProps
      })

      // Trouver l'overlay (le premier div fixed)
      const overlay = wrapper.find('.fixed')
      await overlay.trigger('click')

      expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    })
  })

  describe('Types', () => {
    it('should apply info styling for info type', () => {
      const wrapper = mount(ConfirmModal, {
        props: {
          ...defaultProps,
          type: 'info'
        }
      })

      expect(wrapper.html()).toContain('bg-blue')
    })

    it('should apply warning styling for warning type', () => {
      const wrapper = mount(ConfirmModal, {
        props: {
          ...defaultProps,
          type: 'warning'
        }
      })

      expect(wrapper.html()).toContain('bg-yellow')
    })

    it('should apply danger styling for danger type', () => {
      const wrapper = mount(ConfirmModal, {
        props: {
          ...defaultProps,
          type: 'danger'
        }
      })

      expect(wrapper.html()).toContain('bg-red')
    })
  })
})
