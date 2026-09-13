<template>
  <view class="classrooms">
    <view class="toolbar">
      <picker
        class="toolbar-status"
        :range="statusOptions"
        range-key="label"
        role="button"
        tabindex="0"
        @keydown="activatePickerOnKey"
        @change="changeStatus"
        ><view class="toolbar-status__value">状态：{{ statusLabel }}</view></picker
      >
      <button
        :disabled="!classes.length"
        :tabindex="classes.length ? 0 : -1"
        role="button"
        @keydown="activateButtonOnKey"
        @click="showCreate = !showCreate"
      >
        {{ showCreate ? '收起创建' : '创建课堂' }}
      </button>
    </view>
    <view
      v-if="showCreate"
      class="create-form"
    >
      <text class="form-heading">创建课堂</text>
      <picker
        class="form-picker"
        :range="classes"
        range-key="name"
        role="button"
        tabindex="0"
        @keydown="activatePickerOnKey"
        @change="creationClassIndex = Number($event.detail.value)"
        ><view class="form-picker__value"
          >授课班级：{{ classes[creationClassIndex]?.name || '请选择班级' }}</view
        ></picker
      >
      <picker
        class="form-picker"
        :range="reviewedCases"
        range-key="title"
        role="button"
        tabindex="0"
        @keydown="activatePickerOnKey"
        @change="caseIndex = Number($event.detail.value)"
        ><view class="form-picker__value">已审核病例：{{ reviewedCases[caseIndex]?.title || '请选择' }}</view></picker
      >
      <input
        v-model="topicCode"
        class="topic-input"
        aria-label="课堂主题"
        placeholder="课堂主题（例如：肾小球病变的证据推理）"
      />
      <view class="goal-options"
        ><text class="goal-options__label">知识点（选择 1–3 项）</text
        ><label
          v-for="point in caseKnowledgePoints"
          :key="point.code"
          class="goal-option"
          ><checkbox
            class="goal-option__check"
            :checked="selectedGoalCodes.includes(point.code)"
            @click="toggleGoal(point.code)"
          /><text>{{ point.title }}</text></label
        ></view
      >
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
    <text v-else-if="loading">正在加载课堂…</text>
    <view
      v-else
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
      <view
        v-if="total > 0"
        class="pager"
        ><button
          :disabled="offset === 0"
          :tabindex="offset === 0 ? -1 : 0"
          role="button"
          @keydown="activateButtonOnKey"
          @click="previousPage"
        >
          上一页</button
        ><text>{{ offset + 1 }}–{{ Math.min(offset + 20, total) }}/{{ total }}</text
        ><button
          :disabled="offset + 20 >= total"
          :tabindex="offset + 20 >= total ? -1 : 0"
          role="button"
          @keydown="activateButtonOnKey"
          @click="nextPage"
        >
          下一页
        </button></view
      >
    </view>
    <view
      v-if="dashboard"
      class="dashboard"
    >
      <button
        class="dashboard-back"
        role="button"
        tabindex="0"
        @keydown="activateButtonOnKey"
        @click="dashboard = undefined"
      >
        返回课堂列表
      </button>
      <view class="dashboard-heading"
        ><text>课堂阶段看板</text
        ><button
          v-if="dashboard.session.status !== 'closed'"
          role="button"
          tabindex="0"
          @keydown="activateButtonOnKey"
          @click="close"
        >
          关闭课堂
        </button></view
      >
      <text>参与 {{ dashboard.summary.participants }} 人 · 待判定 {{ dashboard.summary.pending_verification }} 项</text>
      <view
        v-for="student in dashboard.students"
        :key="student.studentId"
        class="student-row"
      >
        <view class="student-summary">
          <text>{{ student.studentName }} · {{ phaseLabel(student.currentPhase) }}</text>
          <text
            >{{ student.taskProgress.completed }}/{{ student.taskProgress.total }} 项任务 ·
            {{ workItemLabel(student.workItemStatus) }}</text
          >
        </view>
        <view class="student-actions">
          <button
            v-if="student.snapshotId"
            role="button"
            tabindex="0"
            @keydown="activateButtonOnKey"
            @click="openDiagnostic(student.snapshotId)"
          >
            查看诊断
          </button>
          <button
            v-if="student.taskProgress.total > 0"
            role="button"
            tabindex="0"
            @keydown="activateButtonOnKey"
            @click="openFollowUp(student.studentId)"
          >
            查看跟进
          </button>
          <text v-if="!student.snapshotId && student.taskProgress.total === 0">等待学生形成诊断或正式任务</text>
        </view>
      </view>
    </view>
  </view>
</template>
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
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

const props = defineProps<{ classId?: string; classes: Array<{ id: number; name: string }> }>()
const emit = defineEmits<{
  openDiagnostic: [snapshotId: string]
  openFollowUp: [context: { classId?: string; sessionId: string; studentId: string }]
}>()
const items = ref<TeacherPblSession[]>([])
const dashboard = ref<TeacherPblDashboard>()
const reviewedCases = ref<Awaited<ReturnType<typeof getGuidedCasesAsync>>>([])
const knowledgeCatalog = ref<KnowledgePoint[]>([])
const loading = ref(false)
const creating = ref(false)
const error = ref('')
const offset = ref(0)
const total = ref(0)
const selectedStatus = ref<string>()
const showCreate = ref(false)
const caseIndex = ref(0)
const topicCode = ref('')
const selectedGoalCodes = ref<string[]>([])
const creationClassIndex = ref(0)
let listRequest = 0
let dashboardRequest = 0
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
const caseKnowledgePoints = computed(() => {
  const selected = reviewedCases.value[caseIndex.value]
  const codes = selected?.knowledgePointCodes || []
  return knowledgeCatalog.value.filter((point) => codes.includes(point.code))
})
const canCreate = computed(() => {
  return Boolean(
    creationClassId.value &&
    reviewedCases.value[caseIndex.value] &&
    topicCode.value.trim() &&
    selectedGoalCodes.value.length >= 1 &&
    selectedGoalCodes.value.length <= 3,
  )
})
async function load() {
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
    reviewedCases.value = cases.filter((item) => item.medicalReviewStatus === 'approved')
    knowledgeCatalog.value = points
  } catch (reason) {
    if (token === listRequest) error.value = reason instanceof Error ? reason.message : '课堂加载失败'
  } finally {
    if (token === listRequest) loading.value = false
  }
}
async function open(item: TeacherPblSession) {
  const classId = props.classId || item.classId
  if (!classId) return
  const token = ++dashboardRequest
  try {
    const value = await getTeacherPblDashboard(classId, item.id)
    if (token === dashboardRequest) dashboard.value = value
  } catch (reason) {
    if (token === dashboardRequest) error.value = reason instanceof Error ? reason.message : '课堂阶段看板加载失败'
  }
}
async function create() {
  if (!creationClassId.value || !canCreate.value) return
  creating.value = true
  try {
    const session = await createPblSession(
      creationClassId.value,
      topicCode.value.trim(),
      reviewedCases.value[caseIndex.value].id,
      selectedGoalCodes.value,
    )
    showCreate.value = false
    topicCode.value = ''
    selectedGoalCodes.value = []
    await load()
    await open({
      id: session.id,
      classId: creationClassId.value,
      className: props.classes.find((item) => String(item.id) === creationClassId.value)?.name || '当前班级',
      topicCode: session.topicCode,
      status: session.status,
    })
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '课堂创建失败'
  } finally {
    creating.value = false
  }
}
async function close() {
  if (!dashboard.value) return
  const classId = props.classId || dashboard.value.session.classId
  if (!classId) return
  try {
    await closePblSession(classId, dashboard.value.session.id)
    await open({
      ...dashboard.value.session,
      className: props.classes.find((item) => String(item.id) === classId)?.name || '当前班级',
      topicCode: '',
    })
    await load()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '课堂关闭失败'
  }
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
function openFollowUp(studentId: string) {
  if (!dashboard.value) return
  emit('openFollowUp', {
    classId: props.classId || dashboard.value.session.classId,
    sessionId: dashboard.value.session.id,
    studentId,
  })
}
function toggleGoal(code: string) {
  if (selectedGoalCodes.value.includes(code))
    selectedGoalCodes.value = selectedGoalCodes.value.filter((item) => item !== code)
  else if (selectedGoalCodes.value.length < 3) selectedGoalCodes.value = [...selectedGoalCodes.value, code]
}
function displaySessionStatus(value: string) {
  return value === 'closed' ? '已关闭' : '进行中'
}
function displayTopic(value: string) {
  const matchingPoint = knowledgeCatalog.value.find((point) => point.code === value)
  if (matchingPoint) return matchingPoint.title
  const knownTopics: Record<string, string> = {
    'pathology.inflammation': '炎症',
  }
  if (knownTopics[value]) return knownTopics[value]
  return value.replace(/^pathology\./, '病理学 · ').replaceAll('.', ' · ')
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
function workItemLabel(value?: string) {
  return (
    (
      {
        pending: '等待教师反馈',
        responded: '已反馈，待学生继续',
        task_published: '已发布正式任务',
        closed: '本轮已关闭',
      } as Record<string, string>
    )[value || ''] || '等待学生提交'
  )
}
watch(caseKnowledgePoints, () => {
  selectedGoalCodes.value = []
})
watch(
  () => props.classId,
  () => {
    offset.value = 0
    dashboard.value = undefined
    load()
  },
)
onMounted(load)
defineExpose({ refresh: load })
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
.pager,
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
.pager button,
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
.toolbar button,
.dashboard-heading > button,
.dashboard-back {
  color: var(--med-clinical);
  background: var(--med-wash);
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
  .pager button,
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
</style>
