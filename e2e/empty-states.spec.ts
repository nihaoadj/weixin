import { expect, test } from '@playwright/test'

test('fresh student and teacher accounts receive actionable empty states', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'The empty-state workflow runs once in the mobile project.')

  await page.route('**/conversations/summaries?*', (route) =>
    route.fulfill({ json: { items: [], total: 0, limit: 20, offset: 0 } }),
  )
  await page.route('**/reports/summaries?*', (route) =>
    route.fulfill({ json: { items: [], total: 0, limit: 20, offset: 0, pending_count: 0, reviewed_count: 0 } }),
  )

  await page.goto('/')
  await page.locator('.role-button.student').click()
  await page.locator('.student-nav__item').filter({ hasText: '记录' }).click()
  await expect(page.getByText('暂无历史记录', { exact: true })).toBeVisible()
  await expect(page.getByText('开始医学问答', { exact: true })).toBeVisible()
  await page.getByText('开始医学问答', { exact: true }).click()
  await expect(page.getByText('今天想训练哪项临床思维？')).toBeVisible()

  await page.getByText('退出', { exact: true }).click()
  await page.locator('.role-button.teacher').click()
  await expect(page.getByText('还没有学生报告', { exact: true })).toBeVisible()
  await expect(page.getByText('管理教学内容', { exact: true })).toBeVisible()
})
