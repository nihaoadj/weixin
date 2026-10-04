<template>
  <TeacherPageFrame
    active="insights"
    title="学情"
    description="查看授权课堂的学习进度、测试结果与诊断事实。"
  >
    <MedState
      v-if="accessDenied"
      variant="error"
      icon="history"
      title="教师身份已变化"
      description="请重新登录教师账号。"
    />
    <MedState
      v-else-if="!scopeAllowed"
      :variant="error ? 'error' : 'loading'"
      icon="retry"
      :title="error || '正在读取班级范围'"
      :description="error ? '请重试读取班级范围。' : '请稍候。'"
      :action-label="error ? '重试' : undefined"
      @action="refresh"
    />
    <view
      v-else
      :key="identityGeneration"
      class="insights-root"
    >
      <picker
        :range="classOptions"
        range-key="name"
        @change="changeClass"
        ><view class="scope-picker">{{
          classes.find((item) => item.id === classId)?.name || '全部授权班级'
        }}</view></picker
      >
      <picker
        :range="sessionOptions"
        range-key="name"
        @change="changeSession"
        ><view class="scope-picker">{{ sessionId ? `已限定课堂 ${sessionId}` : '全部课堂' }}</view></picker
      >
      <text
        v-if="sessionError"
        class="scope-note"
        >{{ sessionError }} <button @click="loadSessions">重试课堂目录</button></text
      >
      <TeacherPager
        v-if="sessionTotal > 20"
        :total="sessionTotal"
        :offset="sessionOffset"
        @previous="paginateSessions(-20)"
        @next="paginateSessions(20)"
      />
      <view class="date-filters">
        <picker
          mode="date"
          :value="dateFrom"
          @change="dateFrom = $event.detail.value"
          ><view>{{ dateFrom || '选择开始日期' }}</view></picker
        >
        <picker
          mode="date"
          :value="dateTo"
          @change="dateTo = $event.detail.value"
          ><view>{{ dateTo || '选择结束日期' }}</view></picker
        >
        <button @click="clearDates">默认区间</button>
      </view>
      <text
        v-if="sessionId"
        class="scope-note"
        >限定课堂 {{ sessionId }} <button @click="sessionId = undefined">清除课堂筛选</button></text
      >
      <view class="panels"
        ><button
          v-for="item in panels"
          :key="item.key"
          :class="{ selected: initialPanel === item.key }"
          @click="initialPanel = item.key"
        >
          {{ item.label }}
        </button></view
      >
      <MedState
        v-if="dateFrom && dateTo && dateFrom > dateTo"
        variant="error"
        icon="retry"
        title="日期范围无效"
        description="结束日期不能早于开始日期。"
      />
      <TeacherInsightsReadWorkspace
        v-else
        ref="workspace"
        :panel="initialPanel"
        :filters="filters"
        :classes="classes"
        @open-student="openStudent"
      />
    </view>
  </TeacherPageFrame>
</template>
<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import TeacherPageFrame from '@/components/teacher/TeacherPageFrame.vue'
import TeacherInsightsReadWorkspace from '@/components/teacher/TeacherInsightsReadWorkspace.vue'
import TeacherPager from '@/components/teacher/TeacherPager.vue'
import { displayTopicCode } from '@/components/teacher/topicLabel'
import MedState from '@/components/ui/MedState.vue'
import { useTeacherRootScope } from '@/components/teacher/useTeacherRootScope'
import { getSession } from '@/features/identity/public'
import { getTeacherPblSessionPage, type TeacherPblSession } from '@/features/pbl/public'
import { readTeacherInsightsPreference, saveTeacherInsightsPreference } from '@/platform/navigation/teacherPreferences'
import { goDetail, ROUTES } from '@/platform/navigation'
import { parseTeacherWorkspaceTarget, type TeacherInsightsPanel } from '@/platform/navigation/teacher'

const {
  classes,
  classId,
  error,
  accessDenied,
  identityGeneration,
  scopeAllowed,
  setInitialClass,
  selectClass,
  refreshScope,
} = useTeacherRootScope('insights')
const workspace = ref<{ refresh(): Promise<void> }>()
const initialPanel = ref<TeacherInsightsPanel>('overview')
const dateFrom = ref<string>()
const dateTo = ref<string>()
const sessionId = ref<number | string>()
const sessions = ref<TeacherPblSession[]>([])
const sessionError = ref('')
const sessionOffset = ref(0)
const sessionTotal = ref(0)
let sessionRequest = 0
const sessionOptions = computed(() => [
  { id: undefined, name: '全部课堂' },
  ...sessions.value.map((item) => ({
    id: item.id,
    name: `${item.className} · ${displayTopicCode(item.topicCode)}${item.status === 'closed' ? '（已关闭）' : ''}`,
  })),
])
let preferenceIdentity: string | undefined
let initialTarget: Extract<ReturnType<typeof parseTeacherWorkspaceTarget>, { workspace: 'insights' }> | undefined
const classOptions = computed(() => [{ id: undefined, name: '全部授权班级' }, ...classes.value])
const filters = computed(() => ({
  classId: classId.value,
  sessionId: sessionId.value,
  dateFrom: dateFrom.value,
  dateTo: dateTo.value,
}))
const panels: Array<{ key: TeacherInsightsPanel; label: string }> = [
  { key: 'overview', label: '总览' },
  { key: 'progress', label: '进度' },
  { key: 'knowledge', label: '知识与推理' },
  { key: 'students', label: '学生' },
]
function changeClass(event: { detail: { value: string } }) {
  sessionId.value = undefined
  selectClass(classOptions.value[Number(event.detail.value)]?.id)
}
function changeSession(event: { detail: { value: string } }) {
  const selected = sessionOptions.value[Number(event.detail.value)]
  const target = parseTeacherWorkspaceTarget({ tab: 'insights', sessionId: selected?.id })
  if (target.workspace === 'insights') sessionId.value = target.sessionId
}
async function loadSessions() {
  const token = ++sessionRequest
  const actor = getSession()
  sessions.value = []
  sessionError.value = ''
  sessionTotal.value = 0
  if (!scopeAllowed.value || actor?.role !== 'teacher') return
  try {
    const value = await getTeacherPblSessionPage({
      classId: classId.value === undefined ? undefined : String(classId.value),
      offset: sessionOffset.value,
    })
    if (token !== sessionRequest || getSession()?.openid !== actor.openid || getSession()?.role !== 'teacher') return
    sessions.value = value.items
    sessionTotal.value = value.total
  } catch (reason) {
    if (token === sessionRequest && getSession()?.openid === actor.openid)
      sessionError.value = reason instanceof Error ? reason.message : '课堂目录读取失败。'
  }
}
function paginateSessions(delta: number) {
  sessionOffset.value = Math.max(0, sessionOffset.value + delta)
  void loadSessions()
}
watch(classId, () => {
  sessionOffset.value = 0
  void loadSessions()
})
function clearDates() {
  dateFrom.value = undefined
  dateTo.value = undefined
}
onLoad((query) => {
  const target = parseTeacherWorkspaceTarget({ ...query, tab: 'insights' })
  if (target.workspace !== 'insights') return
  setInitialClass(target.classId)
  initialPanel.value = target.panel || 'overview'
  sessionId.value = target.sessionId
  dateFrom.value = target.dateFrom
  dateTo.value = target.dateTo
  initialTarget = target
})
async function refresh() {
  const actor = getSession()
  if (actor?.role === 'teacher' && preferenceIdentity !== actor.openid) {
    preferenceIdentity = actor.openid
    const saved = readTeacherInsightsPreference(actor.openid)
    const restored = parseTeacherWorkspaceTarget({
      tab: 'insights',
      panel: saved?.panel,
      sessionId: saved?.sessionId === undefined ? undefined : String(saved.sessionId),
      dateFrom: saved?.dateFrom,
      dateTo: saved?.dateTo,
    })
    if (restored.workspace === 'insights') {
      initialPanel.value = initialTarget?.panel || restored.panel || 'overview'
      sessionId.value = initialTarget?.sessionId ?? restored.sessionId
      dateFrom.value = initialTarget?.dateFrom ?? restored.dateFrom
      dateTo.value = initialTarget?.dateTo ?? restored.dateTo
    }
    initialTarget = undefined
  }
  if (!(await refreshScope())) return
  void loadSessions()
  await nextTick()
  await workspace.value?.refresh()
}
onShow(refresh)
watch([initialPanel, sessionId, dateFrom, dateTo], () => {
  if (!preferenceIdentity || getSession()?.openid !== preferenceIdentity || getSession()?.role !== 'teacher') return
  if (dateFrom.value && dateTo.value && dateFrom.value > dateTo.value) return
  saveTeacherInsightsPreference(preferenceIdentity, {
    panel: initialPanel.value,
    sessionId: sessionId.value,
    dateFrom: dateFrom.value,
    dateTo: dateTo.value,
  })
})
function openStudent(context: { studentId: number; classId: number }) {
  goDetail(ROUTES.teacherInsightsStudentDetail, {
    ...context,
    sessionId: sessionId.value,
    dateFrom: dateFrom.value,
    dateTo: dateTo.value,
    panel: initialPanel.value,
    returnTab: 'insights',
  })
}
</script>
<style scoped>
.insights-root {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}
.scope-picker,
.date-filters picker {
  min-height: 88rpx;
  display: flex;
  align-items: center;
  font-size: 26rpx;
  color: var(--med-text);
}
.date-filters,
.panels {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
}
.date-filters button,
.panels button,
.scope-note button {
  min-height: 44px;
  margin: 0;
  font-size: 24rpx;
  color: var(--med-muted);
  background: var(--med-wash);
}
.panels button {
  flex: 1;
  padding: 0 12rpx;
}
.panels .selected {
  color: var(--med-clinical);
  font-weight: 700;
}
.scope-note {
  color: var(--med-muted);
  font-size: 24rpx;
}
</style>
