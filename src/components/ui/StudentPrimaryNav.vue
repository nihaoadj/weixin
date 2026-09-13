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
  right: 0;
  bottom: 0;
  left: 0;
  padding: 0 16rpx calc(12rpx + env(safe-area-inset-bottom));
  box-sizing: border-box;
  background: var(--med-surface);
  border-top: 1rpx solid var(--med-border);
}

@media screen and (min-width: 900px) {
  .student-primary-nav {
    right: auto;
    left: 50%;
    width: 1080px;
    max-width: 100%;
    transform: translateX(-50%);
  }
}
</style>
