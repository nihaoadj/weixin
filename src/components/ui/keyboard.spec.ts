import { describe, expect, it, vi } from 'vitest'
import { activateButtonOnKey } from './keyboard'

function keyEvent(tagName: string, key: string, disabled: string | null = null) {
  const click = vi.fn()
  const preventDefault = vi.fn()
  const event = { key, preventDefault, currentTarget: { tagName, getAttribute: () => disabled, click } }
  return { event: event as unknown as KeyboardEvent, click, preventDefault }
}

describe('uni-app button keyboard activation', () => {
  it.each(['Enter', ' '])('activates a custom button with %s', (key) => {
    const action = keyEvent('UNI-BUTTON', key)
    activateButtonOnKey(action.event)
    expect(action.click).toHaveBeenCalledOnce()
    expect(action.preventDefault).toHaveBeenCalledOnce()
  })

  it('preserves native button behavior and ignores unrelated keys', () => {
    for (const action of [keyEvent('BUTTON', 'Enter'), keyEvent('UNI-BUTTON', 'Escape')]) {
      activateButtonOnKey(action.event)
      expect(action.click).not.toHaveBeenCalled()
      expect(action.preventDefault).not.toHaveBeenCalled()
    }
  })

  it('does not activate disabled custom buttons', () => {
    const action = keyEvent('UNI-BUTTON', ' ', 'true')
    activateButtonOnKey(action.event)
    expect(action.click).not.toHaveBeenCalled()
  })

  it('handles uni-app normalized targets through the focused H5 button', () => {
    const button = globalThis.document.createElement('uni-button')
    button.tabIndex = 0
    const clicked = vi.fn()
    button.addEventListener('click', clicked)
    globalThis.document.body.append(button)
    button.focus()
    try {
      const event = { key: 'Enter', preventDefault: vi.fn(), currentTarget: { id: '', dataset: {} } }
      activateButtonOnKey(event as unknown as KeyboardEvent)
      expect(clicked).toHaveBeenCalledOnce()
      expect(event.preventDefault).toHaveBeenCalledOnce()
    } finally {
      button.remove()
    }
  })
})
