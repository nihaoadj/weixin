import { expect, test } from '@playwright/test'

test('login page keeps the premium medical layout', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('病理学 PBL 学习助手')).toBeVisible()
  await expect(page).toHaveScreenshot('login-page.png', { fullPage: true })
})
