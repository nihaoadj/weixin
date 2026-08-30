<template>
  <view class="safe-page teacher-page">
    <view class="workspace-header">
      <view class="header-brand">
        <view class="header-mark"><MedIcon name="brand" /></view>
        <view><text class="eyebrow">TEACHER WORKSPACE</text><text class="title">教学协作工作台</text></view>
      </view>
      <text
        class="logout"
        @click="logout"
        >退出</text
      >
    </view>
    <view class="dashboard-strip">
      <view class="metric"
        ><text class="metric-value">{{ pendingReports }}</text
        ><text>待批阅</text></view
      >
      <view class="metric"
        ><text class="metric-value">{{ reviewedReports }}</text
        ><text>已批阅</text></view
      >
      <view class="metric"
        ><text class="metric-value">{{ publishedProblems }}</text
        ><text>已发布题目</text></view
      >
    </view>
    <view class="quick-links">
      <button
        class="secondary"
        @click="openAnalytics"
      >
        学情分析
      </button>
      <button
        v-if="isReviewer"
        class="secondary"
        @click="openReview"
      >
        医学审核<span v-if="pendingReview"> · {{ pendingReview }}</span>
      </button>
      <button
        class="secondary"
        @click="openClasses"
      >
        班级管理
      </button>
    </view>
    <view class="section-heading">
      <text class="eyebrow-label">{{ currentTab === 'reports' ? 'ASSESSMENT' : 'CONTENT' }}</text>
      <text>{{ currentTab === 'reports' ? '学生报告' : '问题管理' }}</text>
    </view>
    <TeacherReportList
      v-if="currentTab === 'reports'"
      ref="reportList"
      @select="openReport"
      @count="pendingReports = $event"
      @reviewed="reviewedReports = $event"
      @manage="switchTab('problems')"
    />
    <TeacherProblemList
      v-else
      ref="problemList"
      @count="pendingProblems = $event"
      @published="publishedProblems = $event"
    />

    <view class="tab-bar">
      <view
        class="tab"
        :class="{ active: currentTab === 'reports' }"
        @click="switchTab('reports')"
      >
        <MedIcon name="report" /><text>报告</text
        ><text
          v-if="pendingReports"
          class="badge"
          >{{ pendingReports }}</text
        >
      </view>
      <view
        class="tab"
        :class="{ active: currentTab === 'problems' }"
        @click="switchTab('problems')"
      >
        <MedIcon name="book" /><text>问题</text
        ><text
          v-if="pendingProblems"
          class="badge"
          >{{ pendingProblems }}</text
        >
      </view>
      <view
        class="tab"
        @click="openAnalytics"
        ><MedIcon name="report" /><text>学情</text></view
      >
    </view>
  </view>
</template>

<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import MedIcon from '@/components/ui/MedIcon.vue'
import TeacherProblemList from '@/components/TeacherProblemList.vue'
import TeacherReportList from '@/components/TeacherReportList.vue'
import { requireRole, logout } from '@/services/auth'
import { goDetail } from '@/services/navigation'
import { getSession } from '@/services/repository'
import { getReviewQueue } from '@/services/teacherInsights'

type Tab = 'reports' | 'problems'
interface Refreshable {
  refresh: () => void
}
const currentTab = ref<Tab>('reports')
const pendingReports = ref(0)
const pendingProblems = ref(0)
const reviewedReports = ref(0)
const publishedProblems = ref(0)
const reportList = ref<Refreshable | null>(null)
const problemList = ref<Refreshable | null>(null)
const isReviewer = ref(false)
const pendingReview = ref(0)

onLoad((query) => {
  if (query?.tab === 'problems') currentTab.value = 'problems'
})

onShow(async () => {
  if (!requireRole('teacher')) return
  isReviewer.value = getSession()?.permissions?.includes('medical_review') || false
  if (isReviewer.value) {
    try {
      pendingReview.value = (await getReviewQueue()).length
    } catch {
      pendingReview.value = 0
    }
  }
  await nextTick()
  reportList.value?.refresh()
  problemList.value?.refresh()
})

async function switchTab(tab: Tab) {
  currentTab.value = tab
  await nextTick()
  if (tab === 'reports') reportList.value?.refresh()
  else problemList.value?.refresh()
}

function openAnalytics() {
  uni.navigateTo({ url: '/pages/teacher/analytics/index' })
}
function openReview() {
  uni.navigateTo({ url: '/pages/teacher/medical-review/review-list' })
}
function openClasses() {
  uni.navigateTo({ url: '/pages/teacher/classes/classes' })
}

function openReport(id: string) {
  goDetail('/pages/teacher/detail/detail', { reportId: id })
}
</script>

<style scoped>
.teacher-page {
  min-height: 100vh;
  background: radial-gradient(circle at 90% 0, rgba(53, 183, 168, 0.12), transparent 30%), #f4f8fa;
}
.workspace-header {
  display: flex;
  padding: 28rpx 32rpx 22rpx;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.96);
  border-bottom: 1rpx solid #dbe7eb;
}
.header-brand,
.header-brand > view:last-child {
  display: flex;
  align-items: center;
}
.header-brand > view:last-child {
  flex-direction: column;
  align-items: flex-start;
}
.header-mark {
  display: flex;
  width: 62rpx;
  height: 62rpx;
  margin-right: 14rpx;
  align-items: center;
  justify-content: center;
  background: #eaf7f5;
  border-radius: 18rpx;
}
.eyebrow {
  color: #087f8c;
  font-size: 18rpx;
  letter-spacing: 2rpx;
}
.title {
  margin-top: 5rpx;
  color: #0b2239;
  font-size: 31rpx;
  font-weight: 750;
}
.logout {
  color: #718096;
  font-size: 24rpx;
}
.dashboard-strip {
  display: grid;
  margin: 24rpx;
  padding: 24rpx 16rpx;
  grid-template-columns: repeat(3, 1fr);
  background: linear-gradient(135deg, #0b2239, #123d50);
  border-radius: 28rpx;
  box-shadow: 0 18rpx 44rpx rgba(11, 34, 57, 0.18);
}
.metric {
  display: flex;
  align-items: center;
  color: #bad3dc;
  flex-direction: column;
  font-size: 20rpx;
}
.metric + .metric {
  border-left: 1rpx solid rgba(255, 255, 255, 0.13);
}
.metric-value {
  margin-bottom: 4rpx;
  color: #fff;
  font-size: 42rpx;
  font-weight: 800;
}
.section-heading {
  display: flex;
  margin: 34rpx 28rpx 0;
  flex-direction: column;
  color: #0b2239;
  font-size: 36rpx;
  font-weight: 800;
  gap: 6rpx;
}
.quick-links {
  display: flex;
  margin: 0 24rpx;
  gap: 14rpx;
}
.quick-links button {
  flex: 1;
}
.tab-bar {
  position: fixed;
  right: 0;
  bottom: 0;
  left: 0;
  display: flex;
  padding-bottom: env(safe-area-inset-bottom);
  background: #fff;
  border-top: 1rpx solid #dce8ef;
  box-shadow: 0 -10rpx 28rpx rgba(37, 54, 75, 0.06);
}
.tab {
  position: relative;
  display: flex;
  height: 112rpx;
  flex: 1;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 4rpx;
  color: #8795a8;
  font-size: 22rpx;
}
.tab.active {
  color: #087f8c;
  font-weight: 700;
}
.badge {
  position: absolute;
  top: 14rpx;
  left: calc(50% + 24rpx);
  min-width: 30rpx;
  height: 30rpx;
  padding: 0 5rpx;
  color: #fff;
  background: #e35d6a;
  border-radius: 99rpx;
  font-size: 18rpx;
  line-height: 30rpx;
  text-align: center;
}
</style>
