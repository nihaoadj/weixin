<template>
  <view class="safe-page page">
    <view class="card intro">
      <text class="title">医学审核队列</text>
      <text class="muted">审核专家可查看病例完整内容、量表和练习蓝图；历史记录不可覆盖。</text>
    </view>
    <view class="card tabs">
      <text
        v-for="tab in tabs"
        :key="tab.id"
        class="tab"
        :class="{ active: status === tab.id }"
        @click="select(tab.id)"
      >
        {{ tab.label }} {{ counts[tab.id] }}
      </text>
    </view>
    <MedState
      v-if="loading"
      variant="loading"
      icon="retry"
      title="正在加载审核队列"
      description="正在同步各分类的病例版本。"
    />
    <MedState
      v-else-if="error"
      variant="error"
      icon="retry"
      title="审核队列加载失败"
      :description="error"
      action-label="重新加载"
      secondary-action-label="返回工作台"
      @action="load"
      @secondary-action="back"
    />
    <MedState
      v-else-if="!items.length"
      variant="empty"
      icon="book"
      :title="status === 'pending' ? '当前没有待审核病例' : '当前分类暂无病例'"
      description="新的病例版本进入该状态后会显示在这里。"
      action-label="重新加载"
      secondary-action-label="返回工作台"
      @action="load"
      @secondary-action="back"
    />
    <view
      v-for="item in items"
      :key="item.id"
      class="card item"
      @click="open(String(item.id))"
    >
      <text class="title-small">{{ item.title }}</text>
      <text class="muted">版本 {{ item.version }} · {{ item.specialty }} · {{ reviewLabel(item) }}</text>
      <text class="link">查看完整病例与审核历史 ›</text>
    </view>
  </view>
</template>
<script setup lang="ts">
import { reactive, ref } from 'vue'
import { onBackPress, onShow } from '@dcloudio/uni-app'
import MedState from '@/components/ui/MedState.vue'
import { requireRole } from '@/features/identity/public'
import { backOrRoute, goDetail, handleBackPress, ROUTES } from '@/platform/navigation'
import { getReviewQueue } from '@/features/content/public'
import type { Problem } from '@/types/domain'

type ReviewStatus = 'pending' | 'approved' | 'rejected'
const tabs: Array<{ id: ReviewStatus; label: string }> = [
  { id: 'pending', label: '待审核' },
  { id: 'approved', label: '已通过' },
  { id: 'rejected', label: '已退回' },
]
const status = ref<ReviewStatus>('pending')
const items = ref<Problem[]>([])
const counts = reactive<Record<ReviewStatus, number>>({ pending: 0, approved: 0, rejected: 0 })
const loading = ref(false)
const error = ref('')

async function load() {
  if (loading.value) return
  loading.value = true
  error.value = ''
  try {
    const [pending, approved, rejected] = await Promise.all(tabs.map((tab) => getReviewQueue(tab.id)))
    counts.pending = pending.length
    counts.approved = approved.length
    counts.rejected = rejected.length
    items.value = status.value === 'pending' ? pending : status.value === 'approved' ? approved : rejected
  } catch (loadError) {
    items.value = []
    error.value = loadError instanceof Error ? loadError.message : '请稍后重试'
  } finally {
    loading.value = false
  }
}
function select(next: ReviewStatus) {
  status.value = next
  void load()
}
function reviewLabel(item: Problem) {
  return item.medicalReviewStatus === 'approved'
    ? '审核通过'
    : item.medicalReviewStatus === 'rejected'
      ? '已退回'
      : '待审核'
}
function open(id: string) {
  goDetail(ROUTES.teacherReviewDetail, { id })
}
function back() {
  backOrRoute(ROUTES.teacherWorkspace)
}
onShow(() => {
  if (requireRole('teacher')) void load()
})
onBackPress(({ from }) => handleBackPress(from, ROUTES.teacherWorkspace))
</script>
<style scoped>
.page {
  min-height: 100vh;
  padding: 28rpx;
  background: var(--med-page);
}
.intro,
.item,
.empty,
.tabs {
  margin-bottom: 18rpx;
  padding: 28rpx;
}
.title {
  display: block;
  font-size: 34rpx;
  font-weight: 750;
}
.title-small {
  display: block;
  font-size: 28rpx;
  font-weight: 700;
}
.muted {
  display: block;
  margin-top: 10rpx;
  color: var(--med-muted);
  font-size: 22rpx;
}
.tabs {
  display: flex;
  gap: 28rpx;
}
.tab {
  padding-bottom: 12rpx;
  color: var(--med-muted);
  font-size: 24rpx;
}
.tab.active {
  color: var(--med-brand);
  border-bottom: 4rpx solid var(--med-brand);
  font-weight: 700;
}
.link {
  display: block;
  margin-top: 16rpx;
  color: var(--med-brand);
}
.empty {
  color: var(--med-muted);
  text-align: center;
}
</style>
