<template>
  <view class="teacher-insights-workspace">
    <TeacherSubsectionNav
      :active="section"
      :items="sections"
      nav-label="学情分区"
      panel-prefix="teacher-insights-panel"
      @change="selectSection"
    />
    <view
      v-if="section !== 'records'"
      class="shared-scope"
    >
      <TeacherClassScope
        :classes="classes"
        :model-value="classId"
        :loading="classLoading"
        :error="classError"
        @update:model-value="$emit('classChange', $event)"
        @retry="$emit('retryClasses')"
      />
    </view>
    <view
      v-if="opened['pbl-follow-ups']"
      v-show="section === 'pbl-follow-ups'"
      id="teacher-insights-panel-pbl-follow-ups"
      class="workspace-panel"
      role="region"
      aria-labelledby="teacher-insights-panel-pbl-follow-ups-heading"
    >
      <text
        id="teacher-insights-panel-pbl-follow-ups-heading"
        class="sr-only"
        role="heading"
        aria-level="2"
        tabindex="-1"
        >PBL 跟进</text
      >
      <TeacherPblFollowUps
        ref="followUps"
        :class-id="classId ? String(classId) : undefined"
      />
    </view>
    <view
      v-if="opened.analytics"
      v-show="section === 'analytics'"
      id="teacher-insights-panel-analytics"
      class="workspace-panel"
      role="region"
      aria-labelledby="teacher-insights-panel-analytics-heading"
    >
      <text
        id="teacher-insights-panel-analytics-heading"
        class="sr-only"
        role="heading"
        aria-level="2"
        tabindex="-1"
        >学情总览</text
      >
      <TeacherAnalyticsOverview
        ref="analyticsOverview"
        :class-id="classId"
        :class-scope-loaded="classScopeLoaded"
        :has-classes="classes.length > 0"
        @classes="$emit('classes')"
        @resources="$emit('resources')"
      />
    </view>
    <view
      v-if="opened.records"
      v-show="section === 'records'"
      id="teacher-insights-panel-records"
      class="workspace-panel"
      role="region"
      aria-labelledby="teacher-insights-panel-records-heading"
    >
      <text
        id="teacher-insights-panel-records-heading"
        class="sr-only"
        role="heading"
        aria-level="2"
        tabindex="-1"
        >学习记录</text
      >
      <text class="records-scope">显示全部授权可见报告；当前报告合同不提供班级筛选。</text>
      <TeacherReportList
        ref="reportList"
        @select="$emit('selectReport', $event)"
        @manage="$emit('resources')"
      />
    </view>
  </view>
</template>

<script setup lang="ts">
import { nextTick, ref } from 'vue'
import TeacherReportList from '@/components/TeacherReportList.vue'
import TeacherAnalyticsOverview from './TeacherAnalyticsOverview.vue'
import TeacherClassScope from './TeacherClassScope.vue'
import TeacherPblFollowUps from './TeacherPblFollowUps.vue'
import TeacherSubsectionNav from './TeacherSubsectionNav.vue'

export type TeacherInsightsSection = 'pbl-follow-ups' | 'analytics' | 'records'
export type TeacherFollowUpContext = { sessionId?: string; studentId?: string; planId?: number }

const props = defineProps<{
  initialSection?: TeacherInsightsSection
  classes: Array<{ id: number; name: string }>
  classId?: number
  classLoading: boolean
  classError: string
  classScopeLoaded: boolean
}>()
const emit = defineEmits<{
  classChange: [classId: number | undefined]
  retryClasses: []
  classes: []
  resources: []
  selectReport: [reportId: string]
  sectionChange: []
}>()

const initialSection = validSection(props.initialSection)
const section = ref<TeacherInsightsSection>(initialSection)
const opened = ref<Record<TeacherInsightsSection, boolean>>({
  'pbl-follow-ups': initialSection === 'pbl-follow-ups',
  analytics: initialSection === 'analytics',
  records: initialSection === 'records',
})
const sections = [
  { key: 'pbl-follow-ups', label: 'PBL 跟进' },
  { key: 'analytics', label: '学情总览' },
  { key: 'records', label: '学习记录' },
]
const followUps = ref<{
  refresh(): Promise<void>
  selectContext(context?: TeacherFollowUpContext): Promise<void>
}>()
const analyticsOverview = ref<{ refresh(): Promise<void> }>()
const reportList = ref<{ refresh(): Promise<void> }>()

function validSection(value: string | undefined): TeacherInsightsSection {
  if (value === 'analytics' || value === 'records') return value
  return 'pbl-follow-ups'
}

async function selectSection(value?: string, context?: TeacherFollowUpContext) {
  const next = validSection(value)
  opened.value[next] = true
  section.value = next
  emit('sectionChange')
  await nextTick()
  if (next === 'pbl-follow-ups' && context) return followUps.value?.selectContext(context)
}

async function refresh() {
  await nextTick()
  if (section.value === 'pbl-follow-ups') return followUps.value?.refresh()
  if (section.value === 'analytics') return analyticsOverview.value?.refresh()
  return reportList.value?.refresh()
}

defineExpose({ refresh, selectSection })
</script>

<style scoped>
.teacher-insights-workspace {
  background: var(--med-page);
}
.workspace-panel:focus {
  outline: none;
}
.records-scope {
  display: block;
  padding: 20rpx 0 4rpx;
  color: var(--med-muted);
  font-size: 22rpx;
  line-height: 1.5;
}
@media screen and (max-width: 360px) {
  .records-scope {
    font-size: 12px;
  }
}
@media screen and (min-width: 600px) {
  .records-scope {
    padding-top: 16px;
    font-size: 13px;
  }
}
</style>
