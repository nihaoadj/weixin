import { expect, test } from '@playwright/test'

test('student direct dialogue uses the unified PBL evidence and teacher queue', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'The unified dialogue workflow runs once in the mobile API project.')

  await page.goto('/')
  await expect(page.getByText('病理学 PBL 学习助手')).toBeVisible()
  await page.locator('.role-button.student').click()
  if (
    !(await page
      .getByText('开始一次病理研讨', { exact: true })
      .isVisible()
      .catch(() => false))
  )
    await page.locator('.new-action').click()
  await expect(page.getByText('开始一次病理研讨', { exact: true })).toBeVisible()
  await page.locator('.choice-chip').first().click()
  await page.locator('.style-card').filter({ hasText: '先直接解释' }).click()
  const created = page.waitForResponse(
    (response) => response.request().method() === 'POST' && response.url().endsWith('/student/learning-dialogues'),
  )
  await page.getByText('进入统一学习流程', { exact: true }).click()
  expect((await created).status()).toBe(201)
  await expect(page.locator('.meta-chip').filter({ hasText: '主动研讨' })).toBeVisible()
  await expect(page.locator('.meta-chip').filter({ hasText: '先直接解释' })).toBeVisible()

  const question = page.locator('textarea').first()
  for (const [index, content] of [
    '细胞肿胀是否一定说明细胞已经坏死？',
    '我提出可逆性损伤与坏死两个机制假设。',
    '细胞肿胀支持可逆损伤，核改变支持坏死。',
    '综合机制与形态证据，目前仍需复核核变化。',
  ].entries()) {
    await question.fill(content)
    const sent = page.waitForResponse(
      (response) =>
        response.request().method() === 'POST' && /\/student\/learning-dialogues\/\d+\/messages$/.test(response.url()),
    )
    await page.getByText('发送', { exact: true }).click()
    expect((await sent).ok()).toBeTruthy()
    if (index === 0) {
      await expect(page.getByText(/先说明/)).toBeVisible()
      await expect(page.getByText('已形成学习线索', { exact: true })).toHaveCount(0)
    }
  }
  await expect(page.getByText('已形成学习线索', { exact: true })).toBeVisible()
  await expect(page.getByText(/四阶段研讨已完成/)).toBeVisible()
  await page.getByText('退出', { exact: true }).click()

  await page.locator('.role-button.teacher').click()
  await page.locator('.teacher-nav__item').filter({ hasText: 'PBL' }).click()
  await expect(page.getByText('统一研讨 v4', { exact: true }).first()).toBeVisible()
  await expect(page.getByText(/学生主动 · 先直接解释/)).toBeVisible()
})
