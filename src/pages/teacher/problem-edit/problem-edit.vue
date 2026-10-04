<template>
  <view class="safe-page"><text>正在进入病例库…</text></view>
</template>

<script setup lang="ts">
import { onShow } from '@dcloudio/uni-app'
import { requireRole } from '@/features/identity/public'
import { relaunchToTeacherWorkspace } from '@/platform/navigation/teacher'

onShow(() => {
  if (!requireRole('teacher')) return
  relaunchToTeacherWorkspace({ workspace: 'content', resource: 'cases' })
})
</script>
