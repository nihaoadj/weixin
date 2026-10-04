<template>
  <TeacherWorkspaceDeck
    v-if="loaded"
    id="teacher-workspace-root"
    initial-workspace="pbl"
    :query="query"
  />
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import TeacherWorkspaceDeck from '@/components/teacher/TeacherWorkspaceDeck.vue'
const query = ref<Record<string, string | undefined>>({})
const loaded = ref(false)
onLoad((value) => {
  query.value = value || {}
  loaded.value = true
})
</script>
