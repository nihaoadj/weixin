<template>
  <view class="safe-page detail-page">
    <MedState
      v-if="accessDenied"
      variant="error"
      icon="history"
      title="教师身份已变化"
      description="固定诊断内容仅对有权教师开放。请返回 PBL 工作区后再继续。"
      action-label="返回 PBL 工作区"
      @action="backToList"
    />
    <MedState
      v-else-if="invalidId"
      variant="error"
      icon="retry"
      title="诊断链接无效"
      description="未提供可读取的诊断编号。"
      action-label="返回 PBL 工作区"
      @action="backToList"
    />
    <MedState
      v-else-if="loading"
      variant="loading"
      icon="history"
      title="正在加载诊断详情"
      description="正在读取当前教师有权查看的固定诊断与研讨分析。"
    />
    <MedState
      v-else-if="error"
      variant="error"
      icon="retry"
      title="诊断详情加载失败"
      :description="error"
      action-label="重新加载"
      secondary-action-label="返回 PBL 工作区"
      @action="load"
      @secondary-action="backToList"
    />
    <template v-else-if="selected && detail">
      <TeacherPblWorkItemDetail
        :selected="selected"
        :detail="detail"
        @retry="load"
      />
      <TeacherModuleSection
        v-if="selected.finalTestId"
        title="研讨分析关联的最终测试"
        description="该测试以本次研讨分析为来源，当前状态与可用操作以最终测试页面为准。"
      >
        <button
          class="route-test-action"
          @click="openFinalTest"
        >
          查看最终测试
        </button>
      </TeacherModuleSection>
    </template>
    <MedState
      v-else
      variant="empty"
      icon="report"
      title="诊断已不可用"
      description="该诊断可能已不存在或当前无法查看。"
      action-label="返回 PBL 工作区"
      @action="backToList"
    />
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onBackPress, onLoad, onShow } from '@dcloudio/uni-app'
import TeacherPblWorkItemDetail from '@/features/pbl/presentation/TeacherPblWorkItemDetail.vue'
import TeacherModuleSection from '@/components/teacher/TeacherModuleSection.vue'
import MedState from '@/components/ui/MedState.vue'
import { getSession, requireRole } from '@/features/identity/public'
import { getTeacherPblWorkItem, type PblWorkItem } from '@/features/pbl/public'
import { backOrRoute, goDetail, handleBackPress, ROUTES } from '@/platform/navigation'
import { parseTeacherWorkspaceTarget, type TeacherSessionId } from '@/platform/navigation/teacher'

type PblReturnTarget = Extract<ReturnType<typeof parseTeacherWorkspaceTarget>, { workspace: 'pbl' }>

const snapshotId = ref('')
const pblReturn = ref<PblReturnTarget>({ workspace: 'pbl', section: 'classrooms' })
const invalidId = ref(true)
const selected = ref<PblWorkItem>()
const detail = ref<Awaited<ReturnType<typeof getTeacherPblWorkItem>>>()
const loading = ref(false)
const error = ref('')
const accessDenied = ref(false)
let request = 0
let activeIdentity = ''

onLoad((query) => {
  const value = queryString(query?.snapshotId) || ''
  const numericSnapshotId = Number(value)
  invalidId.value = !/^\d+$/.test(value) || !Number.isSafeInteger(numericSnapshotId) || numericSnapshotId <= 0
  if (!invalidId.value) snapshotId.value = value
  pblReturn.value = parsePblReturn({
    section: queryString(query?.returnSection),
    classId: queryString(query?.classId),
    sessionId: queryString(query?.sessionId),
  })
})
onShow(() => {
  const session = getSession()
  if (!requireRole('teacher') || session?.role !== 'teacher' || !session.openid) {
    clearForAccessLoss()
    return
  }
  if (activeIdentity !== session.openid) {
    request += 1
    activeIdentity = session.openid
    clearDetail()
  }
  accessDenied.value = false
  if (!invalidId.value) void load()
})
onBackPress(({ from }) => handleBackPress(from, ROUTES.teacherPbl, fallbackParams()))

function queryString(value: unknown): string | undefined {
  return typeof value === 'string' || typeof value === 'number' ? String(value) : undefined
}
function parsePblReturn(query: { section?: string; classId?: string; sessionId?: string }): PblReturnTarget {
  const target = parseTeacherWorkspaceTarget({ ...query, tab: 'pbl' })
  return target.workspace === 'pbl' ? target : { workspace: 'pbl', section: 'classrooms' }
}
function fallbackParams(): {
  section: NonNullable<PblReturnTarget['section']>
  classId?: number
  sessionId?: TeacherSessionId
} {
  const target = pblReturn.value
  return {
    section: target.section || 'classrooms',
    ...(target.classId ? { classId: target.classId } : {}),
    ...(target.sessionId !== undefined ? { sessionId: target.sessionId } : {}),
  }
}
function backToList() {
  backOrRoute(ROUTES.teacherPbl, fallbackParams())
}
function openFinalTest() {
  const finalTestId = selected.value?.finalTestId
  if (!finalTestId || !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(finalTestId))
    return
  const context = fallbackParams()
  goDetail(ROUTES.teacherLearningFinalTest, {
    finalTestId,
    returnSection: context.section,
    ...(context.classId ? { classId: context.classId } : {}),
    ...(context.sessionId !== undefined ? { sessionId: context.sessionId } : {}),
  })
}
function clearDetail() {
  selected.value = undefined
  detail.value = undefined
  loading.value = false
  error.value = ''
}
function clearForAccessLoss() {
  request += 1
  activeIdentity = ''
  clearDetail()
  accessDenied.value = true
}
function hasTeacherIdentity(identity: string) {
  const session = getSession()
  return requireRole('teacher') && session?.role === 'teacher' && session.openid === identity
}
async function load() {
  if (invalidId.value || accessDenied.value) return
  const session = getSession()
  if (!requireRole('teacher') || session?.role !== 'teacher' || !session.openid) {
    clearForAccessLoss()
    return
  }
  if (activeIdentity !== session.openid) {
    activeIdentity = session.openid
    clearDetail()
  }
  const requestedIdentity = session.openid
  const token = ++request
  loading.value = true
  error.value = ''
  detail.value = undefined
  try {
    const loaded = await getTeacherPblWorkItem(snapshotId.value)
    if (token !== request || !hasTeacherIdentity(requestedIdentity) || !loaded.workItem) return
    detail.value = loaded
    selected.value = loaded.workItem
    pblReturn.value = parsePblReturn({
      section: pblReturn.value.section,
      classId: loaded.workItem.class.id,
      sessionId: loaded.workItem.sessionId,
    })
  } catch (reason) {
    if (token === request && hasTeacherIdentity(requestedIdentity))
      error.value = reason instanceof Error ? reason.message : '诊断详情加载失败'
  } finally {
    if (token === request) loading.value = false
  }
}
</script>

<style scoped>
.detail-page {
  min-height: 100vh;
  padding: 0 24rpx calc(32rpx + env(safe-area-inset-bottom));
  box-sizing: border-box;
  background: var(--med-page);
}
@media screen and (min-width: 600px) {
  .detail-page {
    max-width: 920px;
    margin: 0 auto;
    padding: 0 28px calc(28px + env(safe-area-inset-bottom));
  }
}
</style>
