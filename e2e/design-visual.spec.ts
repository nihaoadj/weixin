import { expect, test } from '@playwright/test'

test('student PBL task page keeps the next action prominent', async ({ page }) => {
  await page.goto('/')
  await page.locator('.role-button.student').click()
  await page.locator('.student-nav__item').filter({ hasText: '任务' }).click()
  await expect(page.getByText('PBL 课后任务', { exact: true })).toBeVisible()
  await expect(page).toHaveScreenshot('student-learning-page.png')
})

test('teacher PBL workspace keeps priority work and content switch readable', async ({ page }) => {
  await page.goto('/')
  await page.locator('.role-button.teacher').click()
  await expect(page.getByText('教学查房')).toBeVisible()
  await expect(page.getByText('PBL 教学工作区', { exact: true })).toBeVisible()
  await expect(page.locator('.teacher-nav__item.active')).toHaveText('PBL')
  await expect(page.getByText('诊断待办', { exact: true })).toBeVisible()
  await expect(page).toHaveScreenshot('teacher-workspace-page.png')
})
