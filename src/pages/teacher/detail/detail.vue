<template>
  <view class="safe-page detail-page page-enter">
    <MedDetailSkeleton
      v-if="isLoading"
      label="正在加载报告…"
    />
    <MedState
      v-else-if="loadError"
      variant="error"
      icon="retry"
      title="报告加载失败"
      :description="loadError"
      action-label="重新加载"
      secondary-action-label="返回工作台"
      @action="loadReport(reportKey)"
      @secondary-action="back"
    />
    <MedState
      v-else-if="unavailableMessage"
      icon="report"
      title="报告暂不可批阅"
      :description="unavailableMessage"
      action-label="返回工作台"
      @action="back"
    />
    <MedState
      v-else-if="!report"
      icon="report"
      title="报告不存在"
      description="报告不存在或尚未提交给教师。"
      action-label="返回工作台"
      @action="back"
    />
    <template v-if="report && !isLoading && !loadError">
      <view class="document-header">
        <view class="document-topline">
          <text class="document-kicker">学生学习报告</text>
          <text
            class="document-status"
            :class="{ reviewed: report.status === '已批阅' }"
            >{{ report.status }}</text
          >
        </view>
        <text
          class="document-title"
          role="heading"
          aria-level="1"
          >{{ report.studentName || '学生' }}的推理记录</text
        >
        <text class="document-date">提交于 {{ formatDateTime(report.createdAt) }}</text>
      </view>
      <view class="document-layout">
        <view class="reading-column">
          <ReportTranscript :messages="report.messages" />
          <ReportReference :analysis="report.analysis" />
        </view>
        <view class="feedback-column">
          <view class="review-topics">
            <text class="review-topics-title"
              >建议复习知识点 <text class="review-topics-hint">选填，最多 3 个</text></text
            >
            <text class="review-topics-copy">学生会在自己的复习队列中看到这些主题；不会附带本次报告的完整内容。</text>
            <view class="topic-options">
              <button
                v-for="point in knowledgePoints"
                :key="point.code"
                class="topic-option"
                :class="{ selected: reviewTopicCodes.includes(point.code) }"
                :disabled="submitting || (!reviewTopicCodes.includes(point.code) && reviewTopicCodes.length >= 3)"
                @click="toggleReviewTopic(point.code)"
              >
                {{ point.systemLabel }} · {{ point.title }}
              </button>
            </view>
          </view>
          <ReportFeedback
            v-model:feedback="teacherFeedback"
            :score="teacherScore"
            :score-error="scoreError"
            :submit-error="submitError"
            :submitting="submitting"
            :reviewed="report.status === '已批阅'"
            @update:score="updateScore"
            @submit="submitFeedback"
          />
        </view>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import MedState from '@/components/ui/MedState.vue'
import MedDetailSkeleton from '@/components/ui/MedDetailSkeleton.vue'
import ReportTranscript from '@/components/teacher/ReportTranscript.vue'
import ReportReference from '@/components/teacher/ReportReference.vue'
import ReportFeedback from '@/components/teacher/ReportFeedback.vue'
import { onBackPress, onLoad } from '@dcloudio/uni-app'
import { requireRole } from '@/features/identity/public'
import { backOrRoute, handleBackPress, ROUTES } from '@/platform/navigation'
import { findReportAsync, reviewReportAsync } from '@/features/reports/public'
import { getKnowledgeCatalog } from '@/features/learning/public'
import type { Report } from '@/types/domain'
import type { KnowledgePoint } from '@/types/knowledge'
import { formatDateTime } from '@/utils/date'

const report = ref<Report | null>(null)
const isLoading = ref(false)
const loadError = ref('')
const unavailableMessage = ref('')
const submitting = ref(false)
let reportKey = ''
const teacherScore = ref('')
const teacherFeedback = ref('')
const scoreError = ref('')
const submitError = ref('')
const knowledgePoints = ref<KnowledgePoint[]>([])
const reviewTopicCodes = ref<string[]>([])

function updateScore(value: string) {
  teacherScore.value = value
  scoreError.value = ''
}

function toggleReviewTopic(code: string) {
  if (submitting.value) return
  if (reviewTopicCodes.value.includes(code)) {
    reviewTopicCodes.value = reviewTopicCodes.value.filter((item) => item !== code)
    return
  }
  if (reviewTopicCodes.value.length < 3) reviewTopicCodes.value = [...reviewTopicCodes.value, code]
}

function back() {
  backOrRoute(ROUTES.teacherWorkspace, { tab: 'reports' })
}

onLoad((options) => {
  if (!requireRole('teacher')) return
  const id = typeof options?.reportId === 'string' ? options.reportId : ''
  void loadReport(id)
})
onBackPress(({ from }) => handleBackPress(from, ROUTES.teacherWorkspace, { tab: 'reports' }))

async function loadReport(id: string) {
  if (isLoading.value) return
  reportKey = id
  isLoading.value = true
  loadError.value = ''
  unavailableMessage.value = ''
  try {
    const [loadedReport, catalog] = await Promise.all([findReportAsync(id), getKnowledgeCatalog()])
    report.value = loadedReport || null
    knowledgePoints.value = catalog
    if (!report.value) {
      unavailableMessage.value = '报告不存在、已被移除，或当前身份无权查看。'
      return
    }
    if (report.value.status === '草稿') {
      report.value = null
      unavailableMessage.value = '该报告尚未提交给教师，暂时不能批阅。'
      return
    }
    teacherScore.value = report.value.teacherScore === undefined ? '' : String(report.value.teacherScore)
    teacherFeedback.value = report.value.teacherFeedback || ''
    reviewTopicCodes.value = report.value.reviewTopicCodes || []
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '请稍后重试'
  } finally {
    isLoading.value = false
  }
}

async function submitFeedback() {
  if (submitting.value) return
  scoreError.value = ''
  submitError.value = ''
  if (!report.value || teacherScore.value.trim() === '') {
    scoreError.value = '请填写 0–100 分之间的教师评分。'
    return
  }
  const score = Number(teacherScore.value)
  if (!Number.isFinite(score) || score < 0 || score > 100) {
    scoreError.value = '评分必须在 0–100 分之间。'
    return
  }
  submitting.value = true
  try {
    const reviewed = await reviewReportAsync(
      report.value.id || report.value.conversationId,
      score,
      teacherFeedback.value.trim(),
      reviewTopicCodes.value,
    )
    if (!reviewed) {
      submitError.value = '报告状态已变化，请返回列表刷新后重试。当前输入仍保留在此页。'
      return
    }
    report.value = reviewed
    uni.showToast({ title: '批阅已保存', icon: 'success' })
    back()
  } catch (error) {
    submitError.value = error instanceof Error ? error.message : '保存失败，请重试。当前输入未丢失。'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.detail-page {
  padding: 40rpx 32rpx calc(140px + env(safe-area-inset-bottom));
  background: var(--med-surface);
  box-shadow: none;
}
.document-header {
  padding-bottom: 32rpx;
  border-bottom: 2rpx solid var(--med-ink);
}
.document-topline {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16rpx;
}
.document-kicker {
  color: var(--med-muted);
  font-size: 24rpx;
  letter-spacing: 2rpx;
}
.document-status {
  color: var(--med-safety);
  font-size: 24rpx;
  font-weight: 600;
}
.document-status.reviewed {
  color: var(--med-clinical);
}
.document-title {
  display: block;
  margin-top: 20rpx;
  color: var(--med-ink);
  font-size: 48rpx;
  font-weight: 800;
  line-height: 1.4;
  overflow-wrap: anywhere;
}
.document-date {
  display: block;
  margin-top: 12rpx;
  color: var(--med-muted);
  font-size: 24rpx;
  font-variant-numeric: tabular-nums;
}
.document-layout {
  padding-top: 32rpx;
}
.reading-column {
  min-width: 0;
}
.feedback-column {
  margin: 48rpx -32rpx 0;
  padding: 32rpx;
  background: var(--med-paper);
  border-top: 4rpx solid var(--med-clinical);
}
.review-topics {
  margin-bottom: 32rpx;
  padding-bottom: 28rpx;
  border-bottom: 1px solid var(--med-border);
}
.review-topics-title,
.review-topics-copy {
  display: block;
}
.review-topics-title {
  color: var(--med-text);
  font-size: 28rpx;
  font-weight: 700;
}
.review-topics-hint,
.review-topics-copy {
  color: var(--med-muted);
  font-size: 22rpx;
  font-weight: 400;
}
.review-topics-copy {
  margin-top: 10rpx;
  line-height: 1.6;
}
.topic-options {
  display: flex;
  margin-top: 20rpx;
  flex-wrap: wrap;
  gap: 12rpx;
}
.topic-option {
  min-height: 60rpx;
  margin: 0;
  padding: 10rpx 16rpx;
  color: var(--med-muted);
  background: transparent;
  border: 1px solid var(--med-border);
  border-radius: 4rpx;
  font-size: 22rpx;
  line-height: 1.4;
}
.topic-option.selected {
  color: var(--med-clinical);
  background: var(--med-clinical-soft);
  border-color: var(--med-clinical);
}
@media screen and (max-width: 360px) {
  .document-kicker,
  .document-status,
  .document-date {
    font-size: 12px;
  }
}
@media screen and (min-width: 600px) {
  .detail-page {
    padding: 32px 40px calc(140px + env(safe-area-inset-bottom));
  }
  .document-header {
    padding-bottom: 24px;
    border-bottom-width: 1px;
  }
  .document-kicker,
  .document-status,
  .document-date {
    font-size: 14px;
  }
  .document-title {
    margin-top: 16px;
    font-size: 36px;
  }
  .document-date {
    margin-top: 8px;
  }
  .document-layout {
    padding-top: 32px;
  }
  .review-topics {
    margin-bottom: 20px;
    padding-bottom: 20px;
  }
  .review-topics-title {
    font-size: 15px;
  }
  .review-topics-hint,
  .review-topics-copy,
  .topic-option {
    font-size: 13px;
  }
  .topic-options {
    margin-top: 12px;
    gap: 8px;
  }
  .topic-option {
    min-height: 34px;
    padding: 6px 10px;
  }
  .feedback-column {
    margin: 40px -24px 0;
    padding: 24px;
    border-top-width: 2px;
  }
}
@media screen and (min-width: 1000px) {
  .document-layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 304px;
    align-items: start;
    gap: 32px;
  }
  .feedback-column {
    position: sticky;
    top: 76px;
    margin: 0;
    padding: 24px;
    border-top: 2px solid var(--med-clinical);
    border-left: 0;
  }
}
</style>
