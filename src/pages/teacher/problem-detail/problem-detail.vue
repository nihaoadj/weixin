<template>
  <view class="safe-page page page-enter">
    <MedDetailSkeleton
      v-if="loading"
      label="正在加载问题…"
    />
    <MedState
      v-else-if="loadError"
      variant="error"
      icon="retry"
      title="问题加载失败"
      :description="loadError"
      action-label="重新加载"
      secondary-action-label="返回工作台"
      @action="loadProblem(problemId)"
      @secondary-action="back"
    />
    <MedState
      v-else-if="!problem"
      icon="book"
      title="问题不存在"
      description="内容可能已移除，或当前身份无法查看。"
      action-label="返回工作台"
      @action="back"
    />
    <view
      v-else
      class="detail-card"
    >
      <view class="meta"
        ><text class="type">{{ problem.type }}</text
        ><text class="status">{{ problem.status }}</text></view
      >
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
        >题目内容</text
      >
      <text
        class="description"
        user-select
        >{{ problem.description || '暂无详细描述' }}</text
      >
      <view class="info"
        ><text>发布对象</text><text>{{ targetText }}</text></view
      >
      <view class="info"
        ><text>创建日期</text><text>{{ problem.time }}</text></view
      >
      <view
        v-if="problem.publishTime"
        class="info"
        ><text>发布日期</text><text>{{ problem.publishTime }}</text></view
      >
      <button
        v-if="problem.status === '待审核'"
        class="primary-button edit"
        role="button"
        tabindex="0"
        hover-class="is-pressed"
        :hover-start-time="0"
        :hover-stay-time="80"
        @keydown="activateButtonOnKey"
        @click="edit"
      >
        编辑问题
      </button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { activateButtonOnKey } from '@/components/ui/keyboard'
import MedState from '@/components/ui/MedState.vue'
import MedDetailSkeleton from '@/components/ui/MedDetailSkeleton.vue'
import { onBackPress, onLoad } from '@dcloudio/uni-app'
import { requireRole } from '@/features/identity/public'
import { backOrRoute, goDetail, handleBackPress, ROUTES } from '@/platform/navigation'
import { findProblemAsync } from '@/features/content/public'
import type { Problem } from '@/types/domain'

const problem = ref<Problem | null>(null)
const loading = ref(false)
const loadError = ref('')
let problemId = ''
const targetText = computed(() => {
  if (problem.value?.target === 'class') return problem.value.targetLabel || problem.value.className || '指定班级'
  if (problem.value?.target === 'individual')
    return problem.value.targetLabel || `指定学生 ${problem.value.targetIds?.length || 0} 人`
  return '全体学生'
})
function back() {
  backOrRoute(ROUTES.teacherWorkspace, { tab: 'problems' })
}
onLoad((options) => {
  if (!requireRole('teacher')) return
  const id = typeof options?.id === 'string' ? options.id : ''
  problemId = id
  void loadProblem(id)
})
onBackPress(({ from }) => handleBackPress(from, ROUTES.teacherWorkspace, { tab: 'problems' }))

async function loadProblem(id: string) {
  if (loading.value) return
  loading.value = true
  loadError.value = ''
  try {
    problem.value = (await findProblemAsync(id)) || null
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '暂时无法获取内容，请重试。'
  } finally {
    loading.value = false
  }
}
function edit() {
  if (problem.value) goDetail(ROUTES.teacherProblemEdit, { id: problem.value.id })
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
