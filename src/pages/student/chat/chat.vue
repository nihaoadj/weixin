<template>
  <view class="safe-page chat-page">
    <view class="top-actions">
      <view class="brand">
        <view class="brand-mark"><MedIcon name="brand" /></view>
        <view class="brand-copy"
          ><text>医学学习助手</text><text class="brand-subtitle">CLINICAL LEARNING COPILOT</text></view
        >
      </view>
      <view class="top-actions-right">
        <text
          class="history-link"
          @click="goToHistory"
          >历史</text
        >
        <text
          class="logout"
          @click="logout"
          >退出</text
        >
      </view>
    </view>

    <scroll-view
      class="chat-scroll"
      scroll-y
      :scroll-into-view="lastMessageId"
    >
      <view
        v-if="messages.length === 0"
        class="welcome card"
      >
        <view class="welcome-mark"
          ><MedIcon
            name="chat"
            size="lg"
        /></view>
        <text class="eyebrow-label">GUIDED CLINICAL REASONING</text>
        <text class="welcome-title">今天想训练哪项临床思维？</text>
        <SafetyBanner class="welcome-safety" />
        <view class="quick-list">
          <view
            v-for="question in quickQuestions"
            :key="question"
            class="quick-item"
            @click="quickAsk(question)"
            >{{ question }}</view
          >
        </view>
      </view>

      <view
        v-for="(message, index) in messages"
        :id="`message-${index}`"
        :key="message.id"
        class="message-row"
        :class="message.role"
      >
        <view class="avatar">{{ message.role === 'user' ? '我' : 'AI' }}</view>
        <view class="message-content">
          <text class="bubble">{{ message.content }}</text>
          <view
            v-if="message.role === 'assistant'"
            class="message-tools"
          >
            <view @click="copyMessage(message.content)"
              ><MedIcon
                name="copy"
                size="sm"
              /><text>复制</text></view
            >
          </view>
          <text class="time">{{ message.timestamp }}</text>
        </view>
      </view>
      <view
        v-if="isLoading"
        class="message-row assistant"
      >
        <view class="avatar">AI</view>
        <view class="bubble typing"><text>●</text><text>●</text><text>●</text></view>
      </view>
      <view class="scroll-spacer" />
    </scroll-view>

    <view class="composer">
      <view class="feature-row">
        <button
          class="report-button"
          :disabled="messages.length === 0 || isLoading"
          @click="endConversation"
        >
          <MedIcon
            name="report"
            size="sm"
          />
          生成学习报告
        </button>
        <button
          v-if="lastFailedPrompt"
          class="retry-button"
          :disabled="isLoading"
          @click="retryLastMessage"
        >
          <MedIcon
            name="retry"
            size="sm"
          />重试
        </button>
      </view>
      <view class="input-row">
        <input
          v-model="inputValue"
          class="message-input"
          confirm-type="send"
          placeholder="请输入医学学习问题…"
          :maxlength="2000"
          :disabled="isLoading"
          @confirm="sendMessage"
        />
        <button
          class="send-button"
          :disabled="!inputValue.trim() || isLoading"
          @click="sendMessage"
        >
          <MedIcon name="send" />
        </button>
      </view>
      <StudentNav active="chat" />
    </view>
  </view>
</template>

<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import MedIcon from '@/components/ui/MedIcon.vue'
import SafetyBanner from '@/components/ui/SafetyBanner.vue'
import StudentNav from '@/components/ui/StudentNav.vue'
import { requireRole, logout } from '@/services/auth'
import { goDetail, goPrimary, ROUTES } from '@/services/navigation'
import { requestMedicalAssistant } from '@/services/ai'
import {
  findConversationAsync,
  findReportAsync,
  saveDraftReportAsync,
  upsertConversationAsync,
} from '@/services/repositoryAsync'
import type { ChatMessage } from '@/types/domain'
import { formatClock } from '@/utils/date'
import { analyzeConversation } from '@/utils/report'

const quickQuestions = ['给我一个医学案例让我诊断。', '肺炎的典型症状有哪些？', '高血压的诊断标准是什么？']
const messages = ref<ChatMessage[]>([])
const inputValue = ref('')
const conversationId = ref('')
const lastMessageId = ref('')
const isLoading = ref(false)
const lastFailedPrompt = ref('')

onLoad((options) => {
  if (!requireRole('student')) return
  const requestedId = typeof options?.conversationId === 'string' ? options.conversationId : ''
  void loadConversation(requestedId)
})

async function loadConversation(requestedId: string) {
  const conversation = requestedId ? await findConversationAsync(requestedId) : undefined
  conversationId.value = conversation?.conversationId || `conv_${Date.now()}`
  messages.value = conversation?.messages || []
  await scrollToBottom()
}

function quickAsk(question: string) {
  inputValue.value = question
  void sendMessage()
}

function goToHistory() {
  goPrimary(ROUTES.studentHistory)
}

function createMessage(role: ChatMessage['role'], content: string): ChatMessage {
  return { id: `msg_${Date.now()}_${messages.value.length}`, role, content, timestamp: formatClock() }
}

async function persistConversation(): Promise<boolean> {
  try {
    const existing = await findConversationAsync(conversationId.value)
    const now = new Date().toISOString()
    await upsertConversationAsync({
      conversationId: conversationId.value,
      messages: messages.value,
      createdAt: existing?.createdAt || now,
      updatedAt: now,
    })
    return true
  } catch (error) {
    console.error('保存对话失败', error)
    uni.showToast({ title: error instanceof Error ? error.message : '保存对话失败', icon: 'none' })
    return false
  }
}

async function scrollToBottom() {
  await nextTick()
  lastMessageId.value = messages.value.length ? `message-${messages.value.length - 1}` : ''
}

async function sendMessage() {
  const prompt = inputValue.value.trim()
  if (!prompt || isLoading.value) return
  messages.value.push(createMessage('user', prompt))
  inputValue.value = ''
  isLoading.value = true
  await persistConversation()
  await scrollToBottom()

  try {
    const content = await requestMedicalAssistant({ prompt, history: messages.value, mode: '自由问答' })
    messages.value.push(createMessage('assistant', content))
    lastFailedPrompt.value = ''
  } catch (error) {
    console.error('医学问答服务失败', error)
    lastFailedPrompt.value = prompt
    messages.value.push(
      createMessage('assistant', '抱歉，问答服务暂时不可用。请稍后重试，紧急健康问题请立即联系专业医疗人员。'),
    )
  } finally {
    isLoading.value = false
    await persistConversation()
    await scrollToBottom()
  }
}

function retryLastMessage() {
  if (!lastFailedPrompt.value || isLoading.value) return
  inputValue.value = lastFailedPrompt.value
  void sendMessage()
}

function copyMessage(content: string) {
  uni.setClipboardData({ data: content, success: () => uni.showToast({ title: '已复制', icon: 'success' }) })
}

async function endConversation() {
  if (!messages.value.length || isLoading.value) return
  const existingReport = await findReportAsync(conversationId.value)
  if (existingReport && existingReport.status !== '草稿') {
    uni.showModal({
      title: '报告已提交',
      content: '已提交或已批阅的报告不能被覆盖。你可以查看原报告，或返回后开启新对话。',
      confirmText: '查看报告',
      success: ({ confirm }) => {
        if (confirm) goDetail('/pages/report/report', { conversationId: conversationId.value })
      },
    })
    return
  }
  uni.showLoading({ title: '正在生成报告…' })
  try {
    await persistConversation()
    await saveDraftReportAsync({
      conversationId: conversationId.value,
      messages: messages.value,
      analysis: analyzeConversation(messages.value),
      createdAt: new Date().toISOString(),
    })
    goDetail('/pages/report/report', { conversationId: conversationId.value })
  } catch (error) {
    console.error('生成报告失败', error)
    uni.showToast({ title: error instanceof Error ? error.message : '生成报告失败', icon: 'none' })
  } finally {
    uni.hideLoading()
  }
}
</script>

<style scoped>
.chat-page {
  height: 100vh;
  overflow: hidden;
  background: radial-gradient(circle at 90% 0, rgba(53, 183, 168, 0.12), transparent 34%), #f4f8fa;
}
.top-actions {
  display: flex;
  height: 112rpx;
  padding: 0 30rpx;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.96);
  border-bottom: 1rpx solid #dbe7eb;
}
.brand {
  display: flex;
  align-items: center;
  font-size: 30rpx;
  font-weight: 700;
}
.brand-mark {
  display: flex;
  width: 64rpx;
  height: 64rpx;
  margin-right: 14rpx;
  align-items: center;
  justify-content: center;
  background: #edf8f6;
  border-radius: 18rpx;
}
.brand-copy {
  display: flex;
  flex-direction: column;
}
.brand-subtitle {
  margin-top: 2rpx;
  color: #78909a;
  font-size: 15rpx;
  font-weight: 600;
  letter-spacing: 1.5rpx;
}
.logout {
  color: #718096;
  font-size: 24rpx;
}
.top-actions-right {
  display: flex;
  align-items: center;
  gap: 24rpx;
}
.history-link {
  padding: 10rpx 20rpx;
  color: #4a90e2;
  background: rgba(74, 144, 226, 0.1);
  border-radius: 30rpx;
  font-size: 24rpx;
}
.chat-scroll {
  height: calc(100vh - 400rpx);
  box-sizing: border-box;
  padding: 28rpx;
}
.welcome {
  display: flex;
  margin: 16rpx 0 40rpx;
  padding: 42rpx 30rpx;
  align-items: center;
  flex-direction: column;
}
.welcome-mark {
  display: flex;
  width: 100rpx;
  height: 100rpx;
  margin-bottom: 20rpx;
  align-items: center;
  justify-content: center;
  background: #eaf7f5;
  border: 1rpx solid #cce9e4;
  border-radius: 28rpx;
}
.welcome-title {
  margin-top: 20rpx;
  font-size: 36rpx;
  font-weight: 700;
}
.welcome-desc {
  margin: 14rpx 0 30rpx;
  color: #718096;
  font-size: 24rpx;
  line-height: 1.6;
  text-align: center;
}
.welcome-safety {
  width: 100%;
  margin-top: 24rpx;
  box-sizing: border-box;
}
.quick-list {
  width: 100%;
}
.quick-item {
  margin-top: 16rpx;
  padding: 22rpx 24rpx;
  color: #315568;
  background: #f0f7f7;
  border: 1rpx solid #d9e9e9;
  border-radius: 18rpx;
}
.message-row {
  display: flex;
  margin: 24rpx 0;
  align-items: flex-start;
}
.message-row.user {
  flex-direction: row-reverse;
}
.avatar {
  display: flex;
  width: 62rpx;
  height: 62rpx;
  flex: 0 0 62rpx;
  align-items: center;
  justify-content: center;
  border-radius: 20rpx;
  color: #fff;
  background: #0f8b8d;
  font-size: 23rpx;
  font-weight: 700;
}
.user .avatar {
  background: #315a86;
}
.message-content {
  display: flex;
  max-width: 72%;
  margin: 0 16rpx;
  flex-direction: column;
}
.user .message-content {
  align-items: flex-end;
}
.bubble {
  display: block;
  padding: 22rpx 24rpx;
  color: #25364b;
  background: #fff;
  border-radius: 8rpx 24rpx 24rpx 24rpx;
  line-height: 1.65;
  white-space: pre-wrap;
  box-shadow: 0 6rpx 20rpx rgba(37, 54, 75, 0.06);
}
.user .bubble {
  color: #fff;
  background: linear-gradient(135deg, #24496f, #315a86);
  border-radius: 24rpx 8rpx 24rpx 24rpx;
}
.time {
  margin-top: 8rpx;
  color: #94a3b8;
  font-size: 20rpx;
}
.message-tools {
  display: flex;
  margin-top: 8rpx;
}
.message-tools view {
  display: flex;
  min-height: 44rpx;
  align-items: center;
  gap: 6rpx;
  color: #637985;
  font-size: 20rpx;
}
.typing {
  display: flex;
  gap: 8rpx;
  margin-left: 16rpx;
  color: #76a9a3;
}
.scroll-spacer {
  height: 40rpx;
}
.composer {
  position: fixed;
  right: 0;
  bottom: 0;
  left: 0;
  padding: 16rpx 24rpx calc(18rpx + env(safe-area-inset-bottom));
  background: rgba(255, 255, 255, 0.97);
  border-top: 1rpx solid #dce8ef;
}
.feature-row {
  display: flex;
  align-items: center;
  gap: 16rpx;
}
.report-button {
  display: flex;
  flex: 1;
  height: 70rpx;
  line-height: 70rpx;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
  color: #0b5d61;
  background: #e9f7f5;
  border-radius: 16rpx;
  font-size: 25rpx;
}
.retry-button {
  display: flex;
  height: 70rpx;
  padding: 0 20rpx;
  align-items: center;
  justify-content: center;
  gap: 6rpx;
  color: #9a531e;
  background: #fff4e9;
  border-radius: 16rpx;
  font-size: 23rpx;
}
.input-row {
  display: flex;
  margin-top: 14rpx;
  align-items: center;
  gap: 14rpx;
}
.message-input {
  height: 78rpx;
  padding: 0 26rpx;
  flex: 1;
  background: #f1f5f9;
  border-radius: 22rpx;
}
.send-button {
  display: flex;
  width: 82rpx;
  height: 78rpx;
  padding: 0;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: linear-gradient(135deg, #0b5d61, #0f8b8d);
  border-radius: 22rpx;
}
.send-button[disabled],
.report-button[disabled] {
  opacity: 0.45;
}
</style>
