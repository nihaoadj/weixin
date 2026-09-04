import { expect, test } from '@playwright/test'

const apiPort = Number(process.env.E2E_API_PORT ?? 8001)

test('history uses paged summaries and retries errors without downloading message lists', async ({ page }) => {
  const requests: string[] = []
  let failFirst = true
  page.on('request', (request) => {
    if (request.url().includes(`:${apiPort}/`)) requests.push(new URL(request.url()).pathname)
  })
  await page.route('**/conversations/summaries?*', (route) => {
    if (failFirst) {
      failFirst = false
      return route.fulfill({ status: 503, json: { detail: { code: 'SERVICE_ERROR', message: '暂时不可用' } } })
    }
    const offset = Number(new URL(route.request().url()).searchParams.get('offset'))
    const items = Array.from({ length: offset === 0 ? 20 : 1 }, (_, index) => ({
      id: offset + index + 1,
      client_id: `history-${offset + index}`,
      message_preview: `摘要 ${offset + index}`,
      message_count: 42,
      created_at: '2026-08-30T00:00:00Z',
      updated_at: '2026-08-30T00:00:00Z',
      report_status: null,
      report_id: null,
    }))
    return route.fulfill({ json: { items, total: 21, limit: 20, offset } })
  })
  await page.goto('/')
  await page.locator('.role-button.student').click()
  await page.locator('.student-nav__item').filter({ hasText: '答疑' }).click()
  await page.getByRole('button', { name: '查看历史学习记录' }).click()
  await expect(page.getByText('记录加载失败', { exact: true })).toBeVisible()
  await page.getByText('重新加载', { exact: true }).click()
  await expect(page.locator('.history-card')).toHaveCount(20)
  await page.locator('.load-more').click()
  await expect(page.locator('.history-card')).toHaveCount(21)
  await expect(page.locator('.load-more')).toHaveCount(0)
  expect(requests.filter((path) => path === '/conversations' || path === '/reports')).toEqual([])
  expect(requests.filter((path) => path === '/conversations/summaries')).toHaveLength(3)
})

test('invalid summary DTO produces a retryable contract error, not an empty state', async ({ page }) => {
  await page.route('**/reports/summaries?*', (route) =>
    route.fulfill({
      json: { items: [{ id: 'bad-id' }], total: 1, limit: 20, offset: 0, pending_count: 1, reviewed_count: 0 },
    }),
  )
  await page.goto('/')
  await page.locator('.role-button.teacher').click()
  await page.locator('.teacher-nav__item').filter({ hasText: '报告' }).click()
  await expect(page.getByText('报告加载失败', { exact: true })).toBeVisible()
  await expect(page.getByText('服务响应不符合数据契约', { exact: true })).toBeVisible()
  await expect(page.getByText('还没有学生报告', { exact: true })).toHaveCount(0)
})
