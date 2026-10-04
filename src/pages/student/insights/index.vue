<template>
  <view class="safe-page insight-page">
    <text
      class="sr-only"
      role="heading"
      aria-level="1"
      >学情</text
    >

    <MedState
      v-if="loading"
      centered
      variant="loading"
      icon="history"
      title="正在整理学情"
      description="正在汇总你的学习趋势、薄弱点和最近记录。"
    />
    <MedState
      v-else-if="error"
      centered
      variant="error"
      icon="retry"
      title="学情加载失败"
      :description="error"
      action-label="重新加载"
      @action="load"
    />
    <MedState
      v-else-if="!page.items.length"
      centered
      icon="report"
      title="还没有学情记录"
      description="进入研讨提出你的疑问，完成讨论与学习任务后，这里会逐步形成个人学习档案。"
      action-label="进入研讨"
      @action="openClassroom"
    />

    <scroll-view
      v-else
      class="insight-scroll"
      scroll-y
      enhanced
      :show-scrollbar="false"
    >
      <view class="insight-shell">
        <view class="profile-strip">
          <image
            v-if="profile?.avatarUrl"
            class="profile-avatar"
            :src="profile.avatarUrl"
            mode="aspectFill"
          />
          <view
            v-else
            class="profile-avatar profile-avatar--fallback"
            aria-hidden="true"
          >
            <view class="avatar-head" />
            <view class="avatar-hair" />
            <view class="avatar-coat" />
            <view class="avatar-stethoscope" />
          </view>
          <view class="profile-copy">
            <view class="profile-name-row">
              <text class="profile-name">{{ profileName }}</text>
              <view class="student-badge">
                <text
                  class="student-badge__mark"
                  aria-hidden="true"
                  >＋</text
                >
                <text>医学生</text>
              </view>
            </view>
            <text class="profile-tagline">医学之路，贵在坚持 ›</text>
          </view>
          <view
            class="profile-motivation"
            aria-hidden="true"
          >
            <image
              class="profile-motivation__art"
              src="/static/student-insights-motivation-separated.svg"
              mode="scaleToFill"
            />
          </view>
        </view>

        <view class="insight-section weekly-section">
          <view class="section-heading">
            <view class="section-title-wrap">
              <text class="title-accent" />
              <text class="section-title">本周学习状态</text>
            </view>
            <text class="period-label">{{ periodLabel }}</text>
          </view>

          <view class="weekly-overview">
            <view
              class="mastery-ring"
              :style="masteryRingStyle"
              role="img"
              :aria-label="masteryAriaLabel"
            >
              <view class="mastery-ring__inner">
                <view class="mastery-value-row">
                  <text class="mastery-value">{{ dashboard.masteryScore ?? '--' }}</text>
                  <text
                    v-if="dashboard.masteryScore !== null"
                    class="mastery-unit"
                    >分</text
                  >
                </view>
                <text class="mastery-label">测试得分</text>
              </view>
            </view>

            <view class="weekly-summary">
              <view class="weekly-summary__top">
                <text class="compare-label">较上周变化</text>
                <text class="delta-value">{{ masteryDeltaLabel }}</text>
                <text class="trend-arrow">{{ trendArrow }}</text>
                <text class="status-badge">{{ dashboard.statusLabel }}</text>
              </view>
              <view class="ai-summary-title">
                <view
                  class="bot-icon"
                  aria-hidden="true"
                  ><text /><text /><text
                /></view>
                <text>学习总结</text>
              </view>
              <text class="weekly-copy">{{ weeklySummary }}</text>
              <text class="summary-basis">{{ dataBasisLabel }}</text>
            </view>
          </view>

          <view class="metric-grid">
            <view
              v-for="metric in metricCards"
              :key="metric.label"
              class="metric-card"
            >
              <view
                class="metric-icon"
                :class="`metric-icon--${metric.icon}`"
              >
                <StudentNavIcon
                  v-if="metric.icon !== 'check'"
                  :name="metric.icon"
                />
                <view
                  v-else
                  class="check-symbol"
                  aria-hidden="true"
                />
              </view>
              <view class="metric-value-row">
                <text class="metric-value">{{ metric.value }}</text>
                <text class="metric-unit">{{ metric.unit }}</text>
              </view>
              <text class="metric-label">{{ metric.label }}</text>
              <text class="metric-change">{{ metric.change }}</text>
            </view>
          </view>
        </view>

        <view class="insight-section trend-section">
          <view class="section-heading">
            <view class="section-title-wrap">
              <text class="title-accent" />
              <text class="section-title">学习趋势</text>
            </view>
            <text class="section-link">近 4 周测试得分变化 ›</text>
          </view>
          <view
            class="trend-chart"
            role="img"
            :aria-label="trendAriaLabel"
          >
            <view class="trend-y-axis">
              <text>100</text><text>75</text><text>50</text><text>25</text><text>0</text>
            </view>
            <view class="trend-main">
              <view class="trend-grid"> <text /><text /><text /><text /><text /> </view>
              <view class="trend-columns">
                <view
                  v-for="(point, index) in chartPoints"
                  :key="point.periodStart"
                  class="trend-column"
                >
                  <view
                    v-if="point.segmentStyle"
                    class="trend-segment"
                    :style="point.segmentStyle"
                  />
                  <view
                    v-if="point.score !== null"
                    class="trend-dot"
                    :class="{ 'trend-dot--latest': index === chartPoints.length - 1 }"
                    :style="{ bottom: `${point.score}%` }"
                  >
                    <text v-if="index === chartPoints.length - 1">{{ point.score }}分</text>
                  </view>
                  <text class="trend-x-label">{{ point.label }}</text>
                </view>
              </view>
            </view>
          </view>
          <view class="trend-note"><text class="pulse-mini" />{{ trendNote }}</view>
        </view>

        <view class="insight-section focus-points-section">
          <view class="section-heading">
            <view class="section-title-wrap">
              <text class="title-accent" />
              <text class="section-title">当前薄弱点</text>
            </view>
            <text
              class="section-link"
              role="button"
              :aria-expanded="showAllWeaknesses"
              @click="showAllWeaknesses = !showAllWeaknesses"
              >{{ showAllWeaknesses ? '收起' : '查看更多' }} ›</text
            >
          </view>
          <view
            v-if="dashboard.weaknesses.length"
            class="focus-grid"
          >
            <view
              v-for="(item, index) in showAllWeaknesses ? dashboard.weaknesses : dashboard.weaknesses.slice(0, 3)"
              :key="`${item.targetType}:${item.targetCode}`"
              class="focus-card"
            >
              <text class="focus-index">{{ String(index + 1).padStart(2, '0') }}</text>
              <view
                class="focus-icon"
                :class="`focus-icon--${index}`"
                aria-hidden="true"
              >
                <view
                  v-if="index === 0"
                  class="lungs-symbol"
                  ><text /><text
                /></view>
                <view
                  v-else-if="index === 1"
                  class="capsule-symbol"
                  ><text
                /></view>
                <view
                  v-else
                  class="clipboard-symbol"
                  ><text /><text /><text
                /></view>
              </view>
              <text class="focus-name">{{ item.label }}</text>
              <view class="focus-progress-row">
                <view class="focus-track"><text :style="{ width: `${item.masteryPercentage ?? 0}%` }" /></view>
                <text class="focus-percent">{{
                  item.masteryPercentage === null ? '--' : `${item.masteryPercentage}分`
                }}</text>
              </view>
            </view>
          </view>
          <view
            v-else
            class="focus-empty"
          >
            <text>当前还没有可确认的薄弱点</text>
            <text>完成研讨诊断与最终测试后，这里会显示有证据的学习重点。</text>
          </view>
        </view>

        <view class="insight-section diagnosis-section">
          <view class="diagnosis-heading">
            <view
              class="spark-icon"
              aria-hidden="true"
              ><text /><text /><text
            /></view>
            <text class="section-title">AI 诊断总结</text>
            <text class="section-link">研讨诊断与学习记录 ›</text>
          </view>
          <text class="diagnosis-copy">{{ dashboard.aiSummary }}</text>
          <button
            v-if="page.summary.nextAction"
            class="diagnosis-action"
            @click="openAction(page.summary.nextAction)"
          >
            {{ page.summary.nextAction.label }} <text aria-hidden="true">›</text>
          </button>
        </view>

        <view class="insight-section recent-section">
          <view class="section-heading">
            <view class="section-title-wrap">
              <view class="recent-icon"><StudentNavIcon name="chat" /></view>
              <text class="section-title">最近对话记录</text>
            </view>
            <text
              class="section-link"
              @click="loadMore"
              >查看更多 ›</text
            >
          </view>
          <scroll-view
            class="recent-scroll"
            scroll-x
            enhanced
            :show-scrollbar="false"
          >
            <view
              class="report-list"
              role="list"
            >
              <button
                v-for="(item, index) in page.items"
                :key="item.id"
                class="report-row"
                role="listitem"
                :aria-label="`查看${item.session.topicLabel}知识点的${item.session.caseTitle}记录`"
                @click="openAction(item.action)"
              >
                <view class="report-meta-row">
                  <view class="report-chat-icon"><StudentNavIcon name="chat" /></view>
                  <text class="report-date">{{ formatDate(item.updatedAt) }}</text>
                  <text
                    v-if="index === 0"
                    class="latest-badge"
                    >最新</text
                  >
                </view>
                <text class="case-title">{{ item.session.topicLabel }} · {{ item.session.caseTitle }}</text>
                <text class="summary">{{ item.summaryText }}</text>
                <view
                  class="row-arrow"
                  aria-hidden="true"
                />
              </button>
            </view>
          </scroll-view>
          <button
            v-if="hasMore"
            class="secondary"
            :loading="loadingMore"
            @click="loadMore"
          >
            加载更多
          </button>
        </view>
      </view>
    </scroll-view>
    <StudentPrimaryNav active="insights" />
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import MedState from '@/components/ui/MedState.vue'
import StudentNavIcon from '@/components/ui/StudentNavIcon.vue'
import StudentPrimaryNav from '@/components/ui/StudentPrimaryNav.vue'
import { getSession, requireRole } from '@/features/identity/public'
import {
  getStudentLearningInsights,
  type StudentLearningInsightsPage,
  type StudentLearningInsightsAction,
  type StudentLearningInsightsDashboard,
} from '@/features/learning/public'
import { goDetail, goPrimary, ROUTES } from '@/platform/navigation'

const emptyDashboard: StudentLearningInsightsDashboard = {
  dataBasis: 'learning_route_results',
  periodStart: '',
  periodEnd: '',
  masteryScore: null,
  masteryDelta: null,
  masterySampleCount: 0,
  studyMinutes: 0,
  studyDurationBasis: 'recorded_reading',
  planCompletionRate: null,
  testedKnowledgeCount: 0,
  aiDiagnosticCount: 0,
  statusLabel: '待积累',
  trend: [],
  weaknesses: [],
  aiSummary: '',
}
const page = ref<StudentLearningInsightsPage>({
  summary: {
    dashboard: emptyDashboard,
  },
  items: [],
  total: 0,
  limit: 20,
  offset: 0,
})
const profile = ref(getSession())
const loading = ref(true)
const loadingMore = ref(false)
const error = ref('')
const hasMore = ref(false)
const showAllWeaknesses = ref(false)
const nextOffset = ref(0)
let loadVersion = 0
const dashboard = computed(() => page.value.summary.dashboard)
const profileName = computed(() => profile.value?.nickName?.trim() || '医学生')
const parseDateParts = (value: string) => {
  const [year, month, day] = value.split('-').map(Number)
  return { year, month, day }
}
const shortDate = (value: string) => {
  if (!value) return '--'
  const { month, day } = parseDateParts(value)
  return `${month}.${day}`
}
const periodLabel = computed(
  () => `${shortDate(dashboard.value.periodStart)} - ${shortDate(dashboard.value.periodEnd)}`,
)
const masteryDeltaLabel = computed(() => {
  const value = dashboard.value.masteryDelta
  if (value === null) return '暂无对比'
  return `${value >= 0 ? '+' : ''}${value}分`
})
const trendArrow = computed(() => {
  const delta = dashboard.value.masteryDelta
  return delta === null || delta === 0 ? '→' : delta < 0 ? '↘' : '↗'
})
const masteryRingStyle = computed(() => {
  const score = Math.min(100, Math.max(0, dashboard.value.masteryScore ?? 0))
  return {
    background: `conic-gradient(#2dcbb9 0 ${score * 0.68}%, #087ccf ${score * 0.68}% ${score}%, #e6eef7 ${score}% 100%)`,
  }
})
const masteryAriaLabel = computed(() =>
  dashboard.value.masteryScore === null
    ? '本周暂无最终测试得分'
    : `本周最终测试平均 ${dashboard.value.masteryScore} 分，${dashboard.value.statusLabel}`,
)
const formatStudyHours = (minutes: number) => {
  const hours = minutes / 60
  return Number.isInteger(hours) ? String(hours) : hours.toFixed(1)
}
const metricCards = computed(() => [
  {
    icon: 'history' as const,
    value: formatStudyHours(dashboard.value.studyMinutes),
    unit: '小时',
    label: '累计阅读时长',
    change: '阅读心跳累计',
  },
  {
    icon: 'check' as const,
    value: dashboard.value.planCompletionRate ?? '--',
    unit: dashboard.value.planCompletionRate === null ? '' : '%',
    label: '计划完成率',
    change: dashboard.value.planCompletionRate === null ? '暂无学习计划' : '最终测试已完成',
  },
  {
    icon: 'book' as const,
    value: dashboard.value.testedKnowledgeCount,
    unit: '个',
    label: '已测知识点',
    change: '最终测试结果',
  },
  {
    icon: 'chat' as const,
    value: dashboard.value.aiDiagnosticCount,
    unit: '次',
    label: 'AI 诊断次数',
    change: '研讨完成诊断',
  },
])
const weeklySummary = computed(() => {
  const score = dashboard.value.masteryScore
  if (score === null) return '本周尚无已完成的最终测试。完成评分后，这里会显示测试得分与变化趋势。'
  return `本周最终测试平均 ${score} 分，共 ${dashboard.value.masterySampleCount} 份结果。全部学习计划完成率${dashboard.value.planCompletionRate === null ? '暂无数据' : `为 ${dashboard.value.planCompletionRate}%`}。`
})
const dataBasisLabel = computed(() =>
  dashboard.value.dataBasis === 'synthetic_demo' ? 'Demo 学习记录 · 时长为累计阅读' : '最终测试结果 · 时长为累计阅读',
)
const trendNote = computed(() => {
  const delta = dashboard.value.masteryDelta
  if (delta === null) return '积累测试结果 · 持续学习'
  return delta < 0 ? '结合错题解析 · 巩固学习重点' : '回顾学习证据 · 持续进步'
})
const chartPoints = computed(() => {
  const values = dashboard.value.trend
  return values.map((item, index) => {
    const next = values[index + 1]
    let segmentStyle: Record<string, string> | undefined
    if (item.score !== null && next && next.score !== null) {
      const ratio = ((next.score - item.score) * 0.0129).valueOf()
      const angle = Math.atan2(-ratio, 1) * (180 / Math.PI)
      const width = Math.sqrt(1 + ratio * ratio) * 100
      segmentStyle = { bottom: `${item.score}%`, width: `${width}%`, transform: `rotate(${angle}deg)` }
    }
    return { ...item, label: shortDate(item.periodEnd), segmentStyle }
  })
})
const trendAriaLabel = computed(() =>
  dashboard.value.trend
    .map((item) => `${shortDate(item.periodEnd)} ${item.score === null ? '暂无数据' : `${item.score} 分`}`)
    .join('，'),
)
const formatDate = (value: string) => {
  const date = new Date(value)
  return `${date.getMonth() + 1}月${date.getDate()}日 · ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}
function openClassroom() {
  goPrimary(ROUTES.studentPbl)
}
function openAction(action?: StudentLearningInsightsAction) {
  if (!action) return
  if (action.kind === 'discussion') return goDetail(ROUTES.studentPbl, { dialogueId: action.sessionId })
  if (!action.routeId) return
  goDetail(action.kind === 'result' ? ROUTES.studentLearningResult : ROUTES.studentLearningPlanDetail, {
    routeId: action.routeId,
  })
}

async function readNextPage(version: number) {
  const identity = profile.value?.openid
  const next = await getStudentLearningInsights(20, nextOffset.value)
  if (version !== loadVersion) return
  if (getSession()?.openid !== identity || !requireRole('student')) return
  if (nextOffset.value === 0) page.value.summary = next.summary
  nextOffset.value += next.items.length
  hasMore.value = nextOffset.value < next.total && next.items.length > 0
  const existing = new Set(page.value.items.map((item) => item.id))
  page.value.items.push(...next.items.filter((item) => !existing.has(item.id)))
  page.value.total = next.total
}

async function load() {
  const version = ++loadVersion
  loading.value = true
  error.value = ''
  page.value.items = []
  page.value.summary = { dashboard: { ...emptyDashboard } }
  nextOffset.value = 0
  hasMore.value = false
  showAllWeaknesses.value = false
  loadingMore.value = false
  try {
    await readNextPage(version)
  } catch (reason) {
    if (version === loadVersion) error.value = reason instanceof Error ? reason.message : '请检查网络后重试。'
  } finally {
    if (version === loadVersion) loading.value = false
  }
}
async function loadMore() {
  if (loadingMore.value || !hasMore.value) return
  const version = loadVersion
  loadingMore.value = true
  try {
    await readNextPage(version)
  } catch (reason) {
    uni.showToast({ title: reason instanceof Error ? reason.message : '加载失败', icon: 'none' })
  } finally {
    if (version === loadVersion) loadingMore.value = false
  }
}
onShow(() => {
  profile.value = getSession()
  if (requireRole('student')) void load()
  else {
    loadVersion += 1
    page.value.items = []
    page.value.summary = { dashboard: { ...emptyDashboard } }
    hasMore.value = false
    loading.value = false
    error.value = '学生身份已变化，请重新登录。'
  }
})
</script>

<style scoped>
.insight-page {
  --med-ink: #071a5a;
  --med-text: #365b95;
  --med-text-secondary: #4f6fa3;
  --med-muted: #6f83ad;
  --med-clinical: #087ccf;
  --med-brand-deep: #066eae;
  --med-wash: #eef8fd;
  --med-page: #f7fbfe;
  --med-border: #d6eaf7;
  --med-divider: #e8f2f9;
  height: calc(100vh - var(--window-top, 0px));
  min-height: 0;
  overflow: hidden;
  background: linear-gradient(180deg, #f1f9fe 0, #ffffff 250rpx, #f8fcff 100%);
}
.insight-scroll {
  height: 100%;
}
.insight-shell {
  width: 100%;
  max-width: 920px;
  margin: 0 auto;
  padding: 0 22rpx 184rpx;
  box-sizing: border-box;
}
.profile-strip {
  position: relative;
  display: flex;
  min-height: 126rpx;
  padding: 14rpx 10rpx 18rpx;
  box-sizing: border-box;
  align-items: center;
  gap: 16rpx;
  background: linear-gradient(90deg, rgba(241, 250, 255, 0.7), rgba(255, 255, 255, 0.3));
  border-bottom: 1rpx solid var(--med-border);
}
.profile-avatar {
  width: 94rpx;
  height: 94rpx;
  flex: 0 0 94rpx;
  overflow: hidden;
  background: linear-gradient(145deg, #f2fbff, #dff4fd);
  border-radius: 50%;
}
.profile-avatar--fallback {
  position: relative;
}
.avatar-head {
  position: absolute;
  top: 19rpx;
  left: 32rpx;
  width: 28rpx;
  height: 31rpx;
  background: #ffd6bf;
  border-radius: 45% 45% 50% 50%;
}
.avatar-head::before,
.avatar-head::after {
  position: absolute;
  top: 14rpx;
  width: 3rpx;
  height: 3rpx;
  background: #233b62;
  border-radius: 50%;
  content: '';
}
.avatar-head::before {
  left: 7rpx;
}
.avatar-head::after {
  right: 7rpx;
}
.avatar-hair {
  position: absolute;
  top: 13rpx;
  left: 29rpx;
  width: 35rpx;
  height: 19rpx;
  background: #263452;
  border-radius: 50% 55% 35% 20%;
  transform: rotate(-5deg);
}
.avatar-coat {
  position: absolute;
  bottom: 4rpx;
  left: 19rpx;
  width: 54rpx;
  height: 40rpx;
  background: #fff;
  border: 3rpx solid #2c8fe6;
  border-radius: 28rpx 28rpx 10rpx 10rpx;
}
.avatar-coat::after {
  position: absolute;
  top: 4rpx;
  left: 24rpx;
  width: 3rpx;
  height: 28rpx;
  background: #c9e8f8;
  content: '';
}
.avatar-stethoscope {
  position: absolute;
  bottom: 15rpx;
  left: 38rpx;
  width: 19rpx;
  height: 20rpx;
  border-right: 3rpx solid #153f79;
  border-bottom: 3rpx solid #153f79;
  border-left: 3rpx solid #153f79;
  border-radius: 0 0 50% 50%;
}
.profile-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 7rpx;
}
.profile-name-row {
  display: flex;
  align-items: center;
  gap: 14rpx;
}
.profile-name {
  overflow: hidden;
  color: var(--med-ink);
  font-size: 31rpx;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.student-badge {
  display: flex;
  min-height: 34rpx;
  padding: 3rpx 10rpx 3rpx 7rpx;
  box-sizing: border-box;
  align-items: center;
  gap: 5rpx;
  color: #087ccf;
  background: #e9f5fd;
  border-radius: 99rpx;
  font-size: 18rpx;
  font-weight: 650;
}
.student-badge__mark {
  display: flex;
  width: 23rpx;
  height: 23rpx;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: #198fe0;
  border-radius: 6rpx;
  font-size: 17rpx;
  font-weight: 800;
  line-height: 1;
}
.profile-tagline {
  color: #5b76aa;
  font-size: 21rpx;
}
.profile-motivation {
  position: relative;
  display: flex;
  width: 248rpx;
  height: 94rpx;
  flex: 0 0 248rpx;
  align-items: center;
  justify-content: flex-end;
}
.profile-motivation__art {
  display: block;
  width: 100%;
  height: 100%;
}
.insight-section {
  padding: 28rpx 0 30rpx;
  border-bottom: 1rpx solid var(--med-border);
}
.section-heading,
.section-title-wrap,
.weekly-summary__top,
.ai-summary-title,
.diagnosis-heading,
.row-top,
.report-meta-row,
.report-footer,
.metric-value-row,
.focus-progress-row {
  display: flex;
  align-items: center;
}
.section-heading {
  justify-content: space-between;
  gap: 18rpx;
}
.section-title-wrap {
  min-width: 0;
  gap: 12rpx;
}
.title-accent {
  width: 7rpx;
  height: 34rpx;
  flex: 0 0 7rpx;
  background: linear-gradient(180deg, #0a86ee, #24c8d7);
  border-radius: 99rpx;
}
.section-title {
  color: var(--med-ink);
  font-size: 30rpx;
  font-weight: 800;
  line-height: 1.35;
}
.period-label,
.section-link {
  flex: none;
  color: #6e84af;
  font-size: 21rpx;
}
.weekly-overview {
  display: flex;
  margin-top: 20rpx;
  align-items: center;
  gap: 26rpx;
}
.mastery-ring {
  display: flex;
  width: 176rpx;
  height: 176rpx;
  flex: 0 0 176rpx;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transform: rotate(-30deg);
}
.mastery-ring__inner {
  display: flex;
  width: 136rpx;
  height: 136rpx;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 3rpx;
  background: #fff;
  border-radius: 50%;
  box-shadow: inset 0 0 24rpx rgba(8, 124, 207, 0.04);
  transform: rotate(30deg);
}
.mastery-value-row {
  display: flex;
  align-items: baseline;
}
.mastery-value {
  color: var(--med-ink);
  font-family: var(--med-font-utility);
  font-size: 48rpx;
  font-weight: 850;
  line-height: 1;
}
.mastery-unit {
  margin-left: 3rpx;
  color: var(--med-ink);
  font-size: 21rpx;
  font-weight: 750;
}
.mastery-label {
  color: #7187b2;
  font-size: 20rpx;
}
.weekly-summary {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 9rpx;
}
.weekly-summary__top {
  min-width: 0;
  flex-wrap: wrap;
  gap: 7rpx;
}
.compare-label {
  color: var(--med-ink);
  font-size: 22rpx;
  font-weight: 700;
}
.delta-value,
.trend-arrow {
  color: #19bfc4;
  font-size: 34rpx;
  font-weight: 850;
}
.status-badge {
  margin-left: auto;
  padding: 7rpx 18rpx;
  color: #13b5bb;
  background: #e9fbfa;
  border-radius: 99rpx;
  font-size: 20rpx;
  font-weight: 700;
}
.ai-summary-title {
  gap: 10rpx;
  color: var(--med-ink);
  font-size: 25rpx;
  font-weight: 760;
}
.bot-icon {
  position: relative;
  display: flex;
  width: 34rpx;
  height: 28rpx;
  align-items: center;
  justify-content: center;
  gap: 4rpx;
  background: #1a84ec;
  border-radius: 9rpx;
}
.bot-icon::before {
  position: absolute;
  top: -7rpx;
  width: 3rpx;
  height: 8rpx;
  background: #1a84ec;
  content: '';
}
.bot-icon text {
  width: 4rpx;
  height: 4rpx;
  background: #fff;
  border-radius: 50%;
}
.weekly-copy,
.diagnosis-copy,
.summary,
.topic {
  color: #536fa6;
  font-size: 23rpx;
  line-height: 1.65;
}
.summary-basis {
  color: #8193b6;
  font-size: 19rpx;
}
.metric-grid {
  display: grid;
  margin-top: 22rpx;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12rpx;
}
.metric-card {
  display: flex;
  min-width: 0;
  padding: 16rpx 12rpx 14rpx;
  flex-direction: column;
  gap: 5rpx;
  background: linear-gradient(180deg, #f8fcff, #eef8fd);
  border: 1rpx solid #e0eef7;
  border-radius: 20rpx;
  box-shadow: 0 8rpx 20rpx rgba(8, 124, 207, 0.035);
}
.metric-icon {
  display: flex;
  width: 52rpx;
  height: 52rpx;
  align-items: center;
  justify-content: center;
  color: #1688ef;
  background: #dff3ff;
  border-radius: 50%;
}
.metric-icon--check {
  color: #0ec2be;
  background: #ddf9f7;
}
.metric-icon--book {
  color: #087cf0;
}
.metric-icon--chat {
  color: #1b92d5;
}
.metric-icon .student-nav-icon {
  width: 32rpx;
  height: 32rpx;
  font-size: 32rpx;
}
.check-symbol {
  width: 27rpx;
  height: 15rpx;
  border-bottom: 5rpx solid currentColor;
  border-left: 5rpx solid currentColor;
  transform: rotate(-45deg) translateY(-2rpx);
}
.metric-value-row {
  align-items: baseline;
  gap: 4rpx;
}
.metric-value {
  overflow: hidden;
  color: var(--med-ink);
  font-family: var(--med-font-utility);
  font-size: 31rpx;
  font-weight: 850;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.metric-unit {
  color: var(--med-ink);
  font-size: 18rpx;
  font-weight: 700;
}
.metric-label {
  color: #6f84af;
  font-size: 19rpx;
  line-height: 1.35;
}
.metric-change {
  overflow: hidden;
  color: #18bfc3;
  font-size: 18rpx;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.trend-chart {
  display: flex;
  height: 250rpx;
  margin-top: 20rpx;
  gap: 12rpx;
}
.trend-y-axis {
  display: flex;
  width: 42rpx;
  padding-bottom: 30rpx;
  flex: 0 0 42rpx;
  justify-content: space-between;
  flex-direction: column;
  color: #8395bb;
  font-size: 18rpx;
  text-align: right;
}
.trend-main {
  position: relative;
  min-width: 0;
  flex: 1;
}
.trend-grid {
  position: absolute;
  inset: 0 0 30rpx;
  display: flex;
  justify-content: space-between;
  flex-direction: column;
}
.trend-grid text {
  width: 100%;
  height: 1rpx;
  background: #dcebf5;
}
.trend-columns {
  position: absolute;
  inset: 0 0 30rpx;
  display: flex;
}
.trend-column {
  position: relative;
  height: 100%;
  min-width: 0;
  flex: 1;
}
.trend-segment {
  position: absolute;
  z-index: 1;
  left: 50%;
  height: 4rpx;
  background: #087cf0;
  border-radius: 99rpx;
  transform-origin: left center;
}
.trend-dot {
  position: absolute;
  z-index: 2;
  left: 50%;
  width: 14rpx;
  height: 14rpx;
  margin-bottom: -7rpx;
  margin-left: -7rpx;
  background: #fff;
  border: 4rpx solid #087cf0;
  border-radius: 50%;
}
.trend-dot text {
  position: absolute;
  top: -48rpx;
  left: 50%;
  padding: 6rpx 12rpx;
  color: #fff;
  background: #087cf0;
  border-radius: 12rpx;
  font-size: 18rpx;
  font-weight: 700;
  white-space: nowrap;
  transform: translateX(-50%);
}
.trend-dot text::after {
  position: absolute;
  bottom: -7rpx;
  left: 50%;
  width: 0;
  height: 0;
  border-top: 8rpx solid #087cf0;
  border-right: 6rpx solid transparent;
  border-left: 6rpx solid transparent;
  content: '';
  transform: translateX(-50%);
}
.trend-x-label {
  position: absolute;
  bottom: -30rpx;
  left: 50%;
  color: #8092b8;
  font-size: 18rpx;
  white-space: nowrap;
  transform: translateX(-50%);
}
.trend-note {
  display: flex;
  justify-content: flex-end;
  gap: 10rpx;
  color: #4d8df0;
  font-size: 20rpx;
  font-style: italic;
}
.pulse-mini {
  width: 52rpx;
  height: 14rpx;
  border-bottom: 3rpx solid #5ed7ea;
  transform: skewY(-18deg);
}
.focus-grid {
  display: grid;
  margin-top: 18rpx;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12rpx;
}
.focus-card {
  display: grid;
  min-width: 0;
  padding: 14rpx;
  grid-template-columns: 54rpx minmax(0, 1fr);
  gap: 8rpx 10rpx;
  background: linear-gradient(150deg, #ffffff, #f2f9fe);
  border: 1rpx solid #deebf6;
  border-radius: 22rpx;
}
.focus-index {
  grid-column: 1 / -1;
  color: #5e79ac;
  font-family: var(--med-font-utility);
  font-size: 18rpx;
}
.focus-icon {
  position: relative;
  display: flex;
  width: 52rpx;
  height: 52rpx;
  align-items: center;
  justify-content: center;
  background: #ffedf0;
  border-radius: 50%;
}
.focus-icon--1 {
  background: #eaf5ff;
}
.focus-icon--2 {
  background: #e4fbf8;
}
.lungs-symbol {
  position: relative;
  display: flex;
  width: 34rpx;
  height: 36rpx;
  justify-content: center;
  gap: 3rpx;
}
.lungs-symbol::before {
  position: absolute;
  top: 1rpx;
  left: 50%;
  width: 3rpx;
  height: 18rpx;
  background: #f05261;
  content: '';
}
.lungs-symbol text {
  width: 14rpx;
  height: 31rpx;
  margin-top: 5rpx;
  background: #f05261;
  border-radius: 12rpx 5rpx 12rpx 12rpx;
}
.lungs-symbol text:last-child {
  border-radius: 5rpx 12rpx 12rpx;
}
.capsule-symbol {
  width: 16rpx;
  height: 38rpx;
  overflow: hidden;
  border: 4rpx solid #1d87ec;
  border-radius: 99rpx;
  transform: rotate(45deg);
}
.capsule-symbol text {
  display: block;
  width: 100%;
  height: 50%;
  background: #9dd9ff;
  border-bottom: 3rpx solid #1d87ec;
}
.clipboard-symbol {
  position: relative;
  width: 27rpx;
  height: 34rpx;
  border: 4rpx solid #18bdb7;
  border-radius: 5rpx;
}
.clipboard-symbol::before {
  position: absolute;
  top: -8rpx;
  left: 6rpx;
  width: 15rpx;
  height: 8rpx;
  background: #18bdb7;
  border-radius: 5rpx;
  content: '';
}
.clipboard-symbol text {
  display: block;
  width: 16rpx;
  height: 2rpx;
  margin: 6rpx auto 0;
  background: #18bdb7;
}
.focus-name {
  align-self: center;
  overflow: hidden;
  color: var(--med-ink);
  font-size: 22rpx;
  font-weight: 750;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.focus-progress-row {
  grid-column: 1 / -1;
  gap: 7rpx;
}
.focus-track {
  height: 8rpx;
  overflow: hidden;
  flex: 1;
  background: #e8edf6;
  border-radius: 99rpx;
}
.focus-track text {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #168af0, #2fc9cf);
  border-radius: 99rpx;
}
.focus-percent {
  color: #7488b2;
  font-size: 17rpx;
}
.focus-empty {
  display: flex;
  margin-top: 18rpx;
  padding: 24rpx;
  flex-direction: column;
  gap: 8rpx;
  color: #6f83ad;
  background: #f3f9fd;
  border-radius: 18rpx;
  font-size: 22rpx;
  line-height: 1.55;
}
.diagnosis-heading {
  gap: 12rpx;
}
.diagnosis-heading .section-link {
  margin-left: auto;
}
.spark-icon {
  position: relative;
  width: 34rpx;
  height: 34rpx;
  color: #16bde0;
}
.spark-icon text {
  position: absolute;
  top: 15rpx;
  left: 2rpx;
  width: 30rpx;
  height: 4rpx;
  background: currentColor;
  border-radius: 99rpx;
}
.spark-icon text:nth-child(2) {
  transform: rotate(60deg);
}
.spark-icon text:nth-child(3) {
  transform: rotate(120deg);
}
.diagnosis-copy {
  display: block;
  margin-top: 14rpx;
  font-size: 24rpx;
}
.diagnosis-action {
  width: auto;
  min-height: 62rpx;
  margin: 5rpx 0 0 auto;
  padding: 0 4rpx 0 16rpx;
  color: #087cf0;
  background: transparent;
  font-size: 20rpx;
  font-weight: 650;
}
.recent-icon,
.report-chat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #087cf0;
}
.recent-icon {
  width: 36rpx;
  height: 36rpx;
}
.report-chat-icon {
  width: 44rpx;
  height: 44rpx;
  flex: 0 0 44rpx;
  color: #fff;
  background: #168af0;
  border-radius: 12rpx;
}
.report-chat-icon .student-nav-icon {
  width: 27rpx;
  height: 27rpx;
  font-size: 27rpx;
}
.recent-scroll {
  width: calc(100% + 22rpx);
  margin-top: 16rpx;
}
.report-list {
  display: flex;
  padding-right: 22rpx;
  gap: 16rpx;
}
.report-row {
  position: relative;
  display: flex;
  width: 510rpx;
  min-height: 210rpx;
  margin: 0;
  padding: 18rpx 20rpx;
  flex: 0 0 510rpx;
  flex-direction: column;
  gap: 8rpx;
  color: inherit;
  background: #fff;
  border: 1rpx solid #dcebf6;
  border-radius: 20rpx;
  box-shadow: 0 10rpx 28rpx rgba(8, 124, 207, 0.06);
  text-align: left;
}
.report-meta-row {
  gap: 12rpx;
}
.report-date {
  color: #7b8eb5;
  font-size: 20rpx;
}
.latest-badge {
  margin-left: auto;
  padding: 6rpx 16rpx;
  color: #fff;
  background: #087cf0;
  border-radius: 5rpx;
  font-size: 18rpx;
}
.case-title {
  display: block;
  margin-left: 56rpx;
  padding-right: 68rpx;
  overflow: hidden;
  color: var(--med-ink);
  font-size: 25rpx;
  font-weight: 780;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.summary {
  display: -webkit-box;
  margin-left: 56rpx;
  padding-right: 68rpx;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.row-arrow {
  position: absolute;
  top: 50%;
  right: 20rpx;
  display: flex;
  width: 54rpx;
  height: 54rpx;
  align-items: center;
  justify-content: center;
  color: #087cf0;
  background: #fff;
  border: 1rpx solid #d8e9f8;
  border-radius: 50%;
  box-shadow: 0 5rpx 16rpx rgba(8, 124, 240, 0.1);
  transform: translateY(-50%);
}
.row-arrow::before {
  width: 13rpx;
  height: 13rpx;
  border-top: 4rpx solid currentColor;
  border-right: 4rpx solid currentColor;
  content: '';
  transform: rotate(45deg) translate(-2rpx, 2rpx);
}
.secondary {
  min-height: 80rpx;
  margin: 18rpx 0 0;
  color: #087ccf;
  background: #eef8fd;
  border: 1rpx solid #d6eaf7;
  border-radius: 18rpx;
  font-size: 24rpx;
}
.insight-page :deep(.student-primary-nav) {
  background: rgba(255, 255, 255, 0.98);
  border-top-color: var(--med-border);
  box-shadow: 0 -8rpx 24rpx rgba(8, 73, 138, 0.05);
}
.insight-page :deep(.student-nav__item) {
  color: #7187b2;
}
.insight-page :deep(.student-nav__item.active) {
  color: #078bc8;
}
@media screen and (max-width: 360px) {
  .profile-motivation {
    width: 192rpx;
    height: 74rpx;
    flex-basis: 192rpx;
  }
  .metric-card {
    padding-right: 8rpx;
    padding-left: 8rpx;
  }
  .metric-value {
    font-size: 28rpx;
  }
  .metric-label,
  .metric-change {
    font-size: 17rpx;
  }
}
@media screen and (min-width: 600px) {
  .insight-shell {
    padding: 0 32px 128px;
  }
  .profile-strip {
    padding: 10px 6px 12px;
  }
  .insight-section {
    padding: 24px 4px 26px;
  }
  .profile-avatar {
    width: 64px;
    height: 64px;
    flex-basis: 64px;
  }
  .metric-grid,
  .focus-grid {
    gap: 12px;
  }
  .report-row {
    width: 420px;
    min-height: 188px;
    flex-basis: 420px;
  }
}
</style>
