<template>
  <view class="safe-page page">
    <MedState
      v-if="error"
      variant="error"
      icon="retry"
      title="训练复盘加载失败"
      :description="error"
      action-label="重新加载"
      secondary-action-label="返回学习首页"
      @action="load"
      @secondary-action="back"
    />
    <template v-else>
      <view class="flow-section panel">
        <text class="eyebrow-label">训练证据</text>
        <text class="title">训练复盘</text>
        <text class="muted">正式能力变化与练习掌握度分开显示。</text>
        <view
          v-for="item in profile.formalDimensions"
          :key="String(item.dimension_id)"
          class="row"
        >
          <text>{{ item.label || item.dimension_id }}</text>
          <text>{{ item.score || 0 }}</text>
        </view>
      </view>
      <view class="flow-section panel mastery-section">
        <text class="section-title">微训练掌握度</text>
        <view
          v-for="(item, key) in profile.practiceMastery"
          :key="key"
          class="row"
        >
          <text>{{ key }}</text>
          <text>{{ item.averageScore }} 分 · {{ item.attemptCount }} 次</text>
        </view>
        <text
          v-if="!Object.keys(profile.practiceMastery).length"
          class="muted"
          >完成微训练后显示掌握度。</text
        >
        <button
          class="secondary"
          @click="back"
        >
          返回学习首页
        </button>
      </view>
    </template>
  </view>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { onBackPress, onLoad } from '@dcloudio/uni-app'
import MedState from '@/components/ui/MedState.vue'
import { requireRole } from '@/features/identity/public'
import { backOrRoute, handleBackPress, ROUTES } from '@/platform/navigation'
import { getLearningProfile } from '@/features/learning/public'
import type { LearningProfile } from '@/types/learning'
const profile = ref<LearningProfile>({
  formalDimensions: [],
  recentAssessments: [],
  practiceMastery: {},
  unreadCount: 0,
})
const error = ref('')
async function load() {
  error.value = ''
  try {
    profile.value = await getLearningProfile()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '请稍后重试'
  }
}
function back() {
  backOrRoute(ROUTES.studentLearning)
}
onLoad(async () => {
  if (!requireRole('student')) return
  await load()
})

onBackPress(({ from }) => handleBackPress(from, ROUTES.studentLearning))
</script>
<style scoped>
.page {
  padding: 28rpx;
  background: var(--med-page);
}
.panel {
  display: flex;
  max-width: 920px;
  margin: 0 auto;
  flex-direction: column;
  gap: 16rpx;
}
.flow-section {
  padding: 30rpx 2rpx 36rpx;
}
.mastery-section {
  padding-top: 36rpx;
  border-top: 1rpx solid var(--med-border);
}
.title {
  color: var(--med-navy);
  font-size: 38rpx;
  font-weight: 800;
}
.section-title {
  font-size: 29rpx;
  font-weight: 750;
}
.muted {
  color: var(--med-muted);
  font-size: 23rpx;
}
.row {
  display: flex;
  padding: 16rpx 0;
  justify-content: space-between;
  border-bottom: 1rpx solid var(--med-divider);
}
.secondary {
  color: var(--med-brand);
  background: var(--med-brand-soft);
  border-radius: var(--med-radius-sm);
}
</style>
