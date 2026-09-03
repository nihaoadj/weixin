<template>
  <view class="safe-page stats-page">
    <MedState
      v-if="loading"
      variant="loading"
      icon="retry"
      title="正在加载问题统计"
      description="正在核对问题与作答数据。"
    />
    <MedState
      v-else-if="loadError"
      variant="error"
      icon="retry"
      title="问题统计加载失败"
      :description="loadError"
      :action-label="problemId ? '重新加载' : '返回工作台'"
      :secondary-action-label="problemId ? '返回内容列表' : ''"
      @action="problemId ? loadStats(problemId) : back()"
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
    <template v-else>
      <view class="card hero"
        ><text class="type">{{ problem.type }}</text
        ><text class="title">{{ problem.title }}</text
        ><text class="muted">{{ problem.publishTime || problem.time }}</text></view
      >
      <view class="grid">
        <view class="metric card"
          ><text class="number">{{ answerCount }}</text
          ><text class="label">本机已回答</text></view
        >
        <view class="metric card"
          ><text class="number">{{ problem.status === '已发布' ? 1 : 0 }}</text
          ><text class="label">发布状态</text></view
        >
        <view class="metric card"><text class="number">—</text><text class="label">相关报告</text></view>
        <view class="metric card"><text class="number">—</text><text class="label">平均得分</text></view>
      </view>
      <view class="card note"
        ><text class="note-title">统计说明</text
        ><text
          >当前 Demo
          使用本地存储，统计仅反映本机体验数据。接入服务端后，应按课程、班级、学生和题目版本生成真实统计。</text
        ></view
      >
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onBackPress, onLoad } from '@dcloudio/uni-app'
import MedState from '@/components/ui/MedState.vue'
import { requireRole } from '@/features/identity/public'
import { backOrRoute, handleBackPress, ROUTES } from '@/platform/navigation'
import { findProblemAsync } from '@/features/content/public'
import type { Problem } from '@/types/domain'

const problem = ref<Problem | null>(null)
const answerCount = ref(0)
const loading = ref(false)
const loadError = ref('')
let problemId = ''
function back() {
  backOrRoute(ROUTES.teacherWorkspace, { tab: 'problems' })
}
onLoad((options) => {
  if (!requireRole('teacher')) return
  const id = typeof options?.id === 'string' ? options.id : ''
  problemId = id
  void loadStats(id)
})
onBackPress(({ from }) => handleBackPress(from, ROUTES.teacherWorkspace, { tab: 'problems' }))

async function loadStats(id: string) {
  if (loading.value) return
  if (!id) {
    loadError.value = '缺少问题编号，无法加载统计。'
    return
  }
  loading.value = true
  loadError.value = ''
  try {
    problem.value = (await findProblemAsync(id)) || null
    answerCount.value = problem.value?.answerCount || 0
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '请稍后重试。'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.stats-page {
  padding: 28rpx;
}
.hero {
  display: flex;
  padding: 32rpx;
  flex-direction: column;
  gap: 16rpx;
}
.type {
  align-self: flex-start;
  padding: 6rpx 14rpx;
  color: var(--med-brand);
  background: var(--med-brand-soft);
  border-radius: 99rpx;
  font-size: 21rpx;
}
.title {
  font-size: 32rpx;
  font-weight: 700;
  line-height: 1.5;
}
.grid {
  display: grid;
  margin-top: 24rpx;
  grid-template-columns: 1fr 1fr;
  gap: 20rpx;
}
.metric {
  display: flex;
  padding: 34rpx 20rpx;
  align-items: center;
  flex-direction: column;
}
.number {
  color: var(--med-brand);
  font-size: 56rpx;
  font-weight: 800;
}
.label {
  margin-top: 8rpx;
  color: var(--med-muted);
  font-size: 22rpx;
}
.note {
  margin-top: 24rpx;
  padding: 28rpx;
  color: #64748b;
  line-height: 1.65;
}
.note-title {
  display: block;
  margin-bottom: 12rpx;
  color: #183153;
  font-size: 29rpx;
  font-weight: 700;
}
</style>
