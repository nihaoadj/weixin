import { expect, test } from '@playwright/test'

test('student learning page keeps the next action prominent', async ({ page }) => {
  await page.goto('/')
  await page.locator('.role-button.student').click()
  await page.locator('.student-nav__item').filter({ hasText: '学习' }).click()
  await expect(page.getByText(/能力画像|完成首次病例训练/).first()).toBeVisible()
  await expect(page).toHaveScreenshot('student-learning-page.png')
})

test('teacher workspace keeps priority work and content switch readable', async ({ page }) => {
  await page.goto('/')
  await page.locator('.role-button.teacher').click()
  await expect(page.getByText('教学查房')).toBeVisible()
  await expect(page.getByText('报告批阅', { exact: true })).toBeVisible()
  await expect(page.locator('.teacher-nav__item.active')).toHaveText('报告')
  await expect(page.getByText('今日待办')).toHaveCount(0)
  await expect(page).toHaveScreenshot('teacher-workspace-page.png')
})
