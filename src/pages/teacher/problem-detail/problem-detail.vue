<template>
  <view class="safe-page page page-enter">
    <MedDetailSkeleton
      v-if="loading"
      label="正在加载病例…"
    />
    <MedState
      v-else-if="loadError"
      variant="error"
      icon="retry"
      title="病例加载失败"
      :description="loadError"
      action-label="重新加载"
      secondary-action-label="返回内容列表"
      @action="loadProblem(problemId)"
      @secondary-action="back"
    />
    <MedState
      v-else-if="!problem"
      icon="book"
      title="病例不存在"
      description="内容可能已移除，或当前身份无法查看。"
      action-label="返回内容列表"
      @action="back"
    />
    <view
      v-else
      class="detail-card"
    >
      <text class="type">教学病例</text>
      <text
        class="title"
        role="heading"
        aria-level="1"
        >{{ problem.title }}</text
      >
      <text
        class="section-label"
        role="heading"
        aria-level="2"
        >病例简介</text
      >
      <text
        class="description"
        user-select
        >{{ problem.description || '暂无详细描述' }}</text
      >
      <view class="info"
        ><text>创建日期</text><text>{{ problem.time }}</text></view
      >
      <button
        v-if="problem.allowedActions?.includes('edit')"
        class="primary-button edit"
        role="button"
        tabindex="0"
        hover-class="is-pressed"
        :hover-start-time="0"
        :hover-stay-time="80"
        :disabled="deleting"
        @keydown="activateButtonOnKey"
        @click="edit"
      >
        编辑病例
      </button>
      <button
        v-if="problem.allowedActions?.includes('delete')"
        class="delete-button"
        :disabled="deleting"
        @click="confirmDelete"
      >
        {{ deleting ? '正在删除…' : '删除病例' }}
      </button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'
import { activateButtonOnKey } from '@/components/ui/keyboard'
import MedState from '@/components/ui/MedState.vue'
import MedDetailSkeleton from '@/components/ui/MedDetailSkeleton.vue'
import { onBackPress, onLoad, onShow } from '@dcloudio/uni-app'
import { getSession, requireRole } from '@/features/identity/public'
import { backOrRoute, goDetail, handleBackPress, ROUTES } from '@/platform/navigation'
import { teacherContentReturnParams } from '@/platform/navigation/teacher'
let contentReturn = teacherContentReturnParams({}, 'cases')
import { deleteGuidedCaseAsync, findProblemAsync } from '@/features/content/public'
import type { Problem } from '@/types/domain'

const problem = ref<Problem | null>(null)
const loading = ref(false)
const loadError = ref('')
const deleting = ref(false)
let problemId = ''
let actor: string | undefined
let disposed = false
let sourceQuery: Record<string, string | undefined> = {}
onBeforeUnmount(() => {
  disposed = true
})
const current = () => !disposed && getSession()?.role === 'teacher' && getSession()?.openid === actor
function back() {
  backOrRoute(ROUTES.teacherContent, contentReturn)
}
onLoad((options) => {
  sourceQuery = options || {}
  contentReturn = teacherContentReturnParams(options, 'cases')
  if (!requireRole('teacher')) return
  actor = getSession()?.openid
  const id = typeof options?.id === 'string' ? options.id : ''
  problemId = id
  void loadProblem(id)
})
onShow(() => {
  if (actor && !current()) {
    problem.value = null
    loading.value = false
    deleting.value = false
    loadError.value = '教师账号已变更，请返回内容列表。'
  }
})
onBackPress(({ from }) => {
  if (from === 'navigateBack') return false
  if (deleting.value) return true
  return handleBackPress(from, ROUTES.teacherContent, contentReturn)
})

async function loadProblem(id: string) {
  if (loading.value || !current()) return
  loading.value = true
  loadError.value = ''
  try {
    const result = (await findProblemAsync(id)) || null
    if (!current()) return
    problem.value = result
    if (result && result.contentType !== 'guided_case') {
      problem.value = null
      return
    }
    if (result) contentReturn = teacherContentReturnParams(sourceQuery, 'cases')
  } catch (error) {
    if (current()) loadError.value = error instanceof Error ? error.message : '暂时无法获取内容，请重试。'
  } finally {
    if (current()) loading.value = false
  }
}
function edit() {
  if (!deleting.value && current() && problem.value?.allowedActions?.includes('edit'))
    goDetail(ROUTES.teacherCaseEdit, {
      id: problem.value.id,
      ...contentReturn,
    })
}
function confirmDelete() {
  const item = problem.value
  if (!item || deleting.value || !current() || !item.allowedActions?.includes('delete')) return
  deleting.value = true
  uni.showModal({
    title: '删除这个病例？',
    content: '删除后不能再选入新课堂，已有课堂与历史作答仍会保留。',
    confirmText: '删除',
    success: ({ confirm }) => {
      if (!current()) return
      if (confirm) void removeCase(item.id)
      else deleting.value = false
    },
    fail: () => {
      if (current()) deleting.value = false
    },
  })
}
async function removeCase(id: string) {
  if (!current()) return
  try {
    await deleteGuidedCaseAsync(id)
    if (!current()) return
    problem.value = null
    uni.showToast({ title: '病例已删除', icon: 'success' })
    back()
  } catch (reason) {
    if (current())
      uni.showToast({ title: reason instanceof Error ? reason.message : '删除失败，病例仍保留。', icon: 'none' })
  } finally {
    if (current()) deleting.value = false
  }
}
</script>

<style scoped>
.page {
  padding: 40rpx 32rpx;
  background: var(--med-surface);
}
.detail-card {
  max-width: 760px;
  margin: 0 auto;
}
.meta,
.info {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.type {
  color: var(--med-brand);
  font-size: 22rpx;
}
.status {
  color: var(--med-muted);
  font-size: 23rpx;
}
.title {
  display: block;
  margin-top: 30rpx;
  padding-bottom: 32rpx;
  border-bottom: 2rpx solid var(--med-ink);
  font-size: 44rpx;
  font-weight: 750;
  line-height: 1.5;
  overflow-wrap: anywhere;
}
.section-label {
  display: block;
  margin-top: 32rpx;
  color: var(--med-ink);
  font-size: 30rpx;
  font-weight: 700;
}
.description {
  display: block;
  margin: 16rpx 0 34rpx;
  color: var(--med-text-secondary);
  line-height: 1.7;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  user-select: text;
}
.info {
  padding: 20rpx 0;
  border-top: 1rpx solid var(--med-divider);
  gap: 24rpx;
  color: var(--med-muted);
  overflow-wrap: anywhere;
}
.delete-button {
  margin-top: 20rpx;
  min-height: 80rpx;
  color: #9c3f3a;
  background: #fff;
  border: 1rpx solid #e6c6c3;
  font-size: 24rpx;
}
.edit {
  margin-top: 30rpx;
}
@media screen and (min-width: 600px) {
  .page {
    padding: 40px;
  }
  .title {
    margin-top: 24px;
    padding-bottom: 24px;
    font-size: 28px;
  }
  .section-label {
    margin-top: 24px;
    font-size: 18px;
  }
  .type,
  .status,
  .info {
    font-size: 14px;
  }
  .description {
    margin: 16px 0 24px;
    font-size: 16px;
  }
  .info {
    padding: 16px 0;
  }
  .edit {
    min-height: 48px;
    margin-top: 24px;
    font-size: 16px;
    border-radius: 8px;
  }
}
</style>
