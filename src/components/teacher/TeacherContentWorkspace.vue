<template>
  <view class="teacher-content-workspace">
    <TeacherSubsectionNav
      :active="section"
      :items="sections"
      nav-label="内容分区"
      panel-prefix="teacher-content-panel"
      @change="selectSection"
    />
    <view
      v-if="opened['pbl-diagnostics']"
      v-show="section === 'pbl-diagnostics'"
      id="teacher-content-panel-pbl-diagnostics"
      class="workspace-panel"
      role="region"
      aria-labelledby="teacher-content-panel-pbl-diagnostics-heading"
    >
      <text
        id="teacher-content-panel-pbl-diagnostics-heading"
        class="sr-only"
        role="heading"
        aria-level="2"
        tabindex="-1"
        >诊断建议</text
      >
      <TeacherClassScope
        :classes="classes"
        :model-value="classId"
        :loading="classLoading"
        :error="classError"
        @update:model-value="$emit('classChange', $event)"
        @retry="$emit('retryClasses')"
      />
      <TeacherPblWorkItems
        ref="workItems"
        :class-id="classId ? String(classId) : undefined"
        initial-status="pending"
        @summary="handleSummary"
      />
    </view>
    <view
      v-if="opened.resources"
      v-show="section === 'resources'"
      id="teacher-content-panel-resources"
      class="workspace-panel"
      role="region"
      aria-labelledby="teacher-content-panel-resources-heading"
    >
      <text
        id="teacher-content-panel-resources-heading"
        class="sr-only"
        role="heading"
        aria-level="2"
        tabindex="-1"
        >教学资源</text
      >
      <TeacherProblemList
        ref="problemList"
        show-knowledge-cards
        :show-medical-review="isReviewer"
        @knowledge-cards="$emit('knowledgeCards')"
        @medical-review="$emit('medicalReview')"
      />
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import TeacherProblemList from '@/components/TeacherProblemList.vue'
import TeacherClassScope from './TeacherClassScope.vue'
import TeacherPblWorkItems from './TeacherPblWorkItems.vue'
import TeacherSubsectionNav from './TeacherSubsectionNav.vue'
import type { PblWorkStatus } from '@/features/pbl/public'

export type TeacherContentSection = 'pbl-diagnostics' | 'resources'

const props = defineProps<{
  initialSection?: TeacherContentSection
  classes: Array<{ id: number; name: string }>
  classId?: number
  classLoading: boolean
  classError: string
  isReviewer: boolean
}>()
const emit = defineEmits<{
  classChange: [classId: number | undefined]
  retryClasses: []
  knowledgeCards: []
  medicalReview: []
  sectionChange: []
}>()

const initialSection = validSection(props.initialSection)
const section = ref<TeacherContentSection>(initialSection)
const opened = ref<Record<TeacherContentSection, boolean>>({
  'pbl-diagnostics': initialSection === 'pbl-diagnostics',
  resources: initialSection === 'resources',
})
const pendingCount = ref(0)
const sections = computed(() => [
  { key: 'pbl-diagnostics', label: '诊断建议', count: pendingCount.value },
  { key: 'resources', label: '教学资源' },
])
const workItems = ref<{
  focusPending(): Promise<void>
  openSnapshot(snapshotId: string): Promise<void>
  refresh(): Promise<void>
}>()
const problemList = ref<{ refresh(): Promise<void> }>()

function validSection(value: string | undefined): TeacherContentSection {
  return value === 'resources' ? 'resources' : 'pbl-diagnostics'
}

async function selectSection(value?: string, snapshotId?: string, focusPending = false) {
  const next = validSection(value)
  opened.value[next] = true
  section.value = next
  emit('sectionChange')
  await nextTick()
  if (next !== 'pbl-diagnostics') return
  if (focusPending) await workItems.value?.focusPending()
  if (snapshotId) await workItems.value?.openSnapshot(snapshotId)
}

async function refresh() {
  await nextTick()
  if (section.value === 'pbl-diagnostics') return workItems.value?.refresh()
  return problemList.value?.refresh()
}

function handleSummary(value: Record<PblWorkStatus, number>) {
  pendingCount.value = value.pending
}

defineExpose({ refresh, selectSection })
</script>

<style scoped>
.teacher-content-workspace {
  background: var(--med-page);
}
.workspace-panel:focus {
  outline: none;
}
</style>
