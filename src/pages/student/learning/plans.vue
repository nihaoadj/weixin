<template>
  <view class="page">
    <view
      v-if="denied"
      class="state error"
      role="alert"
      >学生身份不可用，请重新登录。</view
    >
    <view
      class="tabs"
      role="group"
      aria-label="计划状态"
    >
      <button
        :class="{ active: status === 'active' }"
        :aria-pressed="status === 'active'"
        @click="select('active')"
      >
        待完成
      </button>
      <button
        :class="{ active: status === 'completed' }"
        :aria-pressed="status === 'completed'"
        @click="select('completed')"
      >
        已完成
      </button>
    </view>
    <view
      v-if="error && !items.length"
      class="state error"
      role="alert"
    >
      <text>{{ error }}</text
      ><button @click="load(true)">重新加载</button>
    </view>
    <view
      v-else-if="loading && !items.length"
      class="state"
      role="status"
      >正在读取学习计划…</view
    >
    <view
      v-else-if="!items.length"
      class="state empty"
    >
      <text>{{
        status === 'active'
          ? '目前没有待完成的研讨学习计划。完成一次四阶段研讨后，计划会自动出现在这里。'
          : '还没有已完成的学习计划。'
      }}</text>
      <button
        v-if="status === 'active'"
        class="primary"
        @click="goPbl"
      >
        开始研讨
      </button>
    </view>
    <view
      v-for="item in items"
      :key="item.id"
      class="plan-row"
    >
      <button
        class="plan-card"
        @click="open(item.id)"
      >
        <view class="row-top"
          ><text class="kind">{{ item.sourceKind === 'classroom' ? '课堂研讨' : '自主研讨' }}</text
          ><text class="date">{{ formatDate(item.updatedAt) }}</text></view
        >
        <text class="title">{{ item.title }}</text>
        <text class="source">{{ item.sessionLocator }}</text>
        <text class="goals">主要目标：{{ goalLabels(item.goalPointCodes) || '以计划详情为准' }}</text>
        <view class="row-bottom"
          ><text>已完成 {{ item.progress.completedSteps }}/{{ item.progress.totalSteps }} 个学习步骤</text
          ><text>{{ nextLabel(item) }} ›</text></view
        >
      </button>
    </view>
    <view
      v-if="error && items.length"
      class="inline-error"
      role="alert"
      ><text>{{ error }}</text
      ><button @click="loadMore">重试加载</button></view
    >
    <button
      v-else-if="items.length < total"
      class="more"
      :disabled="loading"
      @click="loadMore"
    >
      {{ loading ? '正在加载…' : '加载更多' }}
    </button>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onBackPress, onLoad, onShow } from '@dcloudio/uni-app'
import {
  getKnowledgeCatalog,
  getLearningRoutes,
  type KnowledgePoint,
  type LearningRouteSummary,
  learningGoalLabel,
} from '@/features/learning/public'
import { getSession, requireRole } from '@/features/identity/public'
import { goDetail, handleBackPress, ROUTES } from '@/platform/navigation'

const status = ref<'active' | 'completed'>('active')
const items = ref<LearningRouteSummary[]>([])
const catalog = ref<KnowledgePoint[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
let request = 0
let identity = ''
let initialized = false
let denied = false

function select(value: 'active' | 'completed') {
  if (status.value !== value) {
    status.value = value
    void load(true)
  }
}
function open(id: string) {
  goDetail(ROUTES.studentLearningPlanDetail, { routeId: id })
}
function goPbl() {
  goDetail(ROUTES.studentPbl)
}
function formatDate(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleDateString('zh-CN')
}
function goalLabels(codes: string[]) {
  return codes.map((code) => learningGoalLabel(code, catalog.value)).join('、')
}
async function loadCatalog(requestIdentity: string) {
  try {
    const points = await getKnowledgeCatalog()
    if (getSession()?.role === 'student' && getSession()?.openid === requestIdentity) catalog.value = points
  } catch {
    if (getSession()?.openid === requestIdentity) catalog.value = []
  }
}
function nextLabel(item: LearningRouteSummary) {
  if (item.nextAction === 'wait_teacher') return '等待教师开放测试'
  if (item.nextAction === 'wait_generation') return '计划生成中'
  if (item.nextAction === 'view_result') return '查看学习结果'
  if (item.nextAction === 'wait_grade') return '查看判分进度'
  if (item.nextAction === 'test') return '开始最终测试'
  if (item.nextAction === 'case') return '继续病例学习'
  return item.nextAction === 'retry_route' ? '计划需要重试' : '继续资料学习'
}
async function load(reset = true) {
  const session = getSession()
  if (session?.role !== 'student' || !session.openid) {
    denied = true
    items.value = []
    total.value = 0
    return
  }
  denied = false
  if (!initialized || identity !== session.openid) {
    initialized = true
    identity = session.openid
    request += 1
    items.value = []
    total.value = 0
    error.value = ''
    loading.value = false
  }
  if (loading.value) return
  const token = ++request
  const requestIdentity = identity
  void loadCatalog(requestIdentity)
  loading.value = true
  error.value = ''
  const offset = reset ? 0 : items.value.length
  try {
    const page = await getLearningRoutes(status.value, 20, offset)
    if (token !== request || denied || getSession()?.role !== 'student' || getSession()?.openid !== requestIdentity)
      return
    if (reset) items.value = page.items
    else {
      const existing = new Set(items.value.map((x) => x.id))
      if (!page.items.length || page.items.some((x) => existing.has(x.id)))
        throw new Error('计划列表分页状态已变化，请重新加载。')
      items.value = [...items.value, ...page.items]
    }
    total.value = page.total
  } catch (reason) {
    if (token === request && getSession()?.openid === requestIdentity)
      error.value = reason instanceof Error ? reason.message : '学习计划加载失败，请稍后重试。'
  } finally {
    if (token === request && getSession()?.openid === requestIdentity) loading.value = false
  }
}
function loadMore() {
  if (!loading.value && items.value.length < total.value) void load(false)
}
onLoad(() => {
  requireRole('student')
})
onShow(() => {
  if (!requireRole('student')) {
    denied = true
    request += 1
    items.value = []
    total.value = 0
    loading.value = false
    error.value = ''
    return
  }
  denied = false
  void load(true)
})
onBackPress(({ from }) => handleBackPress(from, ROUTES.studentLearning))
</script>

<style scoped>
.page {
  min-height: 100vh;
  box-sizing: border-box;
  padding: 20rpx 24rpx calc(32rpx + env(safe-area-inset-bottom));
  color: #203a69;
  background: #f7fbfd;
}
.tabs {
  display: flex;
  gap: 24rpx;
  margin: 0 auto 22rpx;
  max-width: 920px;
  border-bottom: 1px solid #dce8ef;
}
.tabs button {
  min-height: 82rpx;
  margin: 0;
  padding: 0 10rpx;
  color: #65768e;
  background: transparent;
  border-radius: 0;
  font-size: 28rpx;
}
.tabs button.active {
  color: #057f91;
  border-bottom: 5rpx solid #12aab3;
  font-weight: 700;
}
.plan-row,
.state,
.more,
.inline-error {
  max-width: 920px;
  margin: 0 auto 18rpx;
}
.plan-card {
  display: flex;
  width: 100%;
  box-sizing: border-box;
  flex-direction: column;
  gap: 10rpx;
  padding: 22rpx 24rpx;
  text-align: left;
  color: inherit;
  background: #fff;
  border: 1px solid #dce8ef;
  border-radius: 16rpx;
}
.row-top,
.row-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16rpx;
}
.kind {
  color: #087f91;
  font-size: 23rpx;
  font-weight: 700;
}
.date,
.source {
  color: #718198;
  font-size: 23rpx;
}
.title {
  color: #142c58;
  font-size: 31rpx;
  font-weight: 700;
}
.goals,
.row-bottom {
  color: #536781;
  font-size: 24rpx;
  line-height: 1.55;
}
.row-bottom {
  padding-top: 8rpx;
  border-top: 1px solid #edf2f5;
}
.row-bottom text:last-child {
  color: #057f91;
  font-weight: 700;
}
.state {
  display: flex;
  min-height: 220rpx;
  box-sizing: border-box;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  gap: 20rpx;
  padding: 30rpx;
  color: #61738c;
  text-align: center;
  background: #fff;
  border: 1px solid #e0eaf0;
  border-radius: 16rpx;
  line-height: 1.65;
}
.error,
.inline-error {
  color: #9c3f4b;
}
.state button,
.inline-error button {
  min-height: 76rpx;
  padding: 0 28rpx;
  color: #087f91;
  background: #eaf7f8;
  border-radius: 12rpx;
}
.state button.primary {
  color: #fff;
  background: #087f91;
}
.more {
  display: block;
  min-height: 76rpx;
  color: #087f91;
  background: #eaf7f8;
  border-radius: 12rpx;
}
.inline-error {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16rpx;
  padding: 16rpx;
  font-size: 24rpx;
}
</style>
