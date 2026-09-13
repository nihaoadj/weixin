import assert from 'node:assert/strict'
import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { Launcher } from '@weapp-vite/miniprogram-automator'
import { diagnose } from './doctor.mjs'

// Background-only Demo workflow. It uses only rendered controls and omits
// screenshots after entry of synthetic learner text.
await diagnose({ probe: false })

const port = Number(process.env.WECHAT_AUTO_PORT || 9420)
const root = fileURLToPath(new URL('../../', import.meta.url))
const output = resolve(root, 'output/wechat', `case-training-${Date.now()}`)
const timeoutMs = 10000
const within = (promise, label) =>
  Promise.race([
    promise,
    new Promise((_, reject) => setTimeout(() => reject(new Error(`timeout:${label}`)), timeoutMs)),
  ])
const wait = (milliseconds) => new Promise((resolveWait) => setTimeout(resolveWait, milliseconds))

async function current(miniProgram, expectedPath) {
  for (let attempt = 0; attempt < 40; attempt += 1) {
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
    const match = await within(host.$(selector), `component:${selector}`)
    if (match) return match
    queue.push(...(await within(host.$$('component'), `nested:${selector}`)))
  }
  return null
}

async function screenshot(path) {
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

async function openStudentLearning(miniProgram, page) {
  if (page.path === 'pages/student/case-training/case-training') {
    if (process.env.WECHAT_RESUME_CASE_TRAINING === '1') return page
    throw new Error('case-training-resume-required')
  }
  if (page.path === 'pages/teacher/case-edit/case-edit') {
    const back = await within(page.$('.authoring-return', { fallback: false }), 'case-authoring-return')
    assert.ok(back, 'The case authoring return control is not rendered.')
    await within(back.tap(), 'case-authoring-return-tap')
    page = await current(miniProgram, 'pages/teacher/index/index')
  }
  if (page.path === 'pages/student/case-report/case-report') {
    const actions = await within(page.$$('button', { fallback: false }), 'case-report-actions')
    let returnToCases
    for (const action of actions) {
      if ((await within(action.text(), 'case-report-action-label')).includes('返回病例列表')) {
        returnToCases = action
        break
      }
    }
    assert.ok(returnToCases, 'The case-report return control is not rendered.')
    await within(returnToCases.tap(), 'case-report-return-tap')
    page = await current(miniProgram, 'pages/student/question/question')
  }
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

async function field(page, selector, label) {
  const value = await within(page.$(selector, { fallback: false }), label)
  assert.ok(value, `${label} is not rendered.`)
  return value
}

async function fields(page, selector, minimum, label) {
  for (let attempt = 0; attempt < 24; attempt += 1) {
    const values = await within(page.$$(selector, { fallback: false }), label)
    if (values.length >= minimum) return values
    await wait(250)
  }
  throw new Error(`timeout:${label}`)
}

async function visibleStage(page) {
  if (await page.$('.question-composer', { fallback: false })) return 'history'
  if (await page.$('.stage-content .primary', { fallback: false })) return 'complete'
  const [inputs, textareas] = await Promise.all([
    page.$$('input', { fallback: false }),
    page.$$('textarea', { fallback: false }),
  ])
  if (inputs.length === 0 && textareas.length === 1) return 'problem'
  if (inputs.length === 2 && textareas.length === 4) return 'differential'
  if (inputs.length === 2 && textareas.length === 1) return 'tests'
  if (inputs.length === 1 && textareas.length === 2) return 'management'
  return 'unknown'
}

async function stageEventually(page, expected, label) {
  for (let attempt = 0; attempt < 24; attempt += 1) {
    const currentStage = await visibleStage(page)
    if (currentStage === expected) return currentStage
    await wait(250)
  }
  throw new Error(`timeout:${label}`)
}

let miniProgram
let step = 'connect'
try {
  console.log('STEP connect')
  miniProgram = await within(new Launcher().connect({ wsEndpoint: `ws://127.0.0.1:${port}` }), 'connect')
  mkdirSync(output, { recursive: true })
  let page = await within(miniProgram.currentPage(), 'initial-page')
  const resuming = page.path === 'pages/student/case-training/case-training'
  let initialScreenshot
  if (!resuming) {
    step = 'open-learning'
    console.log('STEP open-learning')
    page = await openStudentLearning(miniProgram, page)

    step = 'open-case-list'
    console.log('STEP open-case-list')
    const resource = await field(page, '.resource-row', 'case-training-resource')
    await within(resource.tap(), 'case-training-resource-tap')
    page = await current(miniProgram, 'pages/student/question/question')
    const caseCard = await field(page, '.case', 'showcase-case')
    await within(caseCard.tap(), 'showcase-case-tap')
    page = await current(miniProgram, 'pages/student/case-training/case-training')

    step = 'capture-history-entry'
    console.log('STEP capture-history-entry')
    initialScreenshot = resolve(output, 'history-entry.png')
    await screenshot(initialScreenshot)
  } else {
    assert.equal(
      process.env.WECHAT_RESUME_CASE_TRAINING,
      '1',
      'A training page needs an explicit synthetic-record resume flag.',
    )
  }

  let currentStage = await visibleStage(page)
  assert.notEqual(currentStage, 'unknown', 'The case training stage controls are not recognizable.')

  if (currentStage === 'history') {
    step = 'submit-history'
    console.log('STEP submit-history')
    const question = await field(page, '.question-composer input', 'patient-question')
    await within(question.input('合成问诊问题。'), 'patient-question-input')
    const ask = await field(page, '.ask-action', 'patient-question-send')
    await within(ask.tap(), 'patient-question-send-tap')
    await wait(500)
    const notes = await page.$('.notes-fields', { fallback: false })
    if (!notes) await within((await field(page, '.bottom .primary', 'history-expand')).tap(), 'history-expand-tap')
    const historyText = await fields(page, 'textarea', 1, 'history-textareas')
    await within(historyText[0].input('合成病史小结。'), 'history-summary-input')
    const historyInputs = await fields(page, 'input', 2, 'history-inputs')
    await within(historyInputs[1].input('合成关键发现'), 'history-findings-input')
    await within((await field(page, '.bottom .primary', 'history-submit')).tap(), 'history-submit-tap')
    currentStage = await stageEventually(page, 'problem', 'history-to-problem')
  }

  if (currentStage === 'problem') {
    step = 'submit-problem-representation'
    console.log('STEP submit-problem-representation')
    await within((await field(page, 'textarea', 'problem-representation')).input('合成问题表征。'), 'problem-input')
    await within((await field(page, '.bottom .primary', 'problem-submit')).tap(), 'problem-submit-tap')
    currentStage = await stageEventually(page, 'differential', 'problem-to-differential')
  }

  if (currentStage === 'differential') {
    step = 'submit-differential'
    console.log('STEP submit-differential')
    const differentialInputs = await fields(page, 'input', 2, 'differential-inputs')
    const differentialTexts = await fields(page, 'textarea', 4, 'differential-textareas')
    await within(differentialInputs[0].input('合成鉴别诊断'), 'differential-diagnosis-input')
    await within(differentialTexts[0].input('合成支持证据'), 'differential-support-input')
    await within(differentialTexts[1].input('合成反对证据'), 'differential-opposing-input')
    await within((await field(page, '.bottom .primary', 'differential-submit')).tap(), 'differential-submit-tap')
    currentStage = await stageEventually(page, 'tests', 'differential-to-tests')
  }

  if (currentStage === 'tests') {
    step = 'submit-tests'
    console.log('STEP submit-tests')
    const testInputs = await fields(page, 'input', 2, 'test-inputs')
    await within(testInputs[0].input('合成检查'), 'test-name-input')
    await within((await field(page, 'textarea', 'test-rationale')).input('合成检查理由。'), 'test-rationale-input')
    await within((await field(page, '.bottom .primary', 'test-submit')).tap(), 'test-submit-tap')
    currentStage = await stageEventually(page, 'management', 'tests-to-management')
  }

  if (currentStage === 'management') {
    step = 'submit-management'
    console.log('STEP submit-management')
    const managementInputs = await fields(page, 'input', 1, 'management-inputs')
    const managementTexts = await fields(page, 'textarea', 2, 'management-textareas')
    await within(managementInputs[0].input('合成初步处置'), 'management-action-input')
    await within(managementTexts[0].input('合成处置理由。'), 'management-rationale-input')
    await within((await field(page, '.bottom .primary', 'management-submit')).tap(), 'management-submit-tap')
    currentStage = await stageEventually(page, 'complete', 'management-to-complete')
  }
  assert.equal(currentStage, 'complete', 'The case training stages did not reach completion.')
  step = 'complete-training'
  console.log('STEP complete-training')
  await within((await field(page, '.stage-content .primary', 'complete-case')).tap(), 'complete-case-tap')
  page = await current(miniProgram, 'pages/student/case-report/case-report')
  console.log('STEP return-to-case-list')
  let reportReturn
  for (let attempt = 0; attempt < 20 && !reportReturn; attempt += 1) {
    const reportActions = await within(page.$$('button', { fallback: false }), 'case-report-actions')
    for (const action of reportActions) {
      if ((await within(action.text(), 'case-report-action-label')).includes('返回病例列表')) {
        reportReturn = action
        break
      }
    }
    if (!reportReturn) await wait(250)
  }
  assert.ok(reportReturn, 'The case-report return control is not rendered.')
  await within(reportReturn.tap(), 'case-report-return-tap')
  await current(miniProgram, 'pages/student/question/question')
  console.log(
    JSON.stringify({
      result: 'case-training-real-input-and-return-passed',
      screenshots: initialScreenshot ? [initialScreenshot] : [],
      physicalDevices: 'not-tested',
    }),
  )
} catch (error) {
  const safeMessage = error instanceof Error && /^(timeout:|route:)/.test(error.message) ? error.message : undefined
  const safeKind = error instanceof Error ? error.name : typeof error
  const typeErrorDetail =
    error instanceof TypeError ? error.message.replace(/['"`][^'"`]{0,200}['"`]/g, "'…'") : undefined
  console.error(
    error instanceof assert.AssertionError
      ? error.message
      : safeMessage || typeErrorDetail || `FAIL: Case training smoke failed (${step}; ${safeKind}).`,
  )
  process.exitCode = 1
} finally {
  miniProgram?.disconnect()
}
