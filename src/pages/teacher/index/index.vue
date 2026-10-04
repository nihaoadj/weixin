<template><view /></template>
<script setup lang="ts">
import { onLoad } from '@dcloudio/uni-app'
import { parseTeacherWorkspaceTarget, relaunchToTeacherWorkspace } from '@/platform/navigation/teacher'
onLoad((query) => relaunchToTeacherWorkspace(parseTeacherWorkspaceTarget(query || {})))
</script>
