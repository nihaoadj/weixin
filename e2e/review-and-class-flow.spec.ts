import { expect, test } from '@playwright/test'

const apiPort = Number(process.env.E2E_API_PORT ?? 8001)

async function loginAsReviewer(page: import('@playwright/test').Page) {
  const response = await page.request.post(`http://127.0.0.1:${apiPort}/auth/demo-login`, {
    data: {
      role: 'teacher',
      external_id: 'demo_reviewer',
      nickname: '医学审核专家',
      avatar_url: '',
      class_ids: [],
    },
  })
  const body = await response.json()
  await page.evaluate(
    ({ accessToken, user }) => {
      const uniApp = (globalThis as typeof globalThis & { uni: Uni }).uni
      uniApp.setStorageSync('apiAccessToken', accessToken)
      uniApp.setStorageSync('userInfo', {
        openid: `api-user-${user.id}`,
        role: user.role,
        nickName: user.nickname,
        avatarUrl: user.avatar_url || '',
        classIds: user.class_ids,
        permissions: user.permissions,
        createdAt: user.created_at,
      })
    },
    { accessToken: body.access_token, user: body.user },
  )
  await page.goto('/')
}

test('teacher manages a class and completes the guided-case review flow', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'The workflow runs once in the mobile project.')

  const title = '急性胸痛：危险分层与证据推理'

  await page.goto('/')
  await page.locator('.role-button.teacher').click()
  await expect(page.getByText('教学查房')).toBeVisible()

  await page.locator('.teacher-nav__item').filter({ hasText: '工作台' }).click()
  await page.getByText('班级管理', { exact: true }).click()
  await expect(page.getByText('班级管理', { exact: true }).first()).toBeVisible()
  await page.locator('input').nth(0).fill('E2E 春季班')
  await page.locator('input').nth(1).fill('e2e-spring-class')
  await page.getByText('创建班级', { exact: true }).click()
  await expect(page.getByText('E2E 春季班', { exact: true })).toBeVisible()
  const classCard = page.locator('.class-card').filter({ hasText: 'E2E 春季班' })
  await classCard.getByText('查看成员', { exact: true }).click()
  await classCard.locator('input').fill('demo_student')
  await page.getByText('加入', { exact: true }).click()
  await expect(page.getByText(/demo_student/)).toBeVisible()

  await page.goBack()
  await page.locator('.teacher-nav__item').filter({ hasText: '问题' }).click()
  await page.getByText('生成病例', { exact: true }).click()
  await expect(page.getByText('病例五步编排器')).toBeVisible()
  await page.locator('input').first().fill('急性胸痛')
  await page.getByText('生成病例草稿', { exact: true }).click()
  await expect(page.locator('input').first()).toHaveValue(title)
  for (let step = 0; step < 4; step += 1) {
    await page.getByText('下一步', { exact: true }).click()
  }
  await page.getByText('保存草稿', { exact: true }).click()
  await expect(page.getByText('提交医学审核', { exact: true })).toBeVisible()
  await page.getByText('提交医学审核', { exact: true }).click()
  await expect(page.getByText('医学审核中', { exact: true })).toBeVisible()

  await page.goBack()
  await page.getByText('退出', { exact: true }).click()
  await loginAsReviewer(page)
  await expect(page.getByText('教学查房')).toBeVisible()
  await page.locator('.teacher-nav__item').filter({ hasText: '工作台' }).click()
  await page
    .locator('.quick-links')
    .getByText(/医学审核/)
    .click()
  await expect(page.getByText('医学审核队列')).toBeVisible()
  await page.getByText(title, { exact: true }).click()
  await expect(page.getByText('隐藏事实（仅审核专家可见）')).toBeVisible()
  await page.getByText('审核通过', { exact: true }).click()
  await page.getByText('OK', { exact: true }).click()

  await page.goBack()
  await page.getByText('退出', { exact: true }).click()
  await page.locator('.role-button.teacher').click()
  await page.locator('.teacher-nav__item').filter({ hasText: '问题' }).click()
  const card = page.locator('.problem-card').filter({ hasText: title })
  await card.getByText('发布', { exact: true }).click()
  await page.getByText('OK', { exact: true }).click()
  await page.locator('.tab').filter({ hasText: '已发布' }).click()
  await expect(page.getByText(title, { exact: true }).first()).toBeVisible()
  await page
    .locator('.problem-card')
    .filter({ hasText: title })
    .getByText('创建新版本', { exact: true })
    .first()
    .click()
  await expect(page.getByText('草稿，尚未提交审核')).toBeVisible()
})
