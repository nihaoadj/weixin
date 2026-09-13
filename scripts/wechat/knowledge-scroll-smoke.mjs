import assert from 'node:assert/strict'
import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { Launcher } from '@weapp-vite/miniprogram-automator'
import { diagnose } from './doctor.mjs'

// Background-only long-content check. It uses rendered actions and the
// Developer Tools page-scroll primitive; no page data or business method is read.
await diagnose({ probe: false })

const port = Number(process.env.WECHAT_AUTO_PORT || 9420)
const root = fileURLToPath(new URL('../../', import.meta.url))
const output = resolve(root, 'output/wechat', `knowledge-scroll-${Date.now()}`)
const timeoutMs = 10000
const within = (promise, label, limit = timeoutMs) =>
  Promise.race([promise, new Promise((_, reject) => setTimeout(() => reject(new Error(`timeout:${label}`)), limit))])
const wait = (milliseconds) => new Promise((resolveWait) => setTimeout(resolveWait, milliseconds))

async function current(miniProgram, expectedPath) {
  for (let attempt = 0; attempt < 24; attempt += 1) {
    const page = await within(miniProgram.currentPage(), `page:${expectedPath}`)
    if (page.path === expectedPath) return page
    await wait(250)
  }
  throw new Error(`route:${expectedPath}`)
}

async function component(page, selector) {
  const queue = [...(await within(page.$$('component', { fallback: false }), `hosts:${selector}`))]
  const seen = new Set()
  while (queue.length) {
    const host = queue.shift()
    if (!host || seen.has(host)) continue
    seen.add(host)
    const found = await within(host.$(selector), `component:${selector}`)
    if (found) return found
    queue.push(...(await within(host.$$('component'), `nested:${selector}`)))
  }
  return null
}

async function captureBackgroundScreenshot(path) {
  let lastError
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const socket = new WebSocket(`ws://127.0.0.1:${port}`)
    try {
      const data = await new Promise((resolveCapture, rejectCapture) => {
        const timer = setTimeout(() => rejectCapture(new Error('timeout:capture-screenshot')), 30000)
        const finish = (value) => {
          clearTimeout(timer)
          if (value instanceof Error) rejectCapture(value)
          else resolveCapture(value)
        }
        socket.onerror = () => finish(new Error('capture-screenshot-unavailable'))
        socket.onopen = () =>
          socket.send(JSON.stringify({ id: 'background-screenshot', method: 'App.captureScreenshot', params: {} }))
        socket.onmessage = ({ data: payload }) => {
          try {
            const response = JSON.parse(String(payload))
            if (response.id !== 'background-screenshot') return
            if (typeof response.result?.data !== 'string') return finish(new Error('capture-screenshot-missing-data'))
            finish(response.result.data)
          } catch {
            finish(new Error('capture-screenshot-invalid-response'))
          }
        }
      })
      writeFileSync(path, data, 'base64')
      return
    } catch (error) {
      lastError = error
      await wait(750)
    } finally {
      socket.close()
    }
  }
  throw lastError
}

async function openLearning(miniProgram, page) {
  if (page.path === 'pages/teacher/index/index') {
    const logout = await within(page.$('.logout', { fallback: false }), 'teacher-logout')
    assert.ok(logout, 'The teacher logout control is not rendered.')
    await within(logout.tap(), 'teacher-logout-tap')
    page = await current(miniProgram, 'pages/login/login')
  }
  if (page.path === 'pages/login/login') {
    const student = await within(page.$('.role-button.student', { fallback: false }), 'student-role')
    assert.ok(student, 'The student role button is not rendered.')
    await within(student.tap(), 'student-role-tap')
    page = await current(miniProgram, 'pages/student/pbl/pbl')
  }
  if (page.path === 'pages/student/case-report/case-report') {
    const actions = await within(page.$$('.secondary', { fallback: false }), 'case-report-secondary-actions')
    assert.ok(actions[0], 'The case-report learning action is not rendered.')
    await within(actions[0].tap(), 'case-report-learning-tap')
    page = await current(miniProgram, 'pages/student/learning/index')
  }
  if (page.path === 'pages/student/learning/index') return page
  const nav = await component(page, '.student-nav')
  assert.ok(nav, 'The student navigation is not rendered.')
  const items = await within(nav.$$('.student-nav__item'), 'student-navigation-items')
  const labels = await Promise.all(items.map((item) => within(item.text(), 'student-navigation-label')))
  const index = labels.findIndex((label) => label.includes('学习'))
  assert.notEqual(index, -1, 'The student navigation has no learning entry.')
  await within(items[index].tap(), 'student-learning-tap')
  return current(miniProgram, 'pages/student/learning/index')
}

let miniProgram
try {
  console.log('STEP connect')
  miniProgram = await within(new Launcher().connect({ wsEndpoint: `ws://127.0.0.1:${port}` }), 'connect')
  mkdirSync(output, { recursive: true })
  let page = await within(miniProgram.currentPage(), 'initial-page')
  if (page.path !== 'pages/student/question/question') {
    console.log('STEP open-learning')
    page = await openLearning(miniProgram, page)
    console.log('STEP open-resources')
    const resource = await within(page.$('.resource-row', { fallback: false }), 'case-training-resource')
    assert.ok(resource, 'The learning resource entry is not rendered.')
    await within(resource.tap(), 'case-training-resource-tap')
    page = await current(miniProgram, 'pages/student/question/question')
  }
  const tabs = await within(page.$$('.resource-tab', { fallback: false }), 'resource-tabs')
  assert.equal(tabs.length, 3, 'The resource page must show its three tabs.')
  console.log('STEP open-knowledge')
  await within(tabs[1].tap(), 'knowledge-tab-tap')
  await wait(500)
  const tree = await component(page, '.knowledge-tree')
  assert.ok(tree, 'The knowledge tree is not rendered.')
  const top = resolve(output, 'knowledge-top.png')
  await within(miniProgram.pageScrollTo(0), 'knowledge-page-scroll-top')
  await wait(750)
  await captureBackgroundScreenshot(top)
  const before = Number(await within(page.scrollTop(), 'knowledge-scroll-top-before'))
  console.log('STEP scroll-to-bottom')
  await within(miniProgram.pageScrollTo(100000), 'knowledge-page-scroll')
  await wait(1250)
  const after = Number(await within(page.scrollTop(), 'knowledge-scroll-top-after'))
  assert.ok(after > before, 'The knowledge page did not move toward its long-content end.')
  const reference = await within(tree.$('.tree-reference'), 'knowledge-reference')
  assert.ok(reference, 'The knowledge tree reference is not rendered.')
  const size = await within(reference.size(), 'knowledge-reference-size')
  assert.ok(Number(size.width) > 0 && Number(size.height) > 0, 'The knowledge reference has no rendered size.')
  const nav = await component(page, '.student-primary-nav')
  assert.ok(nav, 'The fixed student navigation is not rendered after scrolling.')
  const navSize = await within(nav.size(), 'student-navigation-size')
  assert.ok(
    Number(navSize.width) > 0 && Number(navSize.height) > 0,
    'The fixed student navigation has no rendered size.',
  )
  const bottom = resolve(output, 'knowledge-bottom.png')
  await captureBackgroundScreenshot(bottom)
  console.log(
    JSON.stringify({
      result: 'knowledge-long-content-scroll-passed',
      screenshots: [top, bottom],
      physicalDevices: 'not-tested',
    }),
  )
} catch (error) {
  const safeMessage = error instanceof Error && error.message.startsWith('timeout:') ? error.message : undefined
  console.error(
    error instanceof assert.AssertionError ? error.message : safeMessage || 'FAIL: Knowledge scroll smoke failed.',
  )
  process.exitCode = 1
} finally {
  miniProgram?.disconnect()
}
