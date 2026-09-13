<template>
  <view class="safe-page page">
    <text
      class="sr-only"
      role="heading"
      aria-level="1"
      >学习</text
    >
    <PblTaskList />
    <MedState
      v-if="loading"
      variant="loading"
      icon="retry"
      title="正在加载学习画像"
      description="正在整理你的训练表现与今日计划。"
    />
    <MedState
      v-else-if="error"
      variant="error"
      icon="retry"
      title="学习画像加载失败"
      :description="error"
      action-label="重新加载"
      @action="load"
    />
    <view
      v-else-if="isFirstUse"
      class="card onboarding"
    >
      <text class="eyebrow-label">第一次训练</text>
      <text class="onboarding-title">先完成一份病例，再生成你的学习计划</text>
      <text class="muted">系统会依据正式病例表现建立六维能力画像，并安排三项针对性练习。</text>
      <view
        class="onboarding-steps"
        role="list"
        aria-label="首次训练流程"
      >
        <view
          class="onboarding-step"
          role="listitem"
        >
          <text class="step-index">1</text>
          <view
            ><text class="step-title">完成结构化病例</text
            ><text class="muted">依次完成病史、表征、鉴别、检查与处置。</text></view
          >
        </view>
        <view
          class="onboarding-step"
          role="listitem"
        >
          <text class="step-index">2</text>
          <view
            ><text class="step-title">获得形成性反馈</text
            ><text class="muted">查看优势、薄弱项和下一步建议。</text></view
          >
        </view>
        <view
          class="onboarding-step"
          role="listitem"
        >
          <text class="step-index">3</text>
          <view
            ><text class="step-title">开始个性化练习</text><text class="muted">按顺序完成三项针对性任务。</text></view
          >
        </view>
      </view>
      <view class="onboarding-actions">
        <button
          tabindex="0"
          role="button"
          class="primary"
          @keydown="activateButtonOnKey"
          @click="openCases"
        >
          进入病例训练
        </button>
        <button
          tabindex="0"
          role="button"
          class="text-action"
          @keydown="activateButtonOnKey"
          @click="openChat"
        >
          前往研讨
        </button>
      </view>
    </view>
    <template v-else>
      <view
        v-if="plan"
        class="card today-card"
      >
        <text class="eyebrow-label">今日带教记录</text>
        <view class="section-head"
          ><text class="title">今日训练</text><text class="badge">已完成 {{ progress }}/3</text></view
        >
        <text class="muted">目标维度：{{ plan.targetDimensionIds.map(dimensionLabel).join('、') }}</text>
        <view
          v-if="nextTask"
          class="next-task"
        >
          <text class="next-task-label">下一项任务</text>
          <text class="next-task-title"
            >{{ nextTask.position }}. {{ nextTask.publicDefinition.title || nextTask.taskType }}</text
          >
          <text class="muted">{{ taskInstruction(nextTask) }}</text>
          <button
            tabindex="0"
            role="button"
            class="primary"
            @keydown="activateButtonOnKey"
            @click="openTask(nextTask)"
          >
            {{ nextTask.status === 'in_progress' ? '继续本次训练' : '开始下一项训练' }}
          </button>
        </view>
        <view
          v-else
          class="plan-complete"
        >
          <text class="next-task-label">今日训练已完成</text>
          <text class="muted">复盘本次带教记录，确认下一轮练习重点。</text>
        </view>
        <button
          v-if="plan.status === 'completed'"
          tabindex="0"
          role="button"
          class="secondary"
          @keydown="activateButtonOnKey"
          @click="openReview"
        >
          查看训练复盘
        </button>
        <view
          class="plan-progress"
          role="list"
          aria-label="今日训练进度"
        >
          <view
            v-for="task in plan.tasks"
            :key="task.id"
            class="progress-step"
            :class="task.status"
            role="listitem"
          >
            <text class="progress-index">{{ task.position }}</text>
            <view
              ><text>第 {{ task.position }} 项</text
              ><text class="progress-status">{{ statusLabel(task.status) }}</text></view
            >
          </view>
        </view>
      </view>
      <view
        v-else
        class="card section empty"
      >
        <text class="section-title">还没有进行中的计划</text>
        <text class="muted">完成一份完整病例评估后，将自动生成三项训练。</text>
        <button
          tabindex="0"
          role="button"
          class="primary"
          @keydown="activateButtonOnKey"
          @click="openCases"
        >
          进入病例训练
        </button>
      </view>
    </template>
    <view
      v-if="!loading"
      class="flat-section"
    >
      <view class="flat-head">
        <text class="flat-title">自主训练</text><text class="evidence-label">按需要选择</text>
      </view>
      <view
        class="resource-grid"
        role="list"
        aria-label="自主训练资源"
      >
        <button
          v-for="resource in resources"
          :key="resource.view"
          class="resource-row"
          role="listitem"
          @keydown="activateButtonOnKey"
          @click="openResource(resource.view)"
        >
          <view>
            <text class="resource-title">{{ resource.title }}</text>
            <text class="muted">{{ resource.description }}</text>
          </view>
          <text
            class="resource-arrow"
            aria-hidden="true"
            >›</text
          >
        </button>
      </view>
    </view>
    <template v-if="!loading && !error">
      <view
        v-if="!isFirstUse"
        class="flat-section"
      >
        <view class="flat-head"
          ><text class="flat-title">能力画像</text><text class="evidence-label">评估证据</text></view
        >
        <text class="muted">正式病例成绩与练习掌握度分开记录。</text>
        <view class="dimension-grid">
          <view
            v-for="item in dimensions"
            :key="String(item.dimension_id)"
            class="dimension"
          >
            <view class="dimension-head">
              <text>{{ item.label || dimensionLabel(String(item.dimension_id)) }}</text>
              <text class="score">{{ Number(item.score || 0).toFixed(0) }}</text>
            </view>
            <view
              class="score-track"
              aria-hidden="true"
            >
              <view :style="{ width: `${Math.max(0, Math.min(100, Number(item.score || 0)))}%` }" />
            </view>
          </view>
        </view>
      </view>
      <view class="flat-section">
        <view class="flat-head"
          ><text class="flat-title">站内提醒</text
          ><text
            v-if="profile.unreadCount"
            class="alert"
            >{{ profile.unreadCount }}</text
          ></view
        >
        <view
          v-for="item in notifications"
          :key="item.id"
          class="notification"
          role="button"
          tabindex="0"
          @keydown="activateButtonOnKey"
          @click="openNotification(item)"
          ><text>{{ item.title }}</text
          ><text class="muted">{{ item.body }}</text></view
        >
        <text
          v-if="!notifications.length"
          class="muted"
          >暂无新提醒</text
        >
        <button
          v-if="notifications.length"
          tabindex="0"
          role="button"
          class="link-button"
          @keydown="activateButtonOnKey"
          @click="readAll"
        >
          全部标记已读
        </button>
      </view>
    </template>
    <StudentPrimaryNav active="learning" />
  </view>
</template>

<script setup lang="ts">
import PblTaskList from '@/components/student/PblTaskList.vue'
import { activateButtonOnKey } from '@/components/ui/keyboard'
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import MedState from '@/components/ui/MedState.vue'
import StudentPrimaryNav from '@/components/ui/StudentPrimaryNav.vue'
import { requireRole } from '@/features/identity/public'
import { goDetail, goPrimary, relaunchTo, ROUTES } from '@/platform/navigation'
import { getLearningNotifications, getLearningProfile, markLearningNotificationsRead } from '@/features/learning/public'
import type { LearningNotification, LearningPlan, LearningProfile, LearningTask } from '@/types/learning'

const profile = ref<LearningProfile>({
  formalDimensions: [],
  recentAssessments: [],
  practiceMastery: {},
  unreadCount: 0,
})
const plan = ref<LearningPlan>()
const notifications = ref<LearningNotification[]>([])
const resources = [
  { view: 'cases' as const, title: '病例训练', description: '用结构化病例练习诊断思路' },
  { view: 'knowledge' as const, title: '知识地图', description: '按病理主题定位概念与关联' },
  { view: 'questions' as const, title: '练习题', description: '查看教师发布的讨论题与练习' },
]
const error = ref('')
const loading = ref(false)
const dimensions = computed(() => profile.value.formalDimensions.slice(0, 6))
const isFirstUse = computed(() => !dimensions.value.length && !plan.value)
const progress = computed(() => plan.value?.tasks.filter((task) => task.status === 'completed').length || 0)
const nextTask = computed(() => {
  const tasks = plan.value?.tasks || []
  return tasks.find((task) => task.status === 'in_progress') || tasks.find((task) => task.status === 'pending')
})
const dimensionLabels: Record<string, string> = {
  information_gathering: '信息采集',
  problem_representation: '问题表征',
  differential_diagnosis: '鉴别诊断',
  evidence_reasoning: '证据推理',
  test_selection: '检查合理性',
  management_safety: '处置与安全意识',
}
const stageLabels: Record<string, string> = {
  history: '病史采集',
  problem_representation: '问题表征',
  differential: '鉴别诊断',
  tests: '检查决策',
  management: '初步处置',
}
const dimensionLabel = (id: string) => dimensionLabels[id] || id
const taskInstruction = (task: LearningTask) => {
  const instruction = task.publicDefinition.instruction || '按顺序完成任务'
  return Object.entries(stageLabels).reduce(
    (formatted, [stageId, label]) => formatted.replace(new RegExp(`\\b${stageId}\\b`, 'g'), label),
    instruction,
  )
}
const statusLabel = (status: LearningTask['status']) =>
  status === 'completed' ? '已完成' : status === 'in_progress' ? '进行中' : '待开始'

async function load() {
  if (loading.value) return
  loading.value = true
  error.value = ''
  try {
    profile.value = await getLearningProfile()
    plan.value = profile.value.activePlan
    notifications.value = (await getLearningNotifications(true)).items
  } catch (e) {
    error.value = e instanceof Error ? e.message : '请稍后重试'
  } finally {
    loading.value = false
  }
}
function openCases() {
  goDetail(ROUTES.studentCases, { view: 'cases' })
}
function openReview() {
  goDetail(ROUTES.studentLearningReview)
}
function openResource(view: (typeof resources)[number]['view']) {
  goDetail(ROUTES.studentCases, { view })
}
function openChat() {
  goPrimary(ROUTES.studentPbl)
}
function openTask(task: LearningTask) {
  if (task.status === 'completed') return
  goDetail(ROUTES.studentLearningPlan, { planId: plan.value?.id, taskId: task.id })
}
function openNotification(item: LearningNotification) {
  if (item.entityType === 'pbl_session') {
    relaunchTo(ROUTES.studentPbl, { dialogueId: item.entityId })
    return
  }
  goDetail(ROUTES.studentLearningPlan, { planId: item.entityId })
}
async function readAll() {
  await markLearningNotificationsRead()
  notifications.value = []
  profile.value.unreadCount = 0
}
onShow(() => {
  if (requireRole('student')) void load()
})
</script>

<style scoped>
.page {
  padding: 28rpx 28rpx 170rpx;
  background: var(--med-page);
}
.onboarding,
.today-card,
.section {
  display: flex;
  margin-bottom: 22rpx;
  padding: 28rpx;
  flex-direction: column;
  gap: 14rpx;
}
.onboarding {
  padding: 32rpx 30rpx 28rpx;
}
.onboarding-title {
  max-width: 600rpx;
  color: var(--med-ink);
  font-size: 32rpx;
  font-weight: 800;
  line-height: 1.4;
}
.onboarding-steps {
  display: flex;
  margin-top: 12rpx;
  flex-direction: column;
}
.onboarding-step {
  display: flex;
  padding: 22rpx 0;
  align-items: flex-start;
  border-top: 1rpx solid var(--med-divider);
}
.onboarding-step > view {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 5rpx;
}
.step-index {
  display: flex;
  width: 48rpx;
  height: 48rpx;
  margin-right: 18rpx;
  align-items: center;
  justify-content: center;
  flex: none;
  color: var(--med-clinical);
  background: var(--med-wash);
  border-radius: 50%;
  font-family: var(--med-font-utility);
  font-size: 22rpx;
  font-weight: 700;
  line-height: 48rpx;
  text-align: center;
}
.step-title {
  color: var(--med-ink);
  font-size: 27rpx;
  font-weight: 700;
}
.onboarding-actions {
  display: flex;
  margin-top: 8rpx;
  align-items: center;
  flex-direction: column;
}
.text-action {
  min-height: 72rpx;
  margin: 6rpx 0 0;
  color: var(--med-clinical);
  background: transparent;
  font-size: 24rpx;
}
.title {
  display: block;
  font-size: 33rpx;
  font-weight: 800;
}
.flat-section {
  display: flex;
  margin-bottom: 24rpx;
  flex-direction: column;
  gap: 12rpx;
}
.flat-head {
  display: flex;
  padding-top: 16rpx;
  align-items: baseline;
  justify-content: space-between;
}
.flat-title {
  color: var(--med-navy);
  font-size: 26rpx;
  font-weight: 750;
  letter-spacing: 1rpx;
}
.muted {
  color: var(--med-muted);
  font-size: 24rpx;
  line-height: 1.5;
}
.dimension-grid {
  display: grid;
  margin-top: 10rpx;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  column-gap: 24rpx;
}
.dimension {
  display: flex;
  padding: 18rpx 0;
  flex-direction: column;
  color: var(--med-text-secondary);
  border-bottom: 1rpx solid var(--med-divider);
  font-size: 23rpx;
}
.dimension-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12rpx;
}
.score {
  color: var(--med-ink);
  font-family: var(--med-font-utility);
  font-size: 28rpx;
  font-weight: 750;
}
.score-track {
  height: 6rpx;
  margin-top: 12rpx;
  overflow: hidden;
  background: var(--med-divider);
  border-radius: 99rpx;
}
.score-track > view {
  height: 100%;
  background: var(--med-clinical);
  border-radius: inherit;
}
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.section-title {
  color: var(--med-navy);
  font-size: 30rpx;
  font-weight: 750;
}
.badge,
.alert {
  color: var(--med-clinical);
  font-weight: 700;
}
.next-task,
.plan-complete {
  display: flex;
  padding: 24rpx;
  flex-direction: column;
  gap: 10rpx;
  background: var(--med-wash);
  border-radius: var(--med-radius-md);
}
.next-task-label,
.evidence-label {
  color: var(--med-clinical);
  font-size: 22rpx;
  font-weight: 700;
}
.next-task-title {
  color: var(--med-ink);
  font-size: 30rpx;
  font-weight: 750;
  line-height: 1.4;
}
.notification {
  display: flex;
  padding: 16rpx 0;
  flex-direction: column;
  gap: 6rpx;
  border-bottom: 1rpx solid var(--med-divider);
}
.resource-grid {
  display: flex;
  flex-direction: column;
}
.resource-row {
  display: flex;
  width: 100%;
  min-height: 96rpx;
  margin: 0;
  padding: 18rpx 0;
  align-items: center;
  justify-content: space-between;
  gap: 18rpx;
  color: var(--med-text);
  background: transparent;
  border-top: 1rpx solid var(--med-divider);
  border-radius: 0;
  text-align: left;
}
.resource-row > view {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 5rpx;
}
.resource-title {
  color: var(--med-ink);
  font-size: 27rpx;
  font-weight: 700;
}
.resource-arrow {
  flex: none;
  color: var(--med-clinical);
  font-size: 34rpx;
}
.plan-progress {
  display: grid;
  margin-top: 8rpx;
  padding-top: 18rpx;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border-top: 1rpx solid var(--med-divider);
}
.progress-step {
  position: relative;
  display: flex;
  min-width: 0;
  align-items: center;
}
.progress-step + .progress-step::before {
  position: absolute;
  top: 24rpx;
  right: calc(100% - 4rpx);
  width: calc(100% - 48rpx);
  height: 2rpx;
  content: '';
  background: var(--med-divider);
}
.progress-index {
  display: flex;
  width: 48rpx;
  height: 48rpx;
  align-items: center;
  justify-content: center;
  flex: none;
  color: var(--med-muted);
  background: var(--med-paper);
  border: 1rpx solid var(--med-border);
  border-radius: 50%;
  font-family: var(--med-font-utility);
  font-size: 21rpx;
  line-height: 48rpx;
  text-align: center;
  z-index: 1;
}
.progress-step > view {
  display: flex;
  min-width: 0;
  margin-left: 10rpx;
  flex-direction: column;
  color: var(--med-text-secondary);
  font-size: 20rpx;
}
.progress-status {
  margin-top: 3rpx;
  color: var(--med-muted);
  font-size: 20rpx;
}
.progress-step.in_progress .progress-index {
  color: #fff;
  background: var(--med-clinical);
  border-color: var(--med-clinical);
}
.progress-step.in_progress .progress-status {
  color: var(--med-clinical);
}
.progress-step.completed .progress-index {
  color: var(--med-clinical);
  background: var(--med-wash);
  border-color: var(--med-wash);
}
.empty {
  align-items: flex-start;
}
.primary,
.secondary {
  width: 100%;
  min-height: 88rpx;
  margin-top: 8rpx;
}
.primary {
  color: #fff;
  background: var(--med-clinical);
}
.secondary {
  color: var(--med-clinical);
  background: var(--med-wash);
}
.link-button {
  padding: 0;
  color: var(--med-clinical);
  background: transparent;
  text-align: left;
  font-size: 23rpx;
}
.link-button::after {
  border: 0;
}
@media screen and (max-width: 360px) {
  .muted,
  .text-action,
  .progress-status {
    font-size: 12px;
  }

  .step-title,
  .next-task-label,
  .evidence-label {
    font-size: 13px;
  }

  .progress-step > view {
    font-size: 11px;
  }
}
@media screen and (min-width: 600px) and (max-width: 899px) {
  .page {
    padding: 24px 24px 120px;
  }

  .onboarding,
  .today-card,
  .section {
    width: 100%;
    max-width: 680px;
    padding: 32px;
    box-sizing: border-box;
    margin-right: auto;
    margin-left: auto;
  }

  .flat-section {
    width: 100%;
    max-width: 680px;
    margin-right: auto;
    margin-left: auto;
  }

  .onboarding-title {
    font-size: 26px;
  }

  .muted {
    font-size: 15px;
  }

  .onboarding-step {
    padding: 18px 0;
  }

  .step-index {
    width: 34px;
    height: 34px;
    margin-right: 16px;
    font-size: 14px;
    line-height: 34px;
  }

  .step-title {
    font-size: 17px;
  }

  .primary,
  .secondary {
    min-height: 52px;
    font-size: 17px;
  }

  .text-action {
    min-height: 44px;
    font-size: 14px;
  }
}
@media screen and (min-width: 900px) {
  .page {
    padding: 32px 32px 128px;
  }

  .onboarding {
    display: grid;
    width: 100%;
    max-width: 960px;
    padding: 44px;
    box-sizing: border-box;
    margin-right: auto;
    margin-left: auto;
    grid-template-columns: minmax(0, 0.88fr) minmax(420px, 1fr);
    align-items: start;
    column-gap: 64px;
    row-gap: 14px;
  }

  .onboarding .eyebrow-label,
  .onboarding-title,
  .onboarding > .muted,
  .onboarding-actions {
    grid-column: 1;
  }

  .onboarding-title {
    max-width: 420px;
    font-size: 28px;
    line-height: 1.3;
    text-wrap: balance;
  }

  .onboarding > .muted {
    font-size: 15px;
  }

  .onboarding-steps {
    margin-top: 0;
    grid-column: 2;
    grid-row: 1 / span 4;
  }

  .step-title {
    font-size: 17px;
  }

  .onboarding-step .muted {
    font-size: 14px;
  }

  .step-index {
    width: 34px;
    height: 34px;
    margin-right: 16px;
    font-size: 14px;
    line-height: 34px;
  }

  .onboarding-actions {
    margin-top: 12px;
    align-items: stretch;
  }

  .onboarding-actions .primary {
    min-height: 52px;
    font-size: 17px;
  }

  .text-action {
    min-height: 44px;
    font-size: 14px;
  }

  .today-card,
  .section {
    width: 100%;
    max-width: 920px;
    box-sizing: border-box;
    margin-right: auto;
    margin-left: auto;
  }

  .flat-section {
    width: 100%;
    max-width: 920px;
    margin-right: auto;
    margin-left: auto;
  }

  .dimension-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
