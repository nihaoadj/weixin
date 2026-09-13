import assert from 'node:assert/strict'
import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { Launcher } from '@weapp-vite/miniprogram-automator'
import { diagnose } from './doctor.mjs'

// This is a background-only Developer Tools check. It never uses OS input or
// clears tool state. Its only write is a freshly named Demo classroom that it
// closes before completion, using the rendered teacher controls.
await diagnose({ probe: false })

const port = Number(process.env.WECHAT_AUTO_PORT || 9420)
const root = fileURLToPath(new URL('../../', import.meta.url))
const output = resolve(root, 'output/wechat', `teacher-workspace-${Date.now()}`)
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

async function findComponentRoot(page, selector) {
  const componentHosts = [
    ...(await within(page.$$('component', { fallback: false, timeout: timeoutMs }), `component-hosts:${selector}`)),
  ]
  const seen = new Set()
  while (componentHosts.length) {
    const host = componentHosts.shift()
    if (!host || seen.has(host)) continue
    seen.add(host)
    const rootElement = await within(host.$(selector), `component-root:${selector}`)
    if (rootElement) return rootElement
    componentHosts.push(...(await within(host.$$('component'), `nested-component-hosts:${selector}`)))
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

async function eventuallyClassroomDashboard(classrooms) {
  for (let attempt = 0; attempt < 24; attempt += 1) {
    const dashboard = await within(classrooms.$('.dashboard'), 'created-classroom-dashboard')
    if (dashboard) return dashboard
    await wait(250)
  }
  return null
}

async function openTeacherWorkspace(miniProgram, page) {
  if (page.path === 'pages/teacher/index/index') return page
  if (page.path === 'pages/teacher/case-edit/case-edit') {
    const back = await within(page.$('.authoring-return', { fallback: false }), 'case-authoring-return')
    assert.ok(back, 'The saved case authoring return control is not rendered.')
    await within(back.tap(), 'case-authoring-return-tap')
    return current(miniProgram, 'pages/teacher/index/index')
  }
  if (page.path === 'pages/teacher/classes/classes') {
    // Mirrors the native return for the page opened by this test suite. It does
    // not read or mutate page data or call any business method.
    await within(miniProgram.navigateBack(), 'class-page-back')
    return current(miniProgram, 'pages/teacher/index/index')
  }
  if (page.path === 'pages/login/login') {
    const teacher = await within(page.$('.role-button.teacher', { fallback: false }), 'teacher-role')
    assert.ok(teacher, 'The teacher role button is not rendered.')
    await within(teacher.tap(), 'teacher-role-tap')
    return current(miniProgram, 'pages/teacher/index/index')
  }
  const studentNav = await findComponentRoot(page, '.student-nav')
  assert.ok(studentNav, 'A student navigation is required to leave the current student page safely.')
  const items = await within(studentNav.$$('.student-nav__item'), 'student-navigation-items')
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

let miniProgram
try {
  console.log('STEP connect')
  miniProgram = await within(new Launcher().connect({ wsEndpoint: `ws://127.0.0.1:${port}` }), 'connect')
  let page = await within(miniProgram.currentPage(), 'current-page')
  page = await openTeacherWorkspace(miniProgram, page)

  console.log('STEP open-overview')
  const workspaceNav = await findComponentRoot(page, '.teacher-nav')
  assert.ok(workspaceNav, 'The teacher workspace navigation is not rendered.')
  const workspaceItems = await within(workspaceNav.$$('.teacher-nav__item'), 'workspace-items')
  assert.equal(workspaceItems.length, 4, 'The teacher workspace navigation is incomplete.')
  assert.match(await within(workspaceItems[0].text(), 'overview-label'), /待办/)
  assert.match(await within(workspaceItems[1].text(), 'insights-label'), /学情/)
  assert.match(await within(workspaceItems[2].text(), 'content-label'), /内容/)
  assert.match(await within(workspaceItems[3].text(), 'pbl-label'), /PBL/)
  await within(workspaceItems[0].tap(), 'overview-tap')
  await within(new Promise((resolveWait) => setTimeout(resolveWait, 350)), 'overview-render')

  mkdirSync(output, { recursive: true })
  console.log('STEP screenshot-overview')
  await captureBackgroundScreenshot(resolve(output, 'overview.png'))

  console.log('STEP open-content')
  await within(workspaceItems[2].tap(), 'content-tap')
  await within(new Promise((resolveWait) => setTimeout(resolveWait, 500)), 'content-render')
  const content = await findComponentRoot(page, '.teacher-content-workspace')
  assert.ok(content, 'The teacher content workspace did not open.')
  console.log('STEP screenshot-content')
  await captureBackgroundScreenshot(resolve(output, 'content.png'))

  console.log('STEP open-diagnostic-suggestions')
  const contentSections = await findComponentRoot(content, '.record-index')
  assert.ok(contentSections, 'The teaching-content subsection navigation is not rendered.')
  const contentSectionItems = await within(contentSections.$$('.record-index__item'), 'content-section-items')
  const contentSectionLabels = await Promise.all(
    contentSectionItems.map((item) => within(item.text(), 'content-section-label')),
  )
  const diagnosticsIndex = contentSectionLabels.findIndex((label) => label.includes('诊断建议'))
  assert.notEqual(diagnosticsIndex, -1, 'The diagnostic-suggestions section is not rendered.')
  await within(contentSectionItems[diagnosticsIndex].tap(), 'diagnostic-suggestions-tap')
  await wait(500)

  console.log('STEP open-diagnostic-detail')
  const workItems = await findComponentRoot(page, '.work-items')
  assert.ok(workItems, 'The teacher diagnostic work-items are not rendered.')
  const workItemList = await findComponentRoot(workItems, '.work-item-list')
  assert.ok(workItemList, 'The teacher diagnostic list is not rendered.')
  const diagnosticRow = await within(workItemList.$('.row'), 'diagnostic-row')
  assert.ok(diagnosticRow, 'The seeded diagnostic row is not rendered.')
  await within(diagnosticRow.tap(), 'diagnostic-row-tap')
  await wait(500)
  const diagnosticDetail = await findComponentRoot(workItems, '.detail')
  assert.ok(diagnosticDetail, 'The selected diagnostic detail is not rendered.')
  const diagnosticHeading = await within(diagnosticDetail.$('.detail-heading'), 'diagnostic-detail-heading')
  assert.ok(diagnosticHeading, 'The selected diagnostic detail heading is not rendered.')
  const diagnosticSize = await within(diagnosticDetail.size(), 'diagnostic-detail-size')
  assert.ok(
    Number(diagnosticSize.width) > 0 && Number(diagnosticSize.height) > 0,
    'The selected diagnostic detail has no rendered size.',
  )

  console.log('STEP open-pbl')
  await within(workspaceItems[3].tap(), 'pbl-tap')
  await within(new Promise((resolveWait) => setTimeout(resolveWait, 500)), 'pbl-render')
  const pbl = await findComponentRoot(page, '.pbl-workspace')
  assert.ok(pbl, 'The teacher PBL workspace did not open.')
  console.log('STEP screenshot-pbl')
  await captureBackgroundScreenshot(resolve(output, 'pbl.png'))

  console.log('STEP create-classroom')
  const classrooms = await findComponentRoot(page, '.classrooms')
  assert.ok(classrooms, 'The classroom workspace is not rendered.')
  const initialSessionRows = await within(classrooms.$$('.session-row'), 'initial-classroom-rows')
  const initialSessionLabels = await Promise.all(
    initialSessionRows.map((row) => within(row.text(), 'initial-classroom-row-label')),
  )
  const initialClosedCount = initialSessionLabels.filter((label) => label.includes('已关闭')).length
  let createForm = await within(classrooms.$('.create-form'), 'existing-classroom-create-form')
  if (!createForm) {
    const classroomToolbar = await within(classrooms.$('.toolbar'), 'classroom-toolbar')
    assert.ok(classroomToolbar, 'The classroom toolbar is not rendered.')
    const classroomToolbarActions = await within(classroomToolbar.$$('button'), 'classroom-toolbar-actions')
    let openCreate
    for (const action of classroomToolbarActions) {
      if ((await within(action.text(), 'classroom-toolbar-action-label')).trim() === '创建课堂') {
        openCreate = action
        break
      }
    }
    assert.ok(openCreate, 'The create-classroom control is not rendered.')
    await within(openCreate.tap(), 'open-create-classroom')
    await wait(300)
    createForm = await within(classrooms.$('.create-form'), 'classroom-create-form')
  }
  assert.ok(createForm, 'The classroom creation form is not rendered.')
  const topic = await within(createForm.$('.topic-input'), 'classroom-topic-input')
  assert.ok(topic, 'The classroom topic input is not rendered.')
  await within(topic.input('T24 合成课堂验收'), 'classroom-topic-value')
  const goals = await within(createForm.$$('checkbox'), 'classroom-goal-options')
  assert.ok(goals.length > 0, 'The reviewed Demo case exposes no selectable knowledge point.')
  if ((await within(goals[0].attribute('checked'), 'classroom-first-goal-status')) !== 'true')
    await within(goals[0].tap(), 'classroom-first-goal')
  const createSubmit = await within(createForm.$('.create-submit'), 'classroom-create-submit')
  assert.ok(createSubmit, 'The classroom create action is not rendered.')
  await within(createSubmit.tap(), 'create-classroom-tap')
  console.log('STEP open-created-classroom-dashboard')
  const dashboard = await eventuallyClassroomDashboard(classrooms)
  assert.ok(dashboard, 'The created classroom phase dashboard is not rendered.')
  const dashboardSize = await within(dashboard.size(), 'classroom-dashboard-size')
  assert.ok(
    Number(dashboardSize.width) > 0 && Number(dashboardSize.height) > 0,
    'The created classroom phase dashboard has no rendered size.',
  )
  console.log('STEP screenshot-created-classroom')
  await captureBackgroundScreenshot(resolve(output, 'pbl-created-classroom.png'))
  const classroomButtons = await within(classrooms.$$('button'), 'classroom-controls')
  let close
  for (const action of classroomButtons) {
    if ((await within(action.text(), 'classroom-control-label')).includes('关闭课堂')) {
      close = action
      break
    }
  }
  assert.ok(close, 'The close-classroom control is not rendered.')
  console.log('STEP close-created-classroom')
  await within(close.tap(), 'close-created-classroom-tap')
  for (let attempt = 0; attempt < 20; attempt += 1) {
    const rows = await within(classrooms.$$('.session-row'), 'closed-classroom-rows')
    const labels = await Promise.all(rows.map((row) => within(row.text(), 'closed-classroom-row-label')))
    if (labels.filter((label) => label.includes('已关闭')).length >= initialClosedCount + 1) break
    await wait(250)
    if (attempt === 19) throw new Error('timeout:created-classroom-close')
  }
  const closedRows = await within(classrooms.$$('.session-row'), 'closed-classroom-rows')
  const closedLabels = await Promise.all(closedRows.map((row) => within(row.text(), 'closed-classroom-row-label')))
  assert.ok(
    closedLabels.filter((label) => label.includes('已关闭')).length >= initialClosedCount + 1,
    'The new classroom was not rendered as closed.',
  )

  console.log('STEP reopen-overview')
  await within(workspaceItems[0].tap(), 'overview-reopen-tap')
  await within(new Promise((resolveWait) => setTimeout(resolveWait, 350)), 'overview-rerender')

  console.log('STEP find-student-reports')
  const overview = await findComponentRoot(page, '.overview')
  assert.ok(overview, 'The teacher overview is not rendered.')
  const reports = await within(overview.$('.priority-row'), 'student-reports')
  assert.ok(reports, 'The student reports row is not rendered.')
  assert.match(await within(reports.text(), 'student-reports-label'), /学生报告/)
  const size = await within(reports.size(), 'student-reports-size')
  assert.ok(Number(size.width) > 0 && Number(size.height) > 0, 'The student reports row has no rendered size.')

  console.log('STEP tap-student-reports')
  await within(reports.tap(), 'student-reports-tap')
  await within(new Promise((resolveWait) => setTimeout(resolveWait, 500)), 'workspace-render')

  console.log('STEP assert-learning-records')
  const insights = await findComponentRoot(page, '.teacher-insights-workspace')
  assert.ok(insights, 'The teacher insights workspace did not open.')
  const insightComponents = await within(insights.$$('component'), 'insight-components')
  let insightNav = null
  for (const component of insightComponents) {
    const candidate = await within(component.$('.record-index'), 'insight-navigation')
    if (candidate) {
      insightNav = candidate
      break
    }
  }
  assert.ok(insightNav, 'The teacher insights navigation is not rendered.')
  const activeSection = await within(insightNav.$('.record-index__item.active'), 'active-insight-section')
  assert.ok(activeSection, 'The teacher insights workspace has no active section.')
  assert.match(await within(activeSection.text(), 'active-insight-section-label'), /学习记录/)

  console.log('STEP screenshot-learning-records')
  await captureBackgroundScreenshot(resolve(output, 'learning-records.png'))

  console.log('STEP open-pbl-follow-up')
  const insightSectionItems = await within(insightNav.$$('.record-index__item'), 'insight-section-items')
  const insightSectionLabels = await Promise.all(
    insightSectionItems.map((item) => within(item.text(), 'insight-section-label')),
  )
  const followUpsIndex = insightSectionLabels.findIndex((label) => label.includes('PBL 跟进'))
  assert.notEqual(followUpsIndex, -1, 'The PBL follow-up section is not rendered.')
  await within(insightSectionItems[followUpsIndex].tap(), 'pbl-follow-up-tap')
  await wait(500)
  const followUps = await findComponentRoot(insights, '.follow-ups')
  assert.ok(followUps, 'The PBL follow-up workspace is not rendered.')
  const followUpList = await findComponentRoot(followUps, '.follow-up-list')
  assert.ok(followUpList, 'The PBL follow-up list is not rendered.')
  const followUpRow = await within(followUpList.$('.follow-up-row'), 'pbl-follow-up-row')
  assert.ok(followUpRow, 'The seeded PBL follow-up row is not rendered.')
  await within(followUpRow.tap(), 'pbl-follow-up-row-tap')
  await wait(500)
  const followUpDetail = await findComponentRoot(followUps, '.detail')
  assert.ok(followUpDetail, 'The PBL follow-up detail is not rendered.')
  const followUpDetailSize = await within(followUpDetail.size(), 'pbl-follow-up-detail-size')
  assert.ok(
    Number(followUpDetailSize.width) > 0 && Number(followUpDetailSize.height) > 0,
    'The PBL follow-up detail has no rendered size.',
  )
  console.log(
    JSON.stringify({
      result: 'teacher-workspace-real-tap-passed',
      screenshots: [
        resolve(output, 'overview.png'),
        resolve(output, 'content.png'),
        resolve(output, 'pbl.png'),
        resolve(output, 'pbl-created-classroom.png'),
        resolve(output, 'learning-records.png'),
      ],
      physicalDevices: 'not-tested',
    }),
  )
} catch (error) {
  const safeMessage = error instanceof Error && error.message.startsWith('timeout:') ? error.message : undefined
  console.error(
    error instanceof assert.AssertionError ? error.message : safeMessage || 'FAIL: Teacher workspace smoke failed.',
  )
  process.exitCode = 1
} finally {
  miniProgram?.disconnect()
}
