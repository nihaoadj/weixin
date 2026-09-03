<template>
  <view class="safe-page splash">
    <view class="pulse">✚</view>
    <text class="title">医学知识问答</text>
    <text class="muted">正在进入应用…</text>
  </view>
</template>

<script setup lang="ts">
import { onShow } from '@dcloudio/uni-app'
import { relaunchForRole } from '@/platform/navigation'
import { getRole } from '@/features/identity/public'

onShow(() => {
  relaunchForRole(getRole())
})
</script>

<style scoped>
.splash {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 24rpx;
}
.pulse {
  display: flex;
  width: 120rpx;
  height: 120rpx;
  align-items: center;
  justify-content: center;
  border-radius: 36rpx;
  color: #fff;
  background: linear-gradient(135deg, var(--med-brand), #16a085);
  font-size: 64rpx;
  box-shadow: 0 20rpx 50rpx rgba(8, 127, 140, 0.25);
}
.title {
  font-size: 38rpx;
  font-weight: 700;
}
</style>
