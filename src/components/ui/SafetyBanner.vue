<template>
  <view
    class="safety-banner"
    role="note"
    aria-label="医学学习安全提示"
  >
    <view class="safety-icon"
      ><MedIcon
        name="brand"
        size="sm"
    /></view>
    <view class="safety-copy">
      <text class="safety-title">教学辅助 · 非临床诊疗</text>
      <text class="safety-description"><slot>内容仅用于医学学习，紧急情况请立即联系专业医疗机构。</slot></text>
    </view>
  </view>
</template>

<script setup lang="ts">
import MedIcon from '@/components/ui/MedIcon.vue'
</script>

<style scoped>
.safety-banner {
  display: flex;
  padding: 20rpx 22rpx;
  align-items: flex-start;
  color: var(--med-safety);
  background: var(--med-safety-soft);
  border: 1rpx solid var(--med-safety-border);
  border-left: 6rpx solid var(--med-safety);
  border-radius: var(--med-radius-md);
}
.safety-icon {
  display: flex;
  width: 48rpx;
  height: 48rpx;
  align-items: center;
  justify-content: center;
  background: var(--med-surface);
  border-radius: var(--med-radius-sm);
}
.safety-copy {
  display: flex;
  min-width: 0;
  margin-left: 16rpx;
  flex: 1;
  flex-direction: column;
}
.safety-title {
  color: var(--med-safety);
  font-size: 24rpx;
  font-weight: 700;
}
.safety-description {
  margin-top: 4rpx;
  color: var(--med-safety-text);
  font-size: 24rpx;
  line-height: 1.55;
}
</style>
