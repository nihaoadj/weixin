<template>
  <view
    class="classrooms"
    :class="{ 'classrooms--reference': referenceLayout, 'classrooms--fixed-records': fixedRecords }"
  >
    <view
      v-if="referenceLayout && !createOnly"
      class="reference-filters"
    >
      <view class="reference-filters__class"><slot name="class-picker" /></view>
      <picker
        class="classroom-picker"
        :range="classroomOptions"
        range-key="label"
        :value="classroomIndex"
        :disabled="opening || creating || closing"
        aria-label="课堂选择与管理"
        @change="changeClassroom"
      >
        <view class="classroom-picker__value"
          ><image
            src="/static/pbl-reference-document.svg"
            mode="aspectFit" /><text>{{ dashboard ? selectedClassroomTitle : '选择课堂' }}</text
          ><view
            class="classroom-picker__arrow"
            aria-hidden="true"
        /></view>
      </picker>
    </view>
    <view
      v-if="!referenceLayout && !createOnly && !dashboard"
      class="toolbar"
    >
      <picker
        class="toolbar-status"
        :range="statusOptions"
        range-key="label"
        role="button"
        tabindex="0"
        @keydown="activatePickerOnKey"
        @change="changeStatus"
        ><view class="toolbar-status__value">{{ statusLabel }} <text>⌄</text></view></picker
      >
      <button
        class="create-toggle"
        :disabled="!classes.length"
        :tabindex="classes.length ? 0 : -1"
        role="button"
        @keydown="activateButtonOnKey"
        @click="showCreate = !showCreate"
      >
        {{ showCreate ? '收起创建' : '+ 创建课堂' }}
      </button>
    </view>
    <scroll-view
      v-if="createOnly || showCreate"
      class="classroom-management-scroll"
      :scroll-y="fixedRecords"
    >
      <view
        class="create-form"
        @touchstart.stop
        @touchend.stop
      >
        <view class="create-form__heading"
          ><text class="form-heading">创建课堂</text
          ><button
            v-if="referenceLayout && !createOnly"
            class="create-cancel"
            :disabled="creating"
            @click="showCreate = false"
          >
            取消
          </button></view
        >
        <label class="form-field">
          <text class="form-label">授课班级</text>
          <picker
            class="form-picker"
            :range="classes"
            range-key="name"
            :disabled="Boolean(classId)"
            role="button"
            tabindex="0"
            @keydown="activatePickerOnKey"
            @change="creationClassIndex = Number($event.detail.value)"
            ><view class="form-picker__value">{{ creationClass?.name || '请选择班级' }}</view></picker
          >
        </label>
        <text
          v-if="creationClass?.status === 'archived'"
          class="state"
          >该班级已归档，可查看历史课堂，不能创建新课堂。</text
        >
        <label class="form-field">
          <text class="form-label">教学病例</text>
          <picker
            class="form-picker"
            :range="reviewedCases"
            range-key="title"
            role="button"
            tabindex="0"
            @keydown="activatePickerOnKey"
            @change="caseIndex = Number($event.detail.value)"
            ><view class="form-picker__value">{{ reviewedCases[caseIndex]?.title || '请选择' }}</view></picker
          >
        </label>
        <label class="form-field">
          <text class="form-label">课堂主题</text>
          <input
            v-model="topicCode"
            class="topic-input"
            aria-label="课堂主题"
            placeholder="例如：肾小球病变的证据推理"
          />
        </label>
        <view class="goal-options">
          <text class="goal-options__label">知识点（选择 1 项）</text>
          <radio-group
            class="goal-option-group"
            @change="selectGoal"
          >
            <label
              v-for="point in caseKnowledgePoints"
              :key="point.code"
              class="goal-option"
            >
              <radio
                class="goal-option__check"
                name="classroom-goal"
                :value="point.code"
                :checked="selectedGoalCodes.includes(point.code)"
              />
              <text>{{ point.title }}</text>
            </label>
          </radio-group>
        </view>
        <button
          class="create-submit"
          :disabled="creating || !canCreate"
          :tabindex="creating || !canCreate ? -1 : 0"
          role="button"
          @keydown="activateButtonOnKey"
          @click="create"
        >
          创建课堂
        </button>
      </view>
    </scroll-view>
    <view
      v-if="error"
      role="alert"
      >{{ error }}
      <button
        role="button"
        tabindex="0"
        @keydown="activateButtonOnKey"
        @click="load"
      >
        重试
      </button></view
    >
    <text v-else-if="loading || opening">正在加载课堂…</text>
    <text
      v-else-if="referenceLayout && !createOnly && !dashboard && !items.length && !showCreate"
      class="empty-copy"
      >当前范围还没有课堂，请在课堂下拉菜单中选择“新建课堂”。</text
    >
    <view
      v-else-if="!createOnly && !referenceLayout"
      class="session-list"
      :class="{ 'session-list--dashboard-open': dashboard }"
    >
      <text
        v-if="!items.length"
        class="empty-copy"
        >当前范围还没有课堂。选择一个负责班级后可以创建课堂。</text
      >
      <button
        v-for="item in items"
        :key="item.id"
        class="session-row"
        :class="{ 'session-row--active': item.status !== 'closed' }"
        role="button"
        tabindex="0"
        @keydown="activateButtonOnKey"
        @click="open(item)"
      >
        <text class="session-row__title">{{ item.className }} · {{ displayTopic(item.topicCode) }}</text
        ><view class="session-row__meta"
          ><text :class="['session-row__status', `is-${item.status}`]">{{ displaySessionStatus(item.status) }}</text
          ><text>{{ formatSessionTime(item.createdAt) }}</text></view
        ><text class="session-row__action">{{ item.status === 'closed' ? '查看课堂记录' : '查看阶段看板' }}</text>
      </button>
      <TeacherPager
        :total="total"
        :offset="offset"
        @previous="previousPage"
        @next="nextPage"
      />
    </view>
    <view
      v-if="!createOnly && dashboard && !(referenceLayout && showCreate)"
      class="dashboard"
    >
      <button
        v-if="!referenceLayout"
        class="dashboard-back"
        role="button"
        tabindex="0"
        @keydown="activateButtonOnKey"
        @click="leaveDashboard"
      >
        返回课堂列表
      </button>
      <view
        v-if="!referenceLayout"
        class="dashboard-heading"
        ><view
          ><text class="dashboard-eyebrow">{{
            dashboard.session.status === 'closed' ? '已关闭课堂 · 历史记录' : '进行中课堂'
          }}</text
          ><text class="dashboard-title">{{ selectedClassroomTitle }}</text></view
        ><button
          v-if="dashboard.session.status !== 'closed' && canClose"
          class="close-session"
          :disabled="closing"
          role="button"
          tabindex="0"
          @keydown="activateButtonOnKey"
          @click="close"
        >
          关闭课堂
        </button></view
      >
      <view
        v-if="!referenceLayout"
        class="classroom-metrics"
      >
        <view class="classroom-metric"
          ><text class="classroom-metric__number"
            >{{ dashboard.summary.participants ?? '—' }}<text class="classroom-metric__unit">人</text></text
          ><text>参与学生</text></view
        >
        <view class="classroom-metric"
          ><text class="classroom-metric__number"
            >{{ dashboard.summary.publishedRoutes ?? '—' }}<text class="classroom-metric__unit">条</text></text
          ><text>已发布路线</text></view
        >
        <view class="classroom-metric"
          ><text class="classroom-metric__number"
            >{{ dashboard.summary.completedRoutes ?? '—' }}<text class="classroom-metric__unit">份</text></text
          ><text>完成测试</text></view
        >
      </view>
      <view
        v-if="!referenceLayout"
        class="student-list-heading"
        ><text>学生研讨进度</text><text class="student-list-heading__note">分析与测试分别查看</text></view
      >
      <text
        v-if="!dashboard.students.length"
        class="empty-copy"
        >暂无学生参与，学生进入课堂后会在这里显示。</text
      >
      <template v-if="referenceLayout">
        <view class="reference-metrics">
          <view
            v-for="metric in referenceMetrics"
            :key="metric.label"
            class="reference-metric"
            ><view :class="['reference-metric__icon', 'reference-metric__icon--' + metric.kind]"
              ><image
                :src="metric.icon"
                mode="aspectFit" /></view
            ><view
              ><text class="reference-metric__label">{{ metric.label }}</text
              ><text class="reference-metric__number">{{ metric.value }}<text>人</text></text></view
            ></view
          >
        </view>
        <text
          v-if="dashboard.session.status === 'closed'"
          class="closed-copy"
          >已关闭课堂 · 历史记录</text
        >
        <view
          v-for="group in studentGroups"
          :key="group.label"
          class="reference-group"
        >
          <view class="reference-group__heading"
            ><text>{{ group.label }}</text
            ><text>{{ group.students.length }}人</text></view
          >
          <text
            v-if="!group.students.length"
            class="empty-copy"
            >暂无研讨完成学生，学生完成研讨后会在这里显示。</text
          >
          <scroll-view
            :key="`${classId || 'all'}:${dashboard.session.id}`"
            class="reference-records-scroll"
            :scroll-y="fixedRecords"
            enhanced
            :show-scrollbar="false"
            aria-label="研讨完成学生列表"
          >
            <view
              class="reference-students"
              :class="{ 'reference-students--balanced': firstPageGridStyle }"
              :style="firstPageGridStyle"
            >
              <view
                v-for="student in group.students.slice(0, visibleStudents)"
                :key="student.studentId"
                class="reference-student"
              >
                <view class="reference-student__top"
                  ><text class="reference-student__name">{{ student.studentName }}</text
                  ><view class="reference-student__phase"
                    ><text
                      :class="['reference-student__check', { 'is-active': student.currentPhase !== 'completed' }]"
                      >{{ student.currentPhase === 'completed' ? '✓' : '◷' }}</text
                    ><text>{{
                      student.currentPhase === 'completed' ? '研讨完成' : phaseLabel(student.currentPhase)
                    }}</text></view
                  ><text :class="['reference-student__badge', { 'is-published': routePublished(student) }]">{{
                    routePublished(student) ? '已发布' : '未发布'
                  }}</text></view
                >
                <text class="reference-student__progress"
                  >学习进度 {{ student.taskProgress.completed }}/{{ student.taskProgress.total }}项</text
                >
                <view class="reference-student__actions"
                  ><button
                    :disabled="!student.snapshotId"
                    @click="openDiagnostic(student.snapshotId)"
                  >
                    <image
                      src="/static/pbl-reference-document.svg"
                      mode="aspectFit"
                    />固定诊断</button
                  ><button
                    class="reference-student__test"
                    :disabled="!student.finalTestId"
                    @click="$emit('openFinalTest', student.finalTestId!)"
                  >
                    <image
                      src="/static/pbl-reference-test.svg"
                      mode="aspectFit"
                    />最终测试
                  </button></view
                >
              </view>
            </view>
            <button
              v-if="group.students.length > visibleStudents"
              class="reference-more"
              @click="visibleStudents += 8"
            >
              ⌄ 下拉查看更多 ⌄
            </button>
          </scroll-view>
        </view>
      </template>
      <view
        v-if="!referenceLayout"
        class="legacy-students"
      >
        <view
          v-for="student in dashboard.students"
          :key="student.studentId"
          class="student-row"
        >
          <view class="student-summary">
            <view class="student-identity"
              ><text class="student-name">{{ student.studentName }}</text
              ><text
                class="student-phase"
                :class="{ 'student-phase--completed': student.currentPhase === 'completed' }"
                >{{ phaseLabel(student.currentPhase) }}</text
              ></view
            >
            <text class="student-progress-copy">{{
              student.learningRouteId
                ? `学习进度 ${student.taskProgress.completed}/${student.taskProgress.total} 项`
                : student.currentPhase === 'completed'
                  ? '研讨已完成'
                  : '研讨进行中'
            }}</text>
          </view>
          <view
            class="phase-track"
            :aria-label="`当前阶段：${phaseLabel(student.currentPhase)}`"
          >
            <view
              v-for="(phase, index) in discussionPhases"
              :key="phase.key"
              class="phase-step"
              :class="phaseStepClass(student.currentPhase, index)"
            >
              <view class="phase-step__node"
                ><text>{{ phaseIsDone(student.currentPhase, index) ? '✓' : index + 1 }}</text></view
              ><text class="phase-step__label">{{ phase.label }}</text>
            </view>
          </view>
          <view class="student-actions">
            <button
              v-if="student.snapshotId"
              role="button"
              tabindex="0"
              @keydown="activateButtonOnKey"
              @click="openDiagnostic(student.snapshotId)"
            >
              查看固定诊断
            </button>
            <button
              v-if="student.finalTestId"
              role="button"
              tabindex="0"
              @keydown="activateButtonOnKey"
              @click="$emit('openFinalTest', student.finalTestId!)"
            >
              查看最终测试
            </button>
            <text v-if="!student.snapshotId && !student.learningRouteId">等待学生完成课堂研讨</text>
            <text v-if="student.learningRouteId && !student.finalTestId"
              >学习路线 {{ student.routeStatus || '处理中' }}</text
            >
          </view>
        </view>
      </view>
      <button
        v-if="!referenceLayout"
        class="classroom-insights"
        @click="$emit('openInsights', { classId: dashboard.session.classId, sessionId: dashboard.session.id })"
      >
        查看课堂学情 <text>›</text>
      </button>
    </view>
  </view>
</template>
<script setup lang="ts">
import { computed, getCurrentInstance, onMounted, onUnmounted, ref, watch } from 'vue'
import TeacherPager from '@/components/teacher/TeacherPager.vue'
import { displayTopicCode } from '@/components/teacher/topicLabel'
import { activateButtonOnKey, activatePickerOnKey } from '@/components/ui/keyboard'
import { getGuidedCasesAsync } from '@/features/content/public'
import { getKnowledgeCatalog, type KnowledgePoint } from '@/features/learning/public'
import {
  closePblSession,
  createPblSession,
  getTeacherPblDashboard,
  getTeacherPblSessionPage,
  type TeacherPblDashboard,
  type TeacherPblSession,
} from '@/features/pbl/public'

const props = defineProps<{
  classId?: string
  sessionId?: string
  classes: Array<{ id: number; name: string; status?: 'active' | 'archived' }>
  referenceLayout?: boolean
  fixedRecords?: boolean
  createOnly?: boolean
}>()
const emit = defineEmits<{
  openTestQueue: []
  created: [sessionId: string]
  openDiagnostic: [snapshotId: string]
  openFinalTest: [finalTestId: string]
  openInsights: [context: { classId: string; sessionId: string }]
  sessionChange: [sessionId: string | undefined]
}>()
const items = ref<TeacherPblSession[]>([])
const dashboard = ref<TeacherPblDashboard>()
const reviewedCases = ref<Awaited<ReturnType<typeof getGuidedCasesAsync>>>([])
const knowledgeCatalog = ref<KnowledgePoint[]>([])
const loading = ref(false)
const creating = ref(false)
const closing = ref(false)
const opening = ref(false)
const error = ref('')
const offset = ref(0)
const total = ref(0)
const selectedStatus = ref<string>()
const showCreate = ref(Boolean(props.createOnly))
const selectedClassroomTitle = computed(() => {
  const selected = items.value.find((item) => item.id === dashboard.value?.session.id)
  return selected ? displayTopic(selected.topicCode) : '课堂阶段看板'
})
const visibleStudents = ref(8)
const studentGroups = computed(() => [
  {
    label: '研讨完成学生',
    students: (dashboard.value?.students || []).filter((student) => student.currentPhase === 'completed'),
  },
])
const instance = getCurrentInstance()
const recordsHeight = ref(0)
let recordsMeasurement = 0
const firstPageGridStyle = computed(() => {
  const count = studentGroups.value[0].students.length
  if (!props.fixedRecords || visibleStudents.value !== 8 || count < 8 || !recordsHeight.value) return
  // Keep the more action reachable without requiring a partially hidden fifth row.
  const reserved = count > 8 ? 44 : 0
  return { minHeight: `${Math.max(0, recordsHeight.value - reserved - 2)}px` }
})
function measureRecords() {
  const measurement = ++recordsMeasurement
  recordsHeight.value = 0
  if (!props.fixedRecords || showCreate.value || !dashboard.value || !instance?.proxy || !uni.createSelectorQuery)
    return
  // The Mini Program $nextTick waits for setData to finish, unlike Vue's render queue alone.
  instance.proxy.$nextTick(() => {
    if (!active || measurement !== recordsMeasurement) return
    uni
      .createSelectorQuery()
      .in(instance.proxy)
      .select('.reference-records-scroll')
      .boundingClientRect((result) => {
        if (!active || measurement !== recordsMeasurement) return
        const rectangle = Array.isArray(result) ? result[0] : result
        const height = rectangle?.height
        if (typeof height === 'number' && Number.isFinite(height) && height > 0)
          recordsHeight.value = Math.floor(height)
      })
      .exec()
  })
}
watch([dashboard, showCreate, () => props.fixedRecords], measureRecords, { flush: 'post' })
const referenceMetrics = computed(() => {
  const summary = dashboard.value?.summary
  const phases = summary?.phaseCounts
  const completed = phases ? (phases.completed ?? 0) : undefined
  const ongoing = phases
    ? Object.entries(phases)
        .filter(([phase]) => phase !== 'completed')
        .reduce((sum, [, count]) => sum + count, 0)
    : undefined
  return [
    {
      label: '参与学生',
      value: summary?.participants ?? '—',
      kind: 'people',
      icon: '/static/pbl-reference-people.svg',
    },
    { label: '研讨进行中', value: ongoing ?? '—', kind: 'clock', icon: '/static/pbl-reference-clock.svg' },
    { label: '研讨完成', value: completed ?? '—', kind: 'done', icon: '/static/pbl-reference-done.svg' },
    {
      label: '测试完成',
      value: summary?.completedRoutes ?? '—',
      kind: 'test',
      icon: '/static/pbl-reference-results.svg',
    },
  ]
})
function routePublished(student: TeacherPblDashboard['students'][number]) {
  return [
    'published',
    'in_progress',
    'learning',
    'waiting_test_generation',
    'waiting_teacher',
    'ready_for_test',
    'testing',
    'grading',
    'completed',
  ].includes(student.routeStatus || '')
}
const classroomOptions = computed(() => [
  { label: '请选择课堂 / 管理操作', action: 'placeholder' },
  ...items.value.map((item) => ({
    label: `${displayTopic(item.topicCode)}${item.status === 'closed' ? '（已关闭）' : ''}`,
    action: item.id,
    session: item,
  })),
  ...(props.classes.some((item) => item.status !== 'archived' && (!props.classId || String(item.id) === props.classId))
    ? [{ label: '+ 新建课堂', action: 'create' }]
    : []),
  ...(dashboard.value && dashboard.value.session.status !== 'closed' && canClose.value
    ? [{ label: '关闭当前课堂', action: 'close' }]
    : []),
  { label: '查看课堂学情', action: 'insights' },
  { label: '跨课堂测试待办', action: 'queue' },
  ...(offset.value > 0 ? [{ label: '上一页课堂', action: 'previous' }] : []),
  ...(offset.value + items.value.length < total.value ? [{ label: '下一页课堂', action: 'next' }] : []),
])
const classroomIndex = computed(() =>
  Math.max(
    0,
    classroomOptions.value.findIndex((item) => item.action === dashboard.value?.session.id),
  ),
)
function changeClassroom(event: { detail: { value: string } }) {
  const option = classroomOptions.value[Number(event.detail.value)]
  if (!option) return
  if ('session' in option && option.session) {
    showCreate.value = false
    visibleStudents.value = 8
    void open(option.session)
    return
  }
  if (option.action === 'create') showCreate.value = true
  if (option.action === 'close') void close()
  if (option.action === 'queue') emit('openTestQueue')
  if (option.action === 'insights' && dashboard.value)
    emit('openInsights', { classId: dashboard.value.session.classId, sessionId: dashboard.value.session.id })
  if (option.action === 'previous') previousPage()
  if (option.action === 'next') nextPage()
}
const discussionPhases = [
  { key: 'problem_framing', label: '界定问题' },
  { key: 'hypothesis', label: '提出假设' },
  { key: 'evidence', label: '搜集证据' },
  { key: 'synthesis', label: '形成综合' },
]
function phaseIsDone(currentPhase: string, index: number) {
  return currentPhase === 'completed' || discussionPhases.findIndex((phase) => phase.key === currentPhase) > index
}
function phaseStepClass(currentPhase: string, index: number) {
  return {
    'phase-step--done': phaseIsDone(currentPhase, index),
    'phase-step--current': discussionPhases[index]?.key === currentPhase,
  }
}
const caseIndex = ref(0)
const topicCode = ref('')
const selectedGoalCodes = ref<string[]>([])
const creationClassIndex = ref(0)
let listRequest = 0
let dashboardRequest = 0
let active = true
const statusOptions = [
  { label: '全部状态', value: undefined },
  { label: '进行中', value: 'active' },
  { label: '已关闭', value: 'closed' },
] as const
const statusLabel = computed(() => statusOptions.find((item) => item.value === selectedStatus.value)?.label)
const creationClassId = computed(
  () =>
    props.classId ||
    (props.classes[creationClassIndex.value] ? String(props.classes[creationClassIndex.value].id) : undefined),
)
const creationClass = computed(() => props.classes.find((item) => String(item.id) === creationClassId.value))
const canClose = computed(() => {
  const current = props.classes.find((item) => String(item.id) === (props.classId || dashboard.value?.session.classId))
  return Boolean(current && current.status !== 'archived')
})
const caseKnowledgePoints = computed(() => {
  const selected = reviewedCases.value[caseIndex.value]
  const codes = selected?.knowledgePointCodes || []
  return knowledgeCatalog.value.filter((point) => codes.includes(point.code))
})
const canCreate = computed(() => {
  return Boolean(
    creationClassId.value &&
    creationClass.value &&
    creationClass.value.status !== 'archived' &&
    reviewedCases.value[caseIndex.value] &&
    topicCode.value.trim() &&
    selectedGoalCodes.value.length === 1,
  )
})
async function load() {
  if (!active) return
  const token = ++listRequest
  loading.value = true
  error.value = ''
  try {
    const [page, cases, points] = await Promise.all([
      getTeacherPblSessionPage({ classId: props.classId, status: selectedStatus.value, offset: offset.value }),
      getGuidedCasesAsync(),
      getKnowledgeCatalog(),
    ])
    if (token !== listRequest) return
    items.value = page.items
    total.value = page.total
    reviewedCases.value = cases
    knowledgeCatalog.value = points
    if (props.sessionId) {
      const matching = page.items.find((item) => item.id === props.sessionId)
      const sessionClass =
        props.classId ||
        matching?.classId ||
        (dashboard.value?.session.id === props.sessionId ? dashboard.value.session.classId : undefined)
      if (sessionClass)
        await open({
          id: props.sessionId,
          classId: sessionClass,
          className: matching?.className || '当前班级',
          topicCode: matching?.topicCode || '',
          status: matching?.status || 'active',
        })
      else error.value = '请选择该课堂所属班级后查看课堂记录。'
    } else if (props.referenceLayout && !props.createOnly && page.items[0]) {
      await open(page.items[0])
    }
  } catch (reason) {
    if (token === listRequest) error.value = reason instanceof Error ? reason.message : '课堂加载失败'
  } finally {
    if (token === listRequest) loading.value = false
  }
}
async function open(item: TeacherPblSession) {
  if (!active) return
  const classId = props.classId || item.classId
  if (!classId) return
  const token = ++dashboardRequest
  opening.value = true
  error.value = ''
  try {
    const value = await getTeacherPblDashboard(classId, item.id)
    if (token === dashboardRequest) {
      visibleStudents.value = 8
      dashboard.value = value
      emit('sessionChange', value.session.id)
    }
  } catch (reason) {
    if (token === dashboardRequest) error.value = reason instanceof Error ? reason.message : '课堂阶段看板加载失败'
  } finally {
    if (token === dashboardRequest) opening.value = false
  }
}
async function create() {
  if (creating.value || !creationClassId.value || !canCreate.value) return
  const classId = creationClassId.value
  const context = dashboardRequest
  creating.value = true
  try {
    const session = await createPblSession(classId, topicCode.value.trim(), reviewedCases.value[caseIndex.value].id, [
      ...selectedGoalCodes.value,
    ])
    if (context !== dashboardRequest || creationClassId.value !== classId) return
    showCreate.value = false
    topicCode.value = ''
    selectedGoalCodes.value = []
    await load()
    if (!active || creationClassId.value !== classId) return
    await open({
      id: session.id,
      classId,
      className: props.classes.find((item) => String(item.id) === classId)?.name || '当前班级',
      topicCode: session.topicCode,
      status: session.status,
    })
    if (dashboard.value?.session.id === session.id && creationClassId.value === classId) emit('created', session.id)
  } catch (reason) {
    if (context === dashboardRequest && creationClassId.value === classId)
      error.value = reason instanceof Error ? reason.message : '课堂创建失败'
  } finally {
    creating.value = false
  }
}
async function close() {
  if (closing.value || !dashboard.value || !canClose.value) return
  const classId = props.classId || dashboard.value.session.classId
  if (!classId) return
  closing.value = true
  const selected = { ...dashboard.value.session }
  const context = dashboardRequest
  try {
    await closePblSession(classId, selected.id)
    if (context !== dashboardRequest) return
    await open({
      ...selected,
      className: props.classes.find((item) => String(item.id) === classId)?.name || '当前班级',
      topicCode: '',
    })
    await load()
  } catch (reason) {
    if (context === dashboardRequest) error.value = reason instanceof Error ? reason.message : '课堂关闭失败'
  } finally {
    closing.value = false
  }
}
function leaveDashboard() {
  dashboardRequest += 1
  dashboard.value = undefined
  emit('sessionChange', undefined)
}
function changeStatus(event: { detail: { value: string } }) {
  selectedStatus.value = statusOptions[Number(event.detail.value)].value
  offset.value = 0
  load()
}
function previousPage() {
  offset.value -= 20
  load()
}
function nextPage() {
  offset.value += 20
  load()
}
function openDiagnostic(snapshotId?: string) {
  if (snapshotId) emit('openDiagnostic', snapshotId)
}
function selectGoal(event: { detail?: { value?: string | number } }) {
  const code = String(event.detail?.value || '')
  if (caseKnowledgePoints.value.some((point) => point.code === code)) selectedGoalCodes.value = [code]
}
function displaySessionStatus(value: string) {
  return value === 'closed' ? '已关闭' : '进行中'
}
function displayTopic(value: string) {
  const matchingPoint = knowledgeCatalog.value.find((point) => point.code === value)
  if (matchingPoint) return matchingPoint.title
  return displayTopicCode(value)
}
function formatSessionTime(value?: string) {
  if (!value) return '刚刚创建'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const parts = new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).formatToParts(date)
  const field = (type: Intl.DateTimeFormatPartTypes) => parts.find((part) => part.type === type)?.value || ''
  return `${field('year')}年${field('month')}月${field('day')}日 ${field('hour')}:${field('minute')}`
}
function phaseLabel(value: string) {
  return (
    (
      {
        problem_framing: '界定问题',
        hypothesis: '提出假设',
        evidence: '搜集证据',
        synthesis: '形成综合',
        completed: '讨论完成',
      } as Record<string, string>
    )[value] || '讨论中'
  )
}
watch(caseKnowledgePoints, () => {
  selectedGoalCodes.value = []
})
watch(
  () => props.classId,
  () => {
    dashboardRequest += 1
    opening.value = false
    offset.value = 0
    dashboard.value = undefined
    showCreate.value = Boolean(props.createOnly)
    load()
  },
)
watch(
  () => props.sessionId,
  (value) => {
    if (!value) {
      dashboardRequest += 1
      dashboard.value = undefined
    } else if (dashboard.value?.session.id !== value) void load()
  },
)
onMounted(() => {
  load()
  uni.onWindowResize?.(measureRecords)
})
onUnmounted(() => {
  active = false
  recordsMeasurement += 1
  uni.offWindowResize?.(measureRecords)
  listRequest += 1
  dashboardRequest += 1
})
defineExpose({
  refresh: load,
  beginCreate: () => {
    showCreate.value = true
  },
})
</script>
<style scoped>
.classrooms,
.create-form,
.session-list,
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}
.toolbar,
.dashboard-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
}
.toolbar {
  min-height: 88rpx;
  padding: 4rpx 0;
  border-bottom: 1rpx solid var(--med-divider);
}
.toolbar-status {
  min-width: 0;
  flex: 1;
}
.toolbar-status__value,
.form-picker__value,
.topic-input {
  min-height: 72rpx;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  color: var(--med-text);
  font-size: 26rpx;
  line-height: 1.4;
}
.toolbar-status__value {
  color: var(--med-muted);
}
.toolbar button,
.create-submit,
.dashboard-heading > button,
.dashboard-back {
  min-height: 88rpx;
  margin: 0;
  padding: 0 24rpx;
  border: 0;
  border-radius: 6rpx;
  font-size: 26rpx;
  line-height: 88rpx;
}
.create-toggle {
  color: #fff;
  background: var(--med-clinical);
}
.dashboard-back {
  color: var(--med-clinical);
  background: var(--med-wash);
}
.close-session {
  color: var(--med-safety-text);
  background: transparent;
  border: 1rpx solid var(--med-safety-border);
}
.create-form,
.dashboard {
  gap: 16rpx;
  padding: 24rpx 0;
  border-top: 1rpx solid var(--med-divider);
}
.form-heading {
  color: var(--med-ink);
  font-size: 30rpx;
  font-weight: 700;
}
.form-field {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 6rpx;
}
.form-label {
  color: var(--med-muted);
  font-size: 23rpx;
}
.form-picker__value,
.topic-input {
  width: 100%;
  padding: 0 16rpx;
  box-sizing: border-box;
  border: 1rpx solid var(--med-border);
  border-radius: 4rpx;
  background: var(--med-surface);
}
.topic-input {
  display: block;
  padding-top: 16rpx;
  padding-bottom: 16rpx;
}
.goal-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8rpx 16rpx;
}
.goal-option-group {
  width: 100%;
  display: flex;
  flex-wrap: wrap;
  gap: 8rpx 16rpx;
}
.goal-options__label {
  width: 100%;
  color: var(--med-muted);
  font-size: 24rpx;
}
.goal-option {
  min-width: 0;
  min-height: 88rpx;
  width: calc(50% - 8rpx);
  display: flex;
  align-items: center;
  gap: 8rpx;
  color: var(--med-text);
  font-size: 26rpx;
  line-height: 1.35;
}
.goal-option__check {
  flex: none;
  transform: scale(0.78);
  transform-origin: center;
}
.create-submit {
  color: #fff;
  background: var(--med-clinical);
}
.create-submit[disabled] {
  color: var(--med-muted);
  background: var(--med-wash);
}
.session-row,
.student-row {
  display: flex;
  flex-direction: column;
  gap: 6rpx;
  margin: 0;
  padding: 18rpx 0;
  background: transparent;
  border-top: 1rpx solid var(--med-divider);
  border-radius: 0;
  text-align: left;
}
.session-row {
  gap: 10rpx;
}
.session-row--active {
  border-left: 6rpx solid var(--med-clinical);
  padding-left: 16rpx;
}
.session-row__title {
  color: var(--med-ink);
  font-size: 28rpx;
  font-weight: 700;
  line-height: 1.45;
  overflow-wrap: anywhere;
}
.session-row__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8rpx 14rpx;
  color: var(--med-muted);
  font-size: 24rpx;
  line-height: 1.4;
}
.session-row__status {
  color: var(--med-clinical);
  font-weight: 650;
}
.session-row__status.is-closed {
  color: var(--med-muted);
}
.session-row__action {
  color: var(--med-clinical);
  font-size: 24rpx;
  font-weight: 650;
}
.student-row {
  color: var(--med-text);
}
.student-summary,
.student-actions {
  display: flex;
  gap: 10rpx;
}
.student-summary {
  flex-direction: column;
}
.student-actions {
  min-height: 44px;
  align-items: center;
  flex-wrap: wrap;
}
.student-actions button {
  min-height: 44px;
  margin: 0;
  padding: 0 20rpx;
  color: var(--med-clinical);
  background: var(--med-wash);
  font-size: 22rpx;
}
.dashboard-back {
  min-height: 44px;
}
.classroom-insights {
  min-height: 44px;
  margin: 0;
  color: var(--med-clinical);
  background: var(--med-wash);
  font-size: 26rpx;
}
@media screen and (max-width: 767px) {
  .session-list--dashboard-open {
    display: none;
  }
}
@media screen and (max-width: 360px) {
  .toolbar {
    align-items: flex-start;
  }
  .toolbar button {
    padding: 0 16rpx;
  }
  .goal-option {
    width: 100%;
  }
}
@media screen and (min-width: 768px) {
  .dashboard-back {
    display: none;
  }
}
.student-actions text,
.empty-copy {
  color: var(--med-muted);
  font-size: 22rpx;
}
@media screen and (min-width: 600px) {
  .classrooms,
  .create-form,
  .session-list,
  .dashboard,
  .toolbar-status__value,
  .form-picker__value,
  .topic-input,
  .goal-option,
  .student-actions button,
  .student-actions text,
  .empty-copy,
  .toolbar button,
  .create-submit,
  .dashboard-heading > button,
  .dashboard-back {
    font-size: 14px;
  }
  .session-row__title {
    font-size: 15px;
  }
  .session-row__meta,
  .session-row__action,
  .goal-options__label {
    font-size: 13px;
  }
  .session-row,
  .student-row {
    padding: 14px 0;
    font-size: 15px;
  }
}
.empty-copy {
  display: block;
  padding: 28rpx 0;
}
.classrooms {
  gap: 24rpx;
}
.toolbar {
  border-bottom: 0;
}
.toolbar-status {
  flex: none;
}
.toolbar-status__value {
  gap: 20rpx;
  min-height: 76rpx;
  padding: 0 24rpx;
  border-radius: 40rpx;
  background: var(--med-wash);
  color: var(--med-clinical);
}
.toolbar button,
.create-submit {
  border-radius: 40rpx;
  background: linear-gradient(110deg, #169bdd, #087cf0);
}
.create-submit[disabled] {
  background: var(--med-wash);
}
.create-form {
  padding: 28rpx;
  border: 1rpx solid var(--med-border);
  border-radius: 24rpx;
  background: var(--med-surface);
}
.form-picker__value,
.topic-input {
  border-radius: 12rpx;
}
.session-list {
  gap: 20rpx;
}
.session-row {
  padding: 28rpx;
  gap: 12rpx;
  border: 1rpx solid var(--med-border);
  border-left: 6rpx solid #bcd8ee;
  border-radius: 22rpx;
  background: var(--med-surface);
  text-align: left;
  box-shadow: 0 8rpx 22rpx #087cf008;
}
.session-row--active {
  border-left-color: #18b7c7;
}
.session-row__title {
  line-height: 1.5;
}
.session-row__action {
  align-self: flex-end;
  color: #087cf0;
}
.session-row::after,
.create-toggle::after,
.create-submit::after,
.dashboard-back::after,
.classroom-insights::after,
.student-actions button::after {
  border: 0;
}
.dashboard {
  padding-top: 0;
  border-top: 0;
  gap: 24rpx;
}
.dashboard-back {
  display: block;
  align-self: flex-start;
  min-height: 44px;
  padding: 0 8rpx;
  background: transparent;
}
.dashboard-heading {
  align-items: flex-start;
}
.dashboard-heading > view {
  flex: 1;
  min-width: 0;
}
.dashboard-eyebrow {
  display: block;
  margin-bottom: 10rpx;
  color: var(--med-clinical);
  font-size: 23rpx;
}
.dashboard-title {
  display: block;
  color: var(--med-ink);
  font-weight: 750;
  font-size: 34rpx;
  line-height: 1.45;
  word-break: break-word;
}
.dashboard-heading > .close-session {
  flex: none;
  min-height: 44px;
  padding: 0 16rpx;
  color: var(--med-muted);
  border: 1rpx solid var(--med-border);
  border-radius: 14rpx;
  background: transparent;
}
.classroom-metrics {
  display: flex;
  background: linear-gradient(115deg, #edf8ff, #effbf9);
  border: 1rpx solid var(--med-border);
  border-radius: 24rpx;
  padding: 28rpx 8rpx;
}
.classroom-metric {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10rpx;
  text-align: center;
  color: var(--med-muted);
  font-size: 23rpx;
}
.classroom-metric + .classroom-metric {
  border-left: 1rpx solid var(--med-border);
}
.classroom-metric__number {
  color: var(--med-ink);
  font-weight: 750;
  font-size: 44rpx;
}
.classroom-metric__unit {
  font-size: 23rpx;
  font-weight: 400;
  margin-left: 6rpx;
}
.student-list-heading {
  display: flex;
  justify-content: space-between;
  gap: 12rpx;
  align-items: center;
  font-size: 30rpx;
  font-weight: 700;
}
.student-list-heading__note {
  color: var(--med-muted);
  font-size: 22rpx;
  font-weight: 400;
}
.student-row {
  padding: 28rpx;
  gap: 24rpx;
  border: 1rpx solid var(--med-border);
  border-radius: 24rpx;
  background: var(--med-surface);
}
.student-identity {
  display: flex;
  gap: 16rpx;
  align-items: center;
  flex-wrap: wrap;
}
.student-name {
  font-size: 30rpx;
  font-weight: 700;
}
.student-phase {
  color: #087cf0;
  background: #eaf5ff;
  padding: 6rpx 16rpx;
  border-radius: 28rpx;
  font-size: 22rpx;
}
.student-phase--completed {
  color: #098e9b;
  background: #e8f9f7;
}
.student-progress-copy {
  color: var(--med-muted);
  font-size: 24rpx;
  margin-top: 10rpx;
}
.phase-track {
  display: flex;
  padding: 4rpx 0;
}
.phase-step {
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12rpx;
}
.phase-step::before {
  content: '';
  position: absolute;
  height: 4rpx;
  background: var(--med-border);
  top: 16rpx;
  left: -50%;
  right: 50%;
}
.phase-step:first-child::before {
  display: none;
}
.phase-step--done::before,
.phase-step--current::before {
  background: #28b6c4;
}
.phase-step__node {
  position: relative;
  z-index: 1;
  width: 34rpx;
  height: 34rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--med-wash);
  color: var(--med-muted);
  font-size: 22rpx;
}
.phase-step--done .phase-step__node {
  background: #19aabc;
  color: #fff;
}
.phase-step--current .phase-step__node {
  color: #fff;
  background: #087cf0;
  box-shadow: 0 0 0 6rpx #e8f4ff;
}
.phase-step__label {
  color: var(--med-muted);
  font-size: 21rpx;
  line-height: 1.4;
}
.phase-step--current .phase-step__label {
  color: #087cf0;
  font-weight: 650;
}
.student-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
}
.student-actions button {
  flex: 1;
  min-width: 0;
  min-height: 44px;
  border-radius: 14rpx;
  background: #eff7ff;
  color: #087cf0;
  font-size: 25rpx;
}
.student-actions text {
  line-height: 1.6;
}
.classroom-insights {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20rpx;
  margin: 0;
  min-height: 48px;
  border-radius: 40rpx;
  color: var(--med-clinical);
  background: #e7f8fb;
  font-size: 28rpx;
}
@media screen and (min-width: 768px) {
  .session-list--dashboard-open {
    display: none;
  }
}
.legacy-students {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}
.classrooms--reference {
  gap: 16rpx;
}
.reference-filters {
  display: flex;
  align-items: stretch;
  gap: 16rpx;
}
.reference-filters__class,
.classroom-picker {
  flex: 1;
  min-width: 0;
}
.classroom-picker__value {
  min-height: 60rpx;
  box-sizing: border-box;
  display: flex;
  gap: 10rpx;
  align-items: center;
  padding: 8rpx 16rpx;
  color: #080b63;
  background: #ffffffed;
  border: 1rpx solid #cbe0ff;
  border-radius: 12rpx;
  font-size: 24rpx;
  font-weight: 600;
  line-height: 1.4;
}
.classroom-picker__value image {
  flex: none;
  width: 30rpx;
  height: 34rpx;
}
.classroom-picker__value > text:not(.classroom-picker__arrow) {
  flex: 1;
  min-width: 0;
  overflow-wrap: anywhere;
}
.classroom-picker__arrow {
  flex: none;
  width: 10rpx;
  height: 10rpx;
  margin-left: auto;
  margin-right: 4rpx;
  border-right: 3rpx solid #8494ba;
  border-bottom: 3rpx solid #8494ba;
  transform: translateY(-3rpx) rotate(45deg);
}
.classrooms--reference .dashboard {
  gap: 28rpx;
}
.reference-metrics {
  display: flex;
  padding: 24rpx 8rpx;
  border-radius: 18rpx;
  background: #ffffffed;
  box-shadow: 0 8rpx 24rpx #6cc6ef12;
}
.reference-metric {
  flex: 1;
  min-width: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8rpx;
}
.reference-metric + .reference-metric {
  border-left: 1rpx solid #c5dfff;
}
.reference-metric__icon {
  flex: none;
  width: 44rpx;
  height: 48rpx;
}
.reference-metric__icon image {
  width: 100%;
  height: 100%;
}
.reference-metric__label {
  display: block;
  color: #7488b5;
  font-size: 22rpx;
  line-height: 1.4;
}
.reference-metric__number {
  display: block;
  text-align: center;
  color: #080b63;
  font-size: 36rpx;
  font-weight: 700;
  line-height: 1.3;
  margin-top: 4rpx;
}
.reference-metric__number text {
  font-size: 22rpx;
  font-weight: 400;
  margin-left: 3rpx;
}
.reference-group__heading {
  display: flex;
  align-items: baseline;
  gap: 20rpx;
  margin: 4rpx 4rpx 16rpx;
  color: #080b63;
  font-size: 34rpx;
  font-weight: 750;
}
.reference-group__heading::before {
  content: '';
  flex: none;
  align-self: center;
  width: 12rpx;
  height: 32rpx;
  border-radius: 6rpx;
  background: linear-gradient(#04e7dc, #00b5e6);
}
.classrooms--fixed-records {
  height: 100%;
  min-height: 0;
  overflow: hidden;
}
.classrooms--fixed-records .reference-filters,
.classrooms--fixed-records .reference-metrics,
.classrooms--fixed-records .reference-group__heading {
  flex-shrink: 0;
}
.classrooms--fixed-records .dashboard,
.classrooms--fixed-records .reference-group {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}
.classrooms--fixed-records .reference-records-scroll {
  flex: 1;
  height: 0;
  min-height: 0;
}
.classrooms--fixed-records .classroom-management-scroll {
  flex: 1;
  height: 0;
  min-height: 0;
}
.classrooms--fixed-records .dashboard {
  gap: 20rpx;
}
.classrooms--fixed-records .reference-metrics {
  padding: 20rpx 8rpx;
}
.classrooms--fixed-records .reference-students {
  gap: 12rpx;
}
.classrooms--fixed-records .reference-student {
  padding: 12rpx;
}
.classrooms--fixed-records .reference-student__badge {
  padding: 5rpx 10rpx;
}
.classrooms--fixed-records .reference-student__progress {
  margin: 6rpx 0 8rpx;
}
.reference-group__heading > text + text {
  color: #7488b5;
  font-size: 26rpx;
  font-weight: 400;
}
.reference-students {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 14rpx;
}
.reference-students--balanced {
  grid-auto-rows: 1fr;
}
.reference-students--balanced .reference-student {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 16rpx;
}
.reference-student {
  min-width: 0;
  padding: 16rpx;
  border-top: 6rpx solid #00d7c6;
  border-radius: 18rpx;
  background: #fff;
  box-shadow: 0 8rpx 22rpx #78c5ee12;
}
.reference-student__top {
  display: flex;
  align-items: center;
  gap: 8rpx;
  flex-wrap: wrap;
}
.reference-student__name {
  min-width: 0;
  color: #080b63;
  font-size: 26rpx;
  font-weight: 700;
  line-height: 1.35;
  overflow-wrap: anywhere;
}
.reference-student__phase {
  display: flex;
  align-items: center;
  gap: 8rpx;
  color: #7488b5;
  font-size: 20rpx;
}
.reference-student__check {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28rpx;
  height: 28rpx;
  border-radius: 50%;
  background: linear-gradient(135deg, #03e4b5, #00bbd0);
  color: #fff;
  font-size: 25rpx;
  font-weight: 750;
}
.reference-student__check.is-active {
  background: #ffae43;
}
.reference-student__badge {
  margin-left: auto;
  padding: 7rpx 10rpx;
  border-radius: 10rpx;
  color: #fb6500;
  background: #fff4df;
  font-size: 20rpx;
  line-height: 1.3;
}
.reference-student__badge.is-published {
  color: #00abb5;
  background: #e0fcfc;
}
.reference-student__progress {
  display: block;
  color: #7488b5;
  font-size: 22rpx;
  line-height: 1.5;
  margin: 10rpx 0 14rpx;
}
.reference-student__actions {
  display: flex;
  gap: 10rpx;
}
.reference-student__actions button {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  gap: 6rpx;
  min-width: 0;
  min-height: 48rpx;
  margin: 0;
  padding: 0 6rpx;
  color: #0085ff;
  background: #f0f9ff;
  border: 1rpx solid #a6d3ff;
  border-radius: 10rpx;
  font-size: 22rpx;
  line-height: 1.3;
}
.reference-student__actions button image {
  width: 25rpx;
  height: 30rpx;
  flex: none;
}
.reference-student__actions button.reference-student__test {
  color: #00b6c0;
  background: #e6fbfc;
  border-color: #abedf1;
}
.reference-student__actions button[disabled] {
  opacity: 0.45;
}
.reference-more {
  background: transparent;
  color: #7488b5;
  font-size: 24rpx;
  min-height: 44px;
}
.closed-copy {
  color: #7488b5;
  font-size: 24rpx;
}
.create-form__heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.create-cancel {
  margin: 0;
  min-height: 44px;
  padding: 0 16rpx;
  font-size: 24rpx;
  color: #7488b5;
  background: transparent;
}
</style>
