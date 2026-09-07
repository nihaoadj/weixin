<template>
  <view class="safe-page legacy-page">
    <text
      class="sr-only"
      role="heading"
      aria-level="1"
      >历史答疑</text
    >
    <MedState
      v-if="loading"
      variant="loading"
      icon="retry"
      title="正在加载历史答疑"
      description="旧答疑仅供回看，不会进入新的阶段证据链。"
    />
    <MedState
      v-else-if="error"
      variant="error"
      icon="retry"
      title="历史答疑加载失败"
      :description="error"
      action-label="返回研讨"
      @action="openDialogue"
    />
    <template v-else-if="conversation">
      <view class="notice">
        <text class="notice-title">旧答疑只读保留</text>
        <text>这段对话不会自动转换为诊断或学习计划。你可以带着已确认的知识点和起始问题开始一次新研讨。</text>
      </view>
      <scroll-view
        class="history-scroll"
        scroll-y
      >
        <view
          v-for="message in conversation.messages"
          :key="message.id"
          class="message-row"
          :class="{ own: message.role === 'user' }"
        >
          <view class="avatar">{{ message.role === 'user' ? '我' : 'AI' }}</view>
          <view class="message-content">
            <text class="bubble">{{ message.content }}</text>
            <button
              v-if="message.role === 'assistant'"
              class="copy-action"
              @click="copy(message.content)"
            >
              复制
            </button>
          </view>
        </view>
      </scroll-view>
      <view class="action-bar">
        <button
          class="primary-action"
          @click="openDialogue"
        >
          以此主题开始新研讨
        </button>
        <button
          class="secondary-action"
          @click="goDetail(ROUTES.studentHistory)"
        >
          查看全部历史
        </button>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { onLoad } from '@dcloudio/uni-app'
import { ref } from 'vue'
import MedState from '@/components/ui/MedState.vue'
import { requireRole } from '@/features/identity/public'
import { findConversationAsync } from '@/features/qa/public'
import type { Conversation } from '@/types/domain'
import { goDetail, goReplace, relaunchTo, ROUTES } from '@/platform/navigation'

const loading = ref(true),
  error = ref(''),
  conversation = ref<Conversation>()
const requestedTopic = ref(''),
  requestedStarter = ref('')

onLoad(async (options) => {
  if (!requireRole('student')) return
  const conversationId = typeof options?.conversationId === 'string' ? options.conversationId : ''
  requestedTopic.value = typeof options?.topicCode === 'string' ? options.topicCode : ''
  requestedStarter.value = typeof options?.starter === 'string' ? options.starter : ''
  if (!conversationId) {
    relaunchTo(ROUTES.studentPbl, { topicCode: requestedTopic.value, starter: requestedStarter.value })
    return
  }
  try {
    conversation.value = await findConversationAsync(conversationId)
    if (!conversation.value) error.value = '没有找到这条历史答疑。'
  } catch {
    error.value = '无法读取历史答疑，请稍后重试。'
  } finally {
    loading.value = false
  }
})

function openDialogue() {
  const lastQuestion = [...(conversation.value?.messages ?? [])].reverse().find((item) => item.role === 'user')?.content
  const topicCode = conversation.value?.topicCodes?.[0] || requestedTopic.value
  goReplace(ROUTES.studentPbl, { topicCode, starter: lastQuestion || requestedStarter.value })
}
function copy(content: string) {
  uni.setClipboardData({ data: content, success: () => uni.showToast({ title: '已复制', icon: 'success' }) })
}
</script>

<style scoped>
.legacy-page {
  display: flex;
  height: calc(100vh - var(--window-top, 0px));
  min-height: 0;
  flex-direction: column;
  background: var(--med-page);
}
.notice {
  display: flex;
  margin: 20rpx 24rpx 0;
  padding: 22rpx;
  flex-direction: column;
  gap: 8rpx;
  color: var(--med-text-secondary);
  background: var(--med-wash);
  border: 1rpx solid var(--med-border);
  border-radius: var(--med-radius-md);
  font-size: 24rpx;
  line-height: 1.6;
}
.notice-title {
  color: var(--med-clinical);
  font-size: 27rpx;
  font-weight: 750;
}
.history-scroll {
  height: 0;
  padding: 20rpx 24rpx;
  box-sizing: border-box;
  flex: 1;
}
.message-row {
  display: flex;
  max-width: 800px;
  margin: 22rpx auto;
  align-items: flex-start;
}
.message-row.own {
  flex-direction: row-reverse;
}
.avatar {
  display: flex;
  width: 58rpx;
  height: 58rpx;
  flex: 0 0 58rpx;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: var(--med-clinical);
  border-radius: var(--med-radius-sm);
  font-size: 21rpx;
  font-weight: 700;
}
.own .avatar {
  background: var(--med-ink);
}
.message-content {
  display: flex;
  max-width: 78%;
  margin: 0 14rpx;
  flex-direction: column;
  align-items: flex-start;
  gap: 7rpx;
}
.own .message-content {
  align-items: flex-end;
}
.bubble {
  padding: 20rpx 22rpx;
  color: var(--med-text);
  background: var(--med-surface);
  border: 1rpx solid var(--med-border);
  border-radius: var(--med-radius-md);
  font-size: 27rpx;
  line-height: 1.65;
  white-space: pre-wrap;
}
.own .bubble {
  color: #fff;
  background: var(--med-ink);
  border-color: var(--med-ink);
}
.copy-action {
  width: auto;
  min-height: 52rpx;
  margin: 0;
  padding: 0 14rpx;
  color: var(--med-clinical);
  background: transparent;
  font-size: 21rpx;
}
.action-bar {
  display: flex;
  padding: 18rpx 24rpx calc(22rpx + env(safe-area-inset-bottom));
  gap: 14rpx;
  background: var(--med-surface);
  border-top: 1rpx solid var(--med-border);
}
.primary-action,
.secondary-action {
  min-height: 82rpx;
  margin: 0;
  padding: 0 22rpx;
  border-radius: var(--med-radius-sm);
  font-size: 25rpx;
}
.primary-action {
  flex: 1;
  color: #fff;
  background: var(--med-clinical);
}
.secondary-action {
  width: auto;
  color: var(--med-clinical);
  background: var(--med-wash);
}
</style>
