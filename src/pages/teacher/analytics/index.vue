<template>
  <view class="safe-page redirect-page">
    <MedState
      variant="loading"
      icon="retry"
      title="正在打开学情总览"
      description="教学统计已统一归入教师学情工作区。"
    />
  </view>
</template>

<script setup lang="ts">
import { onBackPress, onLoad } from '@dcloudio/uni-app'
import MedState from '@/components/ui/MedState.vue'
import { requireRole } from '@/features/identity/public'
import { handleBackPress, ROUTES } from '@/platform/navigation'
import { parseTeacherWorkspaceTarget, relaunchToTeacherWorkspace } from '@/platform/navigation/teacher'

onLoad((query) => {
  if (!requireRole('teacher')) return
  relaunchToTeacherWorkspace(parseTeacherWorkspaceTarget({ ...query, tab: 'insights' }))
})
onBackPress(({ from }) => handleBackPress(from, ROUTES.teacherInsights))
</script>

<style scoped>
.redirect-page {
  min-height: 100vh;
  padding: 28rpx;
  box-sizing: border-box;
  background: var(--med-page);
}
</style>
