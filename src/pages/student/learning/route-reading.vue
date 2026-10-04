<template>
  <view class="page">
    <view
      v-if="error && !reading"
      class="state error"
      role="alert"
      ><text>{{ error }}</text
      ><button @click="load">重新加载</button></view
    >
    <view
      v-else-if="loading && !reading"
      class="state"
      role="status"
      >正在读取学习资料…</view
    >
    <template v-else-if="reading">
      <view class="top"
        ><text class="eyebrow">资料学习 · 第 {{ reading.step.position }} 步</text
        ><text class="title">{{ reading.step.title }}</text></view
      >
      <view class="panel guide"
        ><text class="panel-title">学习提示</text><text class="body">{{ reading.aiGuide }}</text></view
      >
      <view
        v-for="(section, index) in reading.sections"
        :key="`${index}-${section.title}`"
        class="panel"
        ><text class="panel-title">{{ section.title }}</text
        ><text class="body">{{ section.text }}</text></view
      >
      <view
        v-if="reading.sources.length"
        class="panel"
        ><text class="panel-title">资料来源</text
        ><view
          v-for="source in reading.sources"
          :key="source.id"
          class="source"
          ><text class="source-title">{{ source.title }}</text
          ><text class="muted"
            >{{ source.institution }}<template v-if="source.version"> · {{ source.version }}</template></text
          ></view
        ></view
      >
      <view
        v-if="reading.learningPoints.length"
        class="panel"
        ><text class="panel-title">完成后检查</text
        ><text
          v-for="point in reading.learningPoints"
          :key="point"
          class="point"
          >• {{ point }}</text
        ></view
      >
      <view class="progress-note"
        >资料学习时长：{{ Math.floor(reading.readingProgress.accumulatedSeconds / 60) }} 分
        {{ reading.readingProgress.accumulatedSeconds % 60 }} 秒</view
      >
      <view
        v-if="error"
        class="inline-error"
        role="alert"
        >{{ error }}</view
      >
      <button
        class="primary"
        :disabled="busy || reading.step.status === 'completed'"
        @click="complete"
      >
        {{ reading.step.status === 'completed' ? '本步骤已完成' : busy ? '正在完成…' : '完成资料学习' }}
      </button>
      <button
        class="quiet"
        @click="back"
      >
        返回学习计划
      </button>
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onBackPress, onHide, onLoad, onShow, onUnload } from '@dcloudio/uni-app'
import {
  completeRouteReading,
  createLearningRequestId,
  getLearningRouteStep,
  saveRouteReadingProgress,
  type LearningRouteReading,
} from '@/features/learning/public'
import { getSession, requireRole } from '@/features/identity/public'
import { backOrRoute, handleBackPress, ROUTES } from '@/platform/navigation'

const reading = ref<LearningRouteReading>()
const loading = ref(false)
const busy = ref(false)
const error = ref('')
let routeId = ''
let stepId = ''
let valid = false
let identity = ''
let visible = false
let contextVersion = 0
let requestVersion = 0
let completionRequestId = ''
let timer: ReturnType<typeof setTimeout> | undefined
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

function back() {
  backOrRoute(ROUTES.studentLearningPlanDetail, { routeId })
}
function stopTimer() {
  if (timer) clearTimeout(timer)
  timer = undefined
}
function current(requestedIdentity = identity, context = contextVersion) {
  return (
    valid &&
    context === contextVersion &&
    requireRole('student') &&
    getSession()?.role === 'student' &&
    getSession()?.openid === requestedIdentity
  )
}
async function progress(action: 'start' | 'heartbeat' | 'pause') {
  if (!current() || !reading.value || (busy.value && action !== 'pause')) return
  const requestedIdentity = identity
  const context = contextVersion
  const step = reading.value.step.id
  const token = reading.value.readingProgress.leaseToken
  if (action !== 'start' && !token) return
  try {
    const value = await saveRouteReadingProgress(stepId, action, createLearningRequestId(`reading-${action}`), token)
    if (!current(requestedIdentity, context) || !reading.value || reading.value.step.id !== step) return
    reading.value.readingProgress = value
  } catch (reason) {
    if (current(requestedIdentity, context) && reading.value?.step.id === step)
      error.value = reason instanceof Error ? reason.message : '资料进度同步失败。'
  }
}
async function heartbeat() {
  stopTimer()
  if (!visible || !current()) return
  await progress(reading.value?.readingProgress.leaseToken ? 'heartbeat' : 'start')
  if (visible && current())
    timer = setTimeout(() => {
      void heartbeat()
    }, 15_000)
}
async function pause() {
  visible = false
  stopTimer()
  if (reading.value?.readingProgress.leaseToken) await progress('pause')
}
async function load() {
  const session = getSession()
  if (!valid || !requireRole('student') || session?.role !== 'student' || !session.openid) return
  if (identity !== session.openid) resetIdentity(session.openid)
  const requestedIdentity = session.openid
  const context = contextVersion
  const token = ++requestVersion
  loading.value = true
  error.value = ''
  try {
    const value = await getLearningRouteStep(stepId)
    if (!current(requestedIdentity, context) || token !== requestVersion) return
    if (value.routeId !== routeId || value.step.id !== stepId || value.step.kind !== 'reading')
      throw new Error('该资料不属于当前学习路线。')
    reading.value = value
  } catch (reason) {
    if (current(requestedIdentity, context) && token === requestVersion)
      error.value = reason instanceof Error ? reason.message : '资料加载失败。'
  } finally {
    if (current(requestedIdentity, context) && token === requestVersion) loading.value = false
  }
}
async function complete() {
  if (!reading.value || busy.value || !current()) return
  const requestedIdentity = identity
  const context = contextVersion
  if (!completionRequestId) completionRequestId = createLearningRequestId('reading-complete')
  busy.value = true
  error.value = ''
  try {
    await progress('pause')
    await completeRouteReading(stepId, completionRequestId)
    if (!current(requestedIdentity, context)) return
    completionRequestId = ''
    back()
  } catch (reason) {
    if (current(requestedIdentity, context))
      error.value = reason instanceof Error ? reason.message : '无法完成资料学习。'
  } finally {
    if (current(requestedIdentity, context)) busy.value = false
  }
}
function resetIdentity(nextIdentity: string) {
  if (identity === nextIdentity) return
  identity = nextIdentity
  contextVersion += 1
  requestVersion += 1
  stopTimer()
  reading.value = undefined
  error.value = ''
  loading.value = false
  busy.value = false
  completionRequestId = ''
}
onLoad((query) => {
  routeId = String(query?.routeId || '')
  stepId = String(query?.stepId || '')
  valid = uuid.test(routeId) && uuid.test(stepId)
  if (!valid) error.value = '学习步骤链接无效。'
  if (requireRole('student')) identity = getSession()?.openid || ''
})
onShow(() => {
  const session = getSession()
  if (!requireRole('student') || session?.role !== 'student' || !session.openid) {
    visible = false
    resetIdentity('')
    return
  }
  resetIdentity(session.openid)
  visible = true
  if (!reading.value)
    void load().then(() => {
      if (visible && reading.value) void heartbeat()
    })
  else void heartbeat()
})
onHide(() => {
  void pause()
  requestVersion += 1
  loading.value = false
})
onUnload(() => {
  void pause()
  requestVersion += 1
  loading.value = false
})
onBackPress(({ from }) => handleBackPress(from, ROUTES.studentLearningPlanDetail, { routeId }))
</script>

<style scoped>
.page {
  min-height: 100vh;
  box-sizing: border-box;
  padding: 24rpx 24rpx calc(36rpx + env(safe-area-inset-bottom));
  background: #f7fbfd;
  color: #20385f;
}
.top,
.panel,
.primary,
.quiet,
.state,
.inline-error,
.progress-note {
  max-width: 920px;
  margin-left: auto;
  margin-right: auto;
}
.top {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
  margin-bottom: 22rpx;
}
.eyebrow {
  color: #09838e;
  font-size: 23rpx;
  font-weight: 700;
}
.title {
  color: #142d5a;
  font-size: 36rpx;
  font-weight: 700;
  line-height: 1.4;
}
.panel {
  box-sizing: border-box;
  margin-bottom: 18rpx;
  padding: 24rpx;
  background: #fff;
  border: 1px solid #dce8ef;
  border-radius: 16rpx;
}
.guide {
  border-left: 5rpx solid #08a3ad;
}
.panel-title {
  display: block;
  margin-bottom: 12rpx;
  color: #193762;
  font-size: 27rpx;
  font-weight: 700;
}
.body,
.point {
  display: block;
  color: #536b83;
  font-size: 25rpx;
  line-height: 1.8;
  white-space: pre-wrap;
}
.point + .point {
  margin-top: 8rpx;
}
.source {
  display: flex;
  flex-direction: column;
  gap: 5rpx;
  padding: 12rpx 0;
  border-bottom: 1px solid #edf2f5;
}
.source:last-child {
  border: 0;
}
.source-title {
  color: #29466c;
  font-size: 24rpx;
}
.muted,
.progress-note {
  color: #7a8b9c;
  font-size: 22rpx;
}
.progress-note {
  margin-top: 14rpx;
  text-align: center;
}
.primary,
.quiet {
  display: block;
  width: 100%;
  min-height: 84rpx;
  margin-top: 16rpx;
  border-radius: 12rpx;
  font-size: 27rpx;
  font-weight: 700;
}
.primary {
  color: #fff;
  background: #078d9b;
}
.quiet {
  color: #087f91;
  background: #eaf7f8;
}
.state {
  display: flex;
  min-height: 200rpx;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  gap: 16rpx;
  padding: 30rpx;
  color: #657991;
  background: #fff;
  border-radius: 16rpx;
  text-align: center;
}
.state button {
  color: #087f91;
  background: #eaf7f8;
}
.error,
.inline-error {
  color: #a0444a;
}
.inline-error {
  margin-top: 10rpx;
  font-size: 23rpx;
}
</style>
