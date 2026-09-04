<template>
  <view class="student-primary-nav">
    <StudentNav :active="active" />
  </view>
</template>

<script setup lang="ts">
import StudentNav, { type StudentTab } from '@/components/ui/StudentNav.vue'

defineProps<{ active: StudentTab }>()
</script>

<style scoped>
.student-primary-nav {
  position: fixed;
  z-index: 20;
  right: 24rpx;
  bottom: calc(18rpx + env(safe-area-inset-bottom));
  left: 24rpx;
  padding: 8rpx;
  background: var(--med-surface);
  border: 1rpx solid var(--med-border);
  border-radius: 24rpx;
  box-shadow: 0 14rpx 40rpx rgba(11, 34, 57, 0.12);
}

@media screen and (min-width: 900px) {
  .student-primary-nav {
    right: auto;
    left: 50%;
    width: calc(1080px - 48rpx);
    max-width: calc(100% - 48rpx);
    transform: translateX(-50%);
  }
}
</style>
