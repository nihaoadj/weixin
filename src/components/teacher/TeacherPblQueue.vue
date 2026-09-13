<template>
  <view class="pbl-workspace">
    <TeacherClassScope
      :classes="classes"
      :model-value="classId"
      :loading="classLoading"
      :error="classError"
      @update:model-value="$emit('classChange', $event)"
      @retry="$emit('retryClasses')"
    />
    <TeacherPblClassrooms
      ref="classrooms"
      :class-id="classId ? String(classId) : undefined"
      :classes="classes"
      @open-diagnostic="$emit('openDiagnostic', $event)"
      @open-follow-up="$emit('openFollowUp', $event)"
    />
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import TeacherClassScope from './TeacherClassScope.vue'
import TeacherPblClassrooms from './TeacherPblClassrooms.vue'

defineProps<{
  classes: Array<{ id: number; name: string }>
  classId?: number
  classLoading: boolean
  classError: string
}>()
defineEmits<{
  classChange: [classId: number | undefined]
  retryClasses: []
  openDiagnostic: [snapshotId: string]
  openFollowUp: [context: { classId?: string; sessionId: string; studentId: string }]
}>()

const classrooms = ref<{ refresh(): Promise<void> }>()
async function refresh() {
  await classrooms.value?.refresh()
}
defineExpose({ refresh })
</script>

<style scoped>
.pbl-workspace {
  background: var(--med-page);
}
</style>
