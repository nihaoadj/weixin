import assert from 'node:assert/strict'
import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { Launcher } from '@weapp-vite/miniprogram-automator'
import { diagnose } from './doctor.mjs'

// Background-only Demo workflow. It uses visible controls to create a synthetic
// guided-case draft, save it, and submit it for review. The only screenshot is
// before entry and generation, so no hidden case fields are captured.
await diagnose({ probe: false })

const port = Number(process.env.WECHAT_AUTO_PORT || 9420)
const root = fileURLToPath(new URL('../../', import.meta.url))
const output = resolve(root, 'output/wechat', `teacher-case-authoring-${Date.now()}`)
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
  if (page.path === 'pages/teacher/case-edit/case-edit') throw new Error('case-authoring-resume-required')
  if (page.path === 'pages/teacher/classes/classes') {
    // This mirrors the native navigation-bar return for the page opened by the
    // preceding class smoke; it does not call a page business method.
    await within(miniProgram.navigateBack(), 'class-page-back')
    return current(miniProgram, 'pages/teacher/index/index')
  }
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

async function actionByLabel(page, label, state) {
  const actions = await within(page.$$('.authoring-action', { fallback: false }), `authoring-actions:${state}`)
  for (const action of actions) {
    if ((await within(action.text(), `authoring-action-label:${state}`)).includes(label)) return action
  }
  return null
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

  step = 'open-content'
  console.log('STEP open-content')
  const nav = await component(page, '.teacher-nav')
  assert.ok(nav, 'The teacher navigation is not rendered.')
  const workspaceItems = await within(nav.$$('.teacher-nav__item'), 'teacher-workspace-items')
  const workspaceLabels = await Promise.all(
    workspaceItems.map((item) => within(item.text(), 'teacher-workspace-label')),
  )
  const contentIndex = workspaceLabels.findIndex((label) => label.includes('内容'))
  assert.notEqual(contentIndex, -1, 'The teacher content entry is not rendered.')
  await within(workspaceItems[contentIndex].tap(), 'teacher-content-tap')
  await wait(500)
  const content = await component(page, '.teacher-content-workspace')
  assert.ok(content, 'The teacher content workspace did not open.')
  const sectionNav = await component(page, '.record-index')
  assert.ok(sectionNav, 'The teaching-content subsection navigation is not rendered.')
  const sections = await within(sectionNav.$$('.record-index__item'), 'content-sections')
  const sectionLabels = await Promise.all(sections.map((item) => within(item.text(), 'content-section-label')))
  const resourcesIndex = sectionLabels.findIndex((label) => label.includes('教学资源'))
  assert.notEqual(resourcesIndex, -1, 'The teaching-resources section is not rendered.')
  await within(sections[resourcesIndex].tap(), 'teaching-resources-tap')
  await wait(500)
  const problems = await component(page, '.problem-list-page')
  assert.ok(problems, 'The teaching-resources list did not open.')
  const createCase = await within(problems.$('.small-button.assist'), 'create-case-button')
  assert.ok(createCase, 'The create-case control is not rendered.')
  await within(createCase.tap(), 'create-case-tap')
  page = await current(miniProgram, 'pages/teacher/case-edit/case-edit')

  step = 'inspect-authoring-setup'
  console.log('STEP inspect-authoring-setup')
  const setup = await component(page, '.case-setup')
  assert.ok(setup, 'The case authoring setup is not rendered.')
  const inputs = await within(setup.$$('input'), 'case-setup-inputs')
  const objectives = await within(setup.$('textarea'), 'case-setup-objectives')
  assert.ok(inputs[0] && inputs[1] && objectives, 'The three case-setup fields are not rendered.')
  const screenshot = resolve(output, 'authoring-setup.png')
  await captureBackgroundScreenshot(screenshot)

  step = 'generate-synthetic-draft'
  console.log('STEP generate-synthetic-draft')
  const stamp = Date.now()
  await within(inputs[0].input(`T24 合成炎症病例 ${stamp}`), 'case-topic-input')
  await within(inputs[1].input('本科生'), 'case-level-input')
  await within(objectives.input('练习结构化病理推理'), 'case-objectives-input')
  const generate = await within(setup.$('.generate-button'), 'generate-case-button')
  assert.ok(generate, 'The generate-case button is not rendered.')
  await within(generate.tap(), 'generate-case-tap')
  for (let attempt = 0; attempt < 24; attempt += 1) {
    if (await page.$('.step-overview', { fallback: false })) break
    await wait(250)
    if (attempt === 23) throw new Error('timeout:generated-case-draft')
  }

  for (let authoringStep = 1; authoringStep < 5; authoringStep += 1) {
    step = `next-authoring-step-${authoringStep}`
    console.log(`STEP ${step}`)
    const next = await actionByLabel(page, '下一步', step)
    assert.ok(next, `The next-step control is missing at authoring step ${authoringStep}.`)
    await within(next.tap(), `next-authoring-step-tap:${authoringStep}`)
    await wait(300)
  }

  step = 'save-draft'
  console.log('STEP save-draft')
  const save = await actionByLabel(page, '保存草稿', step)
  assert.ok(save, 'The save-draft control is not rendered at the final authoring step.')
  await within(save.tap(), 'save-draft-tap')
  let submitReview
  for (let attempt = 0; attempt < 24; attempt += 1) {
    submitReview = await actionByLabel(page, '提交医学审核', 'review-submission')
    if (submitReview) break
    await wait(250)
  }
  assert.ok(submitReview, 'The review-submission control is not rendered after saving the draft.')
  step = 'submit-review'
  console.log('STEP submit-review')
  await within(submitReview.tap(), 'submit-review-tap')
  for (let attempt = 0; attempt < 24; attempt += 1) {
    const status = await within(page.$('.workflow-current', { fallback: false }), 'workflow-current')
    if (status && (await within(status.text(), 'workflow-current-text')).includes('医学审核中')) break
    await wait(250)
    if (attempt === 23) throw new Error('timeout:review-pending-status')
  }
  console.log(
    JSON.stringify({
      result: 'teacher-case-authoring-real-input-passed',
      screenshots: [screenshot],
      physicalDevices: 'not-tested',
    }),
  )
} catch (error) {
  const safeMessage = error instanceof Error && error.message.startsWith('timeout:') ? error.message : undefined
  console.error(
    error instanceof assert.AssertionError
      ? error.message
      : safeMessage || `FAIL: Teacher case-authoring smoke failed (${step}).`,
  )
  process.exitCode = 1
} finally {
  miniProgram?.disconnect()
}
