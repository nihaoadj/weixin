import assert from 'node:assert/strict'
import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { Launcher } from '@weapp-vite/miniprogram-automator'
import { diagnose } from './doctor.mjs'

// Background-only Demo workflow. Demo correctly disables teacher class writes,
// so this verifies the available UI contract: opening the owned class and
// expanding its rendered member scope. API-mode writes remain API test scope.
await diagnose({ probe: false })

const port = Number(process.env.WECHAT_AUTO_PORT || 9420)
const root = fileURLToPath(new URL('../../', import.meta.url))
const output = resolve(root, 'output/wechat', `teacher-class-${Date.now()}`)
const timeoutMs = 10000
const within = (promise, label) =>
  Promise.race([
    promise,
    new Promise((_, reject) => setTimeout(() => reject(new Error(`timeout:${label}`)), timeoutMs)),
  ])
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
          socket.send(JSON.stringify({ id: 'capture', method: 'App.captureScreenshot', params: {} }))
        socket.onmessage = ({ data: payload }) => {
          try {
            const response = JSON.parse(String(payload))
            if (response.id !== 'capture') return
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

async function openTeacherWorkspace(miniProgram, page) {
  if (page.path === 'pages/teacher/classes/classes') return page
  if (page.path === 'pages/teacher/index/index') return page
  if (page.path === 'pages/login/login') {
    const teacher = await within(page.$('.role-button.teacher', { fallback: false }), 'teacher-role')
    assert.ok(teacher, 'The teacher role button is not rendered.')
    await within(teacher.tap(), 'teacher-role-tap')
    return current(miniProgram, 'pages/teacher/index/index')
  }
  const nav = await component(page, '.student-nav')
  assert.ok(nav, 'A student navigation is required to leave the current student page safely.')
  const items = await within(nav.$$('.student-nav__item'), 'student-navigation-items')
  const labels = await Promise.all(items.map((item) => within(item.text(), 'student-navigation-label')))
  const pblIndex = labels.findIndex((label) => label.includes('研讨') || label.includes('课堂'))
  assert.notEqual(pblIndex, -1, 'The student navigation has no discussion entry.')
  await within(items[pblIndex].tap(), 'student-pbl-tap')
  page = await current(miniProgram, 'pages/student/pbl/pbl')
  const actions = await within(page.$$('.account-bar button', { fallback: false }), 'student-account-actions')
  assert.ok(actions[1], 'The student logout control is not rendered.')
  await within(actions[1].tap(), 'student-logout-tap')
  page = await current(miniProgram, 'pages/login/login')
  const teacher = await within(page.$('.role-button.teacher', { fallback: false }), 'teacher-role')
  assert.ok(teacher, 'The teacher role button is not rendered.')
  await within(teacher.tap(), 'teacher-role-tap')
  return current(miniProgram, 'pages/teacher/index/index')
}

async function classCard(page, className) {
  for (let attempt = 0; attempt < 24; attempt += 1) {
    const cards = await within(page.$$('.class-card', { fallback: false }), 'class-cards')
    for (const card of cards) {
      if ((await within(card.text(), 'class-card-text')).includes(className)) return card
    }
    await wait(250)
  }
  throw new Error('timeout:teacher-class-card')
}

let miniProgram
let step = 'connect'
try {
  console.log('STEP connect')
  miniProgram = await within(new Launcher().connect({ wsEndpoint: `ws://127.0.0.1:${port}` }), 'connect')
  mkdirSync(output, { recursive: true })
  let page = await within(miniProgram.currentPage(), 'initial-page')
  step = 'open-teacher-workspace'
  console.log('STEP open-teacher-workspace')
  page = await openTeacherWorkspace(miniProgram, page)
  if (page.path !== 'pages/teacher/classes/classes') {
    step = 'open-class-management'
    console.log('STEP open-class-management')
    const overview = await component(page, '.overview')
    assert.ok(overview, 'The teacher overview is not rendered.')
    const rows = await within(overview.$$('.management-row'), 'management-rows')
    const labels = await Promise.all(rows.map((row) => within(row.text(), 'management-row-label')))
    const classesIndex = labels.findIndex((label) => label.includes('班级管理'))
    assert.notEqual(classesIndex, -1, 'The teacher overview has no class-management entry.')
    await within(rows[classesIndex].tap(), 'class-management-tap')
    page = await current(miniProgram, 'pages/teacher/classes/classes')
  }

  step = 'find-owned-class'
  console.log('STEP find-owned-class')
  const created = await classCard(page, '病理学演示班')
  assert.match(await within(created.text(), 'owned-class-text'), /demo_class_1/)
  const screenshot = resolve(output, 'class-scope.png')
  step = 'capture-class-scope'
  console.log('STEP capture-class-scope')
  await captureBackgroundScreenshot(screenshot)

  step = 'open-members'
  console.log('STEP open-members')
  const members = await within(created.$('.secondary.full', { fallback: false }), 'view-members-button')
  assert.ok(members, 'The view-members button is not rendered.')
  await within(members.tap(), 'view-members-tap')
  for (let attempt = 0; attempt < 24; attempt += 1) {
    const text = await within(created.text(), 'expanded-class-text')
    if (text.includes('demo_student')) {
      console.log(
        JSON.stringify({
          result: 'teacher-class-real-tap-passed',
          screenshots: [screenshot],
          physicalDevices: 'not-tested',
        }),
      )
      break
    }
    await wait(250)
    if (attempt === 23) throw new Error('timeout:rendered-class-members')
  }
} catch (error) {
  const safeMessage = error instanceof Error && error.message.startsWith('timeout:') ? error.message : undefined
  console.error(
    error instanceof assert.AssertionError
      ? error.message
      : safeMessage || `FAIL: Teacher class smoke failed (${step}).`,
  )
  process.exitCode = 1
} finally {
  miniProgram?.disconnect()
}
