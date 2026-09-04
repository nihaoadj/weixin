import { expect, test } from '@playwright/test'

test('PBL-first student entry keeps navigation usable from 320 to 1440 pixels', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'The viewport matrix runs once in the mobile project.')

  for (const width of [320, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/')
    await page.locator('.role-button.student').click()
    await expect(page.getByText('我的 PBL 课堂', { exact: true })).toBeVisible()
    const navigation = page.getByRole('navigation', { name: '学生主导航' })
    await expect(navigation).toBeVisible()
    const box = await navigation.boundingBox()
    expect(box?.y).toBeGreaterThan(0)
    expect((box?.y || 0) + (box?.height || 0)).toBeLessThanOrEqual(900)
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    await page.locator('.student-nav__item').filter({ hasText: '答疑' }).click()
    await page.getByText('退出', { exact: true }).click()
  }
})
