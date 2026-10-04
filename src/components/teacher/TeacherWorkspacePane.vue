<template>
  <TeacherPblScreen v-if="index === 0" />
  <TeacherInsightsScreen v-else-if="index < 4" />
  <TeacherContentScreen
    v-else
    id="teacher-content-screen"
  />
</template>
<script setup lang="ts">
import { computed, provide } from 'vue'
import TeacherPblScreen from '../../features/pbl/presentation/TeacherPblScreen.vue'
import TeacherInsightsScreen from '../../features/analytics/presentation/TeacherInsightsScreen.vue'
import TeacherContentScreen from '../../features/content/presentation/TeacherContentScreen.vue'
import { teacherScreenKey, type TeacherScreenContext } from './teacherScreenContext'
const props = defineProps<{ index: number; current: number; context: Omit<TeacherScreenContext, 'active'> }>()
provide(teacherScreenKey, { ...props.context, active: computed(() => props.current === props.index) })
</script>
