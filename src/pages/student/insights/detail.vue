<template>
  <view class="safe-page detail-page">
    <MedState
      v-if="loading"
      variant="loading"
      icon="history"
      title="正在读取学习证据"
      description="正在整理本次讨论与两轮目标。"
    />
    <MedState
      v-else-if="error"
      variant="error"
      icon="retry"
      title="报告加载失败"
      :description="error"
      :action-label="invalidRoute ? '返回学情' : '重新加载'"
      secondary-action-label="返回学情"
      @action="invalidRoute ? back() : load()"
      @secondary-action="back"
    />
    <template v-else-if="report">
      <view class="report-cover">
        <view
          class="specimen-mark"
          aria-hidden="true"
          ><text /><text /><text /><text
        /></view>
        <text class="eyebrow-label">PBL EVIDENCE FILE</text>
        <text class="page-title">{{ report.session.caseTitle }}</text>
        <view class="cover-meta">
          <text>{{ report.session.topicLabel }}</text
          ><text>{{ formatDate(report.session.createdAt) }}</text>
          <text
            class="status"
            :class="`status--${report.status}`"
            >{{ statusLabels[report.status] }}</text
          >
        </view>
        <text class="cover-summary">{{ report.summaryText }}</text>
        <button
          v-if="report.nextAction.kind !== 'none'"
          class="primary"
          @click="openAction"
        >
          {{ report.nextAction.label }}
        </button>
      </view>

      <view class="report-section">
        <SectionHeading
          kicker="DISCUSSION"
          title="四阶段讨论证据"
          note="每个阶段只使用该阶段开始后的学生消息作为推进依据。"
        />
        <PblPhaseTrack
          v-if="report.phaseProgress.length"
          :phases="report.phaseProgress"
        />
        <text
          v-else
          class="empty-note"
          >你没有参与本次个人讨论；下方任务属于课堂共同训练。</text
        >
      </view>

      <view class="report-section">
        <SectionHeading
          kicker="FINDINGS"
          title="本次个人学习线索"
          note="这些是学习过程中的知识和推理薄弱点，不是临床诊断。"
        />
        <view
          v-if="hasDiagnosis"
          class="finding-groups"
        >
          <view
            v-for="item in report.diagnosis.knowledgeGaps"
            :key="item.id"
            class="finding"
          >
            <text class="finding-type">知识重点</text><text class="finding-title">{{ item.label }}</text>
            <text class="finding-summary">{{ item.summary }}</text>
            <text class="evidence-copy">讨论依据：{{ item.evidenceSummary }}</text>
          </view>
          <view
            v-for="item in report.diagnosis.reasoningIssues"
            :key="item.id"
            class="finding"
          >
            <text class="finding-type">推理重点</text><text class="finding-title">{{ item.label }}</text>
            <text class="finding-summary">{{ item.summary }}</text>
            <text class="evidence-copy">改进方向：{{ item.improvement }}</text>
          </view>
        </view>
        <text
          v-else
          class="empty-note"
          >尚未形成个人薄弱点；完成四阶段讨论后会在这里显示。</text
        >
      </view>

      <view class="report-section">
        <SectionHeading
          kicker="MASTERY"
          title="目标改善对照"
          note="知识再测要求 100 分，推理微训练和病例目标维度要求至少 70 分。"
        />
        <PblTargetComparison
          v-if="report.targetProgress.length"
          :targets="report.targetProgress"
        />
        <text
          v-else
          class="empty-note"
          >完成一轮全部已激活任务后，系统才会形成逐项目标对照。</text
        >
      </view>

      <view
        v-for="plan in report.plans"
        :key="plan.id"
        class="report-section"
      >
        <SectionHeading
          :kicker="`PLAN ${plan.id}`"
          :title="plan.assignmentBasis === 'personal' ? '针对个人线索的学习任务' : '课堂共同训练任务'"
          :note="`第 ${plan.currentCycle}/${plan.maxCycles} 轮 · ${plan.decisionPolicyVersion}`"
        />
        <view
          class="task-list"
          role="list"
        >
          <view
            v-for="task in plan.tasks"
            :key="task.id"
            class="task-row"
            :class="task.status"
            role="listitem"
          >
            <view class="task-head">
              <text>第 {{ task.cycleNumber }} 轮 · {{ taskLabel(task.taskType) }}</text>
              <text>{{ taskStatus(task.status) }}</text>
            </view>
            <text class="task-prompt">{{ task.prompt }}</text>
            <text class="task-target">学习目标：{{ task.targetLabel }}</text>
            <text class="evidence-copy"
              >资料来源：{{ task.reference || '教师采用的 PBL 训练，未提供单独资料来源。' }}</text
            >
            <text
              v-if="task.score != null"
              class="task-result"
              >成绩 {{ task.score }} · {{ task.evidencePresent ? '已有证据' : '证据缺失' }}</text
            >
            <text
              v-if="task.feedback"
              class="evidence-copy"
              >{{ task.feedback }}</text
            >
          </view>
        </view>
      </view>

      <view class="report-section">
        <SectionHeading
          kicker="TIMELINE"
          title="本次闭环时间线"
          note="系统事件按发生顺序保存，历史评价不会被下一轮覆盖。"
        />
        <view
          class="timeline"
          role="list"
        >
          <view
            v-for="item in report.timeline"
            :key="`${item.type}:${item.occurredAt}:${item.cycleNumber ?? 0}`"
            class="timeline-row"
            role="listitem"
          >
            <text
              class="timeline-dot"
              aria-hidden="true"
            />
            <view
              ><text>{{ item.label }}</text
              ><text>{{ formatDateTime(item.occurredAt) }}</text></view
            >
          </view>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, ref } from 'vue'
import { onBackPress, onLoad } from '@dcloudio/uni-app'
import PblPhaseTrack from '@/components/student/PblPhaseTrack.vue'
import PblTargetComparison from '@/components/student/PblTargetComparison.vue'
import MedState from '@/components/ui/MedState.vue'
import { requireRole } from '@/features/identity/public'
import { getPblLearningReport, type PblLearningReport, type PblReportStatus } from '@/features/pbl/public'
import { backOrRoute, goPrimary, handleBackPress, ROUTES } from '@/platform/navigation'

const SectionHeading = defineComponent({
  props: {
    kicker: { type: String, required: true },
    title: { type: String, required: true },
    note: { type: String, required: true },
  },
  setup: (props) => () =>
    h('view', { class: 'section-heading' }, [
      h('text', { class: 'section-kicker' }, props.kicker),
      h('text', { class: 'section-title' }, props.title),
      h('text', { class: 'section-note' }, props.note),
    ]),
})
const report = ref<PblLearningReport>()
const loading = ref(true)
const error = ref('')
const invalidRoute = ref(false)
let sessionId = ''
const statusLabels: Record<PblReportStatus, string> = {
  discussing: '讨论中',
  awaiting_learning: '待发布学习',
  learning_cycle_1: '第一轮学习',
  learning_cycle_2: '第二轮巩固',
  improved: '已改善',
  support_needed: '需线下支持',
}
const hasDiagnosis = computed(() =>
  Boolean(report.value?.diagnosis.knowledgeGaps.length || report.value?.diagnosis.reasoningIssues.length),
)
const formatDate = (value: string) => new Date(value).toLocaleDateString('zh-CN')
const formatDateTime = (value: string) => new Date(value).toLocaleString('zh-CN')
const taskLabel = (value: string) =>
  ({
    discussion: '正式讨论',
    knowledge_review: '知识巩固',
    retest: '客观再测',
    micro_drill: '推理微训练',
    focused_retry: '病例重练',
  })[value] ?? value
const taskStatus = (value: string) =>
  ({ pending: '待完成', in_progress: '进行中', completed: '已完成', inactive: '未激活', skipped: '无需重复' })[value] ??
  value
function back() {
  backOrRoute(ROUTES.studentInsights)
}
function openAction() {
  if (report.value?.nextAction.kind === 'discussion') goPrimary(ROUTES.studentPbl)
  if (report.value?.nextAction.kind === 'tasks') goPrimary(ROUTES.studentLearning)
}
async function load() {
  if (!sessionId) return
  loading.value = true
  error.value = ''
  try {
    report.value = await getPblLearningReport(sessionId)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '请检查网络后重试。'
  } finally {
    loading.value = false
  }
}
onLoad((query) => {
  if (!requireRole('student')) return
  sessionId = typeof query?.sessionId === 'string' ? query.sessionId : ''
  if (!sessionId) {
    invalidRoute.value = true
    loading.value = false
    error.value = '缺少课堂编号，无法读取这份学情报告。'
    return
  }
  void load()
})
onBackPress(({ from }) => handleBackPress(from, ROUTES.studentInsights))
</script>

<style scoped>
.detail-page {
  min-height: 100vh;
  padding: 26rpx 24rpx 70rpx;
  background: var(--med-page);
}
.report-cover,
.report-section {
  display: flex;
  max-width: 920px;
  margin: 0 auto 22rpx;
  padding: 30rpx;
  flex-direction: column;
  gap: 18rpx;
  background: var(--med-surface);
  border: 1rpx solid var(--med-border);
  border-radius: var(--med-radius-md);
}
.report-cover {
  position: relative;
  overflow: hidden;
  padding-top: 42rpx;
}
.specimen-mark {
  position: absolute;
  top: 0;
  right: 0;
  left: 0;
  display: grid;
  height: 11rpx;
  grid-template-columns: 1.4fr 0.7fr 1fr 0.45fr;
  gap: 4rpx;
}
.specimen-mark text:nth-child(odd) {
  background: var(--med-clinical);
}
.specimen-mark text:nth-child(even) {
  background: var(--med-alert, #9f2f2f);
}
.page-title {
  color: var(--med-navy);
  font-size: 40rpx;
  font-weight: 850;
  line-height: 1.3;
}
.cover-meta,
.task-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12rpx 20rpx;
  color: var(--med-muted);
  font-size: 22rpx;
}
.status,
.finding-type {
  padding: 6rpx 12rpx;
  color: var(--med-clinical);
  background: var(--med-wash);
  border-radius: 99rpx;
  font-size: 20rpx;
}
.status--learning_cycle_2,
.status--support_needed {
  color: var(--med-alert, #9f2f2f);
  background: var(--med-alert-soft, #fbe8e8);
}
.cover-summary,
.section-note,
.empty-note,
.finding-summary,
.evidence-copy,
.task-prompt {
  color: var(--med-text-secondary);
  font-size: 25rpx;
  line-height: 1.65;
}
.section-heading {
  display: flex;
  flex-direction: column;
  gap: 7rpx;
}
.section-kicker {
  color: var(--med-clinical);
  font-family: var(--med-font-utility);
  font-size: 20rpx;
  font-weight: 750;
  letter-spacing: 2rpx;
}
.section-title {
  color: var(--med-ink);
  font-size: 31rpx;
  font-weight: 800;
}
.section-note,
.empty-note,
.evidence-copy {
  color: var(--med-muted);
  font-size: 23rpx;
}
.finding-groups,
.task-list,
.timeline {
  display: flex;
  flex-direction: column;
}
.finding {
  display: grid;
  padding: 22rpx 0;
  grid-template-columns: auto 1fr;
  align-items: start;
  gap: 10rpx 14rpx;
  border-top: 1rpx solid var(--med-divider);
}
.finding-type {
  border-radius: 2rpx;
}
.finding-title {
  color: var(--med-ink);
  font-size: 27rpx;
  font-weight: 750;
}
.finding-summary,
.finding .evidence-copy {
  grid-column: span 2;
}
.task-row {
  display: flex;
  padding: 22rpx 0;
  flex-direction: column;
  gap: 9rpx;
  border-top: 1rpx solid var(--med-divider);
}
.task-head {
  justify-content: space-between;
  color: var(--med-ink);
  font-weight: 700;
}
.task-head text:last-child,
.task-result {
  color: var(--med-clinical);
  font-size: 22rpx;
}
.task-row.inactive,
.task-row.skipped {
  opacity: 0.68;
}
.timeline-row {
  position: relative;
  display: grid;
  min-height: 76rpx;
  grid-template-columns: 22rpx 1fr;
  gap: 16rpx;
}
.timeline-row:not(:last-child)::before {
  position: absolute;
  top: 19rpx;
  bottom: 0;
  left: 8rpx;
  width: 2rpx;
  content: '';
  background: var(--med-divider);
}
.timeline-dot {
  z-index: 1;
  width: 16rpx;
  height: 16rpx;
  margin-top: 8rpx;
  background: var(--med-clinical);
  border: 4rpx solid var(--med-wash);
  border-radius: 50%;
}
.timeline-row view {
  display: flex;
  flex-direction: column;
  gap: 5rpx;
  color: var(--med-ink);
  font-size: 25rpx;
}
.timeline-row view text:last-child {
  color: var(--med-muted);
  font-size: 21rpx;
}
.primary {
  min-height: 88rpx;
  margin: 0;
  color: white;
  background: var(--med-clinical);
  font-size: 27rpx;
}
@media (min-width: 768px) {
  .detail-page {
    padding: 32px 32px 96px;
  }
  .report-cover,
  .report-section {
    padding: 34px;
  }
  .page-title {
    font-size: 34px;
  }
}
</style>
