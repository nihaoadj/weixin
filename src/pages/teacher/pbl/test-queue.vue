<template>
  <view class="test-queue-page safe-page">
    <view class="queue-heading">
      <text class="queue-eyebrow">课堂最终测试</text>
      <text class="queue-title">测试待办</text>
      <text class="queue-description">选择一份测试，进入详情核对、退改或开放。</text>
    </view>
    <MedState
      v-if="accessDenied"
      variant="error"
      icon="history"
      title="教师身份已变化"
      description="请重新登录教师账号。"
    />
    <MedState
      v-else-if="!scopeAllowed"
      :variant="error ? 'error' : 'loading'"
      icon="retry"
      :title="error || '正在读取班级范围'"
      description="仅显示当前教师有权处理的课堂测试。"
      :action-label="error ? '重试' : undefined"
      @action="refresh"
    />
    <template v-else>
      <picker
        :range="classOptions"
        range-key="name"
        @change="changeClass"
      >
        <view class="queue-scope"
          >{{ classes.find((item) => item.id === classId)?.name || '全部负责班级' }} <text>⌄</text></view
        >
      </picker>
      <TeacherFinalTestReviewQueue
        :key="identityGeneration"
        ref="workspace"
        :class-id="classId"
        :session-id="sessionId"
        :initial-kind="reviewKind"
        @kind-change="reviewKind = $event"
        @open-final-test="openFinalTest"
      />
    </template>
    <button
      class="queue-back"
      @click="back"
    >
      返回待办
    </button>
  </view>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { onBackPress, onLoad, onShow } from '@dcloudio/uni-app'
import MedState from '@/components/ui/MedState.vue'
import TeacherFinalTestReviewQueue from '@/features/learning/presentation/TeacherFinalTestReviewQueue.vue'
import { useTeacherRootScope } from '@/components/teacher/useTeacherRootScope'
import { getSession } from '@/features/identity/public'
import { backOrRoute, goDetail, handleBackPress, ROUTES } from '@/platform/navigation'
import { parseTeacherWorkspaceTarget, type TeacherReviewKind } from '@/platform/navigation/teacher'

const {
  classes,
  classId,
  error,
  accessDenied,
  identityGeneration,
  scopeAllowed,
  setInitialClass,
  selectClass,
  refreshScope,
} = useTeacherRootScope('pbl')
const workspace = ref<{ refresh(): Promise<void> }>()
const sessionId = ref<number | string>()
const reviewKind = ref<TeacherReviewKind>()
let queueIdentity: string | undefined
const classOptions = computed(() => [{ id: undefined, name: '全部负责班级' }, ...classes.value])
onLoad((query) => {
  const target = parseTeacherWorkspaceTarget({ ...query, tab: 'pbl', section: 'diagnostics' })
  if (target.workspace !== 'pbl') return
  setInitialClass(target.classId)
  sessionId.value = target.sessionId
  reviewKind.value = target.reviewKind
})
function changeClass(event: { detail: { value: string } }) {
  sessionId.value = undefined
  selectClass(classOptions.value[Number(event.detail.value)]?.id)
}
async function refresh() {
  const actor = getSession()
  const currentIdentity = actor?.role === 'teacher' ? actor.openid : undefined
  if (queueIdentity && queueIdentity !== currentIdentity) {
    sessionId.value = undefined
    reviewKind.value = undefined
  }
  queueIdentity = currentIdentity
  if (!(await refreshScope())) return
  await nextTick()
  await workspace.value?.refresh()
}
function openFinalTest(finalTestId: string) {
  goDetail(ROUTES.teacherLearningFinalTest, {
    finalTestId,
    classId: classId.value,
    sessionId: sessionId.value,
    returnSection: 'diagnostics',
    reviewKind: reviewKind.value,
  })
}
function back() {
  backOrRoute(ROUTES.teacherPbl)
}
onShow(refresh)
onBackPress(({ from }) => handleBackPress(from, ROUTES.teacherPbl))
</script>

<style scoped>
.test-queue-page {
  min-height: 100vh;
  box-sizing: border-box;
  padding: 32rpx 28rpx calc(40rpx + env(safe-area-inset-bottom));
  background: var(--med-page);
  color: var(--med-text);
}
.queue-heading {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
  margin-bottom: 28rpx;
}
.queue-eyebrow {
  color: var(--med-clinical);
  font-size: 24rpx;
}
.queue-title {
  font-size: 40rpx;
  font-weight: 700;
}
.queue-description {
  font-size: 26rpx;
  color: var(--med-muted);
  line-height: 1.6;
}
.queue-scope {
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 88rpx;
  padding: 0 24rpx;
  margin-bottom: 24rpx;
  border: 1rpx solid var(--med-border);
  border-radius: 20rpx;
  background: var(--med-surface);
  font-size: 28rpx;
}
.queue-back {
  margin-top: 32rpx;
  min-height: 44px;
  color: var(--med-muted);
  background: transparent;
  font-size: 26rpx;
}
.queue-back::after {
  border: 0;
}
@media screen and (min-width: 600px) {
  .test-queue-page {
    max-width: 920px;
    margin: 0 auto;
  }
}
</style>
