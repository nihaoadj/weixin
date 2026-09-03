import { expect, test } from '@playwright/test'

test('student and teacher complete the pilot learning workflow', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'The complete workflow runs once in the mobile project.')

  await page.goto('/')
  await expect(page.getByText('临床思维学习助手')).toBeVisible()
  await page.locator('.role-button.student').click()
  await expect(page.getByText('从一个医学问题开始')).toBeVisible()

  await page.getByText('肺炎的典型症状有哪些？').click()
  await expect(page.getByText(/演示反馈/)).toBeVisible()
  await page.locator('.report-button').click()
  await expect(page.getByText('AI 形成性评分')).toBeVisible()
  await expect(page).toHaveScreenshot('student-report.png', { fullPage: true })

  const submitResponsePromise = page.waitForResponse((response) => {
    const request = response.request()
    return request.method() === 'POST' && response.url().endsWith('/submit') && response.ok()
  })
  await page.locator('.actions .primary-button').click()
  const submittedReportResponse = await submitResponsePromise
  const submittedReport = (await submittedReportResponse.json()) as { id?: number | string }
  expect(submittedReport.id).toBeDefined()
  const reportId = String(submittedReport.id)
  expect(reportId).not.toBe('')
  await expect(page.getByText('从一个医学问题开始')).toBeVisible()
  await page.getByText('退出', { exact: true }).click()

  await page.locator('.role-button.teacher').click()
  await expect(page.getByText('教学查房')).toBeVisible()
  const reportCard = page.locator(`.report-card[data-report-id="${reportId}"]`)
  await expect(reportCard).toHaveCount(1)
  await expect(reportCard).toContainText('学生体验账号')
  await reportCard.click()
  await page.getByRole('spinbutton').fill('92')
  await page.getByRole('textbox').fill('结构清晰，下一步请补充鉴别诊断依据。')
  const reviewResponsePromise = page.waitForResponse((response) => {
    const request = response.request()
    return request.method() === 'POST' && response.url().endsWith(`/reports/${reportId}/review`) && response.ok()
  })
  await page.locator('.submit-bar .primary-button').click()
  const reviewedReport = (await (await reviewResponsePromise).json()) as { id?: number | string }
  expect(String(reviewedReport.id)).toBe(reportId)
  await expect(page.getByText('教学查房')).toBeVisible()

  await page.locator('.teacher-nav__item').filter({ hasText: '问题' }).click()
  await page.getByText('新建问题', { exact: true }).click()
  const problemEditor = page.locator('.edit-page .form')
  const problemFields = problemEditor.getByRole('textbox')
  await expect(problemFields).toHaveCount(2)
  await problemFields.nth(0).fill('肺炎鉴别诊断训练')
  await problemFields.nth(1).fill('请从症状、体征、实验室与影像证据进行分析。')
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
  await expect(
    page.getByText('演示反馈：建议从定义、常见表现、鉴别要点和处理原则四部分梳理。医学内容仅用于教学。', {
      exact: true,
    }),
  ).toBeVisible()
})
