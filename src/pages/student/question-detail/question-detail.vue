<template>
  <view class="safe-page detail-page">
    <view
      v-if="question"
      class="question-card card"
    >
      <view class="meta"
        ><text class="type">{{ question.type }}</text
        ><text>{{ question.time }}</text></view
      >
      <text class="question-title">{{ question.title }}</text>
      <text
        v-if="question.description"
        class="description"
        >{{ question.description }}</text
      >
    </view>

    <scroll-view
      class="thread"
      scroll-y
      :scroll-into-view="lastMessageId"
    >
      <view
        v-for="(message, index) in messages"
        :id="`thread-${index}`"
        :key="message.id"
        class="message"
        :class="message.role"
      >
        <text class="bubble">{{ message.content }}</text>
      </view>
      <view
        v-if="isLoading"
        class="message assistant"
        ><text class="bubble">正在分析…</text></view
      >
      <view class="thread-spacer" />
    </scroll-view>

    <view class="answer-bar">
      <input
        v-model="answer"
        class="answer-input"
        placeholder="请输入你的回答…"
        confirm-type="send"
        :maxlength="2000"
        :disabled="isLoading"
        @confirm="submitAnswer"
      />
      <button
        class="send"
        :disabled="!answer.trim() || isLoading"
        @click="submitAnswer"
      >
        ➤
      </button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { requireRole } from '@/services/auth'
import { backOrHome } from '@/services/navigation'
import { requestMedicalAssistant } from '@/services/ai'
import { findStudentQuestionAsync, getQuestionThreadAsync, saveQuestionThreadAsync } from '@/services/repositoryAsync'
import type { ChatMessage, StudentQuestion } from '@/types/domain'
import { formatClock } from '@/utils/date'

const question = ref<StudentQuestion | null>(null)
const messages = ref<ChatMessage[]>([])
const answer = ref('')
const isLoading = ref(false)
const lastMessageId = ref('')

onLoad((options) => {
  if (!requireRole('student')) return
  const id = typeof options?.id === 'string' ? options.id : ''
  void loadQuestion(id)
})

async function loadQuestion(id: string) {
  question.value = (await findStudentQuestionAsync(id)) || null
  if (!question.value) {
    uni.showToast({ title: '问题不存在', icon: 'none' })
    backOrHome('student')
    return
  }
  messages.value = (await getQuestionThreadAsync(id))?.messages || []
  void scrollBottom()
}

function newMessage(role: ChatMessage['role'], content: string): ChatMessage {
  return { id: `qmsg_${Date.now()}_${messages.value.length}`, role, content, timestamp: formatClock() }
}

async function persist() {
  if (!question.value) return
  try {
    await saveQuestionThreadAsync({
      questionId: question.value.id,
      messages: messages.value,
      updatedAt: new Date().toISOString(),
    })
  } catch (error) {
    console.error('保存作答记录失败', error)
    uni.showToast({ title: error instanceof Error ? error.message : '保存作答失败', icon: 'none' })
  }
}

async function scrollBottom() {
  await nextTick()
  lastMessageId.value = messages.value.length ? `thread-${messages.value.length - 1}` : ''
}

async function submitAnswer() {
  const content = answer.value.trim()
  if (!content || !question.value || isLoading.value) return
  messages.value.push(newMessage('user', content))
  answer.value = ''
  isLoading.value = true
  await persist()
  await scrollBottom()
  try {
    const response = await requestMedicalAssistant({
      prompt: content,
      history: messages.value,
      question: question.value,
      mode: question.value.type,
    })
    messages.value.push(newMessage('assistant', response))
  } catch (error) {
    console.error('问题解析失败', error)
    messages.value.push(newMessage('assistant', '解析服务暂时不可用，请稍后重试。'))
  } finally {
    isLoading.value = false
    await persist()
    await scrollBottom()
  }
}
</script>

<style scoped>
.detail-page {
  display: flex;
  height: 100vh;
  overflow: hidden;
  padding: 24rpx 24rpx 0;
  box-sizing: border-box;
  flex-direction: column;
}
.question-card {
  max-height: 36vh;
  padding: 26rpx;
  overflow-y: auto;
  flex: 0 0 auto;
}
.meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #8795a8;
  font-size: 22rpx;
}
.type {
  padding: 6rpx 14rpx;
  color: #087f8c;
  background: #e6f7f5;
  border-radius: 99rpx;
}
.question-title {
  display: block;
  margin-top: 20rpx;
  font-size: 31rpx;
  font-weight: 700;
  line-height: 1.55;
}
.description {
  display: block;
  margin-top: 12rpx;
  color: #64748b;
  line-height: 1.55;
}
.thread {
  height: 0;
  min-height: 0;
  margin-top: 20rpx;
  flex: 1;
}
.message {
  display: flex;
  margin: 20rpx 0;
}
.message.user {
  justify-content: flex-end;
}
.bubble {
  display: block;
  max-width: 76%;
  padding: 20rpx 24rpx;
  background: #fff;
  border-radius: 8rpx 22rpx 22rpx 22rpx;
  line-height: 1.6;
  white-space: pre-wrap;
}
.user .bubble {
  color: #fff;
  background: #365c8d;
  border-radius: 22rpx 8rpx 22rpx 22rpx;
}
.thread-spacer {
  height: 40rpx;
}
.answer-bar {
  display: flex;
  margin: 0 -24rpx;
  padding: 18rpx 24rpx calc(18rpx + env(safe-area-inset-bottom));
  gap: 14rpx;
  background: #fff;
  border-top: 1rpx solid #dce8ef;
  flex: 0 0 auto;
}
.answer-input {
  height: 80rpx;
  padding: 0 24rpx;
  flex: 1;
  background: #f1f5f9;
  border-radius: 22rpx;
}
.send {
  width: 82rpx;
  height: 80rpx;
  padding: 0;
  line-height: 80rpx;
  color: #fff;
  background: #087f8c;
  border-radius: 22rpx;
}
.send[disabled] {
  opacity: 0.45;
}
</style>
