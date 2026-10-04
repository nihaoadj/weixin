<template>
  <view
    v-if="selected"
    class="detail"
  >
    <MedState
      v-if="error"
      variant="error"
      icon="retry"
      size="compact"
      title="诊断详情加载失败"
      :description="error"
      action-label="重新加载"
      @action="$emit('retry')"
    />
    <MedState
      v-else-if="loading"
      variant="loading"
      icon="history"
      size="compact"
      title="正在加载诊断详情"
      description="正在读取学生证据与 AI 诊断建议。"
    />
    <template v-else-if="detail">
      <view class="object">
        <text
          class="detail-heading object-title"
          role="heading"
          aria-level="1"
          >{{ detail.diagnostic.studentName }}</text
        >
        <view class="object-meta-row">
          <text class="object-meta">{{ objectMeta }}</text>
          <TeacherStatusTag
            label="研讨分析 · 只读"
            tone="neutral"
          />
        </view>
      </view>

      <TeacherModuleSection
        title="研讨证据摘要"
        description="固定诊断轨迹与学生当前阶段的证据摘要。"
      >
        <view class="evidence-rows">
          <text class="evidence-trajectory">研讨完成 → 固定诊断 → 学习路线与最终测试</text>
          <text class="evidence-summary">{{ detail.diagnostic.phaseEvidenceSummary || '未提供阶段证据摘要' }}</text>
        </view>
      </TeacherModuleSection>

      <TeacherModuleSection
        title="知识薄弱点"
        compact
      >
        <view
          v-if="!detail.diagnostic.knowledgeGaps.length"
          class="finding-empty"
        >
          <text class="muted">未识别到知识薄弱点，不代表学生已掌握相关内容。</text>
        </view>
        <view
          v-else
          class="finding-rows"
        >
          <view
            v-for="(gap, index) in detail.diagnostic.knowledgeGaps"
            :key="gap.id"
            class="finding-row"
          >
            <text class="finding-index">{{ padIndex(index) }}</text>
            <text class="finding-summary">{{ gap.summary }}</text>
          </view>
        </view>
      </TeacherModuleSection>

      <TeacherModuleSection
        title="推理问题"
        compact
      >
        <view
          v-if="!detail.diagnostic.reasoningIssues.length"
          class="finding-empty"
        >
          <text class="muted">未识别到推理问题，不代表学生已掌握相关内容。</text>
        </view>
        <view
          v-else
          class="finding-rows"
        >
          <view
            v-for="(issue, index) in detail.diagnostic.reasoningIssues"
            :key="issue.id"
            class="finding-row"
          >
            <text class="finding-index">{{ padIndex(index) }}</text>
            <view class="finding-copy">
              <text class="finding-summary">{{ issue.summary }}</text>
              <text
                v-if="issue.improvement"
                class="finding-improvement"
                >建议：{{ issue.improvement }}</text
              >
            </view>
          </view>
        </view>
      </TeacherModuleSection>

      <TeacherModuleSection
        v-if="detail.feedbacks.length"
        title="历史教师反馈"
      >
        <view class="feedback-rows">
          <view
            v-for="feedback in detail.feedbacks"
            :key="feedback.id"
            class="feedback-row"
          >
            <text class="feedback-label">教师反馈</text>
            <text class="feedback-body">{{ feedback.body }}</text>
            <text
              v-if="feedback.createdAt"
              class="feedback-time"
              >{{ formatDateTime(feedback.createdAt) }}</text
            >
          </view>
        </view>
      </TeacherModuleSection>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import TeacherModuleSection from '@/components/teacher/TeacherModuleSection.vue'
import TeacherStatusTag from '@/components/teacher/TeacherStatusTag.vue'
import { displayTopicCode } from '@/features/pbl/presentation/teacherPresentation'
import MedState from '@/components/ui/MedState.vue'
import type { PblDiagnostic, PblTeacherFeedback, PblWorkItem } from '@/features/pbl/public'

type WorkItemDetail = {
  workItem?: PblWorkItem
  diagnostic: PblDiagnostic
  feedbacks: PblTeacherFeedback[]
}

const props = withDefaults(
  defineProps<{
    selected?: PblWorkItem
    detail?: WorkItemDetail
    loading?: boolean
    error?: string
  }>(),
  { loading: false, error: '' },
)
defineEmits<{ retry: [] }>()

const objectMeta = computed(() => {
  if (!props.selected) return ''
  const topic = props.detail?.diagnostic.topicCode || props.selected.topic
  return [props.selected.class.name, displayTopicCode(topic || '')].filter(Boolean).join(' · ')
})
function padIndex(index: number) {
  return String(index + 1).padStart(2, '0')
}
function formatDateTime(value: string) {
  return new Date(value).toLocaleString('zh-CN')
}
</script>

<style scoped>
.detail {
  display: flex;
  min-width: 0;
  padding: 24rpx 0;
  flex-direction: column;
  gap: 36rpx;
}
.object {
  display: flex;
  padding: 0 4rpx;
  flex-direction: column;
  gap: 8rpx;
}
.object-title {
  color: var(--med-ink);
  font-size: 34rpx;
  font-weight: 750;
  line-height: 1.35;
}
.object-meta-row {
  display: flex;
  align-items: center;
  gap: 16rpx;
  flex-wrap: wrap;
}
.object-meta {
  color: var(--med-muted);
  font-size: 24rpx;
  line-height: 1.5;
}
.evidence-rows {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
}
.evidence-trajectory {
  color: var(--med-text);
  font-size: 28rpx;
  line-height: 1.6;
}
.evidence-summary {
  color: var(--med-text);
  font-size: 28rpx;
  line-height: 1.6;
  word-break: break-word;
}
.finding-rows {
  display: flex;
  flex-direction: column;
}
.finding-row {
  display: flex;
  padding: 20rpx 0;
  gap: 16rpx;
}
.finding-row + .finding-row {
  border-top: 1rpx solid var(--med-divider);
}
.finding-empty {
  padding: 6rpx 0;
}
.finding-index {
  flex: none;
  color: var(--med-clinical);
  font-family: var(--med-font-utility);
  font-size: 24rpx;
  font-weight: 700;
  line-height: 1.7;
}
.finding-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 6rpx;
}
.finding-summary {
  color: var(--med-text);
  font-size: 28rpx;
  line-height: 1.6;
  word-break: break-word;
}
.finding-improvement {
  color: var(--med-muted);
  font-size: 24rpx;
  line-height: 1.6;
  word-break: break-word;
}
.feedback-rows {
  display: flex;
  flex-direction: column;
}
.feedback-row {
  display: flex;
  padding: 14rpx 0;
  flex-direction: column;
  gap: 4rpx;
}
.feedback-row + .feedback-row {
  border-top: 1rpx solid var(--med-divider);
}
.feedback-label {
  color: var(--med-muted);
  font-size: 24rpx;
  font-weight: 600;
}
.feedback-body {
  color: var(--med-text);
  font-size: 28rpx;
  line-height: 1.6;
  word-break: break-word;
}
.feedback-time {
  color: var(--med-muted);
  font-size: 24rpx;
}
.muted {
  color: var(--med-muted);
  font-size: 28rpx;
  line-height: 1.6;
}
@media screen and (max-width: 360px) {
  .object-meta,
  .finding-index,
  .finding-improvement,
  .feedback-label,
  .feedback-time {
    font-size: 12px;
  }
}
@media screen and (min-width: 600px) {
  .object-title {
    font-size: 18px;
  }
  .object-meta,
  .finding-index,
  .finding-improvement,
  .feedback-label,
  .feedback-time {
    font-size: 12px;
  }
  .evidence-trajectory,
  .evidence-summary,
  .finding-summary,
  .feedback-body,
  .muted {
    font-size: 14px;
  }
}
</style>
