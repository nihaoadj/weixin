<template>
  <view class="safety-banner">
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
  color: #315568;
  background: #e9f7f5;
  border: 1rpx solid #c8e9e3;
  border-radius: 20rpx;
}
.safety-icon {
  display: flex;
  width: 48rpx;
  height: 48rpx;
  align-items: center;
  justify-content: center;
  background: #fff;
  border-radius: 14rpx;
}
.safety-copy {
  display: flex;
  min-width: 0;
  margin-left: 16rpx;
  flex: 1;
  flex-direction: column;
}
.safety-title {
  color: #0b5d61;
  font-size: 24rpx;
  font-weight: 700;
}
.safety-description {
  margin-top: 4rpx;
  color: #55717e;
  font-size: 21rpx;
  line-height: 1.55;
}
</style>
