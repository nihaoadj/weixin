import { expect, test } from '@playwright/test'

test('student and teacher complete the pilot learning workflow', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'The complete workflow runs once in the mobile project.')

  await page.goto('/')
  await expect(page.getByText('临床思维学习助手')).toBeVisible()
  await page.locator('.role-button.student').click()
  await expect(page.getByText('今天想训练哪项临床思维？')).toBeVisible()

  await page.getByText('肺炎的典型症状有哪些？').click()
  await expect(page.getByText(/演示反馈/)).toBeVisible()
  await page.locator('.report-button').click()
  await expect(page.getByText('AI 形成性评分')).toBeVisible()
  await expect(page).toHaveScreenshot('student-report.png', { fullPage: true })

  await page.locator('.actions .primary-button').click()
  await expect(page.getByText('今天想训练哪项临床思维？')).toBeVisible()
  await page.getByText('退出', { exact: true }).click()

  await page.locator('.role-button.teacher').click()
  await expect(page.getByText('教学协作工作台')).toBeVisible()
  await page.getByText(/学生体验账号 · 报告/).click()
  await page.getByRole('spinbutton').fill('92')
  await page.getByRole('textbox').fill('结构清晰，下一步请补充鉴别诊断依据。')
  await page.locator('.submit-bar .primary-button').click()
  await expect(page.getByText('教学协作工作台')).toBeVisible()

  await page.locator('.tab').filter({ hasText: '问题' }).click()
  await page.getByText('＋ 新建', { exact: true }).click()
  await page.getByRole('textbox').nth(0).fill('肺炎鉴别诊断训练')
  await page.getByRole('textbox').nth(1).fill('请从症状、体征、实验室与影像证据进行分析。')
  await page.locator('.save').click()
  await expect(page.getByText('肺炎鉴别诊断训练')).toBeVisible()
  await page.locator('.action.publish').click()
  await page.getByText('OK', { exact: true }).click()
  await expect(page.getByText('肺炎鉴别诊断训练')).toBeVisible()

  await page.getByText('退出', { exact: true }).click()
  await page.locator('.role-button.student').click()
  await page.locator('.student-nav__item').filter({ hasText: '病例' }).click()
  await expect(page.getByText('临床病例训练')).toBeVisible()
  await expect(page.getByText('肺炎鉴别诊断训练')).toBeVisible()
  await page.getByText('肺炎鉴别诊断训练').click()
  await page.getByRole('textbox').fill('结合发热、咳嗽、炎症指标和胸部影像，并排除肺栓塞等疾病。')
  await page.locator('.send').click()
  await expect(page.getByText(/鉴别诊断/).last()).toBeVisible()
})
