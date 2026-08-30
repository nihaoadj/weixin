<template>
  <view class="problem-list-page">
    <view class="toolbar card">
      <view class="tabs">
        <view
          class="tab"
          :class="{ active: currentStatus === 'pending' }"
          @click="switchStatus('pending')"
          >待审核
          <text
            v-if="pendingCount"
            class="count"
            >{{ pendingCount }}</text
          ></view
        >
        <view
          class="tab"
          :class="{ active: currentStatus === 'published' }"
          @click="switchStatus('published')"
          >已发布</view
        >
      </view>
      <view class="toolbar-buttons">
        <button
          class="small-button add"
          @click="addCase"
        >
          ✦ AI 生成病例
        </button>
        <button
          class="small-button add"
          @click="addProblem"
        >
          ＋ 新建
        </button>
        <button
          v-if="isDemoMode()"
          class="small-button"
          @click="resetData"
        >
          ↻ 示例
        </button>
      </view>
    </view>

    <MedState
      v-if="isRefreshing"
      variant="loading"
      icon="retry"
      title="正在加载教学内容"
      description="正在同步问题与病例状态。"
    />
    <MedState
      v-else-if="loadError"
      variant="error"
      icon="retry"
      title="教学内容加载失败"
      :description="loadError"
      action-label="重新加载"
      @action="refresh"
    />
    <MedState
      v-else-if="visibleProblems.length === 0"
      variant="first-use"
      icon="book"
      :title="currentStatus === 'pending' ? '还没有待处理内容' : '还没有已发布内容'"
      description="创建一个练习问题，或生成结构化病例作为新的教学任务。"
      action-label="新建问题"
      secondary-action-label="生成病例"
      @action="addProblem"
      @secondary-action="addCase"
    />
    <template v-if="!isRefreshing && !loadError">
      <view
        v-for="problem in visibleProblems"
        :key="problem.id"
        class="problem-card card"
      >
        <view class="header">
          <view
            ><text class="type">{{ problem.type }}</text
            ><text class="target">{{ targetText(problem) }}</text></view
          >
          <text class="time">{{ problem.time }}</text>
        </view>
        <text
          class="title"
          @click="viewDetail(problem.id)"
          >{{ problem.title }}</text
        >
        <text
          v-if="problem.description"
          class="description"
          >{{ problem.description }}</text
        >
        <text
          v-if="problem.contentType === 'guided_case'"
          class="case-meta"
          >病例 · {{ problem.specialty }} · {{ problem.difficulty }} · {{ problem.estimatedMinutes }}分钟 · V{{
            problem.version
          }}</text
        >
        <view
          v-if="currentStatus === 'pending'"
          class="actions"
        >
          <template v-if="problem.contentType === 'guided_case'">
            <button
              class="action edit"
              @click="editCase(problem.id)"
            >
              {{ problem.medicalReviewStatus === 'pending' ? '查看' : '编辑' }}
            </button>
            <button
              v-if="problem.medicalReviewStatus === 'not_submitted' || problem.medicalReviewStatus === 'rejected'"
              class="action publish"
              @click="submitReview(problem.id)"
            >
              提交审核
            </button>
            <button
              v-else-if="problem.medicalReviewStatus === 'approved'"
              class="action publish"
              @click="publishProblem(problem.id)"
            >
              发布
            </button>
            <text
              v-else
              class="review-status"
              >医学审核中</text
            >
          </template>
          <template v-else>
            <button
              class="action reject"
              @click="rejectProblem(problem.id)"
            >
              拒绝
            </button>
            <button
              class="action edit"
              @click="editProblem(problem.id)"
            >
              编辑
            </button>
            <button
              class="action publish"
              @click="publishProblem(problem.id)"
            >
              发布
            </button>
          </template>
        </view>
        <view
          v-else
          class="actions published-actions"
        >
          <text class="publish-time">{{ problem.publishTime || '已发布' }}</text>
          <button
            class="action stats"
            @click="problem.contentType === 'guided_case' ? editCase(problem.id) : viewStats(problem.id)"
          >
            {{ problem.contentType === 'guided_case' ? '创建新版本' : '查看统计' }}
          </button>
        </view>
      </view>
    </template>
    <button
      v-if="hasMore"
      class="load-more"
      :loading="isLoading"
      @click="loadMore"
    >
      加载更多
    </button>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import MedState from '@/components/ui/MedState.vue'
import { isDemoMode } from '@/config/runtime'
import { goDetail } from '@/services/navigation'
import {
  getProblemsAsync,
  publishProblemAsync,
  rejectProblemAsync,
  resetProblemsAsync,
} from '@/services/repositoryAsync'
import {
  getGuidedCasesAsync,
  publishGuidedCaseAsync,
  submitGuidedCaseForReviewAsync,
} from '@/services/caseRepositoryAsync'
import type { Problem } from '@/types/domain'

type StatusTab = 'pending' | 'published'
const emit = defineEmits<{ count: [value: number]; published: [value: number] }>()
const currentStatus = ref<StatusTab>('pending')
const allProblems = ref<Problem[]>([])
const page = ref(1)
const pageSize = 10
const isLoading = ref(false)
const isRefreshing = ref(false)
const loadError = ref('')
const pendingCount = computed(
  () =>
    allProblems.value.filter(
      (item) =>
        item.status === '待审核' || (item.contentType === 'guided_case' && item.medicalReviewStatus === 'rejected'),
    ).length,
)
const filtered = computed(() =>
  allProblems.value
    .filter((item) =>
      currentStatus.value === 'pending'
        ? item.status === '待审核' || (item.contentType === 'guided_case' && item.medicalReviewStatus === 'rejected')
        : item.status === '已发布',
    )
    .sort((a, b) => b.time.localeCompare(a.time)),
)
const visibleProblems = computed(() => filtered.value.slice(0, page.value * pageSize))
const hasMore = computed(() => visibleProblems.value.length < filtered.value.length)

async function refresh() {
  if (isRefreshing.value) return
  isRefreshing.value = true
  loadError.value = ''
  try {
    const [regularProblems, guidedCases] = await Promise.all([getProblemsAsync(), getGuidedCasesAsync()])
    allProblems.value = [
      ...regularProblems,
      ...guidedCases.filter((guided) => !regularProblems.some((item) => item.id === guided.id)),
    ]
    page.value = 1
  } catch (error) {
    allProblems.value = []
    loadError.value = error instanceof Error ? error.message : '请稍后重试'
  } finally {
    isRefreshing.value = false
  }
  emit('count', pendingCount.value)
  emit('published', allProblems.value.filter((item) => item.status === '已发布').length)
}

function switchStatus(status: StatusTab) {
  currentStatus.value = status
  page.value = 1
}

function targetText(problem: Problem) {
  if (problem.target === 'class') return problem.targetLabel || problem.className || '指定班级'
  if (problem.target === 'individual') return problem.targetLabel || `指定学生 ${problem.targetIds?.length || 0} 人`
  return '全体学生'
}

function loadMore() {
  if (!hasMore.value || isLoading.value) return
  isLoading.value = true
  setTimeout(() => {
    page.value += 1
    isLoading.value = false
  }, 250)
}

async function updateStatus(id: string, status: Problem['status']) {
  const guided = allProblems.value.find((item) => item.id === id)?.contentType === 'guided_case'
  const updated =
    status === '已发布'
      ? guided
        ? await publishGuidedCaseAsync(id)
        : await publishProblemAsync(id)
      : await rejectProblemAsync(id)
  if (updated) {
    allProblems.value = allProblems.value.map((item) => (item.id === id ? updated : item))
  }
  emit('count', pendingCount.value)
  emit('published', allProblems.value.filter((item) => item.status === '已发布').length)
}

async function submitReview(id: string) {
  try {
    const updated = await submitGuidedCaseForReviewAsync(id)
    if (updated) allProblems.value = allProblems.value.map((item) => (item.id === id ? updated : item))
    emit('count', pendingCount.value)
    uni.showToast({ title: '已提交医学审核', icon: 'success' })
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : '提交审核失败', icon: 'none' })
  }
}

function rejectProblem(id: string) {
  uni.showModal({
    title: '确认拒绝',
    content: '确定要拒绝此问题吗？',
    success: async ({ confirm }) => {
      if (confirm) {
        try {
          await updateStatus(id, '已拒绝')
          uni.showToast({ title: '已拒绝', icon: 'success' })
        } catch (error) {
          uni.showToast({ title: error instanceof Error ? error.message : '拒绝失败', icon: 'none' })
        }
      }
    },
  })
}

function publishProblem(id: string) {
  uni.showModal({
    title: '确认发布',
    content: '发布后学生端即可看到该问题。',
    success: async ({ confirm }) => {
      if (confirm) {
        try {
          await updateStatus(id, '已发布')
          uni.showToast({ title: '发布成功', icon: 'success' })
        } catch (error) {
          uni.showToast({ title: error instanceof Error ? error.message : '发布失败', icon: 'none' })
        }
      }
    },
  })
}

function editProblem(id: string) {
  goDetail('/pages/teacher/problem-edit/problem-edit', { id })
}
function addProblem() {
  uni.navigateTo({ url: '/pages/teacher/problem-edit/problem-edit' })
}
function addCase() {
  uni.navigateTo({ url: '/pages/teacher/case-edit/case-edit' })
}
function editCase(id: string) {
  goDetail('/pages/teacher/case-edit/case-edit', { id })
}
function viewDetail(id: string) {
  goDetail('/pages/teacher/problem-detail/problem-detail', { id })
}
function viewStats(id: string) {
  goDetail('/pages/teacher/problem-stats/problem-stats', { id })
}
function resetData() {
  uni.showModal({
    title: '恢复示例数据',
    content: '这会替换当前本地问题数据，是否继续？',
    success: async ({ confirm }) => {
      if (confirm) {
        allProblems.value = await resetProblemsAsync()
        emit('count', pendingCount.value)
        uni.showToast({ title: '已恢复', icon: 'success' })
      }
    },
  })
}

defineExpose({ refresh })
</script>

<style scoped>
.problem-list-page {
  padding: 24rpx 24rpx 180rpx;
}
.toolbar {
  margin-bottom: 20rpx;
  padding: 24rpx;
}
.tabs {
  display: flex;
  border-bottom: 1rpx solid #e8eef4;
}
.tab {
  position: relative;
  padding: 12rpx 24rpx 22rpx;
  color: #718096;
}
.tab.active {
  color: #087f8c;
  font-weight: 700;
}
.tab.active::after {
  position: absolute;
  right: 20rpx;
  bottom: 0;
  left: 20rpx;
  height: 5rpx;
  content: '';
  background: #087f8c;
  border-radius: 99rpx;
}
.count {
  margin-left: 6rpx;
  padding: 2rpx 9rpx;
  color: #fff;
  background: #e35d6a;
  border-radius: 99rpx;
  font-size: 19rpx;
}
.toolbar-buttons {
  display: flex;
  margin-top: 22rpx;
  gap: 14rpx;
}
.small-button {
  height: 64rpx;
  margin: 0;
  padding: 0 24rpx;
  line-height: 64rpx;
  color: #526174;
  background: #edf2f7;
  border-radius: 14rpx;
  font-size: 23rpx;
}
.small-button.add {
  color: #fff;
  background: #087f8c;
}
.problem-card {
  margin-bottom: 20rpx;
  padding: 28rpx;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.type {
  padding: 6rpx 13rpx;
  color: #087f8c;
  background: #e6f7f5;
  border-radius: 10rpx;
  font-size: 21rpx;
}
.target {
  margin-left: 12rpx;
  color: #718096;
  font-size: 21rpx;
}
.time {
  color: #94a3b8;
  font-size: 21rpx;
}
.title {
  display: block;
  margin-top: 22rpx;
  font-size: 30rpx;
  font-weight: 700;
  line-height: 1.5;
}
.description {
  display: -webkit-box;
  margin-top: 14rpx;
  overflow: hidden;
  color: #64748b;
  font-size: 24rpx;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.case-meta {
  display: block;
  margin-top: 12rpx;
  color: #087f8c;
  font-size: 21rpx;
}
.actions {
  display: flex;
  margin-top: 24rpx;
  justify-content: flex-end;
  gap: 12rpx;
}
.action {
  height: 60rpx;
  margin: 0;
  padding: 0 24rpx;
  line-height: 60rpx;
  border-radius: 13rpx;
  font-size: 22rpx;
}
.reject {
  color: #b8323d;
  background: #fff0f1;
}
.edit {
  color: #526174;
  background: #edf2f7;
}
.publish,
.stats {
  color: #fff;
  background: #087f8c;
}
.published-actions {
  align-items: center;
  justify-content: space-between;
}
.publish-time {
  color: #718096;
  font-size: 22rpx;
}
.load-more {
  margin-top: 24rpx;
  color: #087f8c;
  background: transparent;
  font-size: 24rpx;
}
</style>
