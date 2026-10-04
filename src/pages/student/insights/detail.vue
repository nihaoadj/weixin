<template>
  <view class="safe-page detail-page">
    <MedState
      v-if="loading"
      centered
      variant="loading"
      icon="history"
      title="正在读取学习记录"
      description="正在整理本次研讨、学习证据与目标改善情况。"
    />
    <MedState
      v-else-if="error"
      centered
      variant="error"
      icon="retry"
      title="学习记录加载失败"
      :description="error"
      :action-label="invalidRoute ? '返回学情' : '重新加载'"
      :secondary-action-label="invalidRoute ? '' : '返回学情'"
      @action="invalidRoute ? back() : load()"
      @secondary-action="back"
    />

    <scroll-view
      v-else-if="report"
      class="detail-scroll"
      scroll-y
      enhanced
      :show-scrollbar="false"
    >
      <view class="detail-shell">
        <text class="learning-motto">每一次讨论，都让诊断思路更清晰</text>

        <view class="record-header">
          <view class="record-heading-row">
            <view class="record-icon"><StudentNavIcon name="chat" /></view>
            <view class="record-heading-copy">
              <text class="record-kicker">PBL 学习记录</text>
              <text class="record-title">{{ report.session.caseTitle }}</text>
            </view>
          </view>
          <view class="record-meta">
            <text>{{ report.session.topicLabel }}</text>
            <text class="meta-divider" />
            <text>{{ formatDate(report.session.createdAt) }}</text>
            <text
              class="status-pill"
              :class="`status-pill--${report.status}`"
              >{{ statusLabels[report.status] }}</text
            >
          </view>
          <view class="visibility-strip">
            <view
              class="shield-icon"
              aria-hidden="true"
              ><text>✓</text></view
            >
            <view>
              <text class="visibility-title">{{ visibilityInfo.title }}</text>
              <text class="visibility-copy">{{ visibilityInfo.copy }}</text>
            </view>
          </view>
        </view>

        <view class="conclusion-card">
          <view class="conclusion-heading">
            <view
              class="spark-symbol"
              aria-hidden="true"
              ><text /><text /><text
            /></view>
            <text>本次学习结论</text>
          </view>
          <text class="conclusion-copy">{{ report.summaryText }}</text>
          <view class="metric-row">
            <view class="metric-item">
              <text class="metric-value">{{ completedPhaseCount }}/4</text>
              <text class="metric-label">讨论阶段</text>
            </view>
            <view class="metric-item">
              <text class="metric-value">{{ taskProgressLabel }}</text>
              <text class="metric-label">正式任务</text>
            </view>
            <view class="metric-item">
              <text class="metric-value">{{ targetProgressLabel }}</text>
              <text class="metric-label">最新达标</text>
            </view>
          </view>
          <button
            v-if="report.nextAction.kind !== 'none'"
            class="next-action"
            @click="openAction"
          >
            {{ report.nextAction.label }} <text aria-hidden="true">›</text>
          </button>
          <view
            v-else
            class="next-note"
          >
            <text class="next-note-label">下一步</text>
            <text>{{ report.nextAction.label }}</text>
          </view>
        </view>

        <view class="record-section dialogue-section">
          <LearningDialogueReview
            v-if="!dialogueError"
            v-model:current="dialogueTurnIndex"
            :messages="dialogueMessages"
          />
          <view
            v-if="!dialogueError && dialogueTurnCount"
            class="dialogue-review-controls"
          >
            <button
              class="dialogue-turn-arrow dialogue-turn-arrow--previous"
              :disabled="dialogueTurnIndex === 0"
              aria-label="上一轮对话"
              @click="moveDialogueTurn(-1)"
            >
              ‹
            </button>
            <view
              class="dialogue-turn-dots"
              aria-hidden="true"
            >
              <text
                v-for="index in dialogueTurnCount"
                :key="index"
                :class="{ active: index - 1 === dialogueTurnIndex }"
              />
            </view>
            <button
              class="dialogue-turn-arrow dialogue-turn-arrow--next"
              :disabled="dialogueTurnIndex === dialogueTurnCount - 1"
              aria-label="下一轮对话"
              @click="moveDialogueTurn(1)"
            >
              ›
            </button>
          </view>
          <template v-else>
            <LearningRecordSectionHeading
              title="对话内容"
              note="本次学习记录仍可继续查看；对话原文暂未读取成功。"
            />
            <view class="dialogue-load-error">
              <text>{{ dialogueError }}</text>
              <button @click="loadDialogueReview">重新读取对话</button>
            </view>
          </template>
        </view>

        <view class="record-section">
          <LearningRecordSectionHeading
            title="学习证据路径"
            note="四阶段证据只来自你在对应阶段提交的内容。"
          />
          <PblPhaseTrack
            v-if="report.phaseProgress.length"
            class="section-body phase-track"
            :phases="report.phaseProgress"
          />
          <text
            v-else
            class="empty-note"
            >本次记录没有个人讨论阶段；下方内容来自课堂共同训练。</text
          >
        </view>

        <view class="record-section">
          <LearningRecordSectionHeading
            title="本次学习重点"
            note="依据研讨中的表达形成，用于学习改进，不是临床诊断。"
          />
          <view
            v-if="hasDiagnosis"
            class="finding-list"
            role="list"
          >
            <view
              v-for="item in report.diagnosis.knowledgeGaps"
              :key="item.id"
              class="finding-row"
              role="listitem"
            >
              <view class="finding-title-row">
                <text class="finding-tag finding-tag--knowledge">知识重点</text>
                <text class="finding-title">{{ item.label }}</text>
                <text class="confidence-label">{{ confidenceLabel(item.confidence) }}</text>
              </view>
              <text class="finding-summary">{{ item.summary }}</text>
              <view class="evidence-block">
                <text class="evidence-label">证据</text>
                <text>{{ item.evidenceSummary || '当前记录未提供可展示的证据摘要。' }}</text>
              </view>
            </view>
            <view
              v-for="item in report.diagnosis.reasoningIssues"
              :key="item.id"
              class="finding-row"
              role="listitem"
            >
              <view class="finding-title-row">
                <text class="finding-tag finding-tag--reasoning">推理重点</text>
                <text class="finding-title">{{ item.label }}</text>
              </view>
              <text class="finding-summary">{{ item.summary }}</text>
              <view class="evidence-block">
                <text class="evidence-label">证据</text>
                <text>{{ item.evidenceSummary || '当前记录未提供可展示的证据摘要。' }}</text>
              </view>
              <view class="improvement-block">
                <text class="improvement-label">建议</text>
                <text>{{ item.improvement }}</text>
              </view>
            </view>
          </view>
          <text
            v-else
            class="empty-note"
            >尚未形成有证据的学习重点。完成四阶段讨论后，这里会显示需要巩固的知识与推理线索。</text
          >
        </view>

        <view
          v-if="teacherFeedbacks.length"
          class="record-section"
        >
          <LearningRecordSectionHeading
            title="教师反馈"
            note="仅展示与你本次课堂学习记录直接相关的反馈。"
          />
          <view class="feedback-list">
            <view
              v-for="item in teacherFeedbacks"
              :key="item.id"
              class="feedback-row"
            >
              <view class="feedback-meta">
                <text>{{ feedbackActionLabel(item.actionType) }}</text>
                <text>{{ item.createdAt ? formatDateTime(item.createdAt) : '时间待同步' }}</text>
              </view>
              <text class="feedback-body">{{ item.body }}</text>
            </view>
          </view>
        </view>

        <view class="record-section">
          <LearningRecordSectionHeading
            title="目标改善轨迹"
            note="逐项目标对照分数、要求和证据；不合并为综合分。"
          />
          <PblTargetComparison
            v-if="report.targetProgress.length"
            class="section-body target-comparison"
            :targets="report.targetProgress"
          />
          <text
            v-else
            class="empty-note"
            >完成一轮全部已激活任务后，系统才会形成可追溯的目标对照。</text
          >
        </view>

        <view class="record-section">
          <LearningRecordSectionHeading
            title="正式学习任务"
            :note="taskSectionNote"
          />
          <view
            v-if="report.plans.length"
            class="plan-list"
          >
            <view
              v-for="plan in report.plans"
              :key="plan.id"
              class="plan-group"
            >
              <view class="plan-heading">
                <view>
                  <text class="plan-title">{{ planTitle(plan.assignmentBasis) }}</text>
                  <text class="plan-cycle">第 {{ plan.currentCycle }}/{{ plan.maxCycles }} 轮</text>
                </view>
                <text class="plan-status">{{ planStatus(plan.verificationStatus) }}</text>
              </view>
              <view
                class="task-list"
                role="list"
              >
                <view
                  v-for="task in plan.tasks"
                  :key="task.id"
                  class="task-row"
                  :class="`task-row--${task.status}`"
                  role="listitem"
                >
                  <view class="task-heading">
                    <text>第 {{ task.cycleNumber }} 轮 · {{ taskLabel(task.taskType) }}</text>
                    <text>{{ taskStatus(task.status) }}</text>
                  </view>
                  <text class="task-prompt">{{ task.prompt }}</text>
                  <text class="task-target">目标：{{ task.targetLabel }}</text>
                  <text class="task-source">资料：{{ task.reference || '本任务未提供单独资料来源。' }}</text>
                  <view
                    v-if="task.score != null || task.status === 'completed'"
                    class="task-result"
                  >
                    <text>{{ task.score == null ? '未形成分数' : `${task.score} 分` }}</text>
                    <text>{{ task.evidencePresent ? '已有评价证据' : '评价证据缺失' }}</text>
                  </view>
                  <text
                    v-if="task.feedback"
                    class="task-feedback"
                    >{{ task.feedback }}</text
                  >
                </view>
              </view>
            </view>
          </view>
          <text
            v-else
            class="empty-note"
            >本次学习记录暂时没有正式任务。自主练习不会计入教师正式统计。</text
          >
        </view>

        <view class="record-section timeline-section">
          <LearningRecordSectionHeading
            title="学习记录时间线"
            note="事件按发生时间保存，历史评价不会被下一轮覆盖。"
          />
          <view
            class="timeline"
            role="list"
          >
            <view
              v-for="item in visibleTimeline"
              :key="`${item.type}:${item.occurredAt}:${item.cycleNumber ?? 0}`"
              class="timeline-row"
              role="listitem"
            >
              <view class="timeline-marker"><text /></view>
              <view class="timeline-content">
                <text>{{ item.label }}</text>
                <text>{{ formatDateTime(item.occurredAt) }}</text>
              </view>
            </view>
          </view>
          <button
            v-if="report.timeline.length > timelinePreviewCount"
            class="timeline-toggle"
            @click="timelineExpanded = !timelineExpanded"
          >
            {{ timelineExpanded ? '收起时间线' : `查看全部 ${report.timeline.length} 条记录` }}
          </button>
        </view>

        <text class="record-footnote">记录更新时间 {{ formatDateTime(report.updatedAt) }}</text>
      </view>
    </scroll-view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onBackPress, onLoad } from '@dcloudio/uni-app'
import LearningDialogueReview from '@/features/pbl/presentation/LearningDialogueReview.vue'
import LearningRecordSectionHeading from '@/components/student/LearningRecordSectionHeading.vue'
import { groupLearningDialogueTurns } from '@/features/pbl/presentation/learningDialogueTurns'
import PblPhaseTrack from '@/features/pbl/presentation/PblPhaseTrack.vue'
import PblTargetComparison from '@/features/pbl/presentation/PblTargetComparison.vue'
import MedState from '@/components/ui/MedState.vue'
import StudentNavIcon from '@/components/ui/StudentNavIcon.vue'
import { requireRole } from '@/features/identity/public'
import {
  getLearningDialogue,
  getPblLearningReport,
  type LearningDialogue,
  type PblLearningReport,
  type PblReportStatus,
} from '@/features/pbl/public'
import { backOrRoute, goPrimary, handleBackPress, ROUTES } from '@/platform/navigation'

const report = ref<PblLearningReport>()
const dialogue = ref<LearningDialogue>()
const loading = ref(true)
const error = ref('')
const dialogueError = ref('')
const dialogueTurnIndex = ref(0)
const invalidRoute = ref(false)
const timelineExpanded = ref(false)
const timelinePreviewCount = 4
let sessionId = ''

const statusLabels: Record<PblReportStatus, string> = {
  discussing: '讨论中',
  awaiting_learning: '待发布学习',
  learning_cycle_1: '第一轮学习',
  learning_cycle_2: '第二轮巩固',
  improved: '已改善',
  support_needed: '需线下支持',
}
const visibilityMap: Record<PblLearningReport['visibility'], { title: string; copy: string }> = {
  private: { title: '私人学习记录', copy: '仅自己可见，不进入教师统计。' },
  classroom: { title: '课堂学习记录', copy: '教师仅按班级权限查看正式学习证据。' },
  legacy_shared: { title: '历史共享记录', copy: '按原提交范围只读保留，不新增共享内容。' },
}
const hasDiagnosis = computed(() =>
  Boolean(report.value?.diagnosis.knowledgeGaps.length || report.value?.diagnosis.reasoningIssues.length),
)
const visibilityInfo = computed(() => visibilityMap[report.value?.visibility ?? 'private'])
const teacherFeedbacks = computed(() => report.value?.teacherFeedbacks ?? [])
const dialogueMessages = computed(() => dialogue.value?.participation?.messages ?? [])
const dialogueTurnCount = computed(() => groupLearningDialogueTurns(dialogueMessages.value).length)
const completedPhaseCount = computed(
  () => report.value?.phaseProgress.filter((item) => item.state === 'completed').length ?? 0,
)
const taskProgressLabel = computed(() => {
  const progress = report.value?.taskProgress
  return !progress?.total ? '--' : `${progress.completed}/${progress.total}`
})
const latestTargetResults = computed(() =>
  (report.value?.targetProgress ?? []).map((target) => ({
    target,
    latest: [...target.cycles].sort((left, right) => left.cycleNumber - right.cycleNumber).at(-1),
  })),
)
const targetProgressLabel = computed(() => {
  if (!latestTargetResults.value.length) return '--'
  const passed = latestTargetResults.value.filter((item) => item.latest?.evidence_present && item.latest.passed).length
  return `${passed}/${latestTargetResults.value.length}`
})
const taskSectionNote = computed(() => {
  const progress = report.value?.taskProgress
  return progress?.total
    ? `已完成 ${progress.completed}/${progress.total} 项已激活任务。`
    : '只展示教师正式发布的任务与评价证据。'
})
const visibleTimeline = computed(() => {
  const items = report.value?.timeline ?? []
  return timelineExpanded.value ? items : items.slice(-timelinePreviewCount)
})

const formatDate = (value: string) => {
  const date = new Date(value)
  const year = date.getFullYear()
  return `${year}年${date.getMonth() + 1}月${date.getDate()}日`
}
const formatDateTime = (value: string) => new Date(value).toLocaleString('zh-CN', { hour12: false })
const confidenceLabel = (value: string) => ({ high: '高置信', medium: '中置信', low: '低置信' })[value] ?? value
const feedbackActionLabel = (value: string) =>
  ({
    feedback_only: '学习建议',
    task_published: '反馈并发布任务',
    closed: '本轮总结',
    follow_up: '补充支持',
  })[value] ?? '教师反馈'
const planTitle = (basis: 'personal' | 'classroom') => (basis === 'personal' ? '针对个人重点' : '课堂共同训练')
const planStatus = (value: string) =>
  ({
    not_ready: '待完成任务',
    pending_teacher: '待形成评价',
    improved: '目标已达标',
    needs_reinforcement: '需要继续巩固',
  })[value] ?? value
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
function moveDialogueTurn(offset: number) {
  dialogueTurnIndex.value = Math.min(dialogueTurnCount.value - 1, Math.max(0, dialogueTurnIndex.value + offset))
}
async function load() {
  if (!sessionId) return
  loading.value = true
  error.value = ''
  dialogueError.value = ''
  dialogueTurnIndex.value = 0
  timelineExpanded.value = false
  try {
    const dialogueRequest = getLearningDialogue(sessionId).catch((reason) => {
      dialogueError.value = reason instanceof Error ? reason.message : '请检查网络后重新读取。'
      return undefined
    })
    const [nextReport, nextDialogue] = await Promise.all([getPblLearningReport(sessionId), dialogueRequest])
    report.value = nextReport
    dialogue.value = nextDialogue
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '请检查网络后重试。'
  } finally {
    loading.value = false
  }
}
async function loadDialogueReview() {
  if (!sessionId) return
  dialogueError.value = ''
  try {
    dialogue.value = await getLearningDialogue(sessionId)
  } catch (reason) {
    dialogueError.value = reason instanceof Error ? reason.message : '请检查网络后重新读取。'
  }
}
onLoad((query) => {
  if (!requireRole('student')) return
  sessionId = typeof query?.sessionId === 'string' ? query.sessionId : ''
  if (!sessionId) {
    invalidRoute.value = true
    loading.value = false
    error.value = '缺少课堂编号，无法读取这份学习记录。'
    return
  }
  void load()
})
onBackPress(({ from }) => handleBackPress(from, ROUTES.studentInsights))
</script>

<style scoped>
.detail-page {
  --med-ink: #071a5a;
  --med-text: #365b95;
  --med-text-secondary: #4f6fa3;
  --med-muted: #6f83ad;
  --med-clinical: #087ccf;
  --med-brand: #087ccf;
  --med-brand-soft: #eef8fd;
  --med-navy: #071a5a;
  --med-primary: #2dcbb9;
  --med-brand-deep: #066eae;
  --med-wash: #eef8fd;
  --med-page: #f7fbfe;
  --med-border: #d6eaf7;
  --med-divider: #e8f2f9;
  --med-alert: #e95e74;
  --med-alert-soft: #fff0f4;
  height: calc(100vh - var(--window-top, 0px));
  min-height: 0;
  overflow: hidden;
  background: linear-gradient(180deg, #f1f9fe 0, #fff 280rpx, #f8fcff 100%);
}
.detail-scroll {
  height: 100%;
}
.detail-shell {
  width: 100%;
  max-width: 920px;
  margin: 0 auto;
  padding: 0 24rpx calc(68rpx + env(safe-area-inset-bottom));
  box-sizing: border-box;
}
.learning-motto,
.record-footnote {
  display: block;
  color: #7187b2;
  font-size: 22rpx;
  letter-spacing: 1rpx;
  text-align: center;
}
.learning-motto {
  padding: 12rpx 0 20rpx;
}
.record-header {
  padding: 22rpx 8rpx 30rpx;
  border-bottom: 1rpx solid var(--med-border);
}
.dialogue-section {
  padding-top: 34rpx;
}
.dialogue-load-error {
  display: flex;
  margin-top: 20rpx;
  padding: 28rpx 24rpx;
  align-items: flex-start;
  flex-direction: column;
  gap: 16rpx;
  color: var(--med-text-secondary);
  background: #f5fbfe;
  border: 1rpx solid var(--med-border);
  border-radius: 18rpx;
  font-size: 23rpx;
  line-height: 1.6;
}
.dialogue-load-error button {
  min-height: 88rpx;
  margin: 0;
  padding: 0 26rpx;
  color: #078b9c;
  background: #eaf9fb;
  border: 0;
  border-radius: 99rpx;
  font-size: 23rpx;
  font-weight: 700;
}
.dialogue-review-controls {
  display: flex;
  min-height: 88rpx;
  padding: 0 8rpx;
  box-sizing: border-box;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border: 1rpx solid #cfeaf3;
  border-top-color: #e3f1f7;
  border-radius: 0 0 22rpx 22rpx;
}
.dialogue-turn-arrow {
  display: flex;
  width: 88rpx;
  min-width: 88rpx;
  min-height: 88rpx;
  margin: 0;
  padding: 0;
  align-items: center;
  justify-content: center;
  color: #079baa;
  background: transparent;
  border: 0;
  font-size: 38rpx;
}
.dialogue-turn-arrow[disabled] {
  color: #c6d6e7;
  background: transparent;
}
.dialogue-turn-dots {
  display: flex;
  min-width: 0;
  flex: 1;
  align-items: center;
  justify-content: center;
  gap: 9rpx;
}
.dialogue-turn-dots text {
  width: 10rpx;
  height: 10rpx;
  background: #d7e7f2;
  border-radius: 99rpx;
  transition: width 180ms ease;
}
.dialogue-turn-dots text.active {
  width: 30rpx;
  background: linear-gradient(90deg, #169fd0, #21bbc3);
}
.record-heading-row,
.record-meta,
.visibility-strip,
.conclusion-heading,
.section-title-wrap,
.finding-title-row,
.feedback-meta,
.plan-heading,
.task-heading,
.task-result {
  display: flex;
  align-items: center;
}
.record-heading-row {
  gap: 18rpx;
}
.record-icon {
  display: flex;
  width: 72rpx;
  height: 72rpx;
  flex: 0 0 72rpx;
  align-items: center;
  justify-content: center;
  color: #087ccf;
  background: #e9f6fd;
  border-radius: 22rpx;
}
.record-icon :deep(.student-nav-icon) {
  width: 34rpx;
  height: 34rpx;
  font-size: 34rpx;
}
.record-heading-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 5rpx;
}
.record-kicker {
  color: #087ccf;
  font-size: 21rpx;
  font-weight: 700;
  letter-spacing: 2rpx;
}
.record-title {
  color: var(--med-ink);
  font-size: 38rpx;
  font-weight: 850;
  line-height: 1.35;
}
.record-meta {
  margin-top: 18rpx;
  flex-wrap: wrap;
  gap: 12rpx;
  color: #5b76aa;
  font-size: 22rpx;
}
.meta-divider {
  width: 1rpx;
  height: 22rpx;
  background: #bfd9eb;
}
.status-pill {
  margin-left: auto;
  padding: 7rpx 15rpx;
  color: #087ccf;
  background: #e9f6fd;
  border-radius: 99rpx;
  font-size: 20rpx;
  font-weight: 650;
}
.status-pill--improved {
  color: #087e75;
  background: #e8faf6;
}
.status-pill--learning_cycle_2,
.status-pill--support_needed {
  color: #bd405b;
  background: #fff0f4;
}
.visibility-strip {
  margin-top: 20rpx;
  padding: 18rpx 20rpx;
  align-items: flex-start;
  gap: 15rpx;
  background: rgba(234, 247, 253, 0.72);
  border: 1rpx solid #d8ecf7;
  border-radius: 16rpx;
}
.shield-icon {
  display: flex;
  width: 34rpx;
  height: 39rpx;
  flex: 0 0 34rpx;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: linear-gradient(160deg, #24c7d8, #0b86d4);
  border-radius: 10rpx 10rpx 15rpx 15rpx;
  font-size: 18rpx;
  font-weight: 900;
}
.visibility-strip > view:last-child {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 4rpx;
}
.visibility-title {
  color: var(--med-ink);
  font-size: 23rpx;
  font-weight: 750;
}
.visibility-copy {
  color: #607ba8;
  font-size: 21rpx;
  line-height: 1.5;
}
.conclusion-card {
  position: relative;
  overflow: hidden;
  margin: 26rpx 0 6rpx;
  padding: 28rpx 26rpx;
  background: linear-gradient(135deg, #edf9fe 0%, #f7fbff 52%, #edfdf9 100%);
  border: 1rpx solid #cae8f6;
  border-radius: 24rpx;
  box-shadow: 0 10rpx 28rpx rgba(8, 124, 207, 0.07);
}
.conclusion-card::after {
  position: absolute;
  top: -78rpx;
  right: -58rpx;
  width: 210rpx;
  height: 210rpx;
  content: '';
  background: radial-gradient(circle, rgba(45, 203, 185, 0.14), rgba(45, 203, 185, 0));
  border-radius: 50%;
}
.conclusion-heading {
  position: relative;
  z-index: 1;
  gap: 12rpx;
  color: var(--med-ink);
  font-size: 30rpx;
  font-weight: 850;
}
.spark-symbol {
  position: relative;
  width: 32rpx;
  height: 32rpx;
  color: #17b8d2;
}
.spark-symbol text {
  position: absolute;
  top: 14rpx;
  left: 2rpx;
  width: 28rpx;
  height: 4rpx;
  background: currentColor;
  border-radius: 99rpx;
}
.spark-symbol text:nth-child(2) {
  transform: rotate(60deg);
}
.spark-symbol text:nth-child(3) {
  transform: rotate(-60deg);
}
.conclusion-copy {
  position: relative;
  z-index: 1;
  display: block;
  margin-top: 16rpx;
  color: #365b95;
  font-size: 26rpx;
  line-height: 1.72;
}
.metric-row {
  position: relative;
  z-index: 1;
  display: grid;
  margin-top: 24rpx;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border-top: 1rpx solid #cde8f4;
}
.metric-item {
  display: flex;
  min-width: 0;
  padding: 20rpx 8rpx 4rpx;
  align-items: center;
  flex-direction: column;
  gap: 5rpx;
}
.metric-item + .metric-item {
  border-left: 1rpx solid #d5ebf5;
}
.metric-value {
  color: var(--med-ink);
  font-family: var(--med-font-utility);
  font-size: 31rpx;
  font-weight: 850;
}
.metric-label {
  color: #6c82aa;
  font-size: 20rpx;
}
.next-action {
  position: relative;
  z-index: 1;
  min-height: 82rpx;
  margin: 24rpx 0 0;
  color: #fff;
  background: linear-gradient(90deg, #087ccf, #10a9d0);
  border-radius: 16rpx;
  font-size: 26rpx;
  font-weight: 700;
}
.next-action text {
  margin-left: 12rpx;
  font-size: 34rpx;
}
.next-note {
  position: relative;
  z-index: 1;
  display: flex;
  margin-top: 22rpx;
  padding-top: 18rpx;
  align-items: flex-start;
  gap: 14rpx;
  color: #42689d;
  border-top: 1rpx solid #cde8f4;
  font-size: 23rpx;
  line-height: 1.55;
}
.next-note-label {
  flex: none;
  color: #087ccf;
  font-weight: 750;
}
.record-section {
  padding: 32rpx 8rpx 34rpx;
  border-bottom: 1rpx solid var(--med-border);
}
.section-body,
.finding-list,
.feedback-list,
.plan-list,
.timeline,
.empty-note {
  margin-top: 24rpx;
}
.empty-note {
  display: block;
  padding: 20rpx;
  color: #5876a5;
  background: #f3f9fd;
  border-left: 5rpx solid #68cddd;
  border-radius: 12rpx;
  font-size: 23rpx;
  line-height: 1.65;
}
.finding-list,
.feedback-list,
.plan-list,
.task-list,
.timeline {
  display: flex;
  flex-direction: column;
}
.finding-row {
  padding: 24rpx 0;
  border-top: 1rpx solid var(--med-divider);
}
.finding-row:first-child,
.feedback-row:first-child,
.plan-group:first-child,
.task-row:first-child {
  padding-top: 0;
  border-top: 0;
}
.finding-title-row {
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 10rpx 12rpx;
}
.finding-tag {
  flex: none;
  padding: 6rpx 12rpx;
  color: #087ccf;
  background: #e9f6fd;
  border-radius: 99rpx;
  font-size: 19rpx;
  font-weight: 700;
}
.finding-tag--reasoning {
  color: #087f76;
  background: #e8faf6;
}
.finding-title {
  min-width: 180rpx;
  flex: 1;
  color: var(--med-ink);
  font-size: 27rpx;
  font-weight: 800;
  line-height: 1.45;
}
.confidence-label {
  color: #7b8eae;
  font-size: 20rpx;
  line-height: 1.8;
}
.finding-summary {
  display: block;
  margin-top: 13rpx;
  color: #365b95;
  font-size: 25rpx;
  line-height: 1.7;
}
.evidence-block,
.improvement-block {
  display: grid;
  margin-top: 14rpx;
  padding: 16rpx 18rpx;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 12rpx;
  color: #5d78a5;
  background: #f4f9fd;
  border-radius: 12rpx;
  font-size: 22rpx;
  line-height: 1.6;
}
.improvement-block {
  background: #f0fbf8;
}
.evidence-label,
.improvement-label {
  color: #087ccf;
  font-weight: 750;
}
.improvement-label {
  color: #07887d;
}
.feedback-row,
.plan-group {
  padding: 24rpx 0;
  border-top: 1rpx solid var(--med-divider);
}
.feedback-meta,
.plan-heading,
.task-heading,
.task-result {
  justify-content: space-between;
  gap: 18rpx;
}
.feedback-meta text:first-child {
  color: #087ccf;
  font-size: 23rpx;
  font-weight: 750;
}
.feedback-meta text:last-child,
.plan-cycle,
.task-source {
  color: #7185aa;
  font-size: 20rpx;
}
.feedback-body {
  display: block;
  margin-top: 12rpx;
  color: #365b95;
  font-size: 25rpx;
  line-height: 1.7;
}
.plan-heading {
  align-items: flex-start;
}
.plan-heading > view {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 6rpx;
}
.plan-title {
  color: var(--med-ink);
  font-size: 27rpx;
  font-weight: 800;
}
.plan-status {
  flex: none;
  padding: 7rpx 13rpx;
  color: #087f76;
  background: #e8faf6;
  border-radius: 99rpx;
  font-size: 20rpx;
}
.task-list {
  margin-top: 18rpx;
}
.task-row {
  padding: 22rpx 0;
  border-top: 1rpx solid var(--med-divider);
}
.task-row--inactive,
.task-row--skipped {
  opacity: 0.62;
}
.task-heading {
  color: var(--med-ink);
  font-size: 22rpx;
  font-weight: 750;
}
.task-heading text:last-child {
  color: #087ccf;
}
.task-prompt {
  display: block;
  margin-top: 12rpx;
  color: #365b95;
  font-size: 25rpx;
  line-height: 1.65;
}
.task-target,
.task-source,
.task-feedback {
  display: block;
  margin-top: 8rpx;
  line-height: 1.55;
}
.task-target {
  color: #5875a3;
  font-size: 22rpx;
}
.task-result {
  margin-top: 14rpx;
  padding: 13rpx 16rpx;
  color: #087f76;
  background: #eefaf7;
  border-radius: 10rpx;
  font-size: 21rpx;
  font-weight: 700;
}
.task-feedback {
  color: #5a75a0;
  font-size: 22rpx;
}
.timeline-row {
  position: relative;
  display: grid;
  min-height: 78rpx;
  grid-template-columns: 28rpx minmax(0, 1fr);
  gap: 16rpx;
}
.timeline-marker {
  position: relative;
  display: flex;
  justify-content: center;
}
.timeline-marker::after {
  position: absolute;
  top: 18rpx;
  bottom: 0;
  left: 13rpx;
  width: 2rpx;
  content: '';
  background: #d9eaf4;
}
.timeline-row:last-child .timeline-marker::after {
  display: none;
}
.timeline-marker text {
  z-index: 1;
  width: 14rpx;
  height: 14rpx;
  margin-top: 5rpx;
  background: #2dcbb9;
  border: 4rpx solid #e5faf6;
  border-radius: 50%;
}
.timeline-content {
  display: flex;
  padding-bottom: 20rpx;
  flex-direction: column;
  gap: 5rpx;
  color: var(--med-ink);
  font-size: 24rpx;
  line-height: 1.5;
}
.timeline-content text:last-child {
  color: #7a8dad;
  font-size: 20rpx;
}
.timeline-toggle {
  min-height: 70rpx;
  margin: 8rpx 0 0;
  color: #087ccf;
  background: #eef8fd;
  border-radius: 14rpx;
  font-size: 23rpx;
}
.record-footnote {
  padding: 28rpx 0 12rpx;
  font-size: 20rpx;
}
.phase-track :deep(.phase.completed .phase-index) {
  color: #087ccf;
  background: #eaf7fd;
  border-color: #38bcd8;
}
.phase-track :deep(.phase.current .phase-index) {
  background: linear-gradient(135deg, #087ccf, #20bfd9);
  border-color: #087ccf;
}
.phase-track :deep(.missing) {
  color: #c84560;
}
.target-comparison :deep(.comparison:first-child) {
  padding-top: 0;
  border-top: 0;
}
.target-comparison :deep(.cycle) {
  background: #f5f9fd;
  border-left-color: #e95e74;
}
.target-comparison :deep(.cycle.passed) {
  border-left-color: #2dcbb9;
}
@media screen and (min-width: 600px) {
  .detail-shell {
    padding-right: 32px;
    padding-left: 32px;
  }
  .record-title {
    font-size: 30px;
  }
  .record-section,
  .conclusion-card {
    padding-right: 28px;
    padding-left: 28px;
  }
}
</style>
