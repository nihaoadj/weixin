<template>
  <view class="safe-page insight-page">
    <view class="report-heading">
      <text class="eyebrow-label">LEARNING EVIDENCE</text>
      <text class="page-title">我的病理学习档案</text>
      <text class="heading-note">从讨论证据到两轮改善，按每个知识与推理目标回看。</text>
    </view>

    <MedState
      v-if="loading"
      variant="loading"
      icon="history"
      title="正在整理学情"
      description="正在汇总你的 PBL 阶段、薄弱点和学习证据。"
    />
    <MedState
      v-else-if="error"
      variant="error"
      icon="retry"
      title="学情加载失败"
      :description="error"
      action-label="重新加载"
      @action="load"
    />
    <MedState
      v-else-if="!page.items.length"
      icon="report"
      title="还没有 PBL 学情记录"
      description="进入课堂提出你的疑问，四阶段讨论开始后，这里会逐步形成个人学习档案。"
      action-label="进入 PBL 课堂"
      @action="openClassroom"
    />

    <template v-else>
      <view class="evidence-sheet next-sheet">
        <view
          class="sheet-mark"
          aria-hidden="true"
          ><text /><text /><text /><text
        /></view>
        <text class="section-kicker">当前重点</text>
        <text class="next-title">{{ page.summary.nextAction?.caseTitle }}</text>
        <text class="next-copy">{{ page.summary.nextAction?.label }}</text>
        <button
          class="primary"
          @click="openAction(page.summary.nextAction)"
        >
          {{ actionButton(page.summary.nextAction?.kind) }}
        </button>
      </view>

      <view class="evidence-sheet">
        <view class="section-head">
          <view><text class="section-kicker">累计轨迹</text><text class="section-title">学习闭环分布</text></view>
          <text class="total">{{ page.summary.totalReports }} 次 PBL</text>
        </view>
        <PblStatusDistribution :counts="page.summary.statusCounts" />
      </view>

      <view
        v-if="page.summary.recurringTargets.length"
        class="evidence-sheet"
      >
        <view class="section-head">
          <view><text class="section-kicker">重复信号</text><text class="section-title">反复出现的学习重点</text></view>
        </view>
        <text class="section-note">只统计你本人已完成讨论形成的学习线索，不混合其他学生数据。</text>
        <PblRecurringTargets :items="page.summary.recurringTargets" />
      </view>

      <view class="evidence-sheet recent-sheet">
        <view class="section-head">
          <view><text class="section-kicker">最近记录</text><text class="section-title">逐次查看改善过程</text></view>
        </view>
        <view
          class="report-list"
          role="list"
        >
          <button
            v-for="item in page.items"
            :key="item.session.id"
            class="report-row"
            role="listitem"
            @click="openDetail(item.session.id)"
          >
            <view class="row-top">
              <text class="case-title">{{ item.session.caseTitle }}</text>
              <text
                class="status-label"
                :class="`status-label--${item.status}`"
                >{{ statusLabels[item.status] }}</text
              >
            </view>
            <text class="topic">{{ item.session.topicLabel }} · {{ formatDate(item.updatedAt) }}</text>
            <text class="summary">{{ item.summaryText }}</text>
            <view class="row-metrics">
              <text>知识重点 {{ item.knowledgeGapCount }}</text>
              <text>推理重点 {{ item.reasoningIssueCount }}</text>
              <text>任务 {{ item.taskProgress.completed }}/{{ item.taskProgress.total }}</text>
            </view>
          </button>
        </view>
        <button
          v-if="page.items.length < page.total"
          class="secondary"
          :loading="loadingMore"
          @click="loadMore"
        >
          加载更多
        </button>
      </view>
    </template>
    <StudentPrimaryNav active="insights" />
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import PblRecurringTargets from '@/components/student/PblRecurringTargets.vue'
import PblStatusDistribution from '@/components/student/PblStatusDistribution.vue'
import MedState from '@/components/ui/MedState.vue'
import StudentPrimaryNav from '@/components/ui/StudentPrimaryNav.vue'
import { requireRole } from '@/features/identity/public'
import {
  getPblLearningReports,
  type PblReportAction,
  type PblReportPage,
  type PblReportStatus,
} from '@/features/pbl/public'
import { goDetail, goPrimary, ROUTES } from '@/platform/navigation'

const emptyCounts: PblReportPage['summary']['statusCounts'] = {
  discussing: 0,
  awaiting_learning: 0,
  learning_cycle_1: 0,
  learning_cycle_2: 0,
  improved: 0,
  support_needed: 0,
}
const page = ref<PblReportPage>({
  summary: { totalReports: 0, statusCounts: emptyCounts, recurringTargets: [] },
  items: [],
  total: 0,
  limit: 20,
  offset: 0,
})
const loading = ref(true)
const loadingMore = ref(false)
const error = ref('')
const statusLabels: Record<PblReportStatus, string> = {
  discussing: '讨论中',
  awaiting_learning: '待发布学习',
  learning_cycle_1: '第一轮学习',
  learning_cycle_2: '第二轮巩固',
  improved: '已改善',
  support_needed: '需线下支持',
}
const formatDate = (value: string) => new Date(value).toLocaleDateString('zh-CN')
const actionButton = (kind?: PblReportAction['kind']) =>
  kind === 'discussion' ? '继续讨论' : kind === 'tasks' ? '继续学习' : '查看本次报告'
function openDetail(sessionId: string) {
  goDetail(ROUTES.studentInsightDetail, { sessionId })
}
function openClassroom() {
  goPrimary(ROUTES.studentPbl)
}
function openAction(action?: PblReportPage['summary']['nextAction']) {
  if (!action) return
  if (action.kind === 'discussion') return goPrimary(ROUTES.studentPbl)
  if (action.kind === 'tasks') return goPrimary(ROUTES.studentLearning)
  openDetail(action.sessionId)
}
async function load() {
  loading.value = true
  error.value = ''
  try {
    page.value = await getPblLearningReports()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '请检查网络后重试。'
  } finally {
    loading.value = false
  }
}
async function loadMore() {
  if (loadingMore.value) return
  loadingMore.value = true
  try {
    const next = await getPblLearningReports(20, page.value.items.length)
    page.value = { ...next, items: [...page.value.items, ...next.items] }
  } catch (reason) {
    uni.showToast({ title: reason instanceof Error ? reason.message : '加载失败', icon: 'none' })
  } finally {
    loadingMore.value = false
  }
}
onShow(() => {
  if (requireRole('student')) void load()
})
</script>

<style scoped>
.insight-page {
  min-height: 100vh;
  padding: 30rpx 26rpx 180rpx;
  background: var(--med-page);
}
.report-heading {
  display: flex;
  max-width: 980px;
  margin: 0 auto 24rpx;
  padding: 24rpx 6rpx 12rpx;
  flex-direction: column;
  gap: 8rpx;
}
.page-title {
  color: var(--med-navy);
  font-size: 44rpx;
  font-weight: 850;
  line-height: 1.25;
}
.heading-note,
.section-note,
.topic,
.summary {
  color: var(--med-muted);
  font-size: 24rpx;
  line-height: 1.6;
}
.evidence-sheet {
  display: flex;
  max-width: 920px;
  margin: 0 auto 22rpx;
  padding: 28rpx;
  flex-direction: column;
  gap: 20rpx;
  background: var(--med-surface);
  border: 1rpx solid var(--med-border);
  border-radius: var(--med-radius-md);
}
.next-sheet {
  position: relative;
  overflow: hidden;
  padding-top: 38rpx;
}
.sheet-mark {
  position: absolute;
  top: 0;
  right: 0;
  left: 0;
  display: grid;
  height: 10rpx;
  grid-template-columns: 1.4fr 0.7fr 1fr 0.45fr;
  gap: 4rpx;
}
.sheet-mark text:nth-child(odd) {
  background: var(--med-clinical);
}
.sheet-mark text:nth-child(even) {
  background: var(--med-alert, #9f2f2f);
}
.section-kicker {
  display: block;
  color: var(--med-clinical);
  font-family: var(--med-font-utility);
  font-size: 21rpx;
  font-weight: 750;
  letter-spacing: 2rpx;
}
.next-title {
  color: var(--med-ink);
  font-size: 34rpx;
  font-weight: 800;
}
.next-copy {
  color: var(--med-text-secondary);
  font-size: 27rpx;
}
.section-head,
.row-top,
.row-metrics {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18rpx;
}
.section-head > view {
  display: flex;
  flex-direction: column;
  gap: 7rpx;
}
.section-title {
  color: var(--med-ink);
  font-size: 31rpx;
  font-weight: 780;
}
.total {
  color: var(--med-muted);
  font-family: var(--med-font-utility);
  font-size: 23rpx;
}
.report-list {
  display: flex;
  flex-direction: column;
}
.report-row {
  display: flex;
  width: 100%;
  min-height: 44px;
  margin: 0;
  padding: 24rpx 0;
  flex-direction: column;
  gap: 10rpx;
  color: inherit;
  background: transparent;
  border-bottom: 1rpx solid var(--med-divider);
  border-radius: 0;
  text-align: left;
}
.report-row::after {
  border: 0;
}
.case-title {
  color: var(--med-ink);
  font-size: 28rpx;
  font-weight: 750;
}
.status-label {
  flex: none;
  padding: 6rpx 11rpx;
  color: var(--med-clinical);
  background: var(--med-wash);
  border-radius: 99rpx;
  font-size: 20rpx;
}
.status-label--support_needed,
.status-label--learning_cycle_2 {
  color: var(--med-alert, #9f2f2f);
  background: var(--med-alert-soft, #fbe8e8);
}
.status-label--awaiting_learning {
  color: var(--med-warning, #8a5a00);
  background: var(--med-warning-soft, #fff5df);
}
.summary {
  color: var(--med-text-secondary);
}
.row-metrics {
  justify-content: flex-start;
  flex-wrap: wrap;
  color: var(--med-muted);
  font-size: 21rpx;
}
.primary,
.secondary {
  min-height: 88rpx;
  margin: 0;
  font-size: 27rpx;
}
.primary {
  color: white;
  background: var(--med-clinical);
}
.secondary {
  color: var(--med-clinical);
  background: var(--med-wash);
}
@media (min-width: 768px) {
  .insight-page {
    padding: 32px 32px 128px;
  }
  .report-heading {
    margin-bottom: 20px;
  }
  .page-title {
    font-size: 34px;
  }
  .evidence-sheet {
    padding: 32px;
  }
  .next-sheet {
    display: grid;
    grid-template-columns: 1fr auto;
  }
  .next-sheet .section-kicker,
  .next-title,
  .next-copy {
    grid-column: 1;
  }
  .next-sheet .primary {
    width: 180px;
    grid-column: 2;
    grid-row: 2 / span 2;
    align-self: center;
  }
}
</style>
