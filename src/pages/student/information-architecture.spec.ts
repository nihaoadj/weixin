import { readFile } from 'node:fs/promises'
import { describe, expect, it } from 'vitest'
import pagesConfig from '../../pages.json'

const pageSource = (relativePath: string) => readFile(new URL(relativePath, import.meta.url), 'utf8')

describe('T17 student information architecture', () => {
  it('uses concise native titles for the three primary destinations and legacy history', () => {
    const titles = Object.fromEntries(pagesConfig.pages.map((page) => [page.path, page.style.navigationBarTitleText]))
    expect(titles['pages/student/pbl/pbl']).toBe('研讨')
    expect(titles['pages/student/learning/index']).toBe('学习')
    expect(titles['pages/student/insights/index']).toBe('学情')
    expect(titles['pages/student/insights/detail']).toBe('学习记录')
    expect(titles['pages/student/chat/chat']).toBe('历史答疑')
    expect(titles['pages/student/question/question']).toBe('病例学习')
  })

  it('removes the known duplicate visible heroes while retaining accessible page names', async () => {
    const [pbl, insights, insightDetail, dialogueReview, chat] = await Promise.all([
      pageSource('./pbl/pbl.vue'),
      pageSource('./insights/index.vue'),
      pageSource('./insights/detail.vue'),
      pageSource('../../features/pbl/presentation/LearningDialogueReview.vue'),
      pageSource('./chat/chat.vue'),
    ])

    expect(pbl).not.toContain('我的 PBL 课堂')
    expect(pbl).not.toContain('PATHOLOGY · PBL')
    expect(pbl).not.toContain('class="account-bar"')
    expect(pbl).not.toContain('class="case-brief"')
    expect(pbl).not.toContain('id="dialogue-diagnostic"')
    expect(pbl).not.toContain('阶段反馈')
    expect(insights).not.toContain('我的病理学习档案')
    expect(insights).not.toContain('LEARNING EVIDENCE')
    expect(insights).toContain('class="insight-section recent-section"')
    expect(insights).toContain('本周学习状态')
    expect(insights).toContain('学习趋势')
    expect(insights).toContain('当前薄弱点')
    expect(insights).toContain('AI 诊断总结')
    expect(insights).toContain('最近对话记录')
    expect(insights).toContain('class="profile-motivation"')
    expect(insights).toContain('/static/student-insights-motivation-separated.svg')
    expect(insights).not.toContain('class="profile-heart"')
    expect(insights).not.toContain('用 AI 点亮医学之路')
    expect(insights).toContain('dashboard.value.dataBasis')
    expect(insightDetail).toContain(":secondary-action-label=\"invalidRoute ? '' : '返回学情'\"")
    expect(insightDetail).not.toContain('.report-section::before')
    expect(insightDetail).not.toContain('.section-kicker::after')
    expect(insightDetail).toContain('class="empty-note"')
    expect(insightDetail).toContain('<LearningRecordSectionHeading')
    expect(insightDetail).toContain('本次学习结论')
    expect(insightDetail).toContain('<LearningDialogueReview')
    expect(insightDetail).toContain('getLearningDialogue(sessionId)')
    expect(dialogueReview).toContain('class="dialogue-review__swiper"')
    expect(dialogueReview).toContain('scroll-y')
    expect(dialogueReview).toContain('私人续问 · 仅自己可见 · 不计入证据')
    expect(insightDetail).toContain('学习证据路径')
    expect(insightDetail).toContain('本次学习重点')
    expect(insightDetail).toContain('目标改善轨迹')
    expect(insightDetail).toContain('正式学习任务')
    expect(insightDetail).toContain('学习记录时间线')
    expect(insightDetail).toContain('teacherFeedbacks.length')
    expect(insightDetail).toContain('report.value?.visibility')
    expect(insightDetail).toContain('不合并为综合分')
    expect(insightDetail).not.toContain('综合得分')
    expect(insightDetail).not.toContain('defineComponent')
    expect(chat).toContain('class="sr-only"')
    expect([pbl, insights, chat].every((source) => source.includes('aria-level="1"'))).toBe(true)
  })
})

describe('T31 PBL turn response style', () => {
  it('places the per-turn picker in the composer and removes the old session-level selector', async () => {
    const pbl = await pageSource('./pbl/pbl.vue')

    expect(pbl).toContain('<template #context>')
    expect(pbl).toContain('<PblResponseStylePicker')
    expect(pbl).toContain('class="session-book-icon"')
    expect(pbl).toContain('<selection')
    expect(pbl).toContain('disable-context-menu')
    expect(pbl).toContain('user-select')
    expect(pbl).not.toContain('继续问')
    expect(pbl).toContain('@keyboard-height-change="handleKeyboardHeightChange"')
    expect(pbl).toContain('dialogueViewportStyle')
    expect(pbl).toContain('class="bubble"')
    expect(pbl).not.toContain('class="response-heading"')
    expect(pbl).toContain('默认使用探究引导')
    expect(pbl).not.toContain('正式研讨已完成；后续输入为私人续问。')
    expect(pbl).not.toContain('后续学习')
    expect(pbl).not.toContain('class="style-grid"')
    expect(pbl).not.toContain('class="style-card"')
    expect(pbl).not.toContain('选择回应方式后开始')
  })
})
