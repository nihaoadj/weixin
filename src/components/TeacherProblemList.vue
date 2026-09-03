<template>
  <view
    id="teacher-problem-list"
    class="problem-list-page"
  >
    <view class="toolbar">
      <view class="toolbar-buttons">
        <button
          hover-class="is-pressed"
          :hover-start-time="0"
          :hover-stay-time="80"
          tabindex="0"
          role="button"
          class="small-button add"
          @keydown="activateButtonOnKey"
          @click="addProblem"
        >
          新建问题
        </button>
        <button
          hover-class="is-pressed"
          :hover-start-time="0"
          :hover-stay-time="80"
          tabindex="0"
          role="button"
          class="small-button assist"
          @keydown="activateButtonOnKey"
          @click="addCase"
        >
          生成病例
        </button>
      </view>
      <view
        class="tabs"
        role="group"
        aria-label="教学内容状态"
      >
        <button
          hover-class="is-pressed"
          :hover-start-time="0"
          :hover-stay-time="80"
          tabindex="0"
          role="button"
          class="tab"
          :class="{ active: currentStatus === 'pending' }"
          :aria-pressed="currentStatus === 'pending'"
          @keydown="activateButtonOnKey"
          @click="switchStatus('pending')"
        >
          待审核
          <text
            v-if="pendingCount"
            class="count"
            >{{ pendingCount }}</text
          >
        </button>
        <button
          hover-class="is-pressed"
          :hover-start-time="0"
          :hover-stay-time="80"
          tabindex="0"
          role="button"
          class="tab"
          :class="{ active: currentStatus === 'published' }"
          :aria-pressed="currentStatus === 'published'"
          @keydown="activateButtonOnKey"
          @click="switchStatus('published')"
        >
          已发布
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
      class="content-state"
      variant="empty"
      icon="book"
      :title="currentStatus === 'pending' ? '还没有待处理内容' : '还没有已发布内容'"
      :description="
        currentStatus === 'pending'
          ? '可以用上方的新建问题或生成病例开始，也可以查看已发布内容。'
          : '完成审核并发布后，学生就能在练习列表中看到对应内容。'
      "
    />
    <template v-if="!isRefreshing && !loadError">
      <view
        v-for="problem in visibleProblems"
        :key="problem.id"
        class="problem-card card"
      >
        <button
          hover-class="is-pressed"
          :hover-start-time="0"
          :hover-stay-time="80"
          tabindex="0"
          role="button"
          class="problem-open motion-card"
          :aria-label="`查看问题详情：${problem.title}`"
          @keydown="activateButtonOnKey"
          @click="viewDetail(problem.id)"
        >
          <view class="header">
            <view class="target-group"
              ><text class="type">{{ problem.type }}</text
              ><text class="target">{{ targetText(problem) }}</text></view
            >
            <text class="time">{{ problem.time }}</text>
          </view>
          <view class="title-row">
            <text class="title">{{ problem.title }}</text>
            <text
              class="detail-arrow"
              aria-hidden="true"
              >›</text
            >
          </view>
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
        </button>
        <view
          v-if="currentStatus === 'pending'"
          class="actions"
        >
          <template v-if="problem.contentType === 'guided_case'">
            <button
              hover-class="is-pressed"
              :hover-start-time="0"
              :hover-stay-time="80"
              tabindex="0"
              role="button"
              class="action edit"
              @keydown="activateButtonOnKey"
              @click="editCase(problem.id)"
            >
              {{ problem.medicalReviewStatus === 'pending' ? '查看' : '编辑' }}
            </button>
            <button
              v-if="problem.medicalReviewStatus === 'not_submitted' || problem.medicalReviewStatus === 'rejected'"
              hover-class="is-pressed"
              :hover-start-time="0"
              :hover-stay-time="80"
              tabindex="0"
              role="button"
              class="action publish"
              @keydown="activateButtonOnKey"
              @click="submitReview(problem.id)"
            >
              提交审核
            </button>
            <button
              v-else-if="problem.medicalReviewStatus === 'approved'"
              hover-class="is-pressed"
              :hover-start-time="0"
              :hover-stay-time="80"
              tabindex="0"
              role="button"
              class="action publish"
              @keydown="activateButtonOnKey"
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
              hover-class="is-pressed"
              :hover-start-time="0"
              :hover-stay-time="80"
              tabindex="0"
              role="button"
              class="action reject"
              @keydown="activateButtonOnKey"
              @click="rejectProblem(problem.id)"
            >
              拒绝
            </button>
            <button
              hover-class="is-pressed"
              :hover-start-time="0"
              :hover-stay-time="80"
              tabindex="0"
              role="button"
              class="action edit"
              @keydown="activateButtonOnKey"
              @click="editProblem(problem.id)"
            >
              编辑
            </button>
            <button
              hover-class="is-pressed"
              :hover-start-time="0"
              :hover-stay-time="80"
              tabindex="0"
              role="button"
              class="action publish"
              @keydown="activateButtonOnKey"
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
            hover-class="is-pressed"
            :hover-start-time="0"
            :hover-stay-time="80"
            tabindex="0"
            role="button"
            class="action stats"
            @keydown="activateButtonOnKey"
            @click="problem.contentType === 'guided_case' ? editCase(problem.id) : viewStats(problem.id)"
          >
            {{ problem.contentType === 'guided_case' ? '创建新版本' : '查看统计' }}
          </button>
        </view>
      </view>
    </template>
    <button
      v-if="hasMore"
      hover-class="is-pressed"
      :hover-start-time="0"
      :hover-stay-time="80"
      tabindex="0"
      role="button"
      class="load-more"
      @keydown="activateButtonOnKey"
      @click="loadMore"
    >
      加载更多
    </button>
    <button
      v-if="isDemoRuntime()"
      hover-class="is-pressed"
      :hover-start-time="0"
      :hover-stay-time="80"
      tabindex="0"
      role="button"
      class="reset-data"
      @keydown="activateButtonOnKey"
      @click="resetData"
    >
      恢复示例内容
    </button>
  </view>
</template>

<script setup lang="ts">
import { activateButtonOnKey } from '@/components/ui/keyboard'
import { computed, ref } from 'vue'
import MedState from '@/components/ui/MedState.vue'
import { isDemoRuntime } from '@/features/identity/public'
import { goDetail, ROUTES } from '@/platform/navigation'
import {
  getProblemsAsync,
  publishProblemAsync,
  rejectProblemAsync,
  resetProblemsAsync,
} from '@/features/content/public'
import { getGuidedCasesAsync, publishGuidedCaseAsync, submitGuidedCaseForReviewAsync } from '@/features/content/public'
import type { Problem } from '@/types/domain'

type StatusTab = 'pending' | 'published'
const emit = defineEmits<{ count: [value: number]; published: [value: number] }>()
const currentStatus = ref<StatusTab>('pending')
const allProblems = ref<Problem[]>([])
const page = ref(1)
const pageSize = 10
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
  if (hasMore.value) page.value += 1
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
  goDetail(ROUTES.teacherProblemEdit, { id })
}
function addProblem() {
  goDetail(ROUTES.teacherProblemEdit)
}
function addCase() {
  goDetail(ROUTES.teacherCaseEdit)
}
function editCase(id: string) {
  goDetail(ROUTES.teacherCaseEdit, { id })
}
function viewDetail(id: string) {
  goDetail(ROUTES.teacherProblemDetail, { id })
}
function viewStats(id: string) {
  goDetail(ROUTES.teacherProblemStats, { id })
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
  padding: 24rpx 0 40rpx;
}
.toolbar {
  position: sticky;
  z-index: 2;
  top: 0;
  margin-bottom: 20rpx;
  padding: 0;
  background: var(--med-page);
}
.tabs {
  display: flex;
  margin-top: 16rpx;
  border-bottom: 1rpx solid var(--med-border);
}
.tab {
  display: flex;
  min-height: 88rpx;
  min-height: 44px;
  margin: 0;
  padding: 16rpx 24rpx;
  flex: 1;
  align-items: center;
  justify-content: center;
  color: var(--med-muted);
  background: transparent;
  border-bottom: 4rpx solid transparent;
  border-radius: 0;
  font-size: 28rpx;
  line-height: 1.4;
}
.tab.active {
  color: var(--med-brand);
  border-bottom-color: var(--med-brand);
  font-weight: 700;
}
.count {
  margin-left: 6rpx;
  padding: 2rpx 9rpx;
  color: #fff;
  background: var(--med-danger);
  border-radius: 99rpx;
  font-size: 22rpx;
}
.toolbar-buttons {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14rpx;
}
.small-button {
  display: flex;
  min-height: 88rpx;
  min-height: 44px;
  margin: 0;
  padding: 0 24rpx;
  align-items: center;
  justify-content: center;
  line-height: 1.2;
  color: var(--med-text-secondary);
  background: var(--med-divider);
  border-radius: 14rpx;
  font-size: 26rpx;
}
.small-button.add {
  color: #fff;
  background: var(--med-brand);
}
.small-button.assist {
  color: var(--med-brand-deep);
  background: var(--med-brand-soft);
}
.content-state {
  padding: 48rpx 28rpx;
}
.reset-data {
  min-height: 44px;
  margin: 24rpx auto 0;
  color: var(--med-muted);
  background: transparent;
  font-size: 23rpx;
}
.problem-card {
  margin-bottom: 20rpx;
  padding: 0;
}
.problem-open {
  display: block;
  width: 100%;
  margin: 0;
  padding: 24rpx 28rpx 20rpx;
  color: var(--med-text);
  background: transparent;
  border-radius: var(--med-radius-md);
  line-height: 1.5;
  text-align: left;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12rpx;
}
.target-group {
  display: flex;
  min-width: 0;
  align-items: center;
  flex-wrap: wrap;
  gap: 8rpx;
}
.type {
  padding: 6rpx 13rpx;
  color: var(--med-brand);
  background: var(--med-brand-soft);
  border-radius: 10rpx;
  font-size: 23rpx;
}
.target {
  overflow-wrap: anywhere;
  color: var(--med-muted);
  font-size: 23rpx;
}
.time {
  color: var(--med-muted);
  font-size: 23rpx;
  font-variant-numeric: tabular-nums;
}
.title {
  display: block;
  min-width: 0;
  flex: 1;
  overflow-wrap: anywhere;
  color: var(--med-text);
  background: transparent;
  font-size: 32rpx;
  font-weight: 700;
  line-height: 1.5;
  text-align: left;
}
.title-row {
  display: flex;
  align-items: baseline;
  gap: 16rpx;
  margin-top: 16rpx;
}
.detail-arrow {
  flex: none;
  color: var(--med-brand);
  font-size: 36rpx;
}
.description {
  display: -webkit-box;
  margin-top: 10rpx;
  overflow: hidden;
  color: var(--med-text-secondary);
  font-size: 28rpx;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.case-meta {
  display: block;
  margin-top: 12rpx;
  color: var(--med-brand);
  font-size: 23rpx;
}
.actions {
  display: flex;
  margin: 0 28rpx;
  padding: 16rpx 0;
  border-top: 1rpx solid var(--med-divider);
  justify-content: flex-end;
  gap: 12rpx;
}
.action {
  display: flex;
  min-height: 88rpx;
  min-height: 44px;
  margin: 0;
  padding: 0 24rpx;
  align-items: center;
  justify-content: center;
  line-height: 1.2;
  border-radius: 13rpx;
  font-size: 26rpx;
}
.reject {
  margin-right: auto;
  padding-left: 0;
  color: var(--med-danger);
  background: transparent;
}
.edit {
  color: var(--med-text-secondary);
  background: transparent;
  border: 1rpx solid var(--med-border);
}
.publish,
.stats {
  color: #fff;
  background: var(--med-brand);
}
.published-actions {
  align-items: center;
  justify-content: space-between;
}
.publish-time {
  color: var(--med-muted);
  font-size: 23rpx;
}
.load-more {
  min-height: 88rpx;
  margin-top: 24rpx;
  color: var(--med-brand);
  background: transparent;
  font-size: 24rpx;
}
@media screen and (max-width: 360px) {
  .tab,
  .small-button,
  .action {
    font-size: 12px;
  }

  .description {
    font-size: 14px;
  }

  .type,
  .target,
  .time,
  .case-meta,
  .publish-time {
    font-size: 12px;
  }

  .title {
    font-size: 16px;
  }
}
@media screen and (min-width: 600px) {
  .problem-list-page {
    padding: 20px 0 32px;
  }

  .problem-card {
    margin-bottom: 16px;
  }

  .problem-open {
    padding: 20px 24px 16px;
  }

  .toolbar {
    margin-bottom: 16px;
  }

  .tabs {
    margin-top: 12px;
  }

  .toolbar-buttons,
  .actions {
    gap: 12px;
  }

  .tab,
  .small-button,
  .action {
    min-height: 48px;
    padding: 12px 20px;
    border-radius: 8px;
    font-size: 14px;
  }

  .tab {
    border-radius: 0;
    border-bottom-width: 2px;
  }

  .count {
    margin-left: 6px;
    padding: 2px 7px;
    font-size: 12px;
  }

  .type {
    padding: 3px 8px;
    border-radius: 5px;
  }

  .type,
  .target,
  .time,
  .case-meta,
  .publish-time {
    font-size: 12px;
  }

  .title {
    font-size: 18px;
  }

  .title-row {
    margin-top: 12px;
    gap: 12px;
  }
  .detail-arrow {
    font-size: 24px;
  }

  .description {
    margin-top: 8px;
    font-size: 15px;
  }

  .case-meta {
    margin-top: 8px;
  }

  .actions {
    margin: 0 24px;
    padding: 12px 0;
  }

  .reset-data {
    font-size: 13px;
  }
}
</style>
