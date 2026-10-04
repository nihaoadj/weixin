<template>
  <view class="safe-page compatibility-page">
    <text role="status">正在进入病例列表…</text>
  </view>
</template>

<script setup lang="ts">
import { onLoad } from '@dcloudio/uni-app'
import { requireRole } from '@/features/identity/public'
import { goReplace, ROUTES } from '@/platform/navigation'

onLoad(() => {
  if (!requireRole('student')) return
  goReplace(ROUTES.studentCases, { view: 'cases' })
})
</script>

<style scoped>
.compatibility-page {
  padding: 32rpx;
  color: var(--med-muted);
  background: var(--med-page);
}
</style>
