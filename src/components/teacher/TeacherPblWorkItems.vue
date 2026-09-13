<template>
  <view class="work-items">
    <view
      class="layout"
      :class="{ 'layout--selected': selected }"
    >
      <TeacherPblWorkItemList
        :items="items"
        :total="total"
        :offset="offset"
        :loading="listLoading"
        :error="listError"
        :filter-error="filterError"
        :status="status"
        :source="source"
        :session-id="sessionIdDraft"
        :student-id="studentIdDraft"
        :selected-snapshot-id="selected?.snapshotId"
        @update:session-id="sessionIdDraft = $event"
        @update:student-id="studentIdDraft = $event"
        @status-change="changeStatus"
        @source-change="changeSource"
        @apply-filters="applyIdentityFilters"
        @retry="load"
        @open="open"
        @previous-page="previousPage"
        @next-page="nextPage"
      />
      <TeacherPblWorkItemDetail
        :selected="selected"
        :detail="detail"
        :students="students"
        :selected-target-ids="selectedTargetIds"
        :whole-class="wholeClass"
        :body="body"
        :loading="detailLoading"
        :busy="actionBusy"
        :error="detailError"
        :action-error="actionError"
        @back="closeDetail"
        @retry="retryDetail"
        @update:body="body = $event"
        @toggle-target="toggleTarget"
        @toggle-whole-class="wholeClass = !wholeClass"
        @submit="submit"
      />
    </view>
  </view>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import TeacherPblWorkItemDetail from './TeacherPblWorkItemDetail.vue'
import TeacherPblWorkItemList from './TeacherPblWorkItemList.vue'
import {
  createPblMessageId,
  getTeacherPblWorkItem,
  getTeacherPblWorkItems,
  sendTeacherPblFeedback,
  type PblSuggestion,
  type PblWorkItem,
  type PblWorkStatus,
} from '@/features/pbl/public'
import { getClassStudents, type TeacherStudent } from '@/features/classroom/public'

type WorkItemAction = 'feedback_only' | 'closed' | 'task_published'

const props = withDefaults(defineProps<{ classId?: string; initialStatus?: PblWorkStatus }>(), {
  initialStatus: 'pending',
})
const emit = defineEmits<{ summary: [value: Record<PblWorkStatus, number>] }>()

const items = ref<PblWorkItem[]>([])
const selected = ref<PblWorkItem>()
const detail = ref<Awaited<ReturnType<typeof getTeacherPblWorkItem>>>()
const status = ref<PblWorkStatus | undefined>(props.initialStatus)
const source = ref<PblWorkItem['source']>()
const offset = ref(0)
const total = ref(0)
const listLoading = ref(false)
const detailLoading = ref(false)
const actionBusy = ref(false)
const listError = ref('')
const detailError = ref('')
const actionError = ref('')
const filterError = ref('')
const body = ref('')
const students = ref<TeacherStudent[]>([])
const selectedTargetIds = ref<number[]>([])
const wholeClass = ref(false)
const sessionIdDraft = ref('')
const studentIdDraft = ref('')
const sessionId = ref<string>()
const studentId = ref<string>()
let listRequest = 0
let detailRequest = 0

async function load() {
  const token = ++listRequest
  listLoading.value = true
  listError.value = ''
  try {
    const page = await getTeacherPblWorkItems({
      classId: props.classId,
      workStatus: status.value,
      source: source.value,
      sessionId: sessionId.value,
      studentId: studentId.value,
      offset: offset.value,
    })
    if (token !== listRequest) return
    items.value = page.items
    total.value = page.total
    emit('summary', page.summary)
  } catch (reason) {
    if (token === listRequest) listError.value = reason instanceof Error ? reason.message : '诊断建议加载失败'
  } finally {
    if (token === listRequest) listLoading.value = false
  }
}

function beginDetail(item: PblWorkItem) {
  selected.value = item
  detail.value = undefined
  detailError.value = ''
  actionError.value = ''
  body.value = ''
  students.value = []
  selectedTargetIds.value = [Number(item.student.id)].filter((value) => Number.isInteger(value) && value > 0)
  wholeClass.value = false
}

async function open(item: PblWorkItem) {
  beginDetail(item)
  const token = ++detailRequest
  detailLoading.value = true
  try {
    const [loadedDetail, classmates] = await Promise.all([
      getTeacherPblWorkItem(item.snapshotId),
      getClassStudents(Number(item.class.id)),
    ])
    if (token !== detailRequest) return
    detail.value = loadedDetail
    selected.value = loadedDetail.workItem || item
    students.value = classmates
    const sourceStudentId = Number((loadedDetail.workItem || item).student.id)
    selectedTargetIds.value = [sourceStudentId].filter((value) => Number.isInteger(value) && value > 0)
  } catch (reason) {
    if (token === detailRequest) detailError.value = reason instanceof Error ? reason.message : '诊断详情加载失败'
  } finally {
    if (token === detailRequest) detailLoading.value = false
  }
}

async function openSnapshot(snapshotId: string) {
  if (!positiveInteger(snapshotId)) return
  const token = ++detailRequest
  detailLoading.value = true
  detailError.value = ''
  actionError.value = ''
  detail.value = undefined
  try {
    const loaded = await getTeacherPblWorkItem(snapshotId)
    if (token !== detailRequest || !loaded.workItem) return
    selected.value = loaded.workItem
    const classmates = await getClassStudents(Number(loaded.workItem.class.id))
    if (token !== detailRequest) return
    detail.value = loaded
    students.value = classmates
    selectedTargetIds.value = [Number(loaded.workItem.student.id)]
    wholeClass.value = false
    body.value = ''
  } catch (reason) {
    if (token === detailRequest) detailError.value = reason instanceof Error ? reason.message : '诊断详情加载失败'
  } finally {
    if (token === detailRequest) detailLoading.value = false
  }
}

async function submit(actionType: WorkItemAction, suggestion?: PblSuggestion) {
  if (!selected.value || !validBody(body.value)) return
  if (actionType === 'task_published' && (!suggestion || (!wholeClass.value && !selectedTargetIds.value.length))) return
  const defaultStudentId = Number(selected.value.student.id)
  const deviatesFromSource =
    wholeClass.value || selectedTargetIds.value.length !== 1 || selectedTargetIds.value[0] !== defaultStudentId
  if (actionType === 'task_published' && deviatesFromSource && !(await confirmPublish())) return

  const current = selected.value
  actionBusy.value = true
  actionError.value = ''
  try {
    await sendTeacherPblFeedback({
      snapshotId: current.snapshotId,
      clientFeedbackId: createPblMessageId(),
      body: body.value.trim(),
      actionType,
      suggestion: actionType === 'task_published' ? suggestion : undefined,
      targets: {
        studentIds: wholeClass.value ? undefined : selectedTargetIds.value,
        wholeClass: wholeClass.value,
      },
    })
    body.value = ''
    uni.showToast({
      title:
        actionType === 'task_published'
          ? '反馈与任务已发布'
          : actionType === 'closed'
            ? '反馈已发送并关闭'
            : '反馈已发送',
      icon: 'success',
    })
    await Promise.all([open(current), load()])
  } catch (reason) {
    actionError.value = reason instanceof Error ? reason.message : '操作失败，请保留当前反馈并重试。'
  } finally {
    actionBusy.value = false
  }
}

function changeStatus(value?: PblWorkStatus) {
  status.value = value
  offset.value = 0
  closeDetail()
  void load()
}
function changeSource(value?: PblWorkItem['source']) {
  source.value = value
  offset.value = 0
  closeDetail()
  void load()
}
function applyIdentityFilters() {
  const nextSession = positiveInteger(sessionIdDraft.value)
  const nextStudent = positiveInteger(studentIdDraft.value)
  if ((sessionIdDraft.value && !nextSession) || (studentIdDraft.value && !nextStudent)) {
    filterError.value = '课堂编号和学生编号必须为正整数。'
    return
  }
  filterError.value = ''
  sessionId.value = nextSession
  studentId.value = nextStudent
  offset.value = 0
  closeDetail()
  void load()
}
function previousPage() {
  offset.value = Math.max(0, offset.value - 20)
  closeDetail()
  void load()
}
function nextPage() {
  offset.value += 20
  closeDetail()
  void load()
}
function closeDetail() {
  detailRequest += 1
  selected.value = undefined
  detail.value = undefined
  detailLoading.value = false
  detailError.value = ''
  actionError.value = ''
}
function retryDetail() {
  if (selected.value) void open(selected.value)
}
function toggleTarget(id: number) {
  selectedTargetIds.value = selectedTargetIds.value.includes(id)
    ? selectedTargetIds.value.filter((candidate) => candidate !== id)
    : [...selectedTargetIds.value, id]
}
function positiveInteger(value: string): string | undefined {
  return /^\d+$/.test(value) && Number(value) > 0 ? value : undefined
}
function validBody(value: string) {
  return value.trim().length >= 1 && value.trim().length <= 1000
}
async function focusPending() {
  if (status.value === 'pending') {
    closeDetail()
    return
  }
  status.value = 'pending'
  offset.value = 0
  closeDetail()
  await load()
}
function confirmPublish() {
  return new Promise<boolean>((resolve) => {
    uni.showModal({
      title: '确认发布范围',
      content: '发布对象偏离来源学生。确认继续发布正式任务吗？',
      success: (result) => resolve(result.confirm),
      fail: () => resolve(false),
    })
  })
}

watch(
  () => props.classId,
  () => {
    listRequest += 1
    offset.value = 0
    closeDetail()
    void load()
  },
)
onMounted(load)
defineExpose({ focusPending, openSnapshot, refresh: load })
</script>

<style scoped>
.layout {
  display: grid;
  gap: 16rpx;
}
@media screen and (min-width: 768px) {
  .layout--selected {
    grid-template-columns: minmax(280px, 0.8fr) minmax(360px, 1.2fr);
    align-items: start;
  }
}
</style>
