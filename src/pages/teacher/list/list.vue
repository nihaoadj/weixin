<template>
  <view class="safe-page redirect-page">
    <text class="redirect-mark">✚</text>
    <text class="title">正在进入教学工作台…</text>
  </view>
</template>

<script setup lang="ts">
import { onShow } from '@dcloudio/uni-app'
import { requireRole } from '@/services/auth'
import { ROUTES } from '@/services/navigation'

onShow(() => {
  if (!requireRole('teacher')) return
  uni.redirectTo({ url: ROUTES.teacherWorkspace })
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
  color: #0f8b8d;
  font-size: 60rpx;
}
</style>
