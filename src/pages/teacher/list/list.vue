<template>
  <view class="safe-page redirect-page">
    <text class="redirect-mark">✚</text>
    <text class="title">正在进入教学工作台…</text>
  </view>
</template>

<script setup lang="ts">
import { onShow } from '@dcloudio/uni-app'
import { requireRole } from '@/features/identity/public'
import { goReplace, ROUTES } from '@/platform/navigation'

onShow(() => {
  if (!requireRole('teacher')) return
  goReplace(ROUTES.teacherWorkspace)
})
</script>

<style scoped>
.redirect-page {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 20rpx;
}
.title {
  color: #637985;
}
.redirect-mark {
  color: var(--med-brand);
  font-size: 60rpx;
}
</style>
