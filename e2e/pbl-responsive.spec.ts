import { expect, test } from '@playwright/test'

test('PBL-first student entry keeps navigation usable from 320 to 1440 pixels', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'The viewport matrix runs once in the mobile project.')

  for (const width of [320, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/')
    await page.locator('.role-button.student').click()
    const navigation = page.getByRole('navigation', { name: '学生主导航' })
    await expect(navigation).toBeVisible()
    await expect(navigation.locator('.student-nav__item')).toHaveCount(4)
    const box = await navigation.boundingBox()
    expect(box?.y).toBeGreaterThan(0)
    expect((box?.y || 0) + (box?.height || 0)).toBeLessThanOrEqual(900)
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    await page.locator('.student-nav__item').filter({ hasText: '学情' }).click()
    await expect(page.locator('.student-nav__item.active')).toHaveText('学情')
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    await page.locator('.student-nav__item').filter({ hasText: '答疑' }).click()
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    await page.getByText('退出', { exact: true }).click()
  }
})

test('learning resources keep their three views inside the four-item navigation', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'The viewport matrix runs once in the mobile project.')

  for (const width of [320, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/')
    await page.locator('.role-button.student').click()
    await page.locator('.student-nav__item').filter({ hasText: '学习' }).click()
    await page.locator('.resource-row').filter({ hasText: '病例训练' }).click()

    await expect(page.locator('.resource-tab')).toHaveCount(3)
    await expect(page.locator('.student-nav__item')).toHaveCount(4)
    await expect(page.locator('.student-nav__item.active')).toHaveText('学习')
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)

    for (const label of ['知识', '练习', '病例']) {
      await page.locator('.resource-tab').filter({ hasText: label }).click()
      await expect(page.locator('.resource-tab.active')).toHaveText(label)
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    }

    await page.locator('.student-nav__item').filter({ hasText: '答疑' }).click()
    await page.getByText('退出', { exact: true }).click()
  }
})

test('teacher keeps four stable workspaces from 320 to 1440 pixels', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'The viewport matrix runs once in the mobile project.')

  for (const width of [320, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/')
    await page.locator('.role-button.teacher').click()

    const navigation = page.getByRole('navigation', { name: '教师主导航' })
    await expect(navigation.locator('.teacher-nav__item')).toHaveCount(4)
    for (const label of ['待办', '学情', '内容', 'PBL']) {
      await navigation.locator('.teacher-nav__item').filter({ hasText: label }).click()
      await expect(navigation.locator('.teacher-nav__item.active')).toHaveText(label)
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    }

    await page.getByRole('button', { name: '退出教师工作台' }).click()
  }
})
