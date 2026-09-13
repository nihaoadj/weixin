import assert from 'node:assert/strict'
import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { Launcher } from '@weapp-vite/miniprogram-automator'
import { diagnose } from './doctor.mjs'

// Background-only workflow: use visible controls to switch from the current
// teacher Demo session to the student Demo session and inspect public screens.
// It never clears storage, invokes page methods, or captures sensitive content.
await diagnose({ probe: false })

const port = Number(process.env.WECHAT_AUTO_PORT || 9420)
const root = fileURLToPath(new URL('../../', import.meta.url))
const output = resolve(root, 'output/wechat', `student-navigation-${Date.now()}`)
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
  const initialHosts = await within(page.$$('component', { fallback: false, timeout: timeoutMs }), `hosts:${selector}`)
  const queue = [...initialHosts]
  const seen = new Set()
  while (queue.length) {
    const host = queue.shift()
    if (!host || seen.has(host)) continue
    seen.add(host)
    const rootElement = await within(host.$(selector), `component-root:${selector}`)
    if (rootElement) return rootElement
    const children = await within(host.$$('component'), `nested-hosts:${selector}`)
    queue.push(...children)
  }
  return null
}

async function openStudentPrimary(page, key, expectedPath) {
  const studentNav = await findComponentRoot(page, '.student-nav')
  assert.ok(studentNav, 'The student navigation is not rendered.')
  const studentItems = await within(studentNav.$$('.student-nav__item'), 'student-navigation-items')
  assert.equal(studentItems.length, 3, 'The student navigation must expose exactly three workspaces.')
  const labels = await Promise.all(
    studentItems.map((candidate) => within(candidate.text(), 'student-navigation-label')),
  )
  const index = labels.findIndex((label) => label.includes(key))
  assert.notEqual(index, -1, `The student navigation has no ${key} entry.`)
  await within(studentItems[index].tap(), `student-${key}-tap`)
  return currentPageEventually(miniProgram, expectedPath)
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
    const logout = await within(page.$('.logout', { fallback: false, timeout: timeoutMs }), 'logout-control')
    assert.ok(logout, 'The teacher logout control is not rendered.')
    await within(logout.tap(), 'logout-tap')
    page = await currentPageEventually(miniProgram, 'pages/login/login')
  }
  if (page.path === 'pages/login/login') {
    console.log('STEP screenshot-login')
    await captureBackgroundScreenshot(resolve(output, 'login.png'))
    const studentRole = await within(
      page.$('.role-button.student', { fallback: false, timeout: timeoutMs }),
      'student-role',
    )
    assert.ok(studentRole, 'The student role button is not rendered.')
    assert.match(await within(studentRole.text(), 'student-role-label'), /学生/)
    console.log('STEP login-student')
    await within(studentRole.tap(), 'student-role-tap')
    page = await currentPageEventually(miniProgram, 'pages/student/pbl/pbl')
  }
  if (page.path !== 'pages/student/pbl/pbl') {
    console.log('STEP return-to-student-pbl')
    page = await openStudentPrimary(page, '研讨', 'pages/student/pbl/pbl')
  }

  console.log('STEP open-learning')
  page = await openStudentPrimary(page, '学习', 'pages/student/learning/index')
  console.log('STEP screenshot-learning')
  await captureBackgroundScreenshot(resolve(output, 'learning.png'))

  console.log('STEP open-case-training')
  const resource = await within(
    page.$('.resource-row', { fallback: false, timeout: timeoutMs }),
    'case-training-resource',
  )
  assert.ok(resource, 'The case training resource is not rendered.')
  assert.match(await within(resource.text(), 'case-training-label'), /病例训练/)
  await within(resource.tap(), 'case-training-tap')
  page = await currentPageEventually(miniProgram, 'pages/student/question/question')
  console.log('STEP screenshot-cases')
  await captureBackgroundScreenshot(resolve(output, 'cases.png'))

  console.log('STEP switch-resource-tabs')
  const tabs = await within(page.$$('.resource-tab', { fallback: false, timeout: timeoutMs }), 'resource-tabs')
  assert.equal(tabs.length, 3, 'The resource page must expose cases, knowledge, and practice tabs.')
  assert.match(await within(tabs[0].text(), 'cases-tab-label'), /病例/)
  assert.match(await within(tabs[1].text(), 'knowledge-tab-label'), /知识/)
  assert.match(await within(tabs[2].text(), 'practice-tab-label'), /练习/)
  await within(tabs[1].tap(), 'knowledge-tab-tap')
  await within(new Promise((resolveWait) => setTimeout(resolveWait, 400)), 'knowledge-tab-render')
  console.log('STEP screenshot-knowledge')
  await captureBackgroundScreenshot(resolve(output, 'knowledge.png'))
  await within(tabs[2].tap(), 'practice-tab-tap')
  await within(new Promise((resolveWait) => setTimeout(resolveWait, 400)), 'practice-tab-render')
  console.log('STEP screenshot-practice')
  await captureBackgroundScreenshot(resolve(output, 'practice.png'))

  console.log(
    JSON.stringify({
      result: 'student-navigation-real-taps-passed',
      screenshots: [
        resolve(output, 'login.png'),
        resolve(output, 'learning.png'),
        resolve(output, 'cases.png'),
        resolve(output, 'knowledge.png'),
        resolve(output, 'practice.png'),
      ],
      physicalDevices: 'not-tested',
    }),
  )
} catch (error) {
  const safeMessage =
    error instanceof Error && /^(timeout:|capture-screenshot-)/.test(error.message) ? error.message : undefined
  const safeKind = error instanceof Error ? error.name : typeof error
  console.error(
    error instanceof assert.AssertionError
      ? error.message
      : safeMessage || `FAIL: Student navigation smoke failed (${safeKind}).`,
  )
  process.exitCode = 1
} finally {
  miniProgram?.disconnect()
}
