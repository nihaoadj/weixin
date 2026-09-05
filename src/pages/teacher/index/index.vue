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
        :aria-label="workspaceTitle"
      >
        <view class="workspace-content">
          <view
            v-if="currentWorkspace === 'reports' || currentWorkspace === 'problems'"
            class="workspace-shortcuts"
            aria-label="工作区快捷入口"
          >
            <button
              v-if="currentWorkspace === 'reports'"
              @click="openAnalytics"
            >
              查看教学学情
            </button>
            <template v-else>
              <button @click="openKnowledgeCards">知识补充卡</button>
              <button
                v-if="isReviewer"
                @click="openReview"
              >
                医学审核
              </button>
            </template>
          </view>
          <TeacherOverview
            v-if="openedWorkspaces.overview"
            v-show="currentWorkspace === 'overview'"
            :loading="overviewLoading"
            :is-reviewer="isReviewer"
            :pending-reports="pendingReports"
            :pending-review="pendingReview"
            :report-error="reportQueueError"
            :review-error="reviewQueueError"
            @reports="switchWorkspace('reports')"
            @review="openReview"
            @classes="openClasses"
            @analytics="openAnalytics"
            @knowledge-cards="openKnowledgeCards"
            @retry="refreshOverview"
          />
          <TeacherReportList
            v-if="openedWorkspaces.reports"
            v-show="currentWorkspace === 'reports'"
            ref="reportList"
            @select="openReport"
            @manage="switchWorkspace('problems')"
          />
          <TeacherProblemList
            v-if="openedWorkspaces.problems"
            v-show="currentWorkspace === 'problems'"
            ref="problemList"
          />
          <TeacherPblQueue
            v-if="openedWorkspaces.pbl"
            v-show="currentWorkspace === 'pbl'"
            ref="pblQueue"
          />
        </view>
      </scroll-view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { activateButtonOnKey } from '@/components/ui/keyboard'
import { computed, nextTick, ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import TeacherWorkspaceNav, { type TeacherWorkspace } from '@/components/teacher/TeacherWorkspaceNav.vue'
import TeacherOverview from '@/components/teacher/TeacherOverview.vue'
import TeacherProblemList from '@/components/TeacherProblemList.vue'
import TeacherReportList from '@/components/TeacherReportList.vue'
import TeacherPblQueue from '@/components/teacher/TeacherPblQueue.vue'
import PageContextBar from '@/components/ui/PageContextBar.vue'
import { requireRole, logout, getSession } from '@/features/identity/public'
import { getReportSummariesAsync } from '@/features/reports/public'
import { getReviewQueue } from '@/features/content/public'
import { goDetail, ROUTES } from '@/platform/navigation'

interface Refreshable {
  refresh: () => Promise<void>
}
const currentWorkspace = ref<TeacherWorkspace>('pbl')
const openedWorkspaces = ref<Record<TeacherWorkspace, boolean>>({
  overview: false,
  reports: false,
  problems: false,
  pbl: true,
})
const reportList = ref<Refreshable | null>(null)
const problemList = ref<Refreshable | null>(null)
const pblQueue = ref<Refreshable | null>(null)
const isReviewer = ref(false)
const pendingReports = ref<number>()
const pendingReview = ref<number>()
const overviewLoading = ref(false)
const reportQueueError = ref(false)
const reviewQueueError = ref(false)
const workspaceCopy: Record<TeacherWorkspace, { title: string; description: string }> = {
  overview: { title: '工作概览', description: '查看待办，管理班级与学习进展。' },
  reports: { title: '学生学习记录', description: '阅读推理记录并查看班级学习变化。' },
  problems: { title: '内容管理', description: '创建、审核并发布练习问题与结构化病例。' },
  pbl: { title: '课堂与诊断', description: '组织课堂，审阅薄弱分析与建议题。' },
}
const workspaceTitle = computed(() => workspaceCopy[currentWorkspace.value].title)
const workspaceDescription = computed(() => workspaceCopy[currentWorkspace.value].description)

onLoad((query) => {
  const tab = query?.tab
  if (tab === 'overview' || tab === 'reports' || tab === 'problems' || tab === 'pbl') {
    const workspace: TeacherWorkspace = tab
    currentWorkspace.value = workspace
    openedWorkspaces.value[workspace] = true
  }
})

onShow(async () => {
  if (!requireRole('teacher')) return
  isReviewer.value = getSession()?.permissions?.includes('medical_review') || false
  await nextTick()
  void refreshWorkspace(currentWorkspace.value)
})

function switchWorkspace(workspace: TeacherWorkspace) {
  if (workspace === currentWorkspace.value) return
  openedWorkspaces.value[workspace] = true
  currentWorkspace.value = workspace
  void refreshWorkspace(workspace)
}

async function refreshWorkspace(workspace: TeacherWorkspace) {
  await nextTick()
  if (workspace === 'overview') return refreshOverview()
  if (workspace === 'reports') return reportList.value?.refresh()
  if (workspace === 'problems') return problemList.value?.refresh()
  return pblQueue.value?.refresh()
}

async function refreshOverview() {
  if (overviewLoading.value) return
  overviewLoading.value = true
  reportQueueError.value = false
  reviewQueueError.value = false
  const [reports, review] = await Promise.allSettled([
    getReportSummariesAsync(1, 0),
    isReviewer.value ? getReviewQueue() : Promise.resolve([]),
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
  overviewLoading.value = false
}

function openAnalytics() {
  goDetail(ROUTES.teacherAnalytics)
}
function openReview() {
  goDetail(ROUTES.teacherReviewList)
}
function openClasses() {
  goDetail(ROUTES.teacherClasses)
}
function openKnowledgeCards() {
  goDetail(ROUTES.teacherKnowledgeCards)
}
function openReport(id: string) {
  goDetail(ROUTES.teacherReportDetail, { reportId: id })
}
</script>

<style scoped>
.teacher-page {
  display: flex;
  height: calc(100vh - var(--window-top, 0px));
  /* #ifdef H5 */
  height: calc(100dvh - var(--window-top, 0px));
  /* #endif */
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
  max-width: 840px;
  margin: 0 auto;
  padding: 0 24rpx 24rpx;
  box-sizing: border-box;
}
.workspace-shortcuts {
  display: flex;
  padding-top: 20rpx;
  flex-wrap: wrap;
  gap: 12rpx;
}
.workspace-shortcuts button {
  min-height: 72rpx;
  margin: 0;
  padding: 0 22rpx;
  color: var(--med-clinical);
  background: var(--med-wash);
  font-size: 23rpx;
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
  .workspace-shortcuts {
    padding-top: 20px;
    gap: 8px;
  }
  .workspace-shortcuts button {
    min-height: 44px;
    padding: 0 14px;
    font-size: 14px;
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
