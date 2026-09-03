import { nextTick, onBeforeUnmount, onMounted, onUpdated, type Ref } from 'vue'

type FieldRoot = HTMLElement | { $el?: HTMLElement } | null
const fieldAttributes = ['aria-label', 'aria-labelledby', 'aria-describedby', 'aria-invalid', 'name'] as const

function resolveFieldRoot(root: FieldRoot): HTMLElement | null | undefined {
  if (!root) return root
  return (root as { $el?: HTMLElement }).$el ?? (root as HTMLElement)
}

// uni-app H5 puts fallthrough attributes on its wrapper, not on the native
// input. Keep the actual focus target named; no business state or values cross
// this adapter. Callers include it only in H5 builds.
export function syncNativeFieldA11y(root: FieldRoot) {
  const element = resolveFieldRoot(root)
  if (!element || !('querySelectorAll' in element)) return
  for (const wrapper of Array.from(element.querySelectorAll('uni-input, uni-textarea'))) {
    const input = wrapper.querySelector('input, textarea')
    if (!input) continue
    for (const attribute of fieldAttributes) {
      const value = wrapper.getAttribute(attribute)
      if (value === null) input.removeAttribute(attribute)
      else input.setAttribute(attribute, value)
    }
    const nativeName = wrapper.getAttribute('data-native-name')
    if (nativeName !== null) input.setAttribute('name', nativeName)
  }
}

export function useNativeFieldA11y(root: Ref<FieldRoot>) {
  let disconnectObserver: (() => void) | undefined
  const syncAfterChildren = () => {
    syncNativeFieldA11y(root.value)
    // uni-input/textarea update their internal native field after the parent
    // branch switches. Repeat after Vue flushes that child update.
    void nextTick(() => syncNativeFieldA11y(root.value))
  }
  onMounted(() => {
    syncAfterChildren()
    const element = resolveFieldRoot(root.value)
    const Observer = globalThis.MutationObserver
    if (!element || !Observer) return
    const observer = new Observer(() => syncNativeFieldA11y(root.value))
    observer.observe(element, { childList: true, subtree: true })
    disconnectObserver = () => observer.disconnect()
  })
  onUpdated(syncAfterChildren)
  onBeforeUnmount(() => disconnectObserver?.())
}
