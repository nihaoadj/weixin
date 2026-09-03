<template>
  <view class="reference-section">
    <view class="section-heading">
      <text
        class="section-number"
        aria-hidden="true"
        >02</text
      >
      <text
        class="section-title"
        role="heading"
        aria-level="2"
        >AI 参考意见</text
      >
    </view>
    <view class="reference-meta">
      <text class="reference-score"
        >参考评分 <text class="score-value">{{ analysis.score }}</text> / 100</text
      >
      <text class="reference-note">仅供教学参考，最终评价由教师给出。</text>
    </view>
    <text
      class="summary"
      user-select
      >{{ analysis.summary || '暂无摘要，请依据对话原文独立批阅。' }}</text
    >
    <view
      v-if="analysis.strengths?.length"
      class="analysis-group"
    >
      <text class="group-label">已有表现</text>
      <text
        v-for="(strength, index) in analysis.strengths"
        :key="index"
        class="analysis-line"
        >{{ strength }}</text
      >
    </view>
    <view
      v-if="analysis.errors.length"
      class="analysis-group"
    >
      <text class="group-label needs-review">待核对与补充</text>
      <view
        v-for="(issue, index) in analysis.errors"
        :key="index"
        class="issue"
      >
        <text class="issue-content">{{ issue.content }}</text>
        <text class="suggestion">建议：{{ issue.suggestion }}</text>
      </view>
    </view>
    <text
      v-else
      class="no-issues"
      >AI 未标出明显结构性问题，仍需教师核对。</text
    >
    <view
      v-if="analysis.generalSuggestions?.length"
      class="analysis-group"
    >
      <text class="group-label">后续学习建议</text>
      <text
        v-for="(suggestion, index) in analysis.generalSuggestions"
        :key="index"
        class="analysis-line"
        >{{ suggestion }}</text
      >
    </view>
  </view>
</template>

<script setup lang="ts">
import type { ConversationAnalysis } from '@/types/domain'
defineProps<{ analysis: ConversationAnalysis }>()
</script>

<style scoped>
.reference-section {
  margin-top: 40rpx;
  padding-top: 32rpx;
  border-top: 2rpx solid var(--med-ink);
}
.section-heading {
  display: flex;
  align-items: baseline;
  gap: 16rpx;
}
.section-number {
  color: var(--med-muted);
  font-family: var(--med-font-utility);
  font-size: 24rpx;
}
.section-title {
  color: var(--med-ink);
  font-size: 36rpx;
  font-weight: 700;
}
.reference-meta {
  display: flex;
  margin-top: 20rpx;
  flex-direction: column;
  gap: 8rpx;
}
.reference-score,
.reference-note,
.no-issues {
  color: var(--med-muted);
  font-size: 24rpx;
  line-height: 1.6;
}
.score-value {
  color: var(--med-text);
  font-family: var(--med-font-utility);
  font-weight: 700;
}
.summary,
.analysis-line,
.issue-content,
.suggestion {
  display: block;
  color: var(--med-text);
  font-size: 28rpx;
  line-height: 1.8;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  user-select: text;
}
.summary {
  margin-top: 24rpx;
}
.analysis-group {
  margin-top: 28rpx;
}
.group-label {
  display: block;
  margin-bottom: 8rpx;
  color: var(--med-ink);
  font-size: 24rpx;
  font-weight: 700;
}
.needs-review {
  color: var(--med-safety);
}
.issue {
  margin-top: 16rpx;
  padding-left: 20rpx;
  border-left: 3rpx solid var(--med-safety-border);
}
.suggestion {
  margin-top: 4rpx;
  color: var(--med-text-secondary);
}
.analysis-line + .analysis-line {
  margin-top: 12rpx;
}
.no-issues {
  display: block;
  margin-top: 20rpx;
}
@media screen and (max-width: 360px) {
  .summary,
  .analysis-line,
  .issue-content,
  .suggestion {
    font-size: 14px;
  }
  .reference-score,
  .reference-note,
  .section-number,
  .no-issues,
  .group-label {
    font-size: 12px;
  }
}
@media screen and (min-width: 600px) {
  .reference-section {
    margin-top: 32px;
    padding-top: 24px;
    border-top-width: 1px;
  }
  .section-heading {
    gap: 12px;
  }
  .section-title {
    font-size: 20px;
  }
  .reference-meta {
    margin-top: 16px;
    gap: 4px;
  }
  .reference-score,
  .reference-note,
  .section-number,
  .no-issues,
  .group-label {
    font-size: 13px;
  }
  .summary,
  .analysis-line,
  .issue-content,
  .suggestion {
    font-size: 15px;
  }
  .summary,
  .analysis-group {
    margin-top: 20px;
  }
  .issue {
    margin-top: 12px;
    padding-left: 12px;
    border-left-width: 2px;
  }
  .suggestion {
    margin-top: 4px;
  }
}
</style>
