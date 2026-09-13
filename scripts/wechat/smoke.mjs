import assert from 'node:assert/strict'
import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { Launcher } from '@weapp-vite/miniprogram-automator'
import { diagnose } from './doctor.mjs'

// Background-only login regression. It stays inside the already-open Developer
// Tools session and uses only rendered buttons; no route, storage, or page-method
// shortcuts are used.
await diagnose({ probe: false })

const port = Number(process.env.WECHAT_AUTO_PORT || 9420)
const root = fileURLToPath(new URL('../../', import.meta.url))
const output = resolve(root, 'output/wechat', `login-${Date.now()}`)
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

async function openStudentPbl(page, miniProgram) {
  if (page.path === 'pages/student/pbl/pbl') return page
  const studentNav = await findComponentRoot(page, '.student-nav')
  assert.ok(studentNav, 'The student navigation is not rendered.')
  const items = await within(studentNav.$$('.student-nav__item'), 'student-navigation-items')
  const labels = await Promise.all(items.map((item) => within(item.text(), 'student-navigation-label')))
  const pblIndex = labels.findIndex((label) => label.includes('研讨'))
  assert.notEqual(pblIndex, -1, 'The student navigation has no discussion entry.')
  await within(items[pblIndex].tap(), 'student-pbl-tap')
  return currentPageEventually(miniProgram, 'pages/student/pbl/pbl')
}

async function captureBackgroundScreenshot(path) {
  let lastError
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const socket = new WebSocket(`ws://127.0.0.1:${port}`)
    try {
      const data = await new Promise((resolveCapture, rejectCapture) => {
        const timer = setTimeout(() => rejectCapture(new Error('timeout:capture-screenshot')), 30000)
        const finish = (result) => {
          clearTimeout(timer)
          if (result instanceof Error) rejectCapture(result)
          else resolveCapture(result)
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
      await new Promise((resolveWait) => setTimeout(resolveWait, 750))
    } finally {
      socket.close()
    }
  }
  throw lastError
}

let miniProgram
try {
  console.log('STEP connect')
  miniProgram = await within(new Launcher().connect({ wsEndpoint: `ws://127.0.0.1:${port}` }), 'connect')
  mkdirSync(output, { recursive: true })
  let page = await within(miniProgram.currentPage(), 'initial-page')
  if (page.path === 'pages/teacher/index/index') {
    console.log('STEP logout-teacher')
    const logout = await within(page.$('.logout', { fallback: false, timeout: timeoutMs }), 'teacher-logout')
    assert.ok(logout, 'The teacher logout control is not rendered.')
    await within(logout.tap(), 'teacher-logout-tap')
    page = await currentPageEventually(miniProgram, 'pages/login/login')
  } else if (page.path !== 'pages/login/login') {
    console.log('STEP return-to-student-pbl')
    page = await openStudentPbl(page, miniProgram)
    console.log('STEP logout-student')
    const actions = await within(
      page.$$('.account-bar button', { fallback: false, timeout: timeoutMs }),
      'student-actions',
    )
    assert.equal(actions.length, 2, 'The student account actions are incomplete.')
    await within(actions[1].tap(), 'student-logout-tap')
    page = await currentPageEventually(miniProgram, 'pages/login/login')
  }

  console.log('STEP screenshot-login')
  await captureBackgroundScreenshot(resolve(output, 'login.png'))
  for (const role of ['student', 'teacher']) {
    const button = await within(
      page.$(`.role-button.${role}`, { fallback: false, timeout: timeoutMs }),
      `${role}-button`,
    )
    assert.ok(button, `${role} button missing`)
    const size = await within(button.size(), `${role}-size`)
    assert.ok(Number(size.width) > 0 && Number(size.height) > 0, `${role} button has no rendered size`)
  }

  console.log('STEP login-teacher')
  const teacher = await within(
    page.$('.role-button.teacher', { fallback: false, timeout: timeoutMs }),
    'teacher-button',
  )
  await within(teacher.tap(), 'teacher-login-tap')
  page = await currentPageEventually(miniProgram, 'pages/teacher/index/index')
  console.log('STEP screenshot-teacher-overview')
  await captureBackgroundScreenshot(resolve(output, 'teacher-overview.png'))
  console.log(
    JSON.stringify({
      result: 'login-real-taps-passed',
      screenshots: [resolve(output, 'login.png'), resolve(output, 'teacher-overview.png')],
      physicalDevices: 'not-tested',
    }),
  )
} catch (error) {
  const safeMessage =
    error instanceof Error && /^(timeout:|capture-screenshot-)/.test(error.message) ? error.message : undefined
  console.error(error instanceof assert.AssertionError ? error.message : safeMessage || 'FAIL: Login smoke failed.')
  process.exitCode = 1
} finally {
  miniProgram?.disconnect()
}
