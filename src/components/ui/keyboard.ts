/** uni-app renders H5 buttons as custom elements without native keyboard activation. */
export function activateButtonOnKey(event: KeyboardEvent): void {
  if (event.key !== 'Enter' && event.key !== ' ') return
  let button = event.currentTarget as HTMLElement | null
  // H5 normalizes uni-component event targets to { id, dataset, ... }.
  // The focused control is the actual DOM target of a keyboard activation.
  // #ifdef H5
  if (!button?.tagName) button = globalThis.document?.activeElement as HTMLElement | null
  // #endif
  // Native buttons already synthesize clicks; leave their default behavior intact.
  if (button?.tagName?.toLowerCase() !== 'uni-button') return
  event.preventDefault()
  const disabled = button.getAttribute('disabled')
  if (disabled !== null && disabled !== 'false') return
  button.click()
}
