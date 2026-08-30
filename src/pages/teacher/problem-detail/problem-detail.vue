<template>
  <view class="safe-page page">
    <view
      v-if="problem"
      class="card detail-card"
    >
      <view class="meta"
        ><text class="type">{{ problem.type }}</text
        ><text class="status">{{ problem.status }}</text></view
      >
      <text class="title">{{ problem.title }}</text>
      <text class="description">{{ problem.description || '暂无详细描述' }}</text>
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
        @click="edit"
      >
        编辑问题
      </button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { requireRole } from '@/services/auth'
import { backOrHome } from '@/services/navigation'
import { findProblemAsync } from '@/services/repositoryAsync'
import type { Problem } from '@/types/domain'

const problem = ref<Problem | null>(null)
const targetText = computed(() => {
  if (problem.value?.target === 'class') return problem.value.targetLabel || problem.value.className || '指定班级'
  if (problem.value?.target === 'individual')
    return problem.value.targetLabel || `指定学生 ${problem.value.targetIds?.length || 0} 人`
  return '全体学生'
})
onLoad((options) => {
  if (!requireRole('teacher')) return
  const id = typeof options?.id === 'string' ? options.id : ''
  void loadProblem(id)
})

async function loadProblem(id: string) {
  problem.value = (await findProblemAsync(id)) || null
  if (!problem.value) {
    uni.showToast({ title: '问题不存在', icon: 'none' })
    backOrHome('teacher')
  }
}
function edit() {
  if (problem.value) uni.navigateTo({ url: `/pages/teacher/problem-edit/problem-edit?id=${problem.value.id}` })
}
</script>

<style scoped>
.page {
  padding: 30rpx;
}
.detail-card {
  padding: 34rpx;
}
.meta,
.info {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.type {
  padding: 7rpx 14rpx;
  color: #087f8c;
  background: #e6f7f5;
  border-radius: 99rpx;
  font-size: 22rpx;
}
.status {
  color: #718096;
  font-size: 23rpx;
}
.title {
  display: block;
  margin-top: 30rpx;
  font-size: 36rpx;
  font-weight: 750;
  line-height: 1.5;
}
.description {
  display: block;
  margin: 24rpx 0 34rpx;
  color: #526174;
  line-height: 1.7;
}
.info {
  padding: 20rpx 0;
  border-top: 1rpx solid #edf2f7;
  color: #64748b;
}
.edit {
  margin-top: 30rpx;
}
</style>
