<template>
  <view class="safe-page detail-page">
    <MedState
      v-if="accessDenied"
      variant="error"
      icon="history"
      title="需要教师身份"
      description="学生学情仅对教师开放。"
      action-label="返回学生学情"
      @action="back"
    />
    <MedState
      v-else-if="invalid"
      variant="error"
      icon="retry"
      title="学生学情链接无效"
      description="需要有效的班级和学生编号；无法确认范围时不会查询学生记录。"
      action-label="返回学生学情"
      @action="back"
    />
    <MedState
      v-else-if="scopeExpired"
      variant="error"
      icon="history"
      title="教师账号已变更"
      description="已清除原账号读取的学生学情。"
      action-label="返回学生学情"
      @action="backToCurrentAnalytics"
    />
    <MedState
      v-else-if="loading && !detail"
      variant="loading"
      icon="history"
      title="正在读取学生学情"
      description="正在汇总授权课堂中的学习路线与最终测试记录。"
    />
    <MedState
      v-else-if="error && !detail"
      variant="error"
      icon="retry"
      title="学生学情加载失败"
      :description="error"
      action-label="重新加载"
      secondary-action-label="返回学生学情"
      @action="load"
      @secondary-action="back"
    />
    <template v-else-if="detail">
      <TeacherModuleSection
        title="学生学情"
        :description="`${detail.summary.studentName} · ${detail.scope.className || `班级 ${classId}`} · ${detail.scope.dateFrom} 至 ${detail.scope.dateTo}`"
      >
        <view class="period-row">
          <picker
            mode="date"
            :value="dateFrom || detail.scope.dateFrom"
            @change="setDateFrom"
          >
            <view class="date-control">{{ dateFrom || detail.scope.dateFrom }}</view>
          </picker>
          <text class="hint">至</text>
          <picker
            mode="date"
            :value="dateTo || detail.scope.dateTo"
            @change="setDateTo"
          >
            <view class="date-control">{{ dateTo || detail.scope.dateTo }}</view>
          </picker>
        </view>
        <template #actions>
          <button
            class="secondary"
            :loading="loading"
            :disabled="loading"
            @click="load"
          >
            更新范围
          </button>
        </template>
      </TeacherModuleSection>

      <MedState
        v-if="error && detail"
        variant="error"
        icon="retry"
        title="范围更新失败"
        :description="error"
        action-label="重试更新"
        @action="load"
      />

      <TeacherModuleSection
        title="学习与测试概况"
        tone="focus"
      >
        <view class="metric-grid">
          <view class="metric">
            <text class="metric-label">已发布路线</text>
            <text class="metric-value">{{ detail.summary.cohort.publishedRoutes }} 条</text>
          </view>
          <view class="metric">
            <text class="metric-label">已完成测试</text>
            <text class="metric-value">{{ detail.summary.cohort.completedTests }} 份</text>
          </view>
          <view class="metric">
            <text class="metric-label">测试完成率</text>
            <text class="metric-value">{{ percent(detail.summary.cohort.completionRate) }}</text>
          </view>
          <view class="metric">
            <text class="metric-label">评分中</text>
            <text class="metric-value">{{ detail.summary.cohort.gradingTests }} 份</text>
          </view>
        </view>
        <view class="period-summary">
          <text class="hint">范围内已完成测试：{{ detail.summary.periodResults.completedTests }} 份</text>
          <text class="hint">平均分：{{ score(detail.summary.periodResults.averageScore) }}</text>
          <text class="hint"
            >单选旧版 {{ formatCount('single_choice_v1') }} 份 · 混合题型 {{ formatCount('mixed_v2') }} 份</text
          >
          <text class="hint">有效课堂诊断：{{ detail.summary.diagnosisCount }} 份</text>
          <text class="hint">最近完成：{{ dateTime(detail.summary.lastCompletedAt) }}</text>
        </view>
      </TeacherModuleSection>

      <TeacherModuleSection
        title="课堂研讨进度"
        description="按区间内开始参与的记录展示，阶段截至本次查询；与路线发布批次分别统计。"
      >
        <text
          v-if="!detail.discussions?.length"
          class="empty-note"
          >{{ detail.discussions ? '本区间无参与记录。' : '研讨进度未提供。' }}</text
        >
        <view
          v-for="discussion in detail.discussions"
          :key="String(discussion.participationId)"
          class="route-card"
        >
          <text class="route-title">课堂 {{ discussion.sessionId }}</text>
          <text class="hint">开始参与：{{ dateTime(discussion.startedAt) }}</text>
          <text
            v-if="discussion.startedAt === null"
            class="hint"
            >历史记录缺少开始时间，保留只读阶段，不计入日期区间统计。</text
          >
          <text class="hint">阶段：{{ discussionPhaseLabel(discussion.phase) }}</text>
          <text class="hint"
            >状态：{{
              discussion.status === 'completed' ? '已完成' : discussion.status === 'active' ? '进行中' : '状态未识别'
            }}</text
          >
          <text
            v-if="discussion.completedAt"
            class="hint"
            >完成于 {{ dateTime(discussion.completedAt) }}</text
          >
        </view>
      </TeacherModuleSection>

      <TeacherModuleSection title="学习路线与测试进度">
        <text
          v-if="!detail.routes.length"
          class="empty-note"
          >当前授权范围内没有已发布路线。</text
        >
        <view
          v-for="route in detail.routes"
          :key="route.routeId"
          class="route-card"
        >
          <text class="route-title">学习路线 {{ route.routeId.slice(0, 8) }}</text>
          <text class="hint">发布于 {{ dateTime(route.publishedAt) }}</text>
          <view class="route-axis">
            <text class="axis-title">学习进度</text>
            <text class="hint">已完成步骤：{{ stepCount(route.completedSteps, route.totalSteps) }}</text>
            <text class="hint">实际阅读：{{ readingTime(route.readingSeconds) }}</text>
          </view>
          <view class="route-axis">
            <text class="axis-title">最终测试</text>
            <text class="hint">生成：{{ generationLabel(route.testGenerationState) }}</text>
            <text class="hint">审核：{{ reviewLabel(route.testReviewState) }}</text>
            <text class="hint">作答：{{ attemptLabel(route.attemptStatus) }}</text>
            <button
              v-if="reviewNavigationKind(route)"
              class="secondary pbl-review-action"
              @click="openPblReview(route)"
            >
              {{ route.testGenerationState === 'generation_failed' ? '前往 PBL 查看生成异常' : '前往 PBL 审阅' }}
            </button>
          </view>
        </view>
      </TeacherModuleSection>

      <TeacherModuleSection
        title="最终测试结果摘要"
        description="此处只显示统计摘要；完整题目和作答仅在打开单份结果后读取。"
      >
        <text
          v-if="!detail.results.length"
          class="empty-note"
          >当前范围没有已完成测试结果；未完成的测试不按零分计算。</text
        >
        <view
          v-for="result in detail.results"
          :key="result.resultId"
          class="result-row"
          role="button"
          :aria-label="`查看 ${formatLabel(result.formatVersion)}结果，得分 ${result.score}`"
          @click="openResult(result.resultId)"
        >
          <view class="field-copy">
            <text class="route-title">路线 {{ result.routeId.slice(0, 8) }}</text>
            <text class="hint">{{ formatLabel(result.formatVersion) }} · {{ dateTime(result.completedAt) }}</text>
          </view>
          <text class="metric-value">{{ result.score }} 分</text>
          <button
            class="secondary result-action"
            @click.stop="openResult(result.resultId)"
          >
            查看完整结果
          </button>
        </view>
      </TeacherModuleSection>

      <TeacherModuleSection title="知识表现摘要">
        <text
          v-if="!detail.knowledge.length"
          class="empty-note"
          >当前范围没有可汇总的知识目标记录。</text
        >
        <view
          v-for="item in detail.knowledge"
          :key="item.pointCode"
          class="knowledge-row"
        >
          <view class="field-copy">
            <text class="route-title">{{ item.pointCode }}</text>
            <text class="hint">客观题：{{ item.correctCount }} / {{ item.objectiveCount }} 题答对</text>
            <text class="hint"
              >简答题评分：{{ item.shortAnswerCount }} 份 · {{ points(item.pointsAwarded, item.pointsPossible) }}</text
            >
            <text
              v-if="item.invalidObjectiveCount || item.invalidShortAnswerCount"
              class="hint"
              >无效记录：客观题 {{ item.invalidObjectiveCount }} 题，简答题 {{ item.invalidShortAnswerCount }} 份</text
            >
          </view>
          <text class="metric-value">{{ percent(item.accuracyRate) }}</text>
        </view>
      </TeacherModuleSection>

      <TeacherModuleSection title="课堂诊断摘要">
        <text
          v-if="!detail.diagnoses.length"
          class="empty-note"
          >当前范围没有有效的课堂诊断摘要。</text
        >
        <view
          v-for="diagnosis in detail.diagnoses"
          :key="`${diagnosis.participationId}-${diagnosis.completedAt}`"
          class="diagnosis-card"
        >
          <text class="route-title">{{ diagnosis.className }} · {{ dateTime(diagnosis.completedAt) }}</text>
          <view
            v-if="diagnosis.knowledgeGaps.length"
            class="finding-group"
          >
            <text class="axis-title">知识薄弱点</text>
            <text
              v-for="finding in diagnosis.knowledgeGaps"
              :key="finding.code"
              class="hint"
              >{{ finding.summary }}</text
            >
          </view>
          <view
            v-if="diagnosis.reasoningIssues.length"
            class="finding-group"
          >
            <text class="axis-title">推理问题</text>
            <text
              v-for="finding in diagnosis.reasoningIssues"
              :key="finding.code"
              class="hint"
              >{{ finding.summary }}</text
            >
          </view>
          <text
            v-if="!diagnosis.knowledgeGaps.length && !diagnosis.reasoningIssues.length"
            class="hint"
            >该次诊断没有可展示的摘要条目。</text
          >
        </view>
      </TeacherModuleSection>
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onBackPress, onLoad, onShow } from '@dcloudio/uni-app'
import TeacherModuleSection from '@/components/teacher/TeacherModuleSection.vue'
import MedState from '@/components/ui/MedState.vue'
import {
  getTeacherInsightsStudent,
  type TeacherInsightsRouteProgress,
  type TeacherInsightsSessionId,
  type TeacherInsightsStudentDetail,
} from '@/features/analytics/public'
import { getSession, requireRole } from '@/features/identity/public'
import { goDetail, handleBackPress, ROUTES } from '@/platform/navigation'
import {
  backFromTeacherDetail,
  relaunchToTeacherWorkspace,
  type TeacherReviewKind,
  parseTeacherWorkspaceTarget,
  type TeacherInsightsPanel,
  type TeacherDetailFallback,
} from '@/platform/navigation/teacher'

const detail = ref<TeacherInsightsStudentDetail>()
const loading = ref(false)
const error = ref('')
const invalid = ref(true)
const accessDenied = ref(false)
const scopeExpired = ref(false)
const classId = ref<number>()
const studentId = ref<number>()
const sessionId = ref<TeacherInsightsSessionId>()
const panel = ref<TeacherInsightsPanel>('students')
const dateFrom = ref<string>()
const dateTo = ref<string>()
let teacherOpenid = ''
let visible = false
let requestVersion = 0
let contextVersion = 0

function positiveSafeInteger(value: unknown): number | undefined {
  if (typeof value !== 'string' || !/^\d+$/.test(value)) return undefined
  const parsed = Number(value)
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : undefined
}

function makeInsightTarget(
  options: {
    classId?: number
    sessionId?: TeacherInsightsSessionId
    dateFrom?: string
    dateTo?: string
    panel?: TeacherInsightsPanel
  } = {},
): TeacherDetailFallback {
  const parsed = parseTeacherWorkspaceTarget({
    tab: 'insights',
    panel: options.panel || panel.value,
    classId: options.classId ? String(options.classId) : undefined,
    sessionId: options.sessionId === undefined ? undefined : String(options.sessionId),
    dateFrom: options.dateFrom,
    dateTo: options.dateTo,
  })
  if (parsed.workspace !== 'insights') return { workspace: 'insights', panel: 'students' }
  return { ...parsed, panel: parsed.panel || 'students' }
}

function returnTarget(): TeacherDetailFallback {
  const scope = detail.value?.scope
  return makeInsightTarget({
    classId: scope?.classId ?? classId.value,
    sessionId: scope ? (scope.sessionId ?? undefined) : sessionId.value,
    dateFrom: scope?.dateFrom ?? dateFrom.value,
    dateTo: scope?.dateTo ?? dateTo.value,
    panel: panel.value,
  })
}

function navigationParams(target: TeacherDetailFallback) {
  if (target.workspace !== 'insights') return { tab: 'insights', panel: 'students' }
  return {
    tab: 'insights',
    panel: target.panel || 'students',
    ...(target.classId ? { classId: target.classId } : {}),
    ...(target.sessionId !== undefined ? { sessionId: target.sessionId } : {}),
    ...(target.dateFrom ? { dateFrom: target.dateFrom } : {}),
    ...(target.dateTo ? { dateTo: target.dateTo } : {}),
  }
}

function back() {
  backFromTeacherDetail(returnTarget())
}

function backToCurrentAnalytics() {
  backFromTeacherDetail({ workspace: 'insights', panel: 'students' })
}

function verifyTeacherSession(): boolean {
  if (scopeExpired.value) return false
  const session = getSession()
  if (!requireRole('teacher') || session?.role !== 'teacher' || !session.openid) {
    accessDenied.value = true
    visible = false
    requestVersion += 1
    detail.value = undefined
    loading.value = false
    error.value = ''
    return false
  }
  if (teacherOpenid && session.openid !== teacherOpenid) {
    contextVersion += 1
    requestVersion += 1
    visible = false
    scopeExpired.value = true
    detail.value = undefined
    loading.value = false
    error.value = ''
    backToCurrentAnalytics()
    return false
  }
  return visible && session.openid === teacherOpenid
}

async function load() {
  if (invalid.value || !verifyTeacherSession() || !classId.value || !studentId.value) return
  if (dateFrom.value && dateTo.value && dateFrom.value > dateTo.value) {
    error.value = '开始日期不能晚于结束日期。'
    return
  }
  const target = makeInsightTarget({
    classId: classId.value,
    sessionId: sessionId.value,
    dateFrom: dateFrom.value,
    dateTo: dateTo.value,
    panel: panel.value,
  })
  if (target.workspace !== 'insights' || !target.classId) return
  const request = ++requestVersion
  const requestedContext = contextVersion
  loading.value = true
  error.value = ''
  try {
    const value = await getTeacherInsightsStudent(studentId.value, {
      classId: target.classId,
      ...(target.sessionId !== undefined ? { sessionId: target.sessionId } : {}),
      ...(target.dateFrom ? { dateFrom: target.dateFrom } : {}),
      ...(target.dateTo ? { dateTo: target.dateTo } : {}),
    })
    if (request !== requestVersion || requestedContext !== contextVersion || !verifyTeacherSession()) return
    if (value.summary.studentId !== studentId.value || value.scope.classId !== target.classId) {
      throw new Error('返回的学情范围与当前链接不一致。')
    }
    detail.value = value
  } catch (reason) {
    if (request === requestVersion && requestedContext === contextVersion && verifyTeacherSession()) {
      error.value = reason instanceof Error ? reason.message : '请稍后重试。'
    }
  } finally {
    if (request === requestVersion) loading.value = false
  }
}

function pickerValue(event: unknown): string {
  const value = (event as { detail?: { value?: unknown } }).detail?.value
  return typeof value === 'string' ? value : ''
}

function setDateFrom(event: unknown) {
  dateFrom.value = pickerValue(event) || dateFrom.value
}

function setDateTo(event: unknown) {
  dateTo.value = pickerValue(event) || dateTo.value
}

function reviewNavigationKind(route: TeacherInsightsRouteProgress): TeacherReviewKind | undefined {
  if (route.resultId || route.testReviewState === 'released') return undefined
  if (route.testGenerationState === 'generation_failed') return 'generation_failed'
  if (route.testGenerationState !== 'ready') return undefined
  if (route.testReviewState === 'pending_review' || route.testReviewState === 'needs_changes') {
    return route.testReviewState
  }
  return undefined
}

function openPblReview(route: TeacherInsightsRouteProgress) {
  if (!detail.value?.routes.includes(route) || !verifyTeacherSession()) return
  const reviewKind = reviewNavigationKind(route)
  if (!reviewKind) return
  relaunchToTeacherWorkspace({
    workspace: 'pbl',
    section: 'diagnostics',
    classId: route.classId,
    sessionId: route.sessionId,
    reviewKind,
  })
}

function openResult(resultId: string) {
  if (!detail.value || !verifyTeacherSession()) return
  const target = returnTarget()
  if (target.workspace !== 'insights' || !target.classId) return
  goDetail(ROUTES.teacherInsightsResult, {
    resultId,
    studentId: studentId.value,
    ...navigationParams(target),
  })
}

function discussionPhaseLabel(phase: string) {
  const labels: Record<string, string> = {
    problem_framing: '提出问题',
    hypothesis: '形成假设',
    evidence: '证据论证',
    synthesis: '总结反思',
    completed: '研讨完成',
  }
  return labels[phase] || '阶段记录未识别'
}

function percent(value: number | null): string {
  return value === null ? '暂无数据' : `${value}%`
}

function score(value: number | null): string {
  return value === null ? '暂无已完成测试评分' : `${value} 分`
}

function points(awarded: number, possible: number): string {
  return possible > 0 ? `${awarded} / ${possible} 分` : '暂无简答评分'
}

function formatCount(key: 'single_choice_v1' | 'mixed_v2'): string {
  const counts = detail.value?.summary.periodResults.formatCounts
  if (!counts || !Object.prototype.hasOwnProperty.call(counts, key)) return '未统计'
  return String(counts[key])
}

function stepCount(completed: number | null, total: number | null): string {
  return completed === null || total === null ? '暂无记录' : `${completed} / ${total} 步`
}

function readingTime(seconds: number | null): string {
  return seconds === null ? '暂无记录' : `${seconds} 秒`
}

function generationLabel(state: string | null): string {
  if (state === null) return '未生成'
  const labels: Record<string, string> = {
    ready: '已生成',
    generation_failed: '生成失败',
    pending: '待生成',
    generating: '生成中',
  }
  return labels[state] || state
}

function reviewLabel(state: string | null): string {
  if (state === null) return '暂无审核状态'
  const labels: Record<string, string> = {
    pending_review: '待审核',
    needs_changes: '退回修改',
    released: '已发布',
  }
  return labels[state] || state
}

function attemptLabel(state: string | null): string {
  if (state === null) return '未作答'
  const labels: Record<string, string> = {
    in_progress: '作答中',
    grading: '评分中',
    submitted: '已提交',
  }
  return labels[state] || state
}

function formatLabel(version: 'single_choice_v1' | 'mixed_v2'): string {
  return version === 'mixed_v2' ? '混合题型' : '历史单选题'
}

function dateTime(value: string | null): string {
  if (!value) return '暂无记录'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN')
}

onLoad((query) => {
  const values = (query || {}) as Record<string, string | undefined>
  const target = parseTeacherWorkspaceTarget({ ...values, tab: 'insights' })
  if (target.workspace === 'insights') {
    classId.value = target.classId
    sessionId.value = target.sessionId
    panel.value = target.panel || 'students'
    dateFrom.value = target.dateFrom
    dateTo.value = target.dateTo
  }
  studentId.value = positiveSafeInteger(values.studentId)
  invalid.value = target.workspace !== 'insights' || !classId.value || !studentId.value

  const session = getSession()
  if (requireRole('teacher') && session?.role === 'teacher') teacherOpenid = session.openid
})

onShow(() => {
  const session = getSession()
  if (!requireRole('teacher') || session?.role !== 'teacher' || !session.openid) {
    visible = false
    contextVersion += 1
    requestVersion += 1
    detail.value = undefined
    loading.value = false
    error.value = ''
    accessDenied.value = true
    return
  }
  if (teacherOpenid && teacherOpenid !== session.openid) {
    contextVersion += 1
    requestVersion += 1
    visible = false
    detail.value = undefined
    loading.value = false
    error.value = ''
    scopeExpired.value = true
    backToCurrentAnalytics()
    return
  }
  teacherOpenid = session.openid
  visible = true
  accessDenied.value = false
  if (!invalid.value && !detail.value && !loading.value) void load()
})

onBackPress(({ from }) => {
  const target: TeacherDetailFallback = scopeExpired.value
    ? { workspace: 'insights', panel: 'students' }
    : returnTarget()
  return handleBackPress(from, ROUTES.teacherInsights, navigationParams(target))
})
</script>

<style scoped>
.detail-page {
  display: flex;
  min-height: 100vh;
  padding: 28rpx 24rpx 56rpx;
  box-sizing: border-box;
  flex-direction: column;
  gap: 28rpx;
  background: var(--med-page);
}
.detail-page .tms,
.detail-page .med-state {
  width: 100%;
  max-width: 920px;
  margin: 0 auto;
}
.period-row {
  display: flex;
  align-items: center;
  gap: 12rpx;
}
.period-row picker {
  min-width: 0;
  flex: 1;
}
.date-control {
  display: flex;
  min-height: 44px;
  padding: 0 12rpx;
  align-items: center;
  border: 1rpx solid var(--med-border);
  font-size: 24rpx;
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14rpx;
}
.metric {
  display: flex;
  min-height: 100rpx;
  padding: 18rpx;
  flex-direction: column;
  justify-content: space-between;
  background: var(--med-wash);
  border-radius: 12rpx;
}
.metric-label,
.hint {
  color: var(--med-muted);
  font-size: 22rpx;
  line-height: 1.5;
}
.metric-value,
.route-title {
  color: var(--med-ink);
  font-size: 26rpx;
  font-weight: 700;
}
.period-summary,
.route-axis,
.finding-group,
.field-copy {
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}
.period-summary {
  margin-top: 18rpx;
}
.route-card,
.diagnosis-card {
  display: flex;
  margin-top: 16rpx;
  padding: 18rpx;
  flex-direction: column;
  gap: 14rpx;
  background: var(--med-wash);
  border-radius: 12rpx;
}
.route-axis {
  padding-top: 12rpx;
  border-top: 1rpx solid var(--med-divider);
}
.axis-title {
  color: var(--med-clinical);
  font-size: 23rpx;
  font-weight: 700;
}
.result-row,
.knowledge-row {
  display: flex;
  min-width: 0;
  margin-top: 12rpx;
  padding: 16rpx 0;
  align-items: center;
  justify-content: space-between;
  border-top: 1rpx solid var(--med-divider);
  gap: 14rpx;
}
.result-row {
  flex-wrap: wrap;
}
.result-action,
.pbl-review-action {
  font-size: 24rpx;
  min-height: 44px;
  margin: 0;
  color: var(--med-clinical);
  background: var(--med-wash);
  border: 1rpx solid var(--med-border);
}
.knowledge-row .field-copy {
  min-width: 0;
  flex: 1;
}
.empty-note {
  display: block;
  color: var(--med-muted);
  font-size: 23rpx;
  line-height: 1.5;
}
</style>
