/** Activates custom uni-app controls from keyboard-like events when the host exposes them. */
export function activateButtonOnKey(event: KeyboardEvent): void {
  if (event.key !== 'Enter' && event.key !== ' ') return
  const button = event.currentTarget as HTMLElement | null
  // Native buttons already synthesize clicks; leave their default behavior intact.
  if (button?.tagName?.toLowerCase() !== 'uni-button') return
  event.preventDefault()
  const disabled = button.getAttribute('disabled')
  if (disabled !== null && disabled !== 'false') return
  button.click()
}

/** Activates focusable uni-app picker controls when the host exposes keyboard-like events. */
export function activatePickerOnKey(event: KeyboardEvent): void {
  if (event.key !== 'Enter' && event.key !== ' ') return
  const picker = event.currentTarget as HTMLElement | null
  if (!picker?.click) return
  const disabled = picker.getAttribute?.('disabled')
  if (disabled !== null && disabled !== 'false') return
  event.preventDefault()
  picker.click()
}
