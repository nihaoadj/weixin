<template>
  <view class="safe-page logs-page">
    <view class="card intro">
      <text class="title">启动日志</text>
      <text class="muted">用于保留旧版的本地启动记录，仅保存在当前设备。</text>
    </view>
    <view
      v-if="logs.length === 0"
      class="card empty"
    >
      <text>暂无启动记录</text>
    </view>
    <view
      v-for="(log, index) in logs"
      :key="log"
      class="card log-item"
    >
      <text>{{ index + 1 }}. {{ formatLog(log) }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
const logs =
  (uni.getStorageSync('logs') as unknown[] | undefined)?.filter(
    (value): value is number => typeof value === 'number',
  ) || []

function formatLog(value: number): string {
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}
</script>

<style scoped>
.logs-page {
  padding: 30rpx;
}
.intro,
.log-item,
.empty {
  margin-bottom: 20rpx;
  padding: 28rpx;
}
.title {
  display: block;
  font-size: 34rpx;
  font-weight: 700;
}
.muted,
.empty {
  color: #718096;
}
.muted {
  display: block;
  margin-top: 12rpx;
  font-size: 23rpx;
}
</style>
