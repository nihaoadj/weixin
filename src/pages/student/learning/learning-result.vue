<template>
  <view
    class="page"
    :class="{ 'keyboard-open': keyboardHeight > 0 }"
    :style="{
      height: keyboardHeight ? `calc(100vh - ${keyboardHeight}px)` : '100vh',
      paddingTop: `${navigationOffset}px`,
    }"
  >
    <view
      class="page-navbar"
      :style="{ paddingTop: `${statusBarHeight}px`, height: `${navigationOffset + 2}px` }"
    >
      <view
        class="navbar-row"
        :style="{ height: `${navigationHeight}px` }"
      >
        <button
          class="back-button"
          aria-label="返回学习计划"
          @click="back"
        >
          <view class="back-chevron" />
        </button>
        <text class="navbar-title">学习结果</text>
      </view>
    </view>
    <view
      v-if="error && !result"
      class="state error"
      role="alert"
    >
      <text>{{ error }}</text>
      <button @click="load">重新加载</button>
      <button
        class="quiet"
        @click="back"
      >
        返回学习计划
      </button>
    </view>
    <view
      v-else-if="loading && !result"
      class="state"
      role="status"
      >正在读取学习结果…</view
    >
    <view
      v-else-if="result"
      class="result-shell"
    >
      <view class="summary">
        <view class="summary-copy">
          <text class="summary-label"
            >{{ result.sourceKind === 'classroom' ? '课堂研讨' : '自主研讨' }} · 最终测试</text
          >
          <text class="summary-title">{{ routeTitle }}</text>
          <text class="summary-meta"
            >{{ result.reviewKind === 'teacher' ? '教师审阅后开放' : 'AI 生成 · 未经教师审阅' }} ·
            {{ formatDate(result.submittedAt) }}</text
          >
        </view>
        <view class="score"
          ><text>{{ result.score }}</text
          ><small>分</small></view
        >
      </view>

      <view class="question-section">
        <swiper
          class="question-swiper"
          :current="activeIndex"
          @change="onQuestionChange"
        >
          <swiper-item
            v-for="question in result.questions"
            :key="question.id"
          >
            <scroll-view
              class="question-scroll"
              scroll-y
            >
              <view class="question-body">
                <view class="question-top">
                  <view class="question-top-copy">
                    <text class="question-number"
                      >第 {{ question.position }} 题 · {{ typeLabel(question.questionType) }}</text
                    >
                    <text
                      v-if="question.pointsPossible != null"
                      class="question-points"
                      >本题得分 <text>{{ question.pointsAwarded }}/{{ question.pointsPossible }} 分</text></text
                    >
                  </view>
                  <view
                    class="question-dots"
                    aria-label="选择题目"
                  >
                    <button
                      v-for="(item, index) in result.questions"
                      :id="`result-question-${question.position}-dot-${item.position}`"
                      :key="item.id"
                      class="question-dot"
                      :class="{ active: index === activeIndex }"
                      :aria-label="`第 ${item.position} 题`"
                      @click="setQuestion(index)"
                    />
                  </view>
                </view>
                <text class="prompt">{{ question.prompt }}</text>
                <template v-if="question.questionType === 'short_answer'">
                  <text class="answer-heading">你的回答</text>
                  <text class="written-answer">{{ question.selectedText || '未作答' }}</text>
                  <text class="answer-heading">参考答案</text>
                  <text class="written-answer">{{ question.referenceAnswer }}</text>
                  <view
                    v-if="question.rubricResults?.length"
                    class="rubric"
                  >
                    <text
                      v-for="item in question.rubricResults"
                      :key="item.criterionId"
                      >{{ item.evidence }} · {{ item.earnedPoints }}/10 分</text
                    >
                  </view>
                  <text
                    v-if="question.gradingFeedback"
                    class="feedback"
                    >{{ question.gradingFeedback }}</text
                  >
                </template>
                <template v-else>
                  <view
                    v-for="(option, index) in question.options"
                    :key="index"
                    class="option"
                    :class="{
                      correct: isCorrect(question, index),
                      chosenWrong: isChosen(question, index) && !isCorrect(question, index),
                    }"
                  >
                    <text class="option-mark">{{ ['A', 'B', 'C', 'D'][index] }}</text>
                    <text class="option-text">{{ option }}</text>
                    <view
                      v-if="isCorrect(question, index)"
                      class="result-tag"
                      ><text class="tag-symbol">✓</text><text>正确答案</text></view
                    >
                    <view
                      v-else-if="isChosen(question, index)"
                      class="result-tag wrong"
                      ><text class="tag-symbol">×</text><text>你的选择</text></view
                    >
                  </view>
                </template>
                <view class="explanation"
                  ><text class="explanation-icon">✦</text><text class="explanation-label">解析</text
                  ><text>{{ question.explanation }}</text></view
                >
              </view>
            </scroll-view>
          </swiper-item>
        </swiper>
      </view>

      <view class="section-divider"><text>✱</text></view>
      <view class="tutor-section">
        <view
          v-if="!tutor?.messages.length && !sending && !pendingMessage"
          class="tutor-head"
        >
          <view class="tutor-brand"
            ><text class="assistant-star">✱</text><text class="section-title">AI 导学助手</text></view
          >
        </view>
        <scroll-view
          class="chat-log"
          scroll-y
          :scroll-into-view="lastMessageAnchor"
          :show-scrollbar="false"
          aria-label="AI 导学对话"
        >
          <view
            v-if="tutorLoading"
            class="chat-state"
            role="status"
            >正在读取对话…</view
          >
          <view
            v-else-if="!tutor?.messages.length"
            class="suggestions"
          >
            <text class="suggestions-label">你可以这样提问：</text>
            <button
              v-for="(suggestion, index) in suggestions"
              :key="suggestion"
              class="suggestion"
              :disabled="!tutor || sending || Boolean(pendingMessage)"
              @click="useSuggestion(suggestion, index)"
            >
              <image
                v-if="index < suggestionIcons.length"
                class="suggestion-icon"
                :src="suggestionIcons[index]"
                mode="aspectFit"
                aria-hidden="true"
              /><text
                v-else
                class="suggestion-icon"
                >?</text
              ><text>{{ suggestion }}</text
              ><text class="suggestion-arrow">›</text>
            </button>
          </view>
          <view
            v-for="message in tutor?.messages || []"
            :id="`message-${message.sequence}`"
            :key="message.id"
            class="chat-message"
            :class="{ own: message.role === 'student' }"
          >
            <view class="message-main">
              <view class="message-meta-row">
                <text
                  v-if="message.role === 'assistant'"
                  class="message-avatar"
                  aria-hidden="true"
                  >✱</text
                >
                <text class="message-meta"
                  >{{ message.role === 'assistant' ? 'AI 导学助手 · ' : '' }}第
                  {{ questionPosition(message.questionId) }} 题</text
                >
              </view>
              <text class="message-content">{{ message.content }}</text>
            </view>
          </view>
          <text
            v-if="sending || tutor?.processingState === 'processing'"
            class="chat-state"
            role="status"
            >导学助手正在思考…</text
          >
        </scroll-view>
        <view
          v-if="tutorError"
          class="chat-error"
          role="alert"
          >{{ tutorError }}</view
        >
        <view class="composer">
          <textarea
            class="composer-input"
            :value="draft"
            :focus="inputFocused"
            :disabled="sending || tutor?.processingState === 'processing' || !tutor || Boolean(pendingMessage)"
            maxlength="2000"
            auto-height
            :adjust-position="false"
            :cursor-spacing="16"
            aria-label="导学提问"
            placeholder="提出你的问题..."
            @input="updateDraft"
            @keyboardheightchange="keyboardChanged"
            @blur="inputFocused = false"
          />
          <button
            class="send-button"
            :disabled="!canSend"
            :aria-label="pendingMessage ? '重试导学提问' : '发送导学提问'"
            @click="sendMessage"
          >
            <text
              v-if="pendingMessage"
              class="retry-label"
              >重试</text
            >
            <image
              v-else
              src="/static/case-learning-send.svg"
              aria-hidden="true"
            />
          </button>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onBackPress, onHide, onLoad, onShow, onUnload } from '@dcloudio/uni-app'
import {
  createLearningRequestId,
  getLearningResultTutor,
  getLearningRouteResult,
  sendLearningResultTutorMessage,
  type LearningResult,
  type LearningResultQuestion,
  type LearningResultTutorThread,
} from '@/features/learning/public'
import { getSession, requireRole } from '@/features/identity/public'
import { goReplace, handleBackPress, ROUTES } from '@/platform/navigation'

type PendingMessage = { id: string; questionId: string; revision: number; content: string }
const result = ref<LearningResult>()
const tutor = ref<LearningResultTutorThread>()
const statusBarHeight = ref(0)
const navigationHeight = ref(44)
const navigationOffset = computed(() => statusBarHeight.value + navigationHeight.value)
const keyboardHeight = ref(0)
const inputFocused = ref(false)
const suggestions = [
  '请解释一下这个题目的思路。',
  '这个知识点的原理是什么？',
  '还有其他相关的知识吗？',
  '我还有其他问题。',
]
const suggestionIcons = [
  '/static/knowledge-node-chat.svg',
  '/static/knowledge-node-document.svg',
  '/static/knowledge-node-bulb.svg',
]
const loading = ref(false)
const tutorLoading = ref(false)
const sending = ref(false)
const error = ref('')
const tutorError = ref('')
const draft = ref('')
const pendingMessage = ref<PendingMessage>()
const activeIndex = ref(0)
const activeQuestion = computed(() => result.value?.questions[activeIndex.value])
const routeTitle = computed(() => String(result.value?.routeSummary.title || '学习结果'))
const lastMessageAnchor = computed(() => {
  const last = tutor.value?.messages.at(-1)
  return last ? `message-${last.sequence}` : ''
})
const canSend = computed(() =>
  Boolean(
    tutor.value &&
    !sending.value &&
    tutor.value.processingState !== 'processing' &&
    (pendingMessage.value || draft.value.trim().length > 0),
  ),
)
let routeId = ''
let expectedResultId = ''
let identity = ''
let valid = false
let contextVersion = 0
let requestVersion = 0
let tutorTimer: ReturnType<typeof setTimeout> | undefined
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
function back() {
  goReplace(ROUTES.studentLearningPlanDetail, { routeId })
}
function formatDate(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleString('zh-CN')
}
function typeLabel(type: string) {
  return type === 'multiple_choice' ? '多选' : type === 'short_answer' ? '简答' : '单选'
}
function updateDraft(event: unknown) {
  const input = event as { detail?: { value?: string }; target?: { value?: string } }
  draft.value = input.detail?.value ?? input.target?.value ?? ''
}
function keyboardChanged(event: { detail: { height: number } }) {
  keyboardHeight.value = Math.max(0, event.detail.height)
}
function useSuggestion(suggestion: string, index: number) {
  if (!tutor.value || sending.value || pendingMessage.value) return
  if (index === suggestions.length - 1) {
    inputFocused.value = true
    return
  }
  draft.value = suggestion
  void sendMessage()
}
function isCorrect(question: LearningResultQuestion, index: number) {
  return question.questionType === 'multiple_choice'
    ? question.correctOptions?.includes(index)
    : question.correctOption === index
}
function isChosen(question: LearningResultQuestion, index: number) {
  return question.questionType === 'multiple_choice'
    ? question.selectedOptions?.includes(index)
    : question.selectedOption === index
}
function questionPosition(questionId: string) {
  return result.value?.questions.find((item) => item.id === questionId)?.position || '?'
}
function setQuestion(index: number) {
  if (result.value && index >= 0 && index < result.value.questions.length) {
    activeIndex.value = index
  }
}
function onQuestionChange(event: { detail: { current: number } }) {
  setQuestion(event.detail.current)
}
function clearTutorTimer() {
  if (tutorTimer) clearTimeout(tutorTimer)
  tutorTimer = undefined
}
function scheduleTutorRefresh(resultId: string, requestedIdentity: string, context: number) {
  clearTutorTimer()
  tutorTimer = setTimeout(() => void loadTutor(resultId, requestedIdentity, context), 2500)
}
function isCurrent(token: number, requestedIdentity: string, context: number) {
  const session = getSession()
  return (
    token === requestVersion &&
    context === contextVersion &&
    session?.role === 'student' &&
    session.openid === requestedIdentity
  )
}
async function load() {
  const session = getSession()
  if (!valid || !requireRole('student') || session?.role !== 'student' || !session.openid) return
  resetIdentity(session.openid)
  const requestedIdentity = session.openid
  const context = contextVersion
  const token = ++requestVersion
  loading.value = true
  error.value = ''
  try {
    const value = await getLearningRouteResult(routeId)
    if (!isCurrent(token, requestedIdentity, context)) return
    if (expectedResultId && value.id !== expectedResultId) throw new Error('学习结果链接与当前路线不匹配。')
    if (value.routeId !== routeId) throw new Error('学习结果不属于当前路线。')
    result.value = value
    activeIndex.value = Math.max(0, Math.min(activeIndex.value, value.questions.length - 1))
    void loadTutor(value.id, requestedIdentity, context)
  } catch (reason) {
    if (isCurrent(token, requestedIdentity, context))
      error.value = reason instanceof Error ? reason.message : '学习结果加载失败。'
  } finally {
    if (isCurrent(token, requestedIdentity, context)) loading.value = false
  }
}
async function loadTutor(resultId: string, requestedIdentity: string, context: number) {
  tutorLoading.value = true
  tutorError.value = ''
  try {
    const value = await getLearningResultTutor(resultId)
    if (context !== contextVersion || identity !== requestedIdentity || result.value?.id !== resultId) return
    tutor.value = value
    if (value.processingState !== 'idle' && value.pendingMessageId) {
      const last = [...value.messages].reverse().find((item) => item.role === 'student')
      if (last) {
        pendingMessage.value = {
          id: value.pendingMessageId,
          questionId: last.questionId,
          revision: value.revision,
          content: last.content,
        }
        draft.value = last.content
      }
    } else {
      pendingMessage.value = undefined
      clearTutorTimer()
    }
    if (value.processingState === 'processing') scheduleTutorRefresh(resultId, requestedIdentity, context)
  } catch (reason) {
    if (context === contextVersion && identity === requestedIdentity)
      tutorError.value = reason instanceof Error ? reason.message : '导学对话读取失败。'
  } finally {
    if (context === contextVersion && identity === requestedIdentity) tutorLoading.value = false
  }
}
async function sendMessage() {
  if (!canSend.value || !result.value || !tutor.value || !activeQuestion.value) return
  const pending = pendingMessage.value || {
    id: createLearningRequestId('result-tutor'),
    questionId: activeQuestion.value.id,
    revision: tutor.value.revision,
    content: draft.value.trim(),
  }
  pendingMessage.value = pending
  sending.value = true
  tutorError.value = ''
  const requestedIdentity = identity
  const context = contextVersion
  const resultId = result.value.id
  try {
    const value = await sendLearningResultTutorMessage(
      resultId,
      pending.id,
      pending.questionId,
      pending.revision,
      pending.content,
    )
    if (context !== contextVersion || identity !== requestedIdentity || result.value?.id !== resultId) return
    tutor.value = value
    if (value.processingState === 'idle') {
      pendingMessage.value = undefined
      draft.value = ''
    } else if (value.processingState === 'processing') scheduleTutorRefresh(resultId, requestedIdentity, context)
  } catch (reason) {
    if (context === contextVersion && identity === requestedIdentity)
      tutorError.value = reason instanceof Error ? reason.message : '导学回复暂不可用，可重试原消息。'
  } finally {
    if (context === contextVersion && identity === requestedIdentity) sending.value = false
  }
}
function resetIdentity(nextIdentity: string) {
  if (identity === nextIdentity) return
  identity = nextIdentity
  contextVersion += 1
  requestVersion += 1
  result.value = undefined
  tutor.value = undefined
  error.value = ''
  tutorError.value = ''
  loading.value = false
  tutorLoading.value = false
  sending.value = false
  pendingMessage.value = undefined
  draft.value = ''
  activeIndex.value = 0
  keyboardHeight.value = 0
  inputFocused.value = false
  clearTutorTimer()
}
function hide() {
  requestVersion += 1
  loading.value = false
  clearTutorTimer()
  keyboardHeight.value = 0
  inputFocused.value = false
}
onLoad((query) => {
  const windowInfo = typeof uni.getWindowInfo === 'function' ? uni.getWindowInfo() : uni.getSystemInfoSync?.()
  statusBarHeight.value = windowInfo?.statusBarHeight || 0
  if (typeof uni.getMenuButtonBoundingClientRect === 'function') {
    const capsule = uni.getMenuButtonBoundingClientRect()
    if (capsule.top >= statusBarHeight.value && capsule.height > 0)
      navigationHeight.value = Math.max(44, capsule.height + (capsule.top - statusBarHeight.value) * 2)
  }
  routeId = String(query?.routeId || '')
  expectedResultId = String(query?.resultId || '')
  valid = uuid.test(routeId) && (!expectedResultId || uuid.test(expectedResultId))
  if (!valid) error.value = '学习结果链接无效。'
  if (requireRole('student')) identity = getSession()?.openid || ''
})
onShow(() => {
  const session = getSession()
  if (!requireRole('student') || session?.role !== 'student' || !session.openid) {
    resetIdentity('')
    return
  }
  resetIdentity(session.openid)
  if (valid) void load()
})
onHide(hide)
onUnload(hide)
onBackPress(({ from }) => handleBackPress(from, ROUTES.studentLearningPlanDetail, { routeId }))
</script>

<style scoped>
.page {
  position: relative;
  display: flex;
  width: 100%;
  box-sizing: border-box;
  flex-direction: column;
  overflow: hidden;
  background: linear-gradient(145deg, #fbfdff 0%, #f8fcff 53%, #f5faff 100%);
  color: #071653;
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'HarmonyOS Sans SC', 'Microsoft YaHei', sans-serif;
}
.page-navbar {
  position: absolute;
  top: 0;
  right: 0;
  left: 0;
  z-index: 5;
  box-sizing: border-box;
  background: linear-gradient(180deg, #fff 75%, rgba(248, 253, 255, 0.96));
}
.navbar-row {
  position: relative;
  display: flex;
  max-width: 920px;
  align-items: center;
  justify-content: center;
  margin: 0 auto;
}
.navbar-title {
  color: #111827;
  font-size: 32rpx;
  font-weight: 600;
}
.back-button {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 10rpx;
  display: flex;
  width: 88rpx;
  align-items: center;
  justify-content: center;
  margin: 0;
  padding: 0;
  background: transparent;
}
.back-button::after,
.question-dot::after,
.suggestion::after,
.send-button::after {
  border: 0;
}
.back-chevron {
  width: 22rpx;
  height: 22rpx;
  border-bottom: 4rpx solid #111827;
  border-left: 4rpx solid #111827;
  transform: rotate(45deg);
}
.result-shell {
  display: flex;
  min-height: 0;
  width: 100%;
  max-width: 920px;
  box-sizing: border-box;
  flex: 1;
  flex-direction: column;
  margin: 0 auto;
  padding: 0 26rpx calc(12rpx + env(safe-area-inset-bottom));
}
.summary {
  display: flex;
  flex: none;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  padding: 19rpx 14rpx 21rpx;
}
.summary-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 5rpx;
}
.summary-label {
  color: #5967a4;
  font-size: 23rpx;
}
.summary-title {
  color: #071653;
  font-size: 38rpx;
  font-weight: 750;
  line-height: 1.35;
}
.summary-meta {
  color: #646da7;
  font-size: 22rpx;
  line-height: 1.45;
}
.score {
  display: flex;
  flex: none;
  align-items: baseline;
  color: #06a9ce;
}
.score text {
  font-size: 60rpx;
  font-weight: 750;
  line-height: 1;
}
.score small {
  font-size: 26rpx;
}
.question-section {
  height: 530rpx;
  max-height: 39vh;
  min-height: 0;
  box-sizing: border-box;
  flex: none;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(255, 255, 255, 0.9);
  border-radius: 22rpx;
  box-shadow: 0 13rpx 34rpx rgba(62, 157, 195, 0.09);
}
.question-swiper,
.question-scroll {
  height: 100%;
}
.question-body {
  padding: 22rpx 28rpx 26rpx;
}
.question-top,
.question-top-copy,
.question-dots {
  display: flex;
  align-items: center;
}
.question-top {
  justify-content: space-between;
  gap: 6rpx;
}
.question-top-copy {
  min-width: 0;
  flex-wrap: wrap;
  gap: 12rpx;
}
.question-number {
  color: #03a6c8;
  font-size: 26rpx;
  font-weight: 700;
}
.question-points {
  color: #5967a4;
  font-size: 24rpx;
}
.question-points text {
  color: #03a6c8;
  font-weight: 700;
}
.question-dots {
  flex: none;
  gap: 3rpx;
}
.question-dot {
  position: relative;
  display: block;
  width: 42rpx;
  height: 56rpx;
  flex: none;
  margin: 0;
  padding: 0;
  background: transparent;
}
.question-dot::before {
  position: absolute;
  top: 17rpx;
  left: 11rpx;
  width: 20rpx;
  height: 20rpx;
  content: '';
  background: #e5edf5;
  border-radius: 50%;
}
.question-dot.active::before {
  background: #04aed0;
}
.prompt {
  display: block;
  margin: 17rpx 0 17rpx;
  color: #071653;
  font-size: 29rpx;
  font-weight: 700;
  line-height: 1.48;
}
.option {
  display: flex;
  min-height: 61rpx;
  box-sizing: border-box;
  align-items: center;
  gap: 18rpx;
  margin-top: 9rpx;
  padding: 6rpx 15rpx;
  color: #12285d;
  background: #f1f5f9;
  border-radius: 16rpx;
  font-size: 26rpx;
  line-height: 1.45;
}
.option.correct {
  color: #006684;
  background: #e5f9f0;
}
.option.chosenWrong {
  color: #ec303b;
  background: #fff0f0;
}
.option-mark {
  display: flex;
  width: 47rpx;
  height: 47rpx;
  flex: 0 0 47rpx;
  align-items: center;
  justify-content: center;
  color: #092267;
  background: linear-gradient(140deg, #e1e8f0, #f0f3f7);
  border-radius: 12rpx;
  font-size: 28rpx;
  font-weight: 700;
}
.correct .option-mark {
  color: #fff;
  background: #05b78c;
}
.chosenWrong .option-mark {
  color: #fff;
  background: #f43e4b;
}
.option-text {
  min-width: 0;
  flex: 1;
}
.result-tag {
  display: flex;
  flex: none;
  align-items: center;
  gap: 8rpx;
  color: #00ad82;
  font-size: 22rpx;
  font-weight: 700;
  white-space: nowrap;
}
.result-tag.wrong {
  color: #f13744;
}
.tag-symbol {
  display: flex;
  width: 30rpx;
  height: 30rpx;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: #02b991;
  border-radius: 50%;
  font-size: 23rpx;
  font-weight: 800;
}
.wrong .tag-symbol {
  background: #f33c4b;
}
.answer-heading {
  display: block;
  margin: 14rpx 0 6rpx;
  color: #5967a4;
  font-size: 24rpx;
  font-weight: 700;
}
.written-answer,
.feedback,
.rubric {
  color: #274678;
  font-size: 24rpx;
  line-height: 1.6;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
.written-answer,
.feedback {
  display: block;
}
.rubric {
  display: flex;
  flex-direction: column;
  gap: 7rpx;
  margin-top: 13rpx;
}
.feedback {
  margin-top: 13rpx;
}
.explanation {
  display: flex;
  align-items: flex-start;
  gap: 14rpx;
  margin-top: 18rpx;
  padding-top: 14rpx;
  color: #14265d;
  border-top: 1px solid #dcecf9;
  font-size: 24rpx;
  line-height: 1.5;
}
.explanation-icon {
  display: flex;
  width: 42rpx;
  height: 42rpx;
  flex: 0 0 42rpx;
  align-items: center;
  justify-content: center;
  color: #08add0;
  background: #e7faff;
  border-radius: 50%;
}
.explanation-label {
  flex: none;
  color: #06a5c7;
  font-size: 26rpx;
  font-weight: 700;
}
.section-divider {
  position: relative;
  display: flex;
  height: 54rpx;
  flex: none;
  align-items: center;
  justify-content: center;
  color: #07abd0;
  font-size: 44rpx;
}
.section-divider::before {
  display: block;
  min-width: 0;
  height: 1px;
  flex: 1;
  content: '';
  background: #62d5ea;
}
.section-divider::after {
  display: block;
  min-width: 0;
  height: 1px;
  flex: 1;
  content: '';
  background: #62d5ea;
}
.section-divider text {
  padding: 0 13rpx;
}
.tutor-section {
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
}
.tutor-head,
.tutor-brand {
  display: flex;
  align-items: center;
}
.tutor-head {
  min-height: 67rpx;
  flex: none;
  justify-content: space-between;
  gap: 14rpx;
}
.tutor-brand {
  gap: 12rpx;
  color: #06aed0;
}
.assistant-star {
  font-size: 54rpx;
  line-height: 1;
}
.section-title {
  font-size: 32rpx;
  font-weight: 700;
}
.chat-log {
  height: 0;
  min-height: 0;
  box-sizing: border-box;
  flex: 1;
  padding: 4rpx 8rpx 18rpx;
  scrollbar-width: none;
}
.chat-log::-webkit-scrollbar {
  width: 0;
  height: 0;
}
.chat-state,
.chat-error {
  display: block;
  padding: 18rpx 10rpx;
  color: #6677aa;
  font-size: 26rpx;
}
.chat-error {
  color: #ba434d;
}
.suggestions-label {
  display: block;
  margin: 4rpx 6rpx 10rpx;
  color: #5967a4;
  font-size: 27rpx;
}
.suggestion {
  display: flex;
  width: 100%;
  min-height: 69rpx;
  box-sizing: border-box;
  align-items: center;
  gap: 14rpx;
  margin: 0 0 9rpx;
  padding: 5rpx 13rpx;
  color: #071653;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid #d4e9ff;
  border-radius: 20rpx;
  box-shadow: 0 4rpx 11rpx rgba(64, 145, 194, 0.04);
  font-size: 28rpx;
  text-align: left;
}
.suggestion-icon {
  display: flex;
  width: 49rpx;
  height: 49rpx;
  flex: 0 0 49rpx;
  align-items: center;
  justify-content: center;
  color: #08a5c6;
  background: #e8faff;
  border-radius: 50%;
  font-size: 32rpx;
  font-weight: 700;
}
.suggestion-arrow {
  margin-left: auto;
  color: #04a9c8;
  font-size: 42rpx;
  line-height: 1;
}
.chat-message {
  display: flex;
  align-items: flex-start;
  gap: 10rpx;
  margin: 15rpx 4rpx 21rpx;
}
.chat-message.own {
  flex-direction: row-reverse;
}
.message-meta-row {
  display: flex;
  min-height: 38rpx;
  align-items: center;
  gap: 10rpx;
}
.message-avatar {
  display: flex;
  width: 38rpx;
  height: 38rpx;
  flex: 0 0 38rpx;
  align-items: center;
  justify-content: center;
  color: #0cafd0;
  font-size: 36rpx;
  line-height: 1;
}
.message-main {
  display: flex;
  min-width: 0;
  max-width: 100%;
  flex-direction: column;
  gap: 5rpx;
}
.own .message-main {
  max-width: 82%;
  align-items: flex-end;
}
.message-meta {
  color: #06aed0;
  font-size: 24rpx;
  font-weight: 700;
  line-height: 1.4;
}
.message-content {
  display: block;
  margin-left: 48rpx;
  color: #35558d;
  font-size: 30rpx;
  line-height: 1.7;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
.own .message-content {
  margin-left: 0;
  padding: 17rpx 22rpx;
  color: #173867;
  background: linear-gradient(145deg, #f4faff, #eaf5ff);
  border: 1rpx solid #d5e9f8;
  border-radius: 24rpx 24rpx 8rpx 24rpx;
  box-shadow:
    0 10rpx 27rpx rgba(42, 119, 177, 0.16),
    0 2rpx 6rpx rgba(42, 119, 177, 0.07);
}
.composer {
  display: flex;
  align-items: center;
  gap: 12rpx;
  min-height: 92rpx;
  box-sizing: border-box;
  flex: none;
  margin-top: 8rpx;
  padding: 10rpx 14rpx 10rpx 24rpx;
  background: #fff;
  border: 1rpx solid #bfe6ef;
  border-radius: 34rpx;
  box-shadow: 0 8rpx 26rpx rgba(7, 155, 170, 0.085);
  transition:
    border-color 180ms ease,
    box-shadow 180ms ease;
}
.composer:focus-within {
  border-color: #7bd3df;
  box-shadow: 0 9rpx 28rpx rgba(7, 155, 170, 0.14);
}
.composer-input {
  flex: 1;
  width: 0;
  min-height: 42rpx;
  max-height: 180rpx;
  padding: 6rpx 0;
  color: #071653;
  font-size: 26rpx;
  line-height: 1.6;
}
.send-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 72rpx;
  height: 72rpx;
  flex: 0 0 72rpx;
  margin: 0;
  padding: 0;
  color: #fff;
  background: linear-gradient(135deg, #51cddd, #029fbf);
  border-radius: 50%;
}
.send-button image {
  width: 40rpx;
  height: 40rpx;
}
.send-button[disabled] {
  background: linear-gradient(135deg, #51cddd, #029fbf);
  opacity: 0.55;
}
.retry-label {
  font-size: 20rpx;
}
.state {
  display: flex;
  min-height: 210rpx;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16rpx;
  margin: 28rpx;
  padding: 30rpx;
  color: #536899;
  background: #fff;
  border-radius: 22rpx;
}
.state button {
  color: #087eaa;
  background: #e7f7ff;
  border-radius: 15rpx;
}
.state.error {
  color: #a0444a;
}
.keyboard-open .summary,
.keyboard-open .question-section,
.keyboard-open .section-divider {
  display: none;
}
.keyboard-open .tutor-section {
  padding-top: 8rpx;
}
.keyboard-open .result-shell {
  padding-bottom: 6rpx;
}
</style>
