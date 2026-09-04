import { expect, test } from '@playwright/test'

test('PBL API-mode loop creates a pathology classroom and publishes teacher-reviewed work', async ({
  page,
  isMobile,
}) => {
  test.skip(!isMobile, 'The PBL loop runs once in the mobile API project.')

  await page.goto('/')
  await page.locator('.role-button.teacher').click()
  await expect(page.getByText('PBL 教学工作区')).toBeVisible()
  await page.getByText('细胞适应', { exact: true }).click()
  const createResponse = page.waitForResponse(
    (response) => response.request().method() === 'POST' && /\/classes\/\d+\/pbl-sessions$/.test(response.url()),
  )
  await page.getByText('创建课堂', { exact: true }).click()
  expect((await createResponse).status()).toBe(201)
  await expect(page.getByText('进行中')).toBeVisible()
  await page.getByText('退出', { exact: true }).click()

  await page.locator('.role-button.student').click()
  await expect(page.getByText('我的 PBL 课堂')).toBeVisible()
  const question = page.locator('textarea').first()
  await expect(question).toBeVisible()
  await question.fill('细胞肿胀是否一定说明细胞已经坏死？')
  await page.getByText('提交讨论', { exact: true }).click()
  await expect(page.getByText('追问：血管通透性和血流变化分别会造成什么表现？')).toBeVisible()
  await question.fill('我没有把观察到的形态和机制解释对应起来。')
  await page.getByText('提交讨论', { exact: true }).click()
  await expect(page.getByText('待教师确认的学习线索')).toBeVisible()
  await expect(page.getByText('机制解释需要补充')).toBeVisible()
  await page.locator('.student-nav__item').filter({ hasText: '答疑' }).click()
  await page.getByText('退出', { exact: true }).click()

  await page.locator('.role-button.teacher').click()
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
  await page.locator('.student-nav__item').filter({ hasText: '任务' }).click()
  await expect(page.getByText('PBL 课后任务', { exact: true })).toBeVisible()
  await expect(page.getByText('1. 正式讨论题', { exact: true })).toBeVisible()
})
