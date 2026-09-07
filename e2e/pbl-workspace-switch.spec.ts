import { expect, test } from '@playwright/test'

test('teacher switches workspace tabs without replacing the PBL page', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'The workspace interaction runs once in the mobile API project.')

  await page.goto('/')
  await page.locator('.role-button.teacher').click()
  await page.locator('.teacher-nav__item').filter({ hasText: 'PBL' }).click()
  await expect(page.getByText('准备课堂', { exact: true })).toBeVisible()

  let documentNavigations = 0
  page.on('request', (request) => {
    if (request.isNavigationRequest() && request.frame() === page.mainFrame()) documentNavigations += 1
  })

  await page.locator('.teacher-nav__item').filter({ hasText: '学情' }).click()
  await expect(page.getByText('学生学习记录', { exact: true })).toBeVisible()
  await page.locator('.teacher-nav__item').filter({ hasText: 'PBL' }).click()
  await expect(page.getByText('准备课堂', { exact: true })).toBeVisible()
  expect(documentNavigations).toBe(0)
})
