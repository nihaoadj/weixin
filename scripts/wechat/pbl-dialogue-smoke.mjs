import assert from 'node:assert/strict'
import { Launcher } from '@weapp-vite/miniprogram-automator'
import { diagnose } from './doctor.mjs'

// Creates one new Demo-only dialogue using visible controls. It never reads,
// logs, screenshots, clears, or alters existing dialogue content.
await diagnose({ probe: false })

const port = Number(process.env.WECHAT_AUTO_PORT || 9420)
const timeoutMs = 10000
const within = (promise, label, limit = timeoutMs) =>
  Promise.race([promise, new Promise((_, reject) => setTimeout(() => reject(new Error(`timeout:${label}`)), limit))])

async function currentPageEventually(miniProgram, expectedPath) {
  for (let attempt = 0; attempt < 20; attempt += 1) {
    const page = await within(miniProgram.currentPage(), `current-page:${expectedPath}`)
    if (page.path === expectedPath) return page
    await new Promise((resolveWait) => setTimeout(resolveWait, 250))
  }
  throw new Error(`The expected route was not opened: ${expectedPath}`)
}

async function findComponentRoot(page, selector) {
  const queue = [...(await within(page.$$('component', { fallback: false, timeout: timeoutMs }), `hosts:${selector}`))]
  const seen = new Set()
  while (queue.length) {
    const host = queue.shift()
    if (!host || seen.has(host)) continue
    seen.add(host)
    const rootElement = await within(host.$(selector), `component-root:${selector}`)
    if (rootElement) return rootElement
    queue.push(...(await within(host.$$('component'), `nested-hosts:${selector}`)))
  }
  return null
}

async function elementEventually(page, selector, label) {
  for (let attempt = 0; attempt < 20; attempt += 1) {
    const element = await within(page.$(selector, { fallback: false, timeout: timeoutMs }), label)
    if (element) return element
    await new Promise((resolveWait) => setTimeout(resolveWait, 250))
  }
  return null
}

let miniProgram
try {
  console.log('STEP connect')
  miniProgram = await within(new Launcher().connect({ wsEndpoint: `ws://127.0.0.1:${port}` }), 'connect')
  let page = await within(miniProgram.currentPage(), 'initial-page')
  if (page.path === 'pages/teacher/index/index') {
    console.log('STEP logout-teacher')
    const logout = await within(page.$('.logout', { fallback: false, timeout: timeoutMs }), 'teacher-logout')
    assert.ok(logout, 'The teacher logout control is not rendered.')
    await within(logout.tap(), 'teacher-logout-tap')
    page = await currentPageEventually(miniProgram, 'pages/login/login')
  }
  if (page.path === 'pages/login/login') {
    console.log('STEP login-student')
    const student = await within(
      page.$('.role-button.student', { fallback: false, timeout: timeoutMs }),
      'student-role',
    )
    assert.ok(student, 'The student role button is not rendered.')
    await within(student.tap(), 'student-role-tap')
    page = await currentPageEventually(miniProgram, 'pages/student/pbl/pbl')
  }
  if (page.path !== 'pages/student/pbl/pbl') {
    console.log('STEP open-pbl')
    const nav = await findComponentRoot(page, '.student-nav')
    assert.ok(nav, 'The student navigation is not rendered.')
    const items = await within(nav.$$('.student-nav__item'), 'student-navigation-items')
    const labels = await Promise.all(items.map((item) => within(item.text(), 'student-navigation-label')))
    const index = labels.findIndex((label) => label.includes('研讨'))
    assert.notEqual(index, -1, 'The student navigation has no discussion entry.')
    await within(items[index].tap(), 'student-pbl-tap')
    page = await currentPageEventually(miniProgram, 'pages/student/pbl/pbl')
  }

  console.log('STEP open-new-dialogue')
  await within(new Promise((resolveWait) => setTimeout(resolveWait, 750)), 'pbl-initial-render')
  const newDialogue = await elementEventually(page, '.new-action', 'new-dialogue')
  if (newDialogue) await within(newDialogue.tap(), 'new-dialogue-tap')
  const chip = await elementEventually(page, '.choice-chip', 'knowledge-point')
  assert.ok(chip, 'The new dialogue knowledge-point choice is not rendered.')
  await within(chip.tap(), 'knowledge-point-tap')
  const create = await elementEventually(page, '.launch-card .primary-action', 'create-dialogue')
  assert.ok(create, 'The new dialogue confirmation is not rendered.')
  await within(create.tap(), 'create-dialogue-tap')
  await within(new Promise((resolveWait) => setTimeout(resolveWait, 1000)), 'created-dialogue-render')

  for (let phase = 1; phase <= 4; phase += 1) {
    console.log(`STEP phase-${phase}`)
    const composer = await findComponentRoot(page, '.composer')
    assert.ok(composer, 'The dialogue composer is not rendered.')
    const input = await within(composer.$('.message-input'), `phase-${phase}-input`)
    assert.ok(input, 'The dialogue input is not rendered.')
    await within(input.input(`阶段 ${phase} 的合成病理学习证据。`), `phase-${phase}-input-action`)
    const send = await within(composer.$('.send-button'), `phase-${phase}-send`)
    assert.ok(send, 'The dialogue send action is not rendered.')
    await within(send.tap(), `phase-${phase}-send-tap`)
    await within(new Promise((resolveWait) => setTimeout(resolveWait, 500)), `phase-${phase}-settle`)
  }

  const locked = await elementEventually(page, '.locked-bar', 'completed-dialogue')
  assert.ok(locked, 'The four-stage dialogue did not reach its locked completed state.')
  console.log(JSON.stringify({ result: 'pbl-four-stage-real-input-passed', physicalDevices: 'not-tested' }))
} catch (error) {
  const safeMessage = error instanceof Error && error.message.startsWith('timeout:') ? error.message : undefined
  console.error(
    error instanceof assert.AssertionError ? error.message : safeMessage || 'FAIL: PBL dialogue smoke failed.',
  )
  process.exitCode = 1
} finally {
  miniProgram?.disconnect()
}
