<template>
  <view class="safe-page">
    <MedState
      variant="loading"
      icon="history"
      title="正在打开学习结果"
      description="详情已统一归入学情工作区。"
    />
  </view>
</template>
<script setup lang="ts">
import { onBackPress, onLoad } from '@dcloudio/uni-app'
import MedState from '@/components/ui/MedState.vue'
import { requireRole } from '@/features/identity/public'
import { handleBackPress, ROUTES } from '@/platform/navigation'
import { redirectLegacyTeacherInsightsDetail } from '@/platform/navigation/teacher'
onLoad((query) => {
  if (!requireRole('teacher')) return
  redirectLegacyTeacherInsightsDetail('result', query || {})
})
onBackPress(({ from }) => handleBackPress(from, ROUTES.teacherInsights, { panel: 'progress' }))
</script>
