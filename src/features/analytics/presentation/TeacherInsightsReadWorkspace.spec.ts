import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import TeacherInsightsReadWorkspace from './TeacherInsightsReadWorkspace.vue'
import type {
  TeacherInsightsDiagnosisPage,
  TeacherInsightsFilters,
  TeacherInsightsKnowledgePage,
  TeacherInsightsScope,
  TeacherInsightsStudentPage,
} from '@/features/analytics/public'

const api = vi.hoisted(() => ({
  getTeacherInsightsOverview: vi.fn(),
  getTeacherInsightsStudents: vi.fn(),
  getTeacherInsightsStudent: vi.fn(),
  getTeacherInsightsKnowledge: vi.fn(),
  getTeacherInsightsDiagnostics: vi.fn(),
  getKnowledgeCatalog: vi.fn(),
  learningGoalLabel: vi.fn(),
}))
const auth = vi.hoisted(() => ({
  session: null as null | { openid: string; role: 'teacher' | 'student' },
}))

vi.mock('@/features/analytics/public', () => ({
  getTeacherInsightsOverview: api.getTeacherInsightsOverview,
  getTeacherInsightsStudents: api.getTeacherInsightsStudents,
  getTeacherInsightsStudent: api.getTeacherInsightsStudent,
  getTeacherInsightsKnowledge: api.getTeacherInsightsKnowledge,
  getTeacherInsightsDiagnostics: api.getTeacherInsightsDiagnostics,
}))
vi.mock('@/features/identity/public', () => ({ getSession: () => auth.session }))
vi.mock('@/features/learning/public', () => ({
  getKnowledgeCatalog: api.getKnowledgeCatalog,
  learningGoalLabel: api.learningGoalLabel,
}))

const filters = (classId?: number): TeacherInsightsFilters => ({
  classId,
  dateFrom: '2026-09-01',
  dateTo: '2026-09-30',
})

function scope(classId: number | null, className: string | null): TeacherInsightsScope {
  return {
    classId,
    className,
    classIds: classId === null ? [1, 2] : [classId],
    sessionId: null,
    dateFrom: '2026-09-01',
    dateTo: '2026-09-30',
    timezone: 'Asia/Shanghai',
    asOf: '2026-09-30T12:00:00+08:00',
    metricBasis: {
      progress: 'published_route_cohort',
      results: 'completed_test_window',
      diagnoses: 'completed_diagnosis_window',
    },
  }
}

function studentPage(
  classId: number,
  className: string,
  studentId: number,
  studentName: string,
): TeacherInsightsStudentPage {
  return {
    scope: scope(classId, className),
    items: [
      {
        studentId,
        studentName,
        classIds: [classId],
        cohort: { publishedRoutes: 2, completedTests: 1, completionRate: 50, gradingTests: 0 },
        periodResults: { completedTests: 1, averageScore: 0, formatCounts: { mixed_v2: 1 } },
        diagnosisCount: 1,
        lastCompletedAt: '2026-09-20T10:00:00+08:00',
      },
    ],
    total: 1,
    limit: 20,
    offset: 0,
  }
}

function emptyDiagnosisPage(classId: number): TeacherInsightsDiagnosisPage {
  return {
    scope: scope(classId, `班级 ${classId}`),
    items: [],
    total: 0,
    limit: 20,
    offset: 0,
    knowledgeGaps: [],
    reasoningIssues: [],
  }
}

function knowledgePage(classId: number, items: TeacherInsightsKnowledgePage['items']): TeacherInsightsKnowledgePage {
  return { scope: scope(classId, `班级 ${classId}`), items, resultCount: 2 }
}

function mountWorkspace(panel: 'overview' | 'progress' | 'knowledge' | 'students', selectedFilters = filters(1)) {
  return mount(TeacherInsightsReadWorkspace, {
    props: {
      panel,
      filters: selectedFilters,
      classes: [
        { id: 1, name: '炎症班' },
        { id: 2, name: '免疫班' },
      ],
    },
    global: {
      stubs: {
        MedState: {
          props: ['title', 'description', 'actionLabel'],
          emits: ['action'],
          template:
            '<div class="med-state"><span>{{ title }}</span><span>{{ description }}</span><button v-if="actionLabel" @click="$emit(\'action\')">{{ actionLabel }}</button></div>',
        },
        TeacherPager: true,
      },
    },
  })
}

describe('TeacherInsightsReadWorkspace', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    auth.session = { openid: 'teacher-1', role: 'teacher' }
    api.getKnowledgeCatalog.mockResolvedValue([])
    api.learningGoalLabel.mockImplementation((code: string) => code)
  })

  it('renders server percentages as 0–100 values and distinguishes null samples from a real zero', async () => {
    api.getTeacherInsightsKnowledge.mockResolvedValue(
      knowledgePage(1, [
        {
          pointCode: 'pathology.inflammation',
          correctCount: 1,
          objectiveCount: 2,
          invalidObjectiveCount: 0,
          accuracyRate: 50,
          shortAnswerCount: 0,
          invalidShortAnswerCount: 0,
          pointsAwarded: 0,
          pointsPossible: 0,
          shortAnswerScoreRate: null,
        },
        {
          pointCode: 'pathology.zero',
          correctCount: 0,
          objectiveCount: 1,
          invalidObjectiveCount: 0,
          accuracyRate: 0,
          shortAnswerCount: 1,
          invalidShortAnswerCount: 0,
          pointsAwarded: 0,
          pointsPossible: 10,
          shortAnswerScoreRate: 0,
        },
      ]),
    )
    api.getTeacherInsightsDiagnostics.mockResolvedValue(emptyDiagnosisPage(1))

    const wrapper = mountWorkspace('knowledge')
    await flushPromises()

    expect(wrapper.text()).toContain('50%')
    expect(wrapper.text()).toContain('0%')
    expect(wrapper.text()).toContain('暂无样本')
    expect(wrapper.text()).not.toContain('5000.0%')
  })

  it.each([
    { rate: 71.4, text: '71.4%' },
    { rate: null, text: '暂无样本' },
    { rate: 100, text: '100%' },
  ])('renders completion text for a $rate rate', async ({ rate, text }) => {
    const students = studentPage(1, '炎症班', 10, '概况学生')
    api.getTeacherInsightsStudents.mockResolvedValue(students)
    api.getTeacherInsightsKnowledge.mockResolvedValue(knowledgePage(1, []))
    api.getTeacherInsightsOverview.mockResolvedValue({
      scope: students.scope,
      cohort: { ...students.items[0]!.cohort, completionRate: rate },
      periodResults: { ...students.items[0]!.periodResults },
      diagnosisCount: 0,
      studentCount: 1,
    })

    const wrapper = mountWorkspace('overview')
    await flushPromises()

    expect(wrapper.get('.completion-value').text()).toBe(text)
  })

  it('keeps successful knowledge statistics readable when the diagnostics query fails', async () => {
    api.getTeacherInsightsKnowledge.mockResolvedValue(
      knowledgePage(1, [
        {
          pointCode: 'pathology.inflammation',
          correctCount: 1,
          objectiveCount: 2,
          invalidObjectiveCount: 0,
          accuracyRate: 50,
          shortAnswerCount: 0,
          invalidShortAnswerCount: 0,
          pointsAwarded: 0,
          pointsPossible: 0,
          shortAnswerScoreRate: null,
        },
      ]),
    )
    api.getTeacherInsightsDiagnostics.mockRejectedValue(new Error('诊断汇总服务暂不可用'))

    const wrapper = mountWorkspace('knowledge')
    await flushPromises()

    expect(wrapper.text()).toContain('pathology.inflammation')
    expect(wrapper.text()).toContain('50%')
    expect(wrapper.text()).toContain('诊断汇总服务暂不可用')
    expect(wrapper.find('.med-state').text()).toContain('诊断汇总读取失败')
  })

  it('ignores a late response from the previous classroom filter', async () => {
    let resolveFirst!: (value: TeacherInsightsStudentPage) => void
    let resolveSecond!: (value: TeacherInsightsStudentPage) => void
    api.getTeacherInsightsStudents
      .mockReturnValueOnce(new Promise((resolve) => (resolveFirst = resolve)))
      .mockReturnValueOnce(new Promise((resolve) => (resolveSecond = resolve)))

    const wrapper = mountWorkspace('students', filters(1))
    await flushPromises()
    await wrapper.setProps({ filters: filters(2) })

    expect(api.getTeacherInsightsStudents).toHaveBeenNthCalledWith(1, filters(1), 20, 0)
    expect(api.getTeacherInsightsStudents).toHaveBeenNthCalledWith(2, filters(2), 20, 0)
    resolveSecond(studentPage(2, '免疫班', 22, '新班学生'))
    await flushPromises()
    expect(wrapper.text()).toContain('新班学生')

    resolveFirst(studentPage(1, '炎症班', 11, '旧班迟到学生'))
    await flushPromises()
    expect(wrapper.text()).toContain('新班学生')
    expect(wrapper.text()).not.toContain('旧班迟到学生')
  })

  it('emits only the authorized class and student summary for detail navigation', async () => {
    api.getTeacherInsightsStudents.mockResolvedValue(studentPage(7, '病理课堂', 42, '周同学'))

    const wrapper = mountWorkspace('students', filters(7))
    await flushPromises()
    await wrapper.get('.detail-action').trigger('click')

    expect(wrapper.emitted('openStudent')).toEqual([[{ studentId: 42, classId: 7 }]])
    expect(api.getTeacherInsightsStudent).not.toHaveBeenCalled()
    expect(wrapper.text()).not.toContain('resultId')
    expect(wrapper.text()).not.toContain('参考答案')
  })
  it('ranks all student pages for the overview, includes zero and excludes missing scores', async () => {
    const first = studentPage(1, '炎症班', 10, '第一页学生')
    first.items[0]!.periodResults.averageScore = 90
    first.total = 7
    const later = studentPage(1, '炎症班', 11, '零分学生')
    const zeroScore = later.items[0]!
    const withScore = (studentId: number, studentName: string, averageScore: number) => ({
      ...zeroScore,
      studentId,
      studentName,
      periodResults: { ...zeroScore.periodResults, averageScore },
    })
    later.items = [
      zeroScore,
      withScore(12, '低分学生', 55),
      withScore(14, '第三低分学生', 65),
      withScore(15, '第四低分学生', 70),
      withScore(16, '第五低分学生', 80),
      {
        ...zeroScore,
        studentId: 13,
        studentName: '无结果学生',
        periodResults: { ...zeroScore.periodResults, completedTests: 0, averageScore: null },
      },
    ]
    later.total = 7
    later.offset = 1
    api.getTeacherInsightsStudents.mockResolvedValueOnce(first).mockResolvedValueOnce(later)
    api.getTeacherInsightsKnowledge.mockResolvedValue(knowledgePage(1, []))
    api.getTeacherInsightsOverview.mockResolvedValue({
      scope: first.scope,
      cohort: first.items[0]!.cohort,
      periodResults: { completedTests: 2, averageScore: 0, formatCounts: {} },
      diagnosisCount: 0,
      studentCount: 4,
    })
    const wrapper = mountWorkspace('overview')
    await flushPromises()
    expect(api.getTeacherInsightsStudents).toHaveBeenNthCalledWith(2, filters(1), 100, 1)
    expect(wrapper.findAll('.student-row__name').map((item) => item.text())).toEqual(['零分学生', '低分学生'])
    expect(wrapper.findAll('.student-row__name')).toHaveLength(2)
    expect(wrapper.text()).not.toContain('第三低分学生')
    expect(wrapper.text()).not.toContain('无结果学生')
    expect(wrapper.text()).not.toContain('第五低分学生')
    expect(wrapper.text()).not.toContain('第一页学生')
    expect(wrapper.get('.average-value').text()).toBe('0分')
    expect(wrapper.text()).toContain('条路线')
    expect(wrapper.text()).not.toContain('判分中')
    await wrapper.findAll('.see-all')[0]!.trigger('click')
    await wrapper.findAll('.see-all')[1]!.trigger('click')
    expect(wrapper.emitted('selectPanel')).toEqual([['knowledge'], ['students']])
  })

  it('does not publish a partial low-score ranking when a later page fails', async () => {
    const first = studentPage(1, '炎症班', 10, '不完整排名')
    first.total = 2
    api.getTeacherInsightsStudents.mockResolvedValueOnce(first).mockRejectedValueOnce(new Error('后续页读取失败'))
    api.getTeacherInsightsKnowledge.mockResolvedValue(knowledgePage(1, []))
    api.getTeacherInsightsOverview.mockResolvedValue({
      scope: first.scope,
      cohort: first.items[0]!.cohort,
      periodResults: first.items[0]!.periodResults,
      diagnosisCount: 0,
      studentCount: 2,
    })
    const wrapper = mountWorkspace('overview')
    await flushPromises()
    expect(wrapper.text()).toContain('后续页读取失败')
    expect(wrapper.findAll('.student-row')).toHaveLength(0)
    expect(wrapper.find('.overview-counts').exists()).toBe(true)
  })

  it('appends students, keeps existing rows on failure and ignores a late append after scope changes', async () => {
    const first = studentPage(1, '炎症班', 10, '已加载学生')
    first.total = 2
    let resolveLate!: (value: TeacherInsightsStudentPage) => void
    api.getTeacherInsightsStudents
      .mockResolvedValueOnce(first)
      .mockRejectedValueOnce(new Error('继续加载失败'))
      .mockReturnValueOnce(
        new Promise((resolve) => {
          resolveLate = resolve
        }),
      )
      .mockResolvedValueOnce(studentPage(2, '免疫班', 20, '新范围学生'))
    const wrapper = mountWorkspace('students')
    await wrapper.setProps({ studentListOnly: true })
    await flushPromises()
    await wrapper.get('.load-more').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('已加载学生')
    expect(wrapper.text()).toContain('继续加载失败')
    await wrapper.get('.load-more').trigger('click')
    await wrapper.setProps({ filters: filters(2) })
    await flushPromises()
    resolveLate(studentPage(1, '炎症班', 11, '旧范围追加'))
    await flushPromises()
    expect(wrapper.text()).toContain('新范围学生')
    expect(wrapper.text()).not.toContain('旧范围追加')
  })

  it('deduplicates continued student pages and finishes at the server offset', async () => {
    const first = studentPage(1, '炎症班', 10, '原学生')
    first.total = 3
    const second = studentPage(1, '炎症班', 11, '追加学生')
    second.offset = 1
    second.total = 3
    second.items = [first.items[0]!, second.items[0]!]
    api.getTeacherInsightsStudents.mockResolvedValueOnce(first).mockResolvedValueOnce(second)
    const wrapper = mountWorkspace('students')
    await wrapper.setProps({ studentListOnly: true })
    await flushPromises()
    await wrapper.get('.load-more').trigger('click')
    await flushPromises()
    expect(wrapper.findAll('.student-row')).toHaveLength(2)
    expect(wrapper.find('.load-more').exists()).toBe(false)
    expect(wrapper.find('.section-heading').exists()).toBe(false)
  })

  it('requires a class choice for a student in multiple classes', async () => {
    const page = studentPage(1, '炎症班', 42, '跨班学生')
    page.items[0]!.classIds = [1, 2]
    api.getTeacherInsightsStudents.mockResolvedValue(page)
    const wrapper = mountWorkspace('students', filters())
    await flushPromises()
    await wrapper.get('.student-row').trigger('click')
    expect(wrapper.emitted('openStudent')).toBeUndefined()
    await wrapper.findAll('.class-choice button')[1]!.trigger('click')
    expect(wrapper.emitted('openStudent')).toEqual([[{ studentId: 42, classId: 2 }]])
  })

  it('uses group codes for headings and expands each student own diagnosis across pages', async () => {
    const page = emptyDiagnosisPage(1)
    page.total = 2
    page.knowledgeGaps = [
      {
        code: 'pathology.inflammation',
        studentCount: 2,
        diagnosisCount: 2,
        lastCompletedAt: '2026-09-20T10:00:00+08:00',
      },
    ]
    const item = {
      participationId: 1,
      sessionId: 1,
      classId: 1,
      className: '炎症班',
      studentId: 11,
      studentName: '甲同学',
      completedAt: '2026-09-20T10:00:00+08:00',
      knowledgeGapCodes: ['pathology.inflammation'],
      reasoningIssueCodes: [],
      knowledgeGaps: [{ code: 'pathology.inflammation', summary: '甲需要补充机制依据' }],
      reasoningIssues: [],
    }
    page.items = [item]
    const next = {
      ...page,
      offset: 1,
      items: [
        {
          ...item,
          participationId: 2,
          studentId: 12,
          studentName: '乙同学',
          knowledgeGaps: [{ code: 'pathology.inflammation', summary: '乙需要区分形态变化' }],
        },
      ],
    }
    api.getTeacherInsightsKnowledge.mockResolvedValue(knowledgePage(1, []))
    api.getTeacherInsightsDiagnostics.mockResolvedValueOnce(page).mockResolvedValueOnce(next)
    const wrapper = mountWorkspace('knowledge')
    await flushPromises()
    expect(wrapper.get('.finding__title').text()).toContain('pathology.inflammation')
    expect(wrapper.text()).not.toContain('甲需要补充机制依据')
    await wrapper.get('.finding__summary').trigger('click')
    await flushPromises()
    expect(api.getTeacherInsightsDiagnostics).toHaveBeenNthCalledWith(2, filters(1), 100, 1)
    expect(wrapper.text()).toContain('甲需要补充机制依据')
    expect(wrapper.text()).toContain('乙需要区分形态变化')
    await wrapper.findAll('.finding__student button')[1]!.trigger('click')
    expect(wrapper.emitted('openStudent')).toEqual([[{ studentId: 12, classId: 1 }]])
  })

  it('shows a common finding summary only when the complete diagnosis page agrees', async () => {
    const page = emptyDiagnosisPage(1)
    page.total = 2
    page.knowledgeGaps = [
      {
        code: 'pathology.inflammation',
        studentCount: 2,
        diagnosisCount: 2,
        lastCompletedAt: '2026-09-20T10:00:00+08:00',
      },
    ]
    page.items = [
      {
        participationId: 1,
        sessionId: 1,
        classId: 1,
        className: '炎症班',
        studentId: 11,
        studentName: '甲同学',
        completedAt: '2026-09-20T10:00:00+08:00',
        knowledgeGapCodes: ['pathology.inflammation'],
        reasoningIssueCodes: [],
        knowledgeGaps: [{ code: 'pathology.inflammation', summary: '共同摘要：需要补足组织学依据。' }],
        reasoningIssues: [],
      },
      {
        ...page.items[0]!,
        participationId: 2,
        studentId: 12,
        studentName: '乙同学',
        knowledgeGaps: [{ code: 'pathology.inflammation', summary: '共同摘要：需要补足组织学依据。' }],
      },
    ]
    api.getTeacherInsightsKnowledge.mockResolvedValue(knowledgePage(1, []))
    api.getTeacherInsightsDiagnostics.mockResolvedValue(page)

    const wrapper = mountWorkspace('knowledge')
    await flushPromises()

    expect(wrapper.get('.finding__description').text()).toBe('共同摘要：需要补足组织学依据。')
    expect(api.getTeacherInsightsDiagnostics).toHaveBeenCalledTimes(1)
  })

  it('keeps a partial heterogeneous finding group behind student summaries', async () => {
    const firstPage = emptyDiagnosisPage(1)
    firstPage.total = 3
    firstPage.knowledgeGaps = [
      {
        code: 'pathology.inflammation',
        studentCount: 3,
        diagnosisCount: 3,
        lastCompletedAt: '2026-09-20T10:00:00+08:00',
      },
    ]
    const diagnosis = (participationId: number, studentId: number, studentName: string, summary: string) => ({
      participationId,
      sessionId: 1,
      classId: 1,
      className: '炎症班',
      studentId,
      studentName,
      completedAt: '2026-09-20T10:00:00+08:00',
      knowledgeGapCodes: ['pathology.inflammation'],
      reasoningIssueCodes: [],
      knowledgeGaps: [{ code: 'pathology.inflammation', summary }],
      reasoningIssues: [],
    })
    firstPage.items = [diagnosis(1, 11, '甲同学', '暂时相同的摘要。'), diagnosis(2, 12, '乙同学', '暂时相同的摘要。')]
    const finalPage = { ...firstPage, offset: 2, items: [diagnosis(3, 13, '丙同学', '需要区分细胞和血管变化。')] }
    api.getTeacherInsightsKnowledge.mockResolvedValue(knowledgePage(1, []))
    api.getTeacherInsightsDiagnostics.mockResolvedValueOnce(firstPage).mockResolvedValueOnce(finalPage)

    const wrapper = mountWorkspace('knowledge')
    await flushPromises()

    expect(wrapper.get('.finding__description').text()).toBe('查看学生诊断摘要与具体问题')
    expect(wrapper.text()).not.toContain('暂时相同的摘要。')
    await wrapper.get('.finding__summary').trigger('click')
    await flushPromises()

    expect(api.getTeacherInsightsDiagnostics).toHaveBeenNthCalledWith(2, filters(1), 100, 2)
    expect(wrapper.get('.finding__description').text()).toBe('收起学生诊断摘要')
    expect(wrapper.text()).toContain('甲同学')
    expect(wrapper.text()).toContain('乙同学')
    expect(wrapper.text()).toContain('丙同学')
    expect(wrapper.text()).toContain('需要区分细胞和血管变化。')
  })
})
