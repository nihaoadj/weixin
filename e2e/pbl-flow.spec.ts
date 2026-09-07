import { expect, test } from '@playwright/test'

test('PBL API-mode loop advances four stages, publishes work and exposes automatic tasks', async ({
  page,
  isMobile,
}) => {
  test.skip(!isMobile, 'The PBL loop runs once in the mobile API project.')

  await page.goto('/')
  await page.locator('.role-button.teacher').click()
  await page.locator('.teacher-nav__item').filter({ hasText: 'PBL' }).click()
  await expect(page.getByText('准备课堂', { exact: true })).toBeVisible()
  await page.getByText('细胞适应', { exact: true }).click()
  const createResponse = page.waitForResponse(
    (response) => response.request().method() === 'POST' && /\/classes\/\d+\/pbl-sessions$/.test(response.url()),
  )
  await page.getByText('创建课堂', { exact: true }).click()
  expect((await createResponse).status()).toBe(201)
  await expect(page.getByText('进行中')).toBeVisible()
  await page.getByText('退出', { exact: true }).click()

  await page.locator('.role-button.student').click()
  await expect(page.locator('[aria-label="研讨上下文"]')).toBeVisible()
  await page.getByText('确认并开始', { exact: true }).click()
  const question = page.locator('textarea').first()
  await expect(question).toBeVisible()
  await question.fill('细胞肿胀是否一定说明细胞已经坏死？')
  await page.getByText('发送', { exact: true }).click()
  await expect(page.locator('.meta-chip').filter({ hasText: '提出假设' })).toBeVisible()
  await question.fill('我提出可逆性损伤与坏死两个机制假设，但仍不确定。')
  await page.getByText('发送', { exact: true }).click()
  await expect(page.locator('.meta-chip').filter({ hasText: '讨论证据' })).toBeVisible()
  await question.fill('细胞肿胀支持可逆性损伤，核改变支持坏死，但当前形态证据有限。')
  await page.getByText('发送', { exact: true }).click()
  await expect(page.locator('.meta-chip').filter({ hasText: '总结解释' })).toBeVisible()
  await question.fill('综合机制与形态证据，目前倾向可逆性损伤，仍需复核细胞核变化。')
  await page.getByText('发送', { exact: true }).click()
  await expect(page.locator('.meta-chip').filter({ hasText: '已完成' })).toBeVisible()
  await expect(page.getByText('已形成学习线索')).toBeVisible()
  await expect(page.getByText('机制解释需要补充')).toBeVisible()
  await expect(page.getByText(/四阶段研讨已完成，输入已关闭/)).toBeVisible()
  await page.locator('.student-nav__item').filter({ hasText: '学情' }).click()
  await expect(page.getByText('当前重点', { exact: true })).toBeVisible()
  await expect(page.getByText('待发布学习', { exact: true }).first()).toBeVisible()
  await page.locator('.report-row').first().click()
  await expect(page.getByText('四阶段讨论证据', { exact: true })).toBeVisible()
  await expect(page.getByText('已有证据', { exact: true })).toHaveCount(4)
  for (const width of [320, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 })
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  }
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goBack()
  await expect(page.getByText('当前重点', { exact: true })).toBeVisible()
  await page.locator('.student-nav__item').filter({ hasText: '研讨' }).click()
  await page.getByText('退出', { exact: true }).click()

  await page.locator('.role-button.teacher').click()
  await page.locator('.teacher-nav__item').filter({ hasText: 'PBL' }).click()
  await expect(page.getByText('诊断待办')).toBeVisible()
  const title = page.locator('.suggestion input').first()
  await title.fill('教师编辑：细胞损伤的形态与机制')
  const adopted = page.waitForResponse(
    (response) => response.request().method() === 'POST' && response.url().endsWith('/adopt-and-publish'),
  )
  await page.getByText('采用并发布', { exact: true }).click()
  expect((await adopted).ok()).toBeTruthy()
  await expect(page.locator('.suggestion uni-button').filter({ hasText: '已发布' })).toBeVisible()
  await page.getByText('退出', { exact: true }).click()

  await page.locator('.role-button.student').click()
  await page.locator('.student-nav__item').filter({ hasText: '学习' }).click()
  await expect(page.getByText('PBL 课后任务', { exact: true })).toBeVisible()
  await expect(page.getByText('第 1 轮 · 正式讨论题', { exact: true })).toBeVisible()
  await expect(page.getByText(/第 1\/2 轮 · pbl-mastery-v1/)).toBeVisible()

  for (let step = 0; step < 4; step += 1) {
    const task = page.locator('.task--next')
    await expect(task).toBeVisible()
    const title = await task.locator('.subtitle').innerText()
    if (title.includes('正式讨论题')) {
      await task.locator('textarea').fill('完成正式讨论，并说明形态证据、机制解释与不确定性。')
    } else if (title.includes('知识巩固')) {
      await task.locator('uni-label').nth(0).click()
    } else if (title.includes('客观再测')) {
      await task.locator('uni-label').nth(1).click()
    } else {
      await task.locator('textarea').fill('肿胀、细胞膜、核、不可逆')
    }
    await expect(task.locator('uni-button.primary')).not.toHaveAttribute('disabled')
    const submitted = page.waitForResponse(
      (response) => response.request().method() === 'POST' && /pbl-learning-tasks\/\d+\/submit$/.test(response.url()),
    )
    await task.getByText('完成这一步', { exact: true }).click()
    expect((await submitted).ok()).toBeTruthy()
    if (step < 3) await expect(page.locator('.task--next .subtitle')).not.toHaveText(title)
  }
  await expect(page.getByText(/系统判定已改善/)).toBeVisible()
  await page.locator('.student-nav__item').filter({ hasText: '学情' }).click()
  await expect(page.getByText('已改善', { exact: true }).first()).toBeVisible()
  await page.locator('.report-row').first().click()
  await expect(page.getByText('目标改善对照', { exact: true })).toBeVisible()
  await expect(page.getByText('本轮目标全部达标', { exact: true })).toBeVisible()
  await page.goBack()
  await expect(page.getByText('当前重点', { exact: true })).toBeVisible()
  await page.locator('.student-nav__item').filter({ hasText: '研讨' }).click()
  await page.getByText('退出', { exact: true }).click()

  await page.locator('.role-button.teacher').click()
  await page.locator('.teacher-nav__item').filter({ hasText: 'PBL' }).click()
  await expect(page.getByText('学习结果数据', { exact: true })).toBeVisible()
  await expect(page.getByText(/系统判定已改善/)).toBeVisible()
  await expect(page.getByText('第 1 轮 · 已完成', { exact: true }).first()).toBeVisible()
  await expect(page.getByRole('button', { name: '确认已改善' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: '继续巩固' })).toHaveCount(0)
})
