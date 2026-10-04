<template>
  <view class="safe-page"><text>正在进入病例库…</text></view>
</template>
<script setup lang="ts">
import { onBackPress, onShow } from '@dcloudio/uni-app'
import { requireRole } from '@/features/identity/public'
import { handleBackPress, ROUTES } from '@/platform/navigation'
import { relaunchToTeacherWorkspace } from '@/platform/navigation/teacher'
function back() {
  relaunchToTeacherWorkspace({ workspace: 'content', resource: 'cases' })
}
onShow(() => {
  if (requireRole('teacher')) back()
})
onBackPress(({ from }) =>
  handleBackPress(String(from) === 'navigateBack' ? 'navigateBack' : 'backbutton', ROUTES.teacherContent, {
    resource: 'cases',
  }),
)
</script>
