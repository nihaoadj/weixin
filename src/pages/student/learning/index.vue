<template>
  <view class="safe-page page">
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
    <MedState
      v-else-if="isFirstUse"
      variant="first-use"
      icon="report"
      title="完成首次病例训练，建立能力画像"
      description="提交一份完整病例评估后，系统会生成六维能力画像和三项个性化训练计划。"
      action-label="进入病例训练"
      secondary-action-label="先去医学问答"
      @action="openCases"
      @secondary-action="openChat"
    />
    <template v-else>
      <view class="hero card">
        <text class="eyebrow-label">PERSONALIZED PRACTICE</text>
        <text class="title">我的临床能力画像</text>
        <text class="muted">正式病例成绩与练习掌握度分开记录。</text>
        <view class="dimension-grid">
          <view
            v-for="item in dimensions"
            :key="String(item.dimension_id)"
            class="dimension"
          >
            <text>{{ item.label || item.dimension_id }}</text>
            <text class="score">{{ Number(item.score || 0).toFixed(0) }}</text>
          </view>
        </view>
      </view>
      <view
        v-if="plan"
        class="card section"
      >
        <view class="section-head"
          ><text class="section-title">今日训练</text><text class="badge">{{ progress }}/3</text></view
        >
        <text class="muted">目标维度：{{ plan.targetDimensionIds.join('、') }}</text>
        <view
          v-for="task in plan.tasks"
          :key="task.id"
          class="task-row"
          @click="openTask(task)"
        >
          <view
            ><text>{{ task.position }}. {{ task.publicDefinition.title || task.taskType }}</text
            ><text class="muted">{{ task.publicDefinition.instruction || '按顺序完成任务' }}</text></view
          >
          <text :class="['task-status', task.status]">{{ statusLabel(task.status) }}</text>
        </view>
        <button
          v-if="plan.status === 'completed'"
          class="secondary"
          @click="openReview"
        >
          查看训练复盘
        </button>
      </view>
      <view
        v-else
        class="card section empty"
      >
        <text class="section-title">还没有进行中的计划</text>
        <text class="muted">完成一份完整病例评估后，将自动生成三项训练。</text>
        <button
          class="primary"
          @click="openCases"
        >
          进入病例训练
        </button>
      </view>
      <view class="card section">
        <view class="section-head"
          ><text class="section-title">站内提醒</text
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
          class="link-button"
          @click="readAll"
        >
          全部标记已读
        </button>
      </view>
      <view class="card section"
        ><text class="section-title">临床病例训练</text><text class="muted">待完成病例</text
        ><button
          class="secondary"
          @click="openCases"
        >
          查看病例列表
        </button></view
      >
    </template>
    <view class="nav"><StudentNav active="learning" /></view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import MedState from '@/components/ui/MedState.vue'
import StudentNav from '@/components/ui/StudentNav.vue'
import { requireRole } from '@/services/auth'
import { goDetail, goPrimary, ROUTES } from '@/services/navigation'
import {
  getLearningNotifications,
  getLearningProfile,
  markLearningNotificationsRead,
} from '@/services/personalizedLearning'
import type { LearningNotification, LearningPlan, LearningProfile, LearningTask } from '@/types/learning'

const profile = ref<LearningProfile>({
  formalDimensions: [],
  recentAssessments: [],
  practiceMastery: {},
  unreadCount: 0,
})
const plan = ref<LearningPlan>()
const notifications = ref<LearningNotification[]>([])
const error = ref('')
const loading = ref(false)
const dimensions = computed(() => profile.value.formalDimensions.slice(0, 6))
const isFirstUse = computed(() => !dimensions.value.length && !plan.value)
const progress = computed(() => plan.value?.tasks.filter((task) => task.status === 'completed').length || 0)
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
  goPrimary(ROUTES.studentCases)
}
function openReview() {
  uni.navigateTo({ url: '/pages/student/learning/review' })
}
function openChat() {
  goPrimary(ROUTES.studentChat)
}
function openTask(task: LearningTask) {
  if (task.status === 'completed') return
  goDetail('/pages/student/learning/plan', { planId: plan.value?.id, taskId: task.id })
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
  background: #f4f8fa;
}
.hero,
.section {
  display: flex;
  margin-bottom: 22rpx;
  padding: 30rpx;
  flex-direction: column;
  gap: 14rpx;
}
.hero {
  background: linear-gradient(135deg, #0b2239, #12647a);
  color: #fff;
}
.title {
  display: block;
  font-size: 40rpx;
  font-weight: 800;
}
.muted {
  color: #718096;
  font-size: 22rpx;
  line-height: 1.5;
}
.hero .muted {
  color: #d8edf0;
}
.dimension-grid {
  display: grid;
  margin-top: 10rpx;
  grid-template-columns: repeat(3, 1fr);
  gap: 14rpx;
}
.dimension {
  display: flex;
  padding: 18rpx 10rpx;
  flex-direction: column;
  gap: 8rpx;
  border-radius: 16rpx;
  background: rgba(255, 255, 255, 0.12);
  font-size: 21rpx;
}
.score {
  font-size: 34rpx;
  font-weight: 750;
}
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.section-title {
  color: #0b2239;
  font-size: 30rpx;
  font-weight: 750;
}
.badge,
.alert {
  color: #087f8c;
  font-weight: 700;
}
.task-row,
.notification {
  display: flex;
  padding: 16rpx 0;
  flex-direction: column;
  gap: 6rpx;
  border-bottom: 1rpx solid #e5edf0;
}
.task-row {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}
.task-row > view {
  display: flex;
  max-width: 76%;
  flex-direction: column;
  gap: 5rpx;
}
.task-status {
  font-size: 22rpx;
  color: #a0aec0;
}
.task-status.in_progress {
  color: #087f8c;
}
.task-status.completed {
  color: #2f855a;
}
.empty {
  align-items: flex-start;
}
.primary,
.secondary {
  width: 100%;
  margin-top: 8rpx;
}
.primary {
  color: #fff;
  background: #087f8c;
}
.secondary {
  color: #087f8c;
  background: #e6f7f5;
}
.link-button {
  padding: 0;
  color: #087f8c;
  background: transparent;
  text-align: left;
  font-size: 23rpx;
}
.link-button::after {
  border: 0;
}
.nav {
  position: fixed;
  right: 0;
  bottom: 0;
  left: 0;
}
</style>
