<template>
  <view class="safe-page splash">
    <view class="pulse">✚</view>
    <text class="title">医学知识问答</text>
    <text class="muted">正在返回登录页…</text>
  </view>
</template>

<script setup lang="ts">
import { onShow } from '@dcloudio/uni-app'
import { relaunchTo, ROUTES } from '@/platform/navigation'

onShow(() => {
  relaunchTo(ROUTES.login)
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
  background: var(--med-clinical);
  font-size: 64rpx;
  font-weight: 700;
}
.title {
  font-size: 38rpx;
  font-weight: 700;
}
</style>
