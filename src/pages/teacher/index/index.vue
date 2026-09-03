<template>
  <view class="safe-page teacher-page">
    <view class="workspace-header">
      <view class="header-copy">
        <text class="eyebrow-label">教学查房</text>
        <text class="workspace-title">{{ workspaceTitle }}</text>
        <text class="workspace-description">{{ workspaceDescription }}</text>
      </view>
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
    </view>
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
          <TeacherOverview
            v-if="currentWorkspace === 'overview'"
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
            v-else-if="currentWorkspace === 'reports'"
            ref="reportList"
            @select="openReport"
            @manage="switchWorkspace('problems')"
          />
          <TeacherProblemList
            v-else-if="currentWorkspace === 'problems'"
            ref="problemList"
          />
          <TeacherPblQueue v-else />
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
import { requireRole, logout, getSession } from '@/features/identity/public'
import { getReportSummariesAsync } from '@/features/reports/public'
import { getReviewQueue } from '@/features/content/public'
import { goDetail, goReplace, ROUTES } from '@/platform/navigation'

interface Refreshable {
  refresh: () => Promise<void>
}
const currentWorkspace = ref<TeacherWorkspace>('reports')
const reportList = ref<Refreshable | null>(null)
const problemList = ref<Refreshable | null>(null)
const isReviewer = ref(false)
const pendingReports = ref<number>()
const pendingReview = ref<number>()
const overviewLoading = ref(false)
const reportQueueError = ref(false)
const reviewQueueError = ref(false)
const workspaceCopy: Record<TeacherWorkspace, { title: string; description: string }> = {
  overview: { title: '工作台', description: '查看待办，管理班级与学习进展。' },
  reports: { title: '报告批阅', description: '阅读学生推理记录，给出下一步学习建议。' },
  problems: { title: '教学内容', description: '创建、审核并发布练习问题与结构化病例。' },
  pbl: { title: 'PBL 教学助手', description: '审阅病理学讨论中的薄弱分析与建议题。' },
}
const workspaceTitle = computed(() => workspaceCopy[currentWorkspace.value].title)
const workspaceDescription = computed(() => workspaceCopy[currentWorkspace.value].description)

onLoad((query) => {
  if (query?.tab === 'overview' || query?.tab === 'reports' || query?.tab === 'problems' || query?.tab === 'pbl') {
    currentWorkspace.value = query.tab
  }
})

onShow(async () => {
  if (!requireRole('teacher')) return
  isReviewer.value = getSession()?.permissions?.includes('medical_review') || false
  await nextTick()
  if (currentWorkspace.value === 'overview') void refreshOverview()
  else if (currentWorkspace.value === 'reports') void reportList.value?.refresh()
  else if (currentWorkspace.value === 'problems') void problemList.value?.refresh()
})

function switchWorkspace(workspace: TeacherWorkspace) {
  if (workspace === currentWorkspace.value) return
  goReplace(ROUTES.teacherWorkspace, { tab: workspace })
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
.workspace-header {
  display: flex;
  padding: 24rpx 28rpx;
  flex: none;
  align-items: center;
  justify-content: space-between;
  gap: 24rpx;
  background: var(--med-surface);
  border-bottom: 1rpx solid var(--med-border);
}
.header-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
}
.workspace-title {
  margin-top: 6rpx;
  color: var(--med-ink);
  font-size: 38rpx;
  font-weight: 800;
  line-height: 1.4;
}
.workspace-description {
  margin-top: 8rpx;
  color: var(--med-muted);
  font-size: 24rpx;
  line-height: 1.5;
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
@media screen and (max-width: 360px) {
  .workspace-description {
    font-size: 12px;
  }
  .logout {
    font-size: 13px;
  }
}
@media screen and (min-width: 600px) {
  .workspace-header {
    padding: 20px 28px;
  }
  .workspace-title {
    font-size: 26px;
  }
  .workspace-description,
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
