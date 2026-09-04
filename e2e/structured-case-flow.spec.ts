import { expect, test } from '@playwright/test'

test('student opens a pathology showcase case from the PBL-first knowledge entry', async ({ page }) => {
  await page.goto('/')
  await page.locator('.role-button.student').click()
  await page.locator('.student-nav__item').filter({ hasText: '知识' }).click()
  await expect(page.getByText('病理学病例练习')).toBeVisible()
  const showcase = page.getByText('细胞损伤：肾小管上皮的两种结局', { exact: true }).first()
  await expect(showcase).toBeVisible()
  await showcase.click()
  await expect(page.getByText('虚拟患者对话')).toBeVisible()
  await page.locator('input').first().fill('细胞膜和细胞核有什么改变？')
  await page.getByText('询问患者', { exact: true }).click()
  await expect(page.getByText(/细胞肿胀|核/)).toBeVisible()
  await page.locator('textarea').nth(0).fill('合成肾小管上皮细胞肿胀，核结构尚存。')
  await page.locator('textarea').nth(1).fill('细胞肿胀')
  await page.getByText('提交病史采集', { exact: true }).click()
  await expect(page.getByText('提交问题表征', { exact: true })).toBeVisible()
})
