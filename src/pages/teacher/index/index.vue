<template>
  <view class="safe-page teacher-page">
    <text
      class="sr-only"
      role="heading"
      aria-level="1"
      >教师工作台</text
    >
    <PageContextBar
      :label="workspaceTitle"
      :description="workspaceDescription"
      aria-label="当前教师工作区"
    >
      <template #actions>
        <button
          hover-class="is-pressed"
          :hover-start-time="0"
          :hover-stay-time="80"
          tabindex="0"
          role="button"
          class="logout"
          aria-label="退出教师工作台"
          @keydown="activateButtonOnKey"
          @click="logout"
        >
          退出
        </button>
      </template>
    </PageContextBar>
    <view class="workspace-body">
      <view class="workspace-navigation">
        <TeacherWorkspaceNav
          :active="currentWorkspace"
          @change="switchWorkspace"
        />
      </view>
      <scroll-view
        class="workspace-scroll"
        scroll-y
        :scroll-top="workspaceScrollTop"
        :aria-label="workspaceTitle"
        @scroll="recordWorkspaceScroll"
      >
        <view class="workspace-content">
          <TeacherOverview
            v-if="openedWorkspaces.overview"
            v-show="currentWorkspace === 'overview'"
            :loading="overviewLoading"
            :is-reviewer="isReviewer"
            :pending-reports="pendingReports"
            :pending-review="pendingReview"
            :pending-pbl="pendingPbl"
            :report-error="reportQueueError"
            :review-error="reviewQueueError"
            :pbl-error="pblQueueError"
            @reports="openInsights('records')"
            @review="openReview('overview')"
            @pbl="openContent('pbl-diagnostics', undefined, true)"
            @classes="openClasses"
            @analytics="openInsights('analytics')"
            @knowledge-cards="openKnowledgeCards('overview')"
            @retry="refreshOverview"
          />
          <TeacherInsightsWorkspace
            v-if="openedWorkspaces.reports"
            v-show="currentWorkspace === 'reports'"
            ref="insightsWorkspace"
            :initial-section="initialInsightsSection"
            :classes="classes"
            :class-id="selectedClassId"
            :class-loading="classesLoading"
            :class-error="classError"
            :class-scope-loaded="classesLoaded && !classError"
            @class-change="changeClass"
            @retry-classes="loadClasses"
            @classes="openClasses"
            @resources="openContent('resources')"
            @select-report="openReport"
            @section-change="resetWorkspaceScroll"
          />
          <TeacherContentWorkspace
            v-if="openedWorkspaces.problems"
            v-show="currentWorkspace === 'problems'"
            ref="contentWorkspace"
            :initial-section="initialContentSection"
            :classes="classes"
            :class-id="selectedClassId"
            :class-loading="classesLoading"
            :class-error="classError"
            :is-reviewer="isReviewer"
            @class-change="changeClass"
            @retry-classes="loadClasses"
            @knowledge-cards="openKnowledgeCards('resources')"
            @medical-review="openReview('resources')"
            @section-change="resetWorkspaceScroll"
          />
          <TeacherPblQueue
            v-if="openedWorkspaces.pbl"
            v-show="currentWorkspace === 'pbl'"
            ref="pblQueue"
            :classes="classes"
            :class-id="selectedClassId"
            :class-loading="classesLoading"
            :class-error="classError"
            @class-change="changeClass"
            @retry-classes="loadClasses"
            @open-diagnostic="openContent('pbl-diagnostics', $event)"
            @open-follow-up="openFollowUp"
          />
        </view>
      </scroll-view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import TeacherContentWorkspace, { type TeacherContentSection } from '@/components/teacher/TeacherContentWorkspace.vue'
import TeacherInsightsWorkspace, {
  type TeacherFollowUpContext,
  type TeacherInsightsSection,
} from '@/components/teacher/TeacherInsightsWorkspace.vue'
import TeacherOverview from '@/components/teacher/TeacherOverview.vue'
import TeacherPblQueue from '@/components/teacher/TeacherPblQueue.vue'
import {
  normalizeTeacherWorkspaceQuery,
  ownedTeacherClassId,
  type TeacherWorkspaceTarget,
} from '@/components/teacher/teacherWorkspaceRouting'
import TeacherWorkspaceNav, { type TeacherWorkspace } from '@/components/teacher/TeacherWorkspaceNav.vue'
import PageContextBar from '@/components/ui/PageContextBar.vue'
import { activateButtonOnKey } from '@/components/ui/keyboard'
import { getReviewQueue } from '@/features/content/public'
import { getTeacherClasses } from '@/features/classroom/public'
import { getSession, logout, requireRole } from '@/features/identity/public'
import { getTeacherPblWorkItems } from '@/features/pbl/public'
import { getReportSummariesAsync } from '@/features/reports/public'
import { goDetail, ROUTES } from '@/platform/navigation'

interface Refreshable {
  refresh: () => Promise<void>
}
interface ContentWorkspaceRef extends Refreshable {
  selectSection: (section?: string, snapshotId?: string, focusPending?: boolean) => Promise<void>
}
interface InsightsWorkspaceRef extends Refreshable {
  selectSection: (section?: string, context?: TeacherFollowUpContext) => Promise<void>
}

const currentWorkspace = ref<TeacherWorkspace>('overview')
const openedWorkspaces = ref<Record<TeacherWorkspace, boolean>>({
  overview: true,
  reports: false,
  problems: false,
  pbl: false,
})
const workspaceScrollTop = ref(0)
let currentScrollTop = 0
let initialTarget: TeacherWorkspaceTarget = { workspace: 'overview' }
let initialTargetApplied = false
const initialContentSection = ref<TeacherContentSection>()
const initialInsightsSection = ref<TeacherInsightsSection>()
const contentWorkspace = ref<ContentWorkspaceRef>()
const insightsWorkspace = ref<InsightsWorkspaceRef>()
const pblQueue = ref<Refreshable>()
const classes = ref<Array<{ id: number; name: string }>>([])
const selectedClassId = ref<number>()
const classesLoading = ref(false)
const classesLoaded = ref(false)
const classError = ref('')
const isReviewer = ref(false)
const pendingReports = ref<number>()
const pendingReview = ref<number>()
const pendingPbl = ref<number>()
const overviewLoading = ref(false)
const reportQueueError = ref(false)
const reviewQueueError = ref(false)
const pblQueueError = ref(false)
const workspaceCopy: Record<TeacherWorkspace, { title: string; description: string }> = {
  overview: { title: '今日待办', description: '汇总需要处理的报告、医学审核与 PBL 诊断。' },
  reports: { title: '学情与跟进', description: '跟进正式任务，并查看教学统计与学生学习记录。' },
  problems: { title: '内容与诊断', description: '处置诊断建议并管理正式教学资源。' },
  pbl: { title: 'PBL 课堂', description: '创建、运行和关闭课堂，查看逐学生阶段状态。' },
}
const workspaceTitle = computed(() => workspaceCopy[currentWorkspace.value].title)
const workspaceDescription = computed(() => workspaceCopy[currentWorkspace.value].description)

function recordWorkspaceScroll(event: { detail: { scrollTop: number } }) {
  currentScrollTop = event.detail.scrollTop
}
async function resetWorkspaceScroll() {
  workspaceScrollTop.value = currentScrollTop
  await nextTick()
  workspaceScrollTop.value = 0
}

onLoad((query) => {
  initialTarget = normalizeTeacherWorkspaceQuery((query || {}) as Record<string, string | undefined>)
  initialContentSection.value = initialTarget.contentSection
  initialInsightsSection.value = initialTarget.insightsSection
  currentWorkspace.value = initialTarget.workspace
  openedWorkspaces.value[initialTarget.workspace] = true
})

onShow(async () => {
  if (!requireRole('teacher')) return
  isReviewer.value = getSession()?.permissions?.includes('medical_review') || false
  if (!classesLoaded.value) await loadClasses()
  if (!initialTargetApplied) selectedClassId.value = ownedTeacherClassId(initialTarget.classId, classes.value)
  await nextTick()
  if (!initialTargetApplied && initialTarget.workspace === 'problems') {
    await contentWorkspace.value?.selectSection(initialTarget.contentSection, initialTarget.snapshotId)
  } else if (!initialTargetApplied && initialTarget.workspace === 'reports') {
    await insightsWorkspace.value?.selectSection(initialTarget.insightsSection, initialTarget.followUpContext)
  } else {
    await refreshWorkspace(currentWorkspace.value)
  }
  initialTargetApplied = true
})

async function loadClasses() {
  if (classesLoading.value) return
  classesLoading.value = true
  classError.value = ''
  try {
    const values = await getTeacherClasses()
    classes.value = values.filter((item) => item.status === 'active').map((item) => ({ id: item.id, name: item.name }))
    if (selectedClassId.value && !classes.value.some((item) => item.id === selectedClassId.value)) {
      selectedClassId.value = undefined
    }
  } catch (reason) {
    classError.value = reason instanceof Error ? reason.message : '班级范围读取失败'
  } finally {
    classesLoaded.value = true
    classesLoading.value = false
  }
}

function changeClass(classId: number | undefined) {
  selectedClassId.value = classId
}

function switchWorkspace(workspace: TeacherWorkspace) {
  openedWorkspaces.value[workspace] = true
  currentWorkspace.value = workspace
  void resetWorkspaceScroll()
}

async function openContent(section: TeacherContentSection, snapshotId?: string, focusPending = false) {
  openedWorkspaces.value.problems = true
  currentWorkspace.value = 'problems'
  await resetWorkspaceScroll()
  await nextTick()
  await contentWorkspace.value?.selectSection(section, snapshotId, focusPending)
}

async function openInsights(section: TeacherInsightsSection, context?: TeacherFollowUpContext) {
  // The child is created lazily. Supply its initial section before mounting so
  // the first real tap does not briefly fall back to the PBL default.
  initialInsightsSection.value = section
  openedWorkspaces.value.reports = true
  currentWorkspace.value = 'reports'
  await resetWorkspaceScroll()
  await nextTick()
  await insightsWorkspace.value?.selectSection(section, context)
}

async function openFollowUp(context: { classId?: string; sessionId: string; studentId: string }) {
  const classId = Number(context.classId)
  if (classId > 0 && classes.value.some((item) => item.id === classId)) selectedClassId.value = classId
  await openInsights('pbl-follow-ups', context)
}

async function refreshWorkspace(workspace: TeacherWorkspace) {
  await nextTick()
  if (workspace === 'overview') return refreshOverview()
  if (workspace === 'reports') return insightsWorkspace.value?.refresh()
  if (workspace === 'problems') return contentWorkspace.value?.refresh()
  return pblQueue.value?.refresh()
}

async function refreshOverview() {
  if (overviewLoading.value) return
  overviewLoading.value = true
  reportQueueError.value = false
  reviewQueueError.value = false
  pblQueueError.value = false
  const [reports, review, pbl] = await Promise.allSettled([
    getReportSummariesAsync(1, 0),
    isReviewer.value ? getReviewQueue() : Promise.resolve([]),
    getTeacherPblWorkItems({ workStatus: 'pending', offset: 0 }),
  ])
  if (reports.status === 'fulfilled') pendingReports.value = reports.value.pendingCount
  else {
    pendingReports.value = undefined
    reportQueueError.value = true
  }
  if (review.status === 'fulfilled') pendingReview.value = review.value.length
  else {
    pendingReview.value = undefined
    reviewQueueError.value = true
  }
  if (pbl.status === 'fulfilled') pendingPbl.value = pbl.value.total
  else {
    pendingPbl.value = undefined
    pblQueueError.value = true
  }
  overviewLoading.value = false
}

function openReview(source: 'overview' | 'resources') {
  goDetail(ROUTES.teacherReviewList, {
    returnTab: source === 'resources' ? 'problems' : 'overview',
    returnSection: source === 'resources' ? 'resources' : undefined,
  })
}
function openClasses() {
  goDetail(ROUTES.teacherClasses)
}
function openKnowledgeCards(source: 'overview' | 'resources') {
  goDetail(ROUTES.teacherKnowledgeCards, {
    returnTab: source === 'resources' ? 'problems' : 'overview',
    returnSection: source === 'resources' ? 'resources' : undefined,
  })
}
function openReport(id: string) {
  goDetail(ROUTES.teacherReportDetail, { reportId: id })
}
</script>

<style scoped>
.teacher-page {
  display: flex;
  height: calc(100vh - var(--window-top, 0px));
  min-height: 0;
  overflow: hidden;
  flex-direction: column;
  background: var(--med-page);
}
.logout {
  min-width: 44px;
  min-height: 44px;
  margin: 0;
  padding: 0 12rpx;
  flex: none;
  align-self: flex-start;
  color: var(--med-muted);
  background: transparent;
  font-size: 24rpx;
}
.workspace-body {
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
}
.workspace-navigation {
  order: 2;
  flex: none;
}
.workspace-scroll {
  height: 0;
  min-width: 0;
  min-height: 0;
  flex: 1;
}
.workspace-content {
  max-width: 920px;
  margin: 0 auto;
  padding: 0 24rpx 24rpx;
  box-sizing: border-box;
}
@media screen and (max-width: 360px) {
  .logout {
    font-size: 13px;
  }
}
@media screen and (min-width: 600px) {
  .logout {
    font-size: 14px;
  }
  .workspace-content {
    padding: 0 28px 28px;
  }
}
@media screen and (min-width: 900px) {
  .workspace-body {
    flex-direction: row;
  }
  .workspace-navigation {
    width: 176px;
    order: 0;
  }
  .workspace-scroll {
    height: 100%;
  }
  .workspace-content {
    padding: 0 32px 32px;
  }
}
</style>
