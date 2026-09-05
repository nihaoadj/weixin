import { expect, test } from '@playwright/test'

test('student and teacher complete the pilot learning workflow', async ({ page, isMobile }) => {
  test.skip(!isMobile, 'The complete workflow runs once in the mobile project.')

  await page.goto('/')
  await expect(page.getByText('病理学 PBL 学习助手')).toBeVisible()
  await page.locator('.role-button.student').click()
  await page.locator('.student-nav__item').filter({ hasText: '答疑' }).click()
  await expect(page.getByText('从一个医学问题开始')).toBeVisible()

  await page.getByText('坏死与凋亡有哪些区别？').click()
  await expect(page.getByText(/演示反馈/)).toBeVisible()
  await page.locator('.report-button').click()
  await expect(page.getByText('AI 形成性评分')).toBeVisible()

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
  await expect(page.locator('[aria-label="当前课堂上下文"]')).toBeVisible()
  await page.locator('.student-nav__item').filter({ hasText: '答疑' }).click()
  await page.getByText('退出', { exact: true }).click()

  await page.locator('.role-button.teacher').click()
  await expect(page.getByText('课堂与诊断', { exact: true })).toBeVisible()
  await page.locator('.teacher-nav__item').filter({ hasText: '学情' }).click()
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
  await expect(page.getByText('学生学习记录', { exact: true })).toBeVisible()

  await page.locator('.teacher-nav__item').filter({ hasText: '内容' }).click()
  await page.getByText('新建问题', { exact: true }).click()
  const problemEditor = page.locator('.edit-page .form')
  const problemFields = problemEditor.getByRole('textbox')
  await expect(problemFields).toHaveCount(2)
  await problemFields.nth(0).fill('细胞损伤的形态依据练习')
  await problemFields.nth(1).fill('请说明细胞肿胀、核变化与可逆或不可逆损伤之间的证据关系。')
  await page.locator('.save').click()
  await expect(page.getByText('细胞损伤的形态依据练习')).toBeVisible()
  await page.locator('.action.publish').click()
  await page.getByText('OK', { exact: true }).click()
  await expect(page.getByText('细胞损伤的形态依据练习')).toBeVisible()

  await page.getByText('退出', { exact: true }).click()
  await page.locator('.role-button.student').click()
  await page.locator('.student-nav__item').filter({ hasText: '学习' }).click()
  await page.locator('.resource-row').filter({ hasText: '练习题' }).click()
  await expect(page.locator('.resource-tab.active')).toHaveText('练习')
  await expect(page.getByText('细胞损伤的形态依据练习')).toBeVisible()
})
