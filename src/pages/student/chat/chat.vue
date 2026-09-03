<template>
  <view class="safe-page chat-page">
    <view class="top-actions">
      <view class="session-context">
        <text class="session-title">{{ selectedTopics.length ? '主题问答' : '自由问答' }}</text>
        <text class="session-summary">记录推理过程，保留学习依据</text>
        <view class="topic-row">
          <text class="topic-label">本次主题</text>
          <view
            v-if="selectedTopics.length"
            class="topic-chips"
          >
            <button
              v-for="topic in selectedTopics"
              :key="topic.code"
              class="topic-chip"
              :aria-label="`移除学习主题 ${topic.title}`"
              @click="removeTopic(topic.code)"
            >
              {{ topic.title }} ×
            </button>
          </view>
          <picker
            v-if="topicOptions.length"
            class="topic-picker"
            :range="topicOptions"
            range-key="label"
            @change="addTopic"
          >
            <button class="topic-add">选择主题</button>
          </picker>
        </view>
      </view>
      <view class="top-actions-right">
        <button
          tabindex="0"
          role="button"
          class="history-link"
          aria-label="查看历史学习记录"
          @keydown="activateButtonOnKey"
          @click="goToHistory"
        >
          历史
        </button>
        <button
          tabindex="0"
          role="button"
          class="logout"
          aria-label="退出学生账号"
          @keydown="activateButtonOnKey"
          @click="logout"
        >
          退出
        </button>
      </view>
    </view>

    <scroll-view
      class="chat-scroll"
      scroll-y
      :scroll-into-view="lastMessageId"
    >
      <ChatWelcome
        v-if="messages.length === 0"
        :questions="quickQuestions"
        @ask="quickAsk"
      />

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
            <button
              tabindex="0"
              role="button"
              aria-label="复制助手回答"
              @keydown="activateButtonOnKey"
              @click="copyMessage(message.content)"
            >
              <MedIcon
                name="copy"
                size="sm"
              /><text>复制</text>
            </button>
            <button
              tabindex="0"
              role="button"
              aria-label="围绕这条回答继续提问"
              @keydown="activateButtonOnKey"
              @click="continueFromAnswer(message.content)"
            >
              <text>继续问</text>
            </button>
            <button
              tabindex="0"
              role="button"
              aria-label="将此回答加入复习"
              @keydown="activateButtonOnKey"
              @click="saveAnswerForReview(message)"
            >
              <text>加入复习</text>
            </button>
          </view>
          <text class="time">{{ message.timestamp }}</text>
        </view>
      </view>
      <view
        v-if="isLoading"
        class="message-row assistant"
        role="status"
        aria-live="polite"
      >
        <view class="avatar">AI</view>
        <view class="bubble typing"><text>正在组织回答…</text></view>
      </view>
      <view class="scroll-spacer" />
    </scroll-view>

    <ChatComposer
      v-model="inputValue"
      :loading="isLoading"
      :can-generate-report="messages.length > 0"
      :can-retry="Boolean(lastFailedPrompt)"
      @send="sendMessage"
      @report="endConversation"
      @retry="retryLastMessage"
    />
  </view>
</template>

<script setup lang="ts">
import { activateButtonOnKey } from '@/components/ui/keyboard'
import { computed, nextTick, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import MedIcon from '@/components/ui/MedIcon.vue'
import ChatWelcome from '@/components/chat/ChatWelcome.vue'
import ChatComposer from '@/components/chat/ChatComposer.vue'
import { requireRole, logout } from '@/features/identity/public'
import { goDetail, goPrimary, ROUTES } from '@/platform/navigation'
import { requestMedicalAssistant } from '@/features/qa/public'
import { findConversationAsync, upsertConversationAsync } from '@/features/qa/public'
import { captureManualReviewItem, getKnowledgeCatalog } from '@/features/learning/public'
import { findReportAsync, saveDraftReportAsync } from '@/features/reports/public'
import type { ChatMessage } from '@/types/domain'
import type { KnowledgePoint } from '@/types/knowledge'
import { formatClock } from '@/utils/date'
import { analyzeConversation } from '@/utils/report'

const quickQuestions = ['给我一个医学案例让我诊断。', '肺炎的典型症状有哪些？', '高血压的诊断标准是什么？']
const messages = ref<ChatMessage[]>([])
const inputValue = ref('')
const conversationId = ref('')
const lastMessageId = ref('')
const isLoading = ref(false)
const lastFailedPrompt = ref('')
const knowledgePoints = ref<KnowledgePoint[]>([])
const topicCodes = ref<string[]>([])
const selectedTopics = computed(() => knowledgePoints.value.filter((item) => topicCodes.value.includes(item.code)))
const topicOptions = computed(() =>
  knowledgePoints.value
    .filter((item) => !topicCodes.value.includes(item.code))
    .map((item) => ({ label: `${item.systemLabel} · ${item.title}`, code: item.code })),
)

onLoad((options) => {
  if (!requireRole('student')) return
  const requestedId = typeof options?.conversationId === 'string' ? options.conversationId : ''
  const requestedTopic = typeof options?.topicCode === 'string' ? options.topicCode : ''
  const starter = typeof options?.starter === 'string' ? options.starter : ''
  inputValue.value = starter
  void loadConversation(requestedId, requestedTopic)
})

async function loadConversation(requestedId: string, requestedTopic = '') {
  try {
    knowledgePoints.value = await getKnowledgeCatalog()
  } catch {
    knowledgePoints.value = []
  }
  const conversation = requestedId ? await findConversationAsync(requestedId) : undefined
  conversationId.value = conversation?.conversationId || `conv_${Date.now()}`
  messages.value = conversation?.messages || []
  topicCodes.value = (conversation?.topicCodes || []).filter((code) =>
    knowledgePoints.value.some((item) => item.code === code),
  )
  if (
    requestedTopic &&
    topicCodes.value.length < 3 &&
    knowledgePoints.value.some((item) => item.code === requestedTopic)
  ) {
    topicCodes.value = [...topicCodes.value, requestedTopic]
  }
  await scrollToBottom()
}

function addTopic(event: { detail: { value: string | number } }) {
  const topic = topicOptions.value[Number(event.detail.value)]
  if (!topic || topicCodes.value.length >= 3) return
  topicCodes.value = [...topicCodes.value, topic.code]
  void persistConversation()
}

function removeTopic(code: string) {
  topicCodes.value = topicCodes.value.filter((item) => item !== code)
  void persistConversation()
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
      topicCodes: topicCodes.value,
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
    const content = await requestMedicalAssistant({
      prompt,
      history: messages.value,
      mode: '自由问答',
      topicCodes: topicCodes.value,
    })
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

function continueFromAnswer(content: string) {
  const topic = selectedTopics.value[0]?.title
  inputValue.value = topic
    ? `请围绕“${topic}”继续解释：${content.slice(0, 80)}`
    : `请进一步解释：${content.slice(0, 80)}`
}

async function saveAnswerForReview(message: ChatMessage) {
  const pointCode = topicCodes.value[0]
  if (!pointCode) {
    uni.showToast({ title: '请先在顶部选择本次学习主题', icon: 'none' })
    return
  }
  try {
    await captureManualReviewItem({
      pointCode,
      sourceType: 'assistant_message',
      sourceId: message.id,
      note: message.content.slice(0, 300),
    })
    uni.showToast({ title: '已加入复习', icon: 'success' })
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : '加入复习失败', icon: 'none' })
  }
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
        if (confirm) goDetail(ROUTES.studentReport, { conversationId: conversationId.value })
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
    if (!topicCodes.value.length) {
      goDetail(ROUTES.studentReport, { conversationId: conversationId.value })
      return
    }
    uni.showModal({
      title: '报告已生成',
      content: '现在完成本次主题的客观小测，错误会进入你的复习队列。也可以稍后从学习页进入。',
      confirmText: '开始小测',
      cancelText: '查看报告',
      success: ({ confirm }) => {
        if (confirm) {
          goDetail(ROUTES.studentKnowledgeLoop, { topicCodes: topicCodes.value.join(',') })
          return
        }
        goDetail(ROUTES.studentReport, { conversationId: conversationId.value })
      },
    })
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
  display: flex;
  height: calc(100vh - var(--window-top, 0px));
  /* #ifdef H5 */
  height: calc(100dvh - var(--window-top, 0px));
  /* #endif */
  min-height: 0;
  overflow: hidden;
  flex-direction: column;
  background: var(--med-page);
}
.top-actions {
  display: flex;
  padding: 16rpx 28rpx;
  align-items: center;
  justify-content: space-between;
  flex: none;
  gap: 20rpx;
  background: var(--med-surface);
  border-bottom: 1rpx solid var(--med-border);
}
.session-context {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 4rpx;
}
.session-title {
  color: var(--med-ink);
  font-size: 30rpx;
  font-weight: 800;
}
.session-summary {
  color: var(--med-muted);
  font-size: 22rpx;
  line-height: 1.5;
}
.topic-row,
.topic-chips {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 8rpx;
}
.topic-row {
  flex-wrap: wrap;
}
.topic-label {
  color: var(--med-muted);
  font-size: 20rpx;
}
.topic-chip,
.topic-add {
  min-height: 42rpx;
  margin: 0;
  padding: 0 12rpx;
  color: var(--med-clinical);
  background: var(--med-wash);
  border-radius: 99rpx;
  font-size: 20rpx;
  line-height: 42rpx;
}
.topic-add {
  color: var(--med-text-secondary);
  background: transparent;
  border: 1rpx solid var(--med-border);
}
.top-actions-right {
  display: flex;
  align-items: center;
  flex: none;
  gap: 4rpx;
}
.history-link,
.logout {
  min-width: 44px;
  min-height: 44px;
  margin: 0;
  padding: 0 12rpx;
  color: var(--med-clinical);
  background: transparent;
  font-size: 24rpx;
}
.logout {
  color: var(--med-muted);
}
.chat-scroll {
  height: 0;
  min-height: 0;
  padding: 28rpx;
  box-sizing: border-box;
  flex: 1;
}
.message-row {
  display: flex;
  max-width: 800px;
  margin: 24rpx auto;
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
  color: #fff;
  background: var(--med-clinical);
  border-radius: var(--med-radius-sm);
  font-size: 23rpx;
  font-weight: 700;
}
.user .avatar {
  background: var(--med-ink);
}
.message-content {
  display: flex;
  min-width: 0;
  max-width: 76%;
  margin: 0 16rpx;
  flex-direction: column;
}
.user .message-content {
  align-items: flex-end;
}
.bubble {
  display: block;
  padding: 22rpx 24rpx;
  color: var(--med-text);
  background: var(--med-surface);
  border: 1rpx solid var(--med-border);
  border-radius: 6rpx var(--med-radius-md) var(--med-radius-md) var(--med-radius-md);
  font-size: 28rpx;
  line-height: 1.65;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
.user .bubble {
  color: #fff;
  background: var(--med-ink);
  border-color: var(--med-ink);
  border-radius: var(--med-radius-md) 6rpx var(--med-radius-md) var(--med-radius-md);
}
.time {
  margin-top: 8rpx;
  color: var(--med-muted);
  font-size: 22rpx;
}
.message-tools {
  display: flex;
}
.message-tools button {
  display: flex;
  min-height: 44px;
  margin: 0;
  padding: 0 12rpx;
  align-items: center;
  gap: 6rpx;
  color: var(--med-muted);
  background: transparent;
  font-size: 22rpx;
}
.typing {
  margin-left: 16rpx;
  color: var(--med-muted);
}
.scroll-spacer {
  height: 24rpx;
}
@media screen and (max-width: 360px) {
  .session-summary {
    font-size: 11px;
  }
  .bubble {
    font-size: 14px;
  }
}
@media screen and (min-width: 600px) {
  .top-actions {
    padding: 16px 32px;
  }
  .session-title {
    font-size: 22px;
  }
  .session-summary,
  .history-link,
  .logout {
    font-size: 14px;
  }
  .topic-label,
  .topic-chip,
  .topic-add {
    font-size: 12px;
  }
  .history-link,
  .logout {
    min-width: 56px;
    padding: 0 12px;
  }
  .chat-scroll {
    padding: 28px 32px;
  }
  .avatar {
    width: 40px;
    height: 40px;
    flex-basis: 40px;
    font-size: 14px;
  }
  .bubble {
    padding: 14px 16px;
    font-size: 16px;
  }
  .time,
  .message-tools button {
    font-size: 13px;
  }
}
</style>
