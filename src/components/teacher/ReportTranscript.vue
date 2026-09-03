<template>
  <view class="transcript">
    <view class="section-heading">
      <text
        class="section-number"
        aria-hidden="true"
        >01</text
      >
      <text
        class="section-title"
        role="heading"
        aria-level="2"
        >对话原文</text
      >
      <text class="message-count">{{ messages.length }} 条</text>
    </view>
    <view
      v-if="messages.length === 0"
      class="empty-copy"
      role="status"
      >这份报告未包含对话原文。</view
    >
    <view
      v-for="(message, index) in messages"
      :key="message.id"
      class="transcript-entry"
    >
      <text
        class="entry-number"
        aria-hidden="true"
        >{{ String(index + 1).padStart(2, '0') }}</text
      >
      <view class="entry-copy">
        <view class="entry-meta">
          <text class="speaker">{{ message.role === 'user' ? '学生' : 'AI 教学助手' }}</text>
          <text class="entry-time">{{ formatDateTime(message.timestamp) }}</text>
        </view>
        <text
          class="entry-content"
          :class="{ 'assistant-content': message.role === 'assistant' }"
          user-select
          >{{ message.content }}</text
        >
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import type { ChatMessage } from '@/types/domain'
import { formatDateTime } from '@/utils/date'
defineProps<{ messages: ChatMessage[] }>()
</script>

<style scoped>
.section-heading,
.entry-meta {
  display: flex;
  align-items: baseline;
  gap: 16rpx;
}
.section-heading {
  padding-bottom: 24rpx;
  border-bottom: 1rpx solid var(--med-border);
}
.section-number,
.entry-number {
  color: var(--med-muted);
  font-family: var(--med-font-utility);
  font-size: 24rpx;
}
.section-title {
  color: var(--med-ink);
  font-size: 36rpx;
  font-weight: 700;
}
.message-count {
  margin-left: auto;
  color: var(--med-muted);
  font-size: 24rpx;
}
.transcript-entry {
  display: flex;
  padding: 28rpx 0;
  gap: 20rpx;
  border-bottom: 1rpx solid var(--med-divider);
}
.transcript-entry:last-child {
  border-bottom: 0;
}
.entry-number {
  width: 32rpx;
  padding-top: 4rpx;
  flex: none;
}
.entry-copy {
  min-width: 0;
  flex: 1;
}
.entry-meta {
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 8rpx 16rpx;
}
.speaker {
  color: var(--med-ink);
  font-size: 26rpx;
  font-weight: 700;
}
.entry-time {
  color: var(--med-muted);
  font-size: 22rpx;
  font-variant-numeric: tabular-nums;
}
.entry-content,
.empty-copy {
  display: block;
  margin-top: 12rpx;
  color: var(--med-text);
  font-size: 30rpx;
  line-height: 1.8;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  user-select: text;
}
.empty-copy {
  color: var(--med-muted);
}
.assistant-content {
  color: var(--med-text-secondary);
}
@media screen and (max-width: 360px) {
  .entry-content,
  .empty-copy {
    font-size: 15px;
  }
  .speaker {
    font-size: 13px;
  }
  .entry-time,
  .section-number,
  .entry-number,
  .message-count {
    font-size: 12px;
  }
}
@media screen and (min-width: 600px) {
  .section-heading {
    padding-bottom: 16px;
    gap: 12px;
  }
  .section-title {
    font-size: 20px;
  }
  .section-number,
  .entry-number,
  .message-count,
  .entry-time {
    font-size: 12px;
  }
  .transcript-entry {
    padding: 20px 0;
    gap: 16px;
  }
  .entry-number {
    width: 20px;
    padding-top: 4px;
  }
  .entry-meta {
    gap: 4px 12px;
  }
  .speaker {
    font-size: 14px;
  }
  .entry-content,
  .empty-copy {
    margin-top: 8px;
    font-size: 16px;
  }
}
</style>
