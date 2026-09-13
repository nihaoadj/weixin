import assert from 'node:assert/strict'
import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { Launcher } from '@weapp-vite/miniprogram-automator'
import { diagnose } from './doctor.mjs'

await diagnose({ probe: false })
const port = Number(process.env.WECHAT_AUTO_PORT || 9420)
const root = fileURLToPath(new URL('../../', import.meta.url))
const output = resolve(root, 'output/wechat', `pbl-handoff-${Date.now()}`)
const timeoutMs = 10000
const publish = process.argv.includes('--publish')
const completeFirstTask = process.argv.includes('--complete-first-task')
const feedbackEcho = process.argv.includes('--feedback-echo')
if (completeFirstTask && !publish) throw new Error('The first-task check requires --publish.')
if (feedbackEcho && publish) throw new Error('The feedback-echo check requires formative feedback only.')
const within = (promise, label) =>
  Promise.race([
    promise,
    new Promise((_, reject) => setTimeout(() => reject(new Error(`timeout:${label}`)), timeoutMs)),
  ])
const feedbackMarker = feedbackEcho ? `验收回显-${Date.now()}` : ''
async function current(miniProgram, path) {
  for (let i = 0; i < 20; i += 1) {
    const page = await within(miniProgram.currentPage(), `page:${path}`)
    if (page.path === path) return page
    await new Promise((r) => setTimeout(r, 250))
  }
  throw new Error(`route:${path}`)
}
async function component(page, selector) {
  const queue = [...(await within(page.$$('component', { fallback: false }), `hosts:${selector}`))]
  while (queue.length) {
    const host = queue.shift()
    const match = await within(host.$(selector), `component:${selector}`)
    if (match) return match
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
  miniProgram = await within(new Launcher().connect({ wsEndpoint: `ws://127.0.0.1:${port}` }), 'connect')
  mkdirSync(output, { recursive: true })
  let page = await within(miniProgram.currentPage(), 'student-page')
  assert.equal(page.path, 'pages/student/pbl/pbl', 'Run after the completed PBL dialogue smoke.')
  const locked = await within(page.$('.locked-bar', { fallback: false }), 'locked-dialogue')
  assert.ok(locked, 'The dialogue must be completed before submission.')
  const actions = await within(locked.$$('.secondary-action'), 'completed-dialogue-actions')
  const labels = await Promise.all(actions.map((action) => within(action.text(), 'completed-dialogue-action-label')))
  const submitIndex = labels.findIndex((label) => label.includes('提交教师'))
  assert.notEqual(submitIndex, -1, 'The completed dialogue has no teacher submission action.')
  const submit = actions[submitIndex]
  assert.ok(submit, 'The teacher submission action is not rendered.')
  await within(submit.tap(), 'submit-to-teacher-tap')
  await new Promise((r) => setTimeout(r, 500))
  const account = await within(page.$$('.account-bar button', { fallback: false }), 'student-account-actions')
  await within(account[1].tap(), 'student-logout')
  page = await current(miniProgram, 'pages/login/login')
  const teacher = await within(page.$('.role-button.teacher', { fallback: false }), 'teacher-role')
  await within(teacher.tap(), 'teacher-login')
  page = await current(miniProgram, 'pages/teacher/index/index')
  const nav = await component(page, '.teacher-nav')
  assert.ok(nav, 'The teacher navigation is not rendered.')
  const tabs = await within(nav.$$('.teacher-nav__item'), 'teacher-tabs')
  await within(tabs[2].tap(), 'teacher-content')
  await new Promise((r) => setTimeout(r, 500))
  const content = await component(page, '.teacher-content-workspace')
  assert.ok(content, 'The teacher content workspace is not rendered.')
  const sectionNav = await component(content, '.record-index')
  assert.ok(sectionNav, 'The teacher content subsection navigation is not rendered.')
  const sections = await within(sectionNav.$$('.record-index__item'), 'teacher-content-sections')
  const sectionLabels = await Promise.all(sections.map((item) => within(item.text(), 'teacher-content-section-label')))
  const diagnosticsIndex = sectionLabels.findIndex((label) => label.includes('诊断建议'))
  assert.notEqual(diagnosticsIndex, -1, 'The diagnostic-suggestions section is not rendered.')
  await within(sections[diagnosticsIndex].tap(), 'teacher-diagnostic-suggestions')
  await new Promise((r) => setTimeout(r, 500))
  const workItems = await component(page, '.work-items')
  assert.ok(workItems, 'The teacher diagnostic queue is not rendered.')
  const workItemList = await component(workItems, '.work-item-list')
  assert.ok(workItemList, 'The teacher diagnostic list is not rendered.')
  const row = await within(workItemList.$('.row'), 'submitted-diagnostic-row')
  assert.ok(row, 'The submitted diagnostic is not visible to the teacher.')
  const screenshot = resolve(output, 'teacher-content-queue.png')
  await within(miniProgram.pageScrollTo(0), 'teacher-queue-scroll-top')
  await new Promise((resolveWait) => setTimeout(resolveWait, 500))
  await captureBackgroundScreenshot(screenshot)

  console.log('STEP open-submitted-diagnostic')
  await within(row.tap(), 'submitted-diagnostic-row-tap')
  await new Promise((resolveWait) => setTimeout(resolveWait, 500))
  const detail = await component(workItems, '.detail')
  assert.ok(detail, 'The submitted diagnostic detail is not rendered.')
  const detailSize = await within(detail.size(), 'submitted-diagnostic-detail-size')
  assert.ok(
    Number(detailSize.width) > 0 && Number(detailSize.height) > 0,
    'The submitted diagnostic detail has no rendered size.',
  )
  const feedback = await within(detail.$('textarea'), 'teacher-feedback-input')
  assert.ok(feedback, 'The teacher feedback input is not rendered.')
  console.log(publish ? 'STEP publish-formal-task' : 'STEP send-formative-feedback')
  await within(
    feedback.input(`请先区分形态证据与机制解释，再补充它们之间的连接。${feedbackMarker}`),
    'teacher-feedback-value',
  )
  const feedbackActions = await within(detail.$$('.actions button'), 'teacher-feedback-actions')
  const actionLabel = publish ? '反馈并发布任务' : '仅发送反馈'
  const expectedStatus = publish ? '已发布' : '已反馈'
  let submitAction
  for (const action of feedbackActions) {
    if ((await within(action.text(), 'teacher-feedback-action-label')).includes(actionLabel)) {
      submitAction = action
      break
    }
  }
  assert.ok(submitAction, `The ${actionLabel} control is not rendered.`)
  await within(submitAction.tap(), publish ? 'publish-formal-task-tap' : 'send-formative-feedback-tap')
  for (let attempt = 0; attempt < 24; attempt += 1) {
    const status = await within(detail.$('.status-line'), 'feedback-status-line')
    if (status && (await within(status.text(), 'feedback-status-label')).includes(expectedStatus)) break
    await new Promise((resolveWait) => setTimeout(resolveWait, 250))
    if (attempt === 23) throw new Error('timeout:formative-feedback-status')
  }
  const screenshots = [screenshot]
  if (publish) {
    const teacherLogout = await within(page.$('.logout', { fallback: false }), 'teacher-logout')
    assert.ok(teacherLogout, 'The teacher logout control is not rendered.')
    await within(teacherLogout.tap(), 'teacher-logout-tap')
    page = await current(miniProgram, 'pages/login/login')
    const student = await within(page.$('.role-button.student', { fallback: false }), 'student-role')
    await within(student.tap(), 'student-login')
    page = await current(miniProgram, 'pages/student/pbl/pbl')
    const studentNav = await component(page, '.student-nav')
    assert.ok(studentNav, 'The student navigation is not rendered.')
    const studentTabs = await within(studentNav.$$('.student-nav__item'), 'student-navigation-items')
    const studentLabels = await Promise.all(studentTabs.map((item) => within(item.text(), 'student-navigation-label')))
    const learningIndex = studentLabels.findIndex((label) => label.includes('学习'))
    assert.notEqual(learningIndex, -1, 'The student learning navigation is not rendered.')
    await within(studentTabs[learningIndex].tap(), 'student-learning-tap')
    page = await current(miniProgram, 'pages/student/learning/index')
    await new Promise((resolveWait) => setTimeout(resolveWait, 750))
    const tasks = await component(page, '.tasks')
    assert.ok(tasks, 'The student PBL task list is not rendered.')
    const plans = await within(tasks.$$('.plan'), 'student-published-plans')
    assert.ok(plans.length > 0, 'The published PBL task is not visible to the student.')
    const planSize = await within(plans[0].size(), 'student-published-plan-size')
    assert.ok(Number(planSize.width) > 0 && Number(planSize.height) > 0, 'The published PBL task has no rendered size.')
    const studentScreenshot = resolve(output, 'student-published-plan.png')
    await within(miniProgram.pageScrollTo(0), 'student-published-plan-scroll-top')
    await new Promise((resolveWait) => setTimeout(resolveWait, 350))
    await captureBackgroundScreenshot(studentScreenshot)
    screenshots.push(studentScreenshot)
    if (completeFirstTask) {
      const firstPlan = plans[0]
      const firstTask = await within(firstPlan.$('.task'), 'student-first-published-task')
      assert.ok(firstTask, 'The first published task is not rendered.')
      const answer = await within(firstTask.$('.answer-input'), 'student-first-task-answer')
      assert.ok(answer, 'The first published task input is not rendered.')
      console.log('STEP complete-first-published-task')
      await within(answer.input('我会逐项对应形态表现与血流、通透性改变的机制。'), 'student-first-task-answer-value')
      const complete = await within(firstTask.$('button'), 'student-first-task-submit')
      assert.ok(complete, 'The first published task submit control is not rendered.')
      await within(complete.tap(), 'student-first-task-submit-tap')
      for (let attempt = 0; attempt < 24; attempt += 1) {
        const progress = await within(firstPlan.$('.plan-progress'), 'student-first-task-progress')
        if (progress && (await within(progress.text(), 'student-first-task-progress-label')).includes('已完成 1 / 3'))
          break
        await new Promise((resolveWait) => setTimeout(resolveWait, 250))
        if (attempt === 23) throw new Error('timeout:student-first-task-completion')
      }
    }
  }
  if (feedbackEcho) {
    const teacherLogout = await within(page.$('.logout', { fallback: false }), 'teacher-logout')
    assert.ok(teacherLogout, 'The teacher logout control is not rendered.')
    await within(teacherLogout.tap(), 'teacher-logout-tap')
    page = await current(miniProgram, 'pages/login/login')
    const student = await within(page.$('.role-button.student', { fallback: false }), 'student-role')
    await within(student.tap(), 'student-login')
    page = await current(miniProgram, 'pages/student/pbl/pbl')
    const studentNav = await component(page, '.student-nav')
    assert.ok(studentNav, 'The student navigation is not rendered.')
    const studentTabs = await within(studentNav.$$('.student-nav__item'), 'student-navigation-items')
    const studentLabels = await Promise.all(studentTabs.map((item) => within(item.text(), 'student-navigation-label')))
    const learningIndex = studentLabels.findIndex((label) => label.includes('学习'))
    assert.notEqual(learningIndex, -1, 'The student learning navigation is not rendered.')
    await within(studentTabs[learningIndex].tap(), 'student-learning-tap')
    page = await current(miniProgram, 'pages/student/learning/index')
    await new Promise((resolveWait) => setTimeout(resolveWait, 750))
    const notifications = await within(page.$$('.notification'), 'student-feedback-notifications')
    let notification
    for (const candidate of notifications) {
      if ((await within(candidate.text(), 'student-feedback-notification-label')).includes(feedbackMarker)) {
        notification = candidate
        break
      }
    }
    assert.ok(notification, 'The teacher-feedback notification is not rendered.')
    const notificationSize = await within(notification.size(), 'student-feedback-notification-size')
    assert.ok(
      Number(notificationSize.width) > 0 && Number(notificationSize.height) > 0,
      'The teacher-feedback notification has no rendered size.',
    )
    await within(notification.tap(), 'student-feedback-notification-tap')
    page = await current(miniProgram, 'pages/student/pbl/pbl')
    await new Promise((resolveWait) => setTimeout(resolveWait, 500))
    const submittedDialogue = await within(page.$('.locked-bar', { fallback: false }), 'student-feedback-dialogue')
    assert.ok(submittedDialogue, 'The submitted dialogue is not rendered after opening the feedback notification.')
    const teacherFeedback = await within(page.$('.teacher-feedbacks', { fallback: false }), 'student-teacher-feedback')
    assert.ok(teacherFeedback, 'The teacher feedback is not rendered in the submitted dialogue.')
    const feedbackSize = await within(teacherFeedback.size(), 'student-teacher-feedback-size')
    assert.ok(
      Number(feedbackSize.width) > 0 && Number(feedbackSize.height) > 0,
      'The teacher feedback has no rendered size.',
    )
    const studentScreenshot = resolve(output, 'student-feedback-echo.png')
    await within(miniProgram.pageScrollTo(0), 'student-feedback-scroll-top')
    await new Promise((resolveWait) => setTimeout(resolveWait, 350))
    await captureBackgroundScreenshot(studentScreenshot)
    screenshots.push(studentScreenshot)
  }
  console.log(
    JSON.stringify({
      result: 'pbl-student-to-teacher-feedback-passed',
      action: publish ? 'task_published' : 'feedback_only',
      feedbackEcho,
      firstTaskCompleted: completeFirstTask,
      screenshots,
      physicalDevices: 'not-tested',
    }),
  )
} catch (error) {
  console.error(
    error instanceof assert.AssertionError
      ? error.message
      : error instanceof Error && error.message.startsWith('timeout:')
        ? error.message
        : 'FAIL: PBL handoff smoke failed.',
  )
  process.exitCode = 1
} finally {
  miniProgram?.disconnect()
}
