<template>
  <view class="safe-page stats-page">
    <template v-if="problem">
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
import { onLoad } from '@dcloudio/uni-app'
import { requireRole } from '@/services/auth'
import { backOrHome } from '@/services/navigation'
import { findProblemAsync } from '@/services/repositoryAsync'
import type { Problem } from '@/types/domain'

const problem = ref<Problem | null>(null)
const answerCount = ref(0)
onLoad((options) => {
  if (!requireRole('teacher')) return
  const id = typeof options?.id === 'string' ? options.id : ''
  void loadStats(id)
})

async function loadStats(id: string) {
  problem.value = (await findProblemAsync(id)) || null
  answerCount.value = problem.value?.answerCount || 0
  if (!problem.value) {
    uni.showToast({ title: '问题不存在', icon: 'none' })
    backOrHome('teacher')
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
  color: #087f8c;
  background: #e6f7f5;
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
  color: #087f8c;
  font-size: 56rpx;
  font-weight: 800;
}
.label {
  margin-top: 8rpx;
  color: #718096;
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
