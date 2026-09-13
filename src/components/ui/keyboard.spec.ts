import { describe, expect, it, vi } from 'vitest'
import { activateButtonOnKey, activatePickerOnKey } from './keyboard'

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
})

describe('uni-app picker keyboard activation', () => {
  it.each(['Enter', ' '])('activates a focusable picker with %s', (key) => {
    const action = keyEvent('UNI-PICKER', key)
    activatePickerOnKey(action.event)
    expect(action.click).toHaveBeenCalledOnce()
    expect(action.preventDefault).toHaveBeenCalledOnce()
  })

  it('ignores unrelated keys', () => {
    const action = keyEvent('UNI-PICKER', 'Escape')
    activatePickerOnKey(action.event)
    expect(action.click).not.toHaveBeenCalled()
    expect(action.preventDefault).not.toHaveBeenCalled()
  })

  it('does not activate a disabled picker', () => {
    const action = keyEvent('UNI-PICKER', 'Enter', 'true')
    activatePickerOnKey(action.event)
    expect(action.click).not.toHaveBeenCalled()
  })
})
