<template>
  <TeacherPageFrame
    active="insights"
    title="学情"
    reference-layout
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
      <view
        class="insights-hero"
        @click="rangeOpen = true"
        ><image
          class="insights-hero__waves"
          src="/static/insights-wave.svg"
          mode="scaleToFill"
        /><image
          class="insights-hero__art"
          src="/static/insights-hero.png"
          mode="aspectFit"
        /><text class="insights-hero__title">{{ hero.title }}</text
        ><button
          class="insights-hero__description"
          aria-label="查看和调整统计日期范围"
          @click="rangeOpen = true"
        >
          {{ hero.description }}
        </button></view
      >
      <view class="scope-pickers">
        <picker
          class="scope-pickers__item"
          :range="classOptions"
          range-key="name"
          :value="
            Math.max(
              0,
              classOptions.findIndex((item) => item.id === classId),
            )
          "
          @change="changeClass"
          ><view class="scope-picker"
            ><image
              src="/static/insights-class.svg"
              mode="aspectFit" /><text>{{ classes.find((item) => item.id === classId)?.name || '全部授权班级' }}</text
            ><view class="scope-picker__arrow" /></view
        ></picker>
        <picker
          class="scope-pickers__item"
          :range="sessionOptions"
          range-key="name"
          :value="
            Math.max(
              0,
              sessionOptions.findIndex((item) => item.id === sessionId),
            )
          "
          @change="changeSession"
          ><view class="scope-picker"
            ><image
              src="/static/insights-book.svg"
              mode="aspectFit" /><text>{{ selectedSessionName }}</text
            ><view class="scope-picker__arrow" /></view
        ></picker>
      </view>
      <view
        v-if="sessionError"
        class="scope-note"
        >{{ sessionError }} <button @click="loadSessions">重试课堂目录</button></view
      >
      <TeacherPager
        v-if="sessionTotal > 20"
        :total="sessionTotal"
        :offset="sessionOffset"
        @previous="paginateSessions(-20)"
        @next="paginateSessions(20)"
      />
      <view
        class="panels"
        role="tablist"
        aria-label="学情视图"
        ><button
          v-for="item in panels"
          :key="item.key"
          role="tab"
          :aria-selected="initialPanel === item.key"
          :class="[`insights-panel--${item.key}`, { selected: initialPanel === item.key }]"
          @click="selectPanel(item.key)"
        >
          {{ item.label }}
        </button></view
      >
      <MedState
        v-if="dateFrom && dateTo && dateFrom > dateTo"
        variant="error"
        icon="retry"
        title="日期范围无效"
        description="结束日期不能早于开始日期，请在顶部统计范围中调整。"
      />
      <TeacherInsightsReadWorkspace
        v-else
        ref="workspace"
        :panel="initialPanel"
        :filters="filters"
        :classes="classes"
        @open-student="openStudent"
        @select-panel="selectPanel"
        @scope="actualScope = $event"
      />
    </view>
    <view
      v-if="rangeOpen && scopeAllowed"
      class="range-mask"
      @click="rangeOpen = false"
      ><view
        class="range-sheet"
        @click.stop
        ><view class="range-heading"><text>统计范围</text><button @click="rangeOpen = false">完成</button></view
        ><text class="range-current"
          >{{
            actualScope
              ? `${actualScope.dateFrom} 至 ${actualScope.dateTo}`
              : `${dateFrom || '默认起始日期'} 至 ${dateTo || '默认结束日期'}`
          }}
          · 北京时间</text
        ><text class="range-note">未指定日期时使用最近30天；全部课堂也受日期限制。</text
        ><view class="date-filters"
          ><view
            ><text>开始日期</text
            ><picker
              mode="date"
              :value="dateFrom || actualScope?.dateFrom"
              @change="dateFrom = $event.detail.value"
              ><view>{{ dateFrom || '默认起始日期' }}</view></picker
            ></view
          ><view
            ><text>结束日期</text
            ><picker
              mode="date"
              :value="dateTo || actualScope?.dateTo"
              @change="dateTo = $event.detail.value"
              ><view>{{ dateTo || '默认结束日期' }}</view></picker
            ></view
          ></view
        ><button
          class="range-reset"
          @click="clearDates"
        >
          默认区间</button
        ><text
          v-if="dateFrom && dateTo && dateFrom > dateTo"
          class="range-error"
          >结束日期不能早于开始日期。</text
        ><text class="range-note"
          >批次测试按区间内发布路线统计，完成情况截至本次查询；下方已完成数量属于该发布批次，不是平均分的样本数。平均分与作答表现按测试完成时间，研讨次数按参与开始时间，诊断按研讨完成时间分别统计。</text
        ></view
      ></view
    >
  </TeacherPageFrame>
</template>
<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import type { TeacherInsightsScope } from '@/features/analytics/public'
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
const rangeOpen = ref(false)
const actualScope = ref<TeacherInsightsScope>()
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
  { key: 'knowledge', label: '知识与推理' },
  { key: 'students', label: '学生' },
]
const hero = computed(() =>
  initialPanel.value === 'knowledge'
    ? { title: '知识与推理', description: '从作答与研讨中，发现学习薄弱点' }
    : initialPanel.value === 'students'
      ? { title: '学生学习情况', description: '研讨进度与测试表现，一处查看' }
      : { title: '课堂学情概览', description: '从课堂事实，了解学习进展' },
)
const selectedSessionName = computed(() =>
  sessionId.value
    ? sessionOptions.value.find((item) => String(item.id) === String(sessionId.value))?.name.replace(/^.*? · /, '') ||
      `课堂 ${sessionId.value}`
    : '全部课堂',
)
function normalizePanel(panel?: TeacherInsightsPanel): TeacherInsightsPanel {
  return panel === 'progress' ? 'students' : panel || 'overview'
}
function selectPanel(panel: TeacherInsightsPanel) {
  initialPanel.value = normalizePanel(panel)
}
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
watch([classId, sessionId, dateFrom, dateTo], () => {
  actualScope.value = undefined
})
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
  initialPanel.value = normalizePanel(target.panel)
  sessionId.value = target.sessionId
  dateFrom.value = target.dateFrom
  dateTo.value = target.dateTo
  initialTarget = target
})
async function refresh() {
  const actor = getSession()
  if (actor?.role === 'teacher' && preferenceIdentity !== actor.openid) {
    preferenceIdentity = actor.openid
    rangeOpen.value = false
    actualScope.value = undefined
    const saved = readTeacherInsightsPreference(actor.openid)
    const restored = parseTeacherWorkspaceTarget({
      tab: 'insights',
      panel: saved?.panel,
      sessionId: saved?.sessionId === undefined ? undefined : String(saved.sessionId),
      dateFrom: saved?.dateFrom,
      dateTo: saved?.dateTo,
    })
    if (restored.workspace === 'insights') {
      initialPanel.value = normalizePanel(initialTarget?.panel || restored.panel)
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
  gap: 18rpx;
  --insights-ink: #0000b4;
  color: var(--insights-ink);
}
.insights-hero {
  box-sizing: border-box;
  position: relative;
  min-height: 148rpx;
  margin: 0 -22rpx;
  padding: 46rpx 36rpx 0;
  overflow: hidden;
}
.insights-hero__waves {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
.insights-hero__art {
  position: absolute;
  right: 42rpx;
  top: 0;
  width: 220rpx;
  height: 166rpx;
}
.insights-hero__title {
  position: relative;
  display: block;
  width: 73%;
  color: #0000b4;
  font-size: 40rpx;
  line-height: 1.3;
  font-weight: 750;
}
.insights-hero__description {
  position: relative;
  width: 73%;
  display: flex;
  align-items: center;
  min-height: 44rpx;
  margin: 0;
  padding: 0;
  background: transparent;
  color: #304cff;
  text-align: left;
  font-size: 24rpx;
  line-height: 1.5;
}
.insights-hero__description::after,
.panels button::after,
.range-sheet button::after,
.scope-note button::after {
  border: 0;
}
.scope-pickers {
  display: flex;
  gap: 14rpx;
}
.scope-pickers__item {
  flex: 1;
  width: 0;
  min-width: 0;
}
.scope-picker {
  box-sizing: border-box;
  min-height: 56rpx;
  display: flex;
  align-items: center;
  gap: 12rpx;
  padding: 0 18rpx;
  border: 1rpx solid #96d7ff;
  border-radius: 10rpx;
  background: rgba(255, 255, 255, 0.88);
  font-size: 24rpx;
  font-weight: 650;
  line-height: 1.4;
}
.scope-pickers__item {
  min-height: 56rpx;
  display: flex;
  align-items: stretch;
}
.scope-picker {
  width: 346rpx;
}
.scope-picker image {
  flex: none;
  width: 32rpx;
  height: 32rpx;
}
.scope-picker text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.scope-picker__arrow {
  flex: none;
  width: 12rpx;
  height: 12rpx;
  margin-left: 6rpx;
  margin-top: -6rpx;
  border-right: 3rpx solid #8d98cd;
  border-bottom: 3rpx solid #8d98cd;
  transform: rotate(45deg);
}
.panels {
  display: flex;
  padding: 2rpx;
  border: 1rpx solid #cee9ff;
  border-radius: 26rpx;
  background: rgba(238, 249, 255, 0.7);
}
.panels button {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 0;
  min-height: 54rpx;
  margin: 0;
  padding: 10rpx 4rpx;
  border-radius: 26rpx;
  font-size: 24rpx;
  font-weight: 650;
  line-height: 1.4;
  background: transparent;
  color: #7b88c2;
}
.panels .selected {
  color: #fff;
  background: linear-gradient(115deg, #14e4df, #00bbd5);
  box-shadow:
    inset 0 2rpx 5rpx #9cf9f4,
    0 3rpx 8rpx #aeefee;
}
.scope-note {
  font-size: 24rpx;
  color: #697fab;
}
.scope-note button {
  min-height: 44px;
  margin: 0;
  background: #fff;
  color: #178dff;
  font-size: 24rpx;
}
.range-mask {
  position: fixed;
  inset: 0;
  z-index: 40;
  display: flex;
  align-items: flex-end;
  background: rgba(10, 30, 70, 0.25);
}
.range-sheet {
  box-sizing: border-box;
  width: 100%;
  max-height: 80vh;
  overflow-y: auto;
  padding: 28rpx 28rpx calc(28rpx + env(safe-area-inset-bottom));
  border-radius: 24rpx 24rpx 0 0;
  background: #fff;
  color: #0000b4;
}
.range-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 32rpx;
  font-weight: 700;
}
.range-heading button {
  min-height: 44px;
  margin: 0;
  background: transparent;
  color: #008a9e;
  font-size: 26rpx;
}
.range-current {
  display: block;
  font-size: 26rpx;
  margin: 12rpx 0;
}
.range-note {
  display: block;
  margin-top: 16rpx;
  color: #62769e;
  font-size: 24rpx;
  line-height: 1.6;
}
.date-filters {
  display: flex;
  gap: 20rpx;
  margin-top: 24rpx;
}
.date-filters > view {
  flex: 1;
  font-size: 24rpx;
}
.date-filters picker {
  display: flex;
  align-items: center;
  min-height: 44px;
  margin-top: 8rpx;
  padding: 0 16rpx;
  border: 1rpx solid #cee9ff;
  border-radius: 10rpx;
  background: #effaff;
}
.range-reset {
  min-height: 44px;
  margin: 20rpx 0 0;
  background: #e8faff;
  color: #008a9e;
  font-size: 24rpx;
}
.range-error {
  display: block;
  margin-top: 16rpx;
  color: #a34d2a;
  font-size: 24rpx;
}
</style>
