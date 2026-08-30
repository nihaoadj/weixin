import { expect, test } from '@playwright/test'

test('login page keeps the premium medical layout', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('临床思维学习助手')).toBeVisible()
  await expect(page).toHaveScreenshot('login-page.png', { fullPage: true })
})
