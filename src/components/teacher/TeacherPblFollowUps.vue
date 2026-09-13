<template>
  <view
    class="follow-ups"
    :class="{ 'follow-ups--selected': selectedPlanId }"
  >
    <TeacherPblFollowUpList
      :items="items"
      :total="total"
      :offset="offset"
      :loading="listLoading"
      :error="listError"
      :filter-error="filterError"
      :status="status"
      :session-id="sessionIdDraft"
      :student-id="studentIdDraft"
      :selected-plan-id="selectedPlanId"
      @update:session-id="sessionIdDraft = $event"
      @update:student-id="studentIdDraft = $event"
      @status-change="changeStatus"
      @apply-filters="applyContextFilters"
      @retry="load"
      @open="open"
      @previous-page="previousPage"
      @next-page="nextPage"
    />
    <TeacherPblFollowUpDetail
      :selected-plan-id="selectedPlanId"
      :detail="detail"
      :body="body"
      :loading="detailLoading"
      :busy="actionBusy"
      :error="detailError"
      :action-error="actionError"
      @back="closeDetail"
      @retry="retryDetail"
      @update:body="body = $event"
      @send-feedback="sendFeedback"
    />
  </view>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import TeacherPblFollowUpDetail from './TeacherPblFollowUpDetail.vue'
import TeacherPblFollowUpList from './TeacherPblFollowUpList.vue'
import {
  createPblMessageId,
  getTeacherPblFollowUp,
  getTeacherPblFollowUps,
  sendTeacherPblFollowUpFeedback,
  type PblFollowUp,
  type PblFollowUpStatus,
} from '@/features/pbl/public'

const props = defineProps<{ classId?: string }>()
const items = ref<PblFollowUp[]>([])
const selectedPlanId = ref<number>()
const detail = ref<Awaited<ReturnType<typeof getTeacherPblFollowUp>>>()
const status = ref<PblFollowUpStatus>()
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
    const page = await getTeacherPblFollowUps({
      classId: props.classId,
      sessionId: sessionId.value,
      studentId: studentId.value,
      status: status.value,
      offset: offset.value,
    })
    if (token !== listRequest) return
    items.value = page.items
    total.value = page.total
  } catch (reason) {
    if (token === listRequest) listError.value = reason instanceof Error ? reason.message : 'PBL 跟进加载失败'
  } finally {
    if (token === listRequest) listLoading.value = false
  }
}

async function open(planId: number) {
  if (!Number.isInteger(planId) || planId <= 0) return
  selectedPlanId.value = planId
  detail.value = undefined
  detailError.value = ''
  actionError.value = ''
  body.value = ''
  detailLoading.value = true
  const token = ++detailRequest
  try {
    const value = await getTeacherPblFollowUp(planId)
    if (token === detailRequest) detail.value = value
  } catch (reason) {
    if (token === detailRequest) detailError.value = reason instanceof Error ? reason.message : '跟进详情加载失败'
  } finally {
    if (token === detailRequest) detailLoading.value = false
  }
}

async function sendFeedback() {
  if (!detail.value || !validBody(body.value)) return
  if (detail.value.plan.verification_status !== 'needs_reinforcement' || !detail.value.plan.automation_exhausted) return
  actionBusy.value = true
  actionError.value = ''
  const planId = detail.value.plan.id
  try {
    await sendTeacherPblFollowUpFeedback(planId, createPblMessageId(), body.value.trim())
    body.value = ''
    uni.showToast({ title: '补充反馈已发送', icon: 'success' })
    await open(planId)
  } catch (reason) {
    actionError.value = reason instanceof Error ? reason.message : '反馈发送失败，请保留当前文字并重试。'
  } finally {
    actionBusy.value = false
  }
}

function changeStatus(value?: PblFollowUpStatus) {
  status.value = value
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
function applyContextFilters() {
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
async function selectContext(context?: { sessionId?: string; studentId?: string; planId?: number }) {
  sessionIdDraft.value = positiveInteger(context?.sessionId) || ''
  studentIdDraft.value = positiveInteger(context?.studentId) || ''
  sessionId.value = sessionIdDraft.value || undefined
  studentId.value = studentIdDraft.value || undefined
  filterError.value = ''
  offset.value = 0
  closeDetail()
  await load()
  if (context?.planId && Number.isInteger(context.planId) && context.planId > 0) await open(context.planId)
}
function closeDetail() {
  detailRequest += 1
  selectedPlanId.value = undefined
  detail.value = undefined
  detailLoading.value = false
  detailError.value = ''
  actionError.value = ''
}
function retryDetail() {
  if (selectedPlanId.value) void open(selectedPlanId.value)
}
function positiveInteger(value?: string): string | undefined {
  return /^\d+$/.test(value || '') && Number(value) > 0 ? value : undefined
}
function validBody(value: string) {
  return value.trim().length >= 1 && value.trim().length <= 1000
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
defineExpose({ refresh: load, selectContext })
</script>

<style scoped>
.follow-ups {
  display: grid;
  gap: 16rpx;
}
@media screen and (min-width: 768px) {
  .follow-ups--selected {
    grid-template-columns: minmax(280px, 0.8fr) minmax(360px, 1.2fr);
    align-items: start;
  }
}
</style>
