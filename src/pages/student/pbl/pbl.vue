<template>
  <view
    class="safe-page dialogue-page"
    :class="{ 'is-dialogue': canSendMessage, 'is-keyboard-open': keyboardHeight > 0 }"
    :style="dialogueViewportStyle"
  >
    <text
      class="sr-only"
      role="heading"
      aria-level="1"
      >研讨</text
    >
    <MedState
      v-if="error && !sessions.length"
      variant="error"
      icon="retry"
      title="研讨加载失败"
      :description="error"
      action-label="重新加载"
      @action="load"
    />
    <MedState
      v-else-if="loading"
      variant="loading"
      icon="retry"
      title="正在加载研讨"
      description="正在同步会话、阶段证据和学习线索。"
    />

    <template v-else-if="creating">
      <scroll-view
        class="launch-scroll"
        scroll-y
      >
        <view class="launch-card">
          <view class="launch-heading">
            <view><text class="eyebrow">NEW DIALOGUE</text><text class="launch-title">开始一次病理研讨</text></view>
            <button
              v-if="sessions.length"
              class="text-action"
              @click="cancelCreate"
            >
              返回会话
            </button>
          </view>
          <view class="field-group">
            <text class="field-label">病理主题</text>
            <picker
              :range="topicOptions"
              range-key="label"
              :value="topicIndex"
              aria-label="选择病理主题"
              @change="selectTopic"
            >
              <view class="field-picker">{{ topicOptions[topicIndex]?.label || '请选择主题' }} ▾</view>
            </picker>
          </view>
          <view class="field-group">
            <view class="field-heading"
              ><text class="field-label">本次知识点</text><text class="field-hint">选择 1 个</text></view
            >
            <view class="point-grid">
              <button
                v-for="point in topicPoints"
                :key="point.code"
                class="choice-chip"
                :class="{ selected: selectedPointCodes.includes(point.code) }"
                :aria-pressed="selectedPointCodes.includes(point.code)"
                @click="togglePoint(point.code)"
              >
                {{ point.title }}
              </button>
            </view>
          </view>
          <view
            v-if="starter"
            class="starter-note"
          >
            <text class="field-label">从旧答疑带来的起始问题</text><text>{{ starter }}</text>
            <text class="field-hint">旧回答不会复制为阶段证据，你可以在会话中修改后发送。</text>
          </view>
          <text
            v-if="createError"
            class="field-error"
            role="alert"
            >{{ createError }}</text
          >
          <button
            class="primary-action"
            :disabled="!canCreate || submitting"
            @click="createDialogue"
          >
            {{ submitting ? '正在创建…' : '进入统一学习流程' }}
          </button>
          <text class="field-hint">自主研讨默认私有，不会进入教师待办或班级统计。</text>
        </view>
      </scroll-view>
    </template>

    <template v-else-if="session">
      <view
        class="dialogue-toolbar"
        aria-label="研讨上下文"
      >
        <view class="toolbar-heading">
          <view class="topic-field">
            <picker
              class="session-picker"
              :range="sessionOptions"
              :value="sessionIndex"
              aria-label="选择研讨主题"
              :disabled="sending"
              @change="selectSession"
            >
              <view class="session-selector">
                <view class="session-leading">
                  <view class="session-book-icon"><StudentNavIcon name="book" /></view>
                  <text class="session-topic">{{ sessionTopicLabel }}</text>
                </view>
                <text
                  class="selector-icon"
                  aria-hidden="true"
                  >⌄</text
                >
              </view>
            </picker>
          </view>
          <button
            class="new-action"
            :disabled="sending"
            hover-class="is-pressed"
            :hover-start-time="0"
            :hover-stay-time="80"
            @click="openCreate"
          >
            <text aria-hidden="true">＋</text><text>新研讨</text>
          </button>
        </view>
        <view class="toolbar-context">
          <text class="context-status"><text class="status-dot" />{{ sessionStatusLabel }}</text
          ><text>{{ sessionKindLabel }}</text
          ><text>当前阶段：{{ phaseLabels[currentPhase] }}</text>
        </view>
      </view>
      <scroll-view
        class="chat-scroll"
        scroll-y
        :scroll-into-view="scrollTarget"
        aria-live="polite"
        aria-label="PBL 研讨消息"
      >
        <view
          v-if="!messages.length"
          class="welcome"
        >
          <view class="welcome-title-row">
            <text
              class="welcome-accent"
              aria-hidden="true"
            />
            <text class="section-title">从你的疑问开始</text>
          </view>
          <text class="muted">默认使用探究引导，你可以在输入框左下角切换本轮回应方式。</text>
          <text class="field-hint">探究引导会通过提示和追问推进；直接讲解会先解释，再用一个问题确认理解。</text>
          <button
            class="example-card"
            aria-label="使用参考写法填入输入框"
            @click="useTemplate"
          >
            <view class="example-leading">
              <view class="example-icon"><StudentNavIcon name="chat" /></view>
              <text class="example-copy">我的疑问是：…… 我目前的理解或判断依据是：……</text>
            </view>
            <text
              class="example-arrow"
              aria-hidden="true"
              >›</text
            >
          </button>
          <view
            class="phase-steps"
            aria-label="统一学习流程"
          >
            <template
              v-for="(step, index) in phaseSteps"
              :key="step.key"
            >
              <text
                v-if="index"
                class="phase-connector"
                aria-hidden="true"
                >—</text
              >
              <view
                class="phase-step"
                :class="{ active: step.key === currentPhase }"
                ><text class="phase-index">{{ index + 1 }}</text
                ><text class="phase-label">{{ step.label }}</text></view
              >
            </template>
          </view>
        </view>
        <template
          v-for="(item, index) in messages"
          :key="item.id"
        >
          <PblConversationBoundary v-if="index === privateBoundaryIndex" />
          <view
            :id="`message-${index}`"
            class="message-row"
            :class="{ own: item.role === 'student' }"
          >
            <view
              v-if="item.role === 'assistant'"
              class="avatar"
              aria-label="AI 助教"
            >
              <view
                class="assistant-mark"
                aria-hidden="true"
              >
                <text class="assistant-mark__beam" />
                <text class="assistant-mark__beam" />
                <text class="assistant-mark__beam" />
              </view>
            </view>
            <view class="message-content">
              <selection
                v-if="item.role === 'assistant'"
                class="message-selection"
                aria-label="可选择并引用的助手回复"
                disable-context-menu
                @selectionchange="handleQuoteSelection($event, item.id)"
              >
                <text
                  :id="`assistant-message-${item.id}`"
                  class="bubble"
                  user-select
                  >{{ item.content }}</text
                >
              </selection>
              <text
                v-else
                class="bubble"
                >{{ item.content }}</text
              >
              <button
                v-if="activeQuoteSelection?.messageId === item.id"
                class="selection-quote-action"
                :style="activeQuoteSelection.style"
                aria-label="引用已选中的文字"
                hover-class="is-pressed"
                :hover-start-time="0"
                :hover-stay-time="80"
                @click.stop="applySelectedQuote"
              >
                引用
              </button>
              <view
                v-if="item.role === 'assistant'"
                class="message-tools"
                ><button
                  hover-class="is-pressed"
                  :hover-start-time="0"
                  :hover-stay-time="80"
                  @click="copyMessage(item.content)"
                >
                  复制
                </button></view
              >
            </view>
          </view>
        </template>
        <PblConversationBoundary v-if="showBoundaryAfterEvidence" />
        <view
          v-if="sending"
          class="message-row"
          role="status"
        >
          <view
            class="avatar"
            aria-label="AI 助教"
          >
            <view
              class="assistant-mark"
              aria-hidden="true"
            >
              <text class="assistant-mark__beam" />
              <text class="assistant-mark__beam" />
              <text class="assistant-mark__beam" />
            </view>
          </view>
          <view class="message-content"><text class="bubble typing">AI 正在回复…</text></view>
        </view>
        <view
          :id="`stream-end-${messages.length}-${sending ? 1 : 0}`"
          class="scroll-spacer"
        />
      </scroll-view>
      <view
        v-if="showCompletionActions"
        class="completion-actions"
      >
        <button
          v-if="submission?.teacherStatus === 'responded'"
          class="text-action"
          @click="openCreate"
        >
          按历史反馈新建研讨
        </button>
        <button
          class="text-action"
          @click="openPublishedPlan"
        >
          {{ participation?.learningRouteId ? '查看研讨学习计划' : '查看学习计划列表' }}
        </button>
      </view>
      <ChatComposer
        v-if="canSendMessage"
        v-model="draft"
        appearance="dialogue"
        :loading="sending"
        multiline
        :tone="retry ? 'retry' : 'primary'"
        :send-label="retry ? '重试' : '发送'"
        :send-aria-label="retry ? '重试发送' : composerSendAriaLabel"
        :input-label="composerInputLabel"
        :placeholder="composerPlaceholder"
        :error="sendError"
        @keyboard-height-change="handleKeyboardHeightChange"
        @send="send"
      >
        <template #quote>
          <view
            v-if="quotedMessage"
            class="composer-quote"
            aria-label="已引用的聊天内容"
          >
            <text
              class="composer-quote__mark"
              aria-hidden="true"
              >↳</text
            ><text class="composer-quote__text">{{ quotedMessagePreview }}</text
            ><button
              class="composer-quote__close"
              aria-label="移除引用"
              @click="quotedMessage = ''"
            >
              ×
            </button>
          </view>
        </template>
        <template #context>
          <view class="composer-context">
            <PblResponseStylePicker
              v-model="responseStyle"
              :disabled="sending"
              @change="changeResponseStyle"
            />
            <text
              v-if="isPrivateMode"
              class="privacy-context"
              >仅自己可见 · 不计入诊断</text
            >
          </view>
        </template>
      </ChatComposer>
      <view
        v-else
        class="locked-bar"
        role="alert"
      >
        <text>{{ composerLockedMessage }}</text>
      </view>
    </template>
    <view
      v-else
      class="empty-state"
    >
      <text class="section-title">还没有研讨会话</text
      ><text class="muted">你可以从一个病理问题开始，或等待教师创建课堂病例。</text>
      <button
        class="primary-action compact"
        @click="openCreate"
      >
        开始新研讨</button
      ><text class="field-hint">自主研讨默认私有，不会进入教师待办或班级统计。</text>
    </view>
    <StudentPrimaryNav active="pbl" />
  </view>
</template>

<script setup lang="ts">
import { onBackPress, onLoad, onShow } from '@dcloudio/uni-app'
import { computed, nextTick, ref } from 'vue'
import ChatComposer from '@/components/chat/ChatComposer.vue'
import PblConversationBoundary from '@/features/pbl/presentation/PblConversationBoundary.vue'
import PblResponseStylePicker from '@/features/pbl/presentation/PblResponseStylePicker.vue'
import MedState from '@/components/ui/MedState.vue'
import StudentNavIcon from '@/components/ui/StudentNavIcon.vue'
import StudentPrimaryNav from '@/components/ui/StudentPrimaryNav.vue'
import {
  createLearningDialogue,
  createPblMessageId,
  getLearningDialogue,
  getLearningDialogueSubmission,
  getLearningDialogues,
  sendPblMessage,
  type InteractionStyle,
  type PblMessage,
  type PblParticipation,
  type PblSession,
  type LearningDialogueSubmission,
} from '@/features/pbl/public'
import { getKnowledgeCatalog, type KnowledgePoint } from '@/features/learning/public'
import { goDetail, handleBackPress, ROUTES } from '@/platform/navigation'
import { invalidatePendingPblMessage, resolvePendingPblMessage, type PendingPblMessage } from './responseStyleState'
import { resolvePblConversationState } from './conversationState'

const loading = ref(true),
  sending = ref(false),
  submitting = ref(false),
  creating = ref(false),
  keyboardHeight = ref(0)
const error = ref(''),
  createError = ref(''),
  sendError = ref('')
const sessions = ref<PblSession[]>([]),
  points = ref<KnowledgePoint[]>([])
const sessionIndex = ref(0),
  topicIndex = ref(0)
const selectedPointCodes = ref<string[]>([]),
  responseStyle = ref<InteractionStyle>('guided')
const participation = ref<PblParticipation>(),
  messages = ref<PblMessage[]>([]),
  submission = ref<LearningDialogueSubmission>()
const draft = ref(''),
  starter = ref(''),
  requestedPointCode = ref(''),
  requestedSessionId = ref(''),
  createRequestId = ref(''),
  scrollTarget = ref(''),
  quotedMessage = ref('')
type QuoteSelectionRect = {
  left?: number
  top?: number
  x?: number
  y?: number
  width?: number
  height?: number
}
type QuoteSelectionEvent = {
  detail?: {
    isCollapsed?: boolean
    selectedString?: string
    firstRangeRect?: QuoteSelectionRect
  }
}
type ActiveQuoteSelection = {
  messageId: string
  text: string
  style: string
}
const activeQuoteSelection = ref<ActiveQuoteSelection>()
let quoteSelectionDismissTimer: ReturnType<typeof setTimeout> | undefined
const retry = ref<PendingPblMessage>()
const phaseSteps = [
  { key: 'problem_framing', label: '明确问题' },
  { key: 'hypothesis', label: '提出假设' },
  { key: 'evidence', label: '讨论证据' },
  { key: 'synthesis', label: '总结解释' },
] as const
const phaseLabels = {
  problem_framing: '明确问题',
  hypothesis: '提出假设',
  evidence: '讨论证据',
  synthesis: '总结解释',
  completed: '已完成',
}
const session = computed(() => sessions.value[sessionIndex.value])
const conversationState = computed(() =>
  resolvePblConversationState(session.value?.status, participation.value, messages.value),
)
const isPrivateMode = computed(() => conversationState.value.isPrivate)
const completionIntegrityError = computed(() => conversationState.value.integrityError)
const canSendMessage = computed(() => conversationState.value.canSend)
const privateBoundaryIndex = computed(() => conversationState.value.privateBoundaryIndex)
const showBoundaryAfterEvidence = computed(
  () => isPrivateMode.value && privateBoundaryIndex.value < 0 && !completionIntegrityError.value,
)
const composerInputLabel = computed(() => (isPrivateMode.value ? '输入仅自己可见的续问' : '输入你的病理学问题或理解'))
const composerPlaceholder = computed(() =>
  isPrivateMode.value ? '继续追问已经完成的研讨内容……' : '写下你的疑问、判断依据，或希望先讲解的内容……',
)
const composerSendAriaLabel = computed(() => (isPrivateMode.value ? '发送私人续问' : '提交研讨'))
const dialogueViewportStyle = computed(() =>
  keyboardHeight.value > 0 ? `height:calc(100vh - var(--window-top, 0px) - ${keyboardHeight.value}px)` : '',
)
const quotedMessagePreview = computed(() => quotedMessage.value.replace(/\s+/g, ' ').trim())
const composerLockedMessage = computed(() =>
  completionIntegrityError.value
    ? '完成边界暂时无法核验，请刷新后重试；若仍未恢复，请联系支持。'
    : '课堂已关闭，尚未完成的四阶段研讨不能继续发送。',
)
const showCompletionActions = computed(() => participation.value?.phaseStatus === 'completed')
const currentPhase = computed(() => session.value?.studentPhase || session.value?.phase || 'problem_framing')
const groupedTopics = computed(() => {
  const seen = new Set<string>()
  return points.value
    .filter((item) => !seen.has(item.systemCode) && Boolean(seen.add(item.systemCode)))
    .map((item) => ({ code: item.systemCode, label: item.systemLabel }))
})
const topicOptions = computed(() => groupedTopics.value)
const selectedTopic = computed(() => topicOptions.value[topicIndex.value]?.code || '')
const topicPoints = computed(() => points.value.filter((item) => item.systemCode === selectedTopic.value))
const canCreate = computed(() => selectedPointCodes.value.length === 1)
const sessionOptions = computed(() =>
  sessions.value.map((item) => `${topicTitle(item.topicCode)} · ${item.status === 'active' ? '进行中' : '已结束'}`),
)
const sessionKindLabel = computed(() => (session.value?.sessionKind === 'student_initiated' ? '主动研讨' : '课堂研讨'))
const sessionStatusLabel = computed(() =>
  isPrivateMode.value ? '证据已完成 · 私人续问' : session.value?.status === 'active' ? '进行中' : '已结束',
)
const sessionTopicLabel = computed(() => (session.value ? topicTitle(session.value.topicCode) : '未选择主题'))
const topicTitle = (code: string) => points.value.find((item) => item.systemCode === code)?.systemLabel ?? code
function openPublishedPlan() {
  const routeId = participation.value?.learningRouteId
  if (routeId) goDetail(ROUTES.studentLearningPlanDetail, { routeId })
  else goDetail(ROUTES.studentLearningPlans)
}
function applyRouteOptions(options?: Record<string, unknown>) {
  if (typeof options?.starter === 'string') starter.value = options.starter
  if (typeof options?.topicCode === 'string') requestedPointCode.value = options.topicCode
  if (typeof options?.dialogueId === 'string') requestedSessionId.value = options.dialogueId
  if (starter.value || requestedPointCode.value) creating.value = true
}
onLoad(applyRouteOptions)
onShow(() => {
  void load()
})
onBackPress(({ from }) => handleBackPress(from, ROUTES.studentPbl))
async function load() {
  loading.value = true
  error.value = ''
  try {
    const [page, catalog] = await Promise.all([getLearningDialogues(), getKnowledgeCatalog()])
    sessions.value = page.items
    points.value = catalog
    const requestedIndex = sessions.value.findIndex((item) => item.id === requestedSessionId.value)
    if (requestedSessionId.value && requestedIndex < 0) {
      error.value = '指定研讨记录暂不可用，请返回学习页后重试。'
      return
    }
    if (requestedIndex >= 0) sessionIndex.value = requestedIndex
    else if (sessionIndex.value >= sessions.value.length) sessionIndex.value = 0
    applyRequestedPoint()
    if (!sessions.value.length) creating.value = true
    if (!creating.value && session.value) {
      await loadDialogue(session.value.id)
    }
  } catch {
    error.value = '研讨加载失败，请检查网络后重新加载。'
  } finally {
    loading.value = false
  }
}
function applyRequestedPoint() {
  const point = points.value.find((item) => item.code === requestedPointCode.value)
  if (!point) return
  const index = topicOptions.value.findIndex((item) => item.code === point.systemCode)
  if (index >= 0) topicIndex.value = index
  selectedPointCodes.value = [point.code]
}
async function loadDialogue(id: string) {
  const value = await getLearningDialogue(id),
    index = sessions.value.findIndex((item) => item.id === id)
  if (index >= 0) sessions.value[index] = value.session
  participation.value = value.participation
  messages.value = value.participation?.messages ?? []
  responseStyle.value = value.participation?.interactionStyle ?? 'guided'
  submission.value = undefined
  if (value.session.sessionKind === 'student_initiated' && value.participation?.phaseStatus === 'completed') {
    try {
      submission.value = await getLearningDialogueSubmission(id)
    } catch {
      submission.value = undefined
    }
  }
  draft.value = starter.value && !messages.value.length ? starter.value : draft.value
  await refreshScroll()
}
function openCreate() {
  creating.value = true
  createError.value = ''
  createRequestId.value = ''
}
function cancelCreate() {
  creating.value = false
  createError.value = ''
  if (session.value) void loadDialogue(session.value.id)
}
function selectTopic(event: { detail: { value: string | number } }) {
  topicIndex.value = Number(event.detail.value)
  selectedPointCodes.value = []
}
function togglePoint(code: string) {
  if (selectedPointCodes.value.includes(code))
    selectedPointCodes.value = selectedPointCodes.value.filter((item) => item !== code)
  else selectedPointCodes.value = [code]
}
async function createDialogue() {
  if (!canCreate.value || submitting.value) return
  submitting.value = true
  createError.value = ''
  if (!createRequestId.value) createRequestId.value = createPblMessageId()
  try {
    const value = await createLearningDialogue({
      clientSessionId: createRequestId.value,
      interactionStyle: 'guided',
      goalPointCodes: selectedPointCodes.value,
    })
    sessions.value = [value.session, ...sessions.value.filter((item) => item.id !== value.session.id)]
    sessionIndex.value = 0
    participation.value = value.participation
    messages.value = value.participation?.messages ?? []
    responseStyle.value = value.participation?.interactionStyle ?? 'guided'
    draft.value = starter.value
    creating.value = false
    createRequestId.value = ''
    await refreshScroll()
  } catch {
    createError.value = '创建未确认，设置已保留。重试会沿用同一会话标识。'
  } finally {
    submitting.value = false
  }
}
async function selectSession(event: { detail: { value: string | number } }) {
  sessionIndex.value = Number(event.detail.value)
  participation.value = undefined
  messages.value = []
  draft.value = ''
  quotedMessage.value = ''
  activeQuoteSelection.value = undefined
  retry.value = undefined
  responseStyle.value = 'guided'
  sendError.value = ''
  if (!session.value) return
  try {
    await loadDialogue(session.value.id)
  } catch {
    sendError.value = '研讨记录加载失败，请重试。'
  }
}
function useTemplate() {
  draft.value = '我的疑问是：\n我目前的理解或判断依据是：'
}
function changeResponseStyle(next: InteractionStyle) {
  retry.value = invalidatePendingPblMessage(retry.value, next)
}
function copyMessage(content: string) {
  uni.setClipboardData({ data: content, success: () => uni.showToast({ title: '已复制', icon: 'success' }) })
}
function handleQuoteSelection(event: QuoteSelectionEvent, messageId: string) {
  if (quoteSelectionDismissTimer) clearTimeout(quoteSelectionDismissTimer)
  const detail = event.detail
  const selectedText = detail?.selectedString?.trim() ?? ''
  if (!detail || detail.isCollapsed || !selectedText) {
    quoteSelectionDismissTimer = setTimeout(() => {
      activeQuoteSelection.value = undefined
    }, 160)
    return
  }
  const rect = detail.firstRangeRect
  const systemInfo = uni.getSystemInfoSync()
  const actionWidth = 68
  const actionHeight = 36
  const selectionLeft = rect?.left ?? rect?.x ?? 12
  const selectionTop = rect?.top ?? rect?.y ?? 56
  const selectionWidth = rect?.width ?? 0
  const left = Math.max(
    12,
    Math.min(selectionLeft + selectionWidth / 2 - actionWidth / 2, systemInfo.windowWidth - actionWidth - 12),
  )
  const top = Math.max(12, selectionTop - actionHeight - 10)
  activeQuoteSelection.value = {
    messageId,
    text: selectedText,
    style: `left:${left}px;top:${top}px`,
  }
}
function applySelectedQuote() {
  if (!activeQuoteSelection.value?.text) return
  quotedMessage.value = activeQuoteSelection.value.text
  activeQuoteSelection.value = undefined
}
async function handleKeyboardHeightChange(height: number) {
  keyboardHeight.value = Math.max(0, height)
  if (keyboardHeight.value > 0) await refreshScroll()
}
async function refreshScroll() {
  scrollTarget.value = ''
  await nextTick()
  scrollTarget.value = `stream-end-${messages.value.length}-${sending.value ? 1 : 0}`
}
async function send() {
  if (!session.value || sending.value || !draft.value.trim()) return
  sending.value = true
  sendError.value = ''
  const content = draft.value.trim()
  retry.value = resolvePendingPblMessage(
    retry.value,
    {
      content,
      sessionId: session.value.id,
      interactionStyle: responseStyle.value,
    },
    createPblMessageId,
  )
  await refreshScroll()
  try {
    const result = await sendPblMessage(session.value.id, content, retry.value.id, retry.value.interactionStyle)
    participation.value = result
    messages.value = result.messages
    session.value.studentPhase = result.currentPhase
    session.value.phaseStatus = result.phaseStatus
    session.value.interactionStyle = result.interactionStyle
    session.value.evidenceLocked = result.evidenceLocked
    session.value.conversationMode = result.conversationMode
    session.value.completionSnapshotId = result.completionSnapshotId
    session.value.evidenceCompletedRevision = result.evidenceCompletedRevision
    responseStyle.value = result.interactionStyle
    draft.value = ''
    quotedMessage.value = ''
    activeQuoteSelection.value = undefined
    retry.value = undefined
  } catch {
    sendError.value = '提交未确认，内容已保留。点击重试会使用同一消息标识。'
  } finally {
    sending.value = false
    await refreshScroll()
  }
}
</script>

<style scoped>
.dialogue-page {
  --med-ink: #071a5a;
  --med-text: #35558d;
  --med-text-secondary: #506b9c;
  --med-muted: #7183a8;
  --med-clinical: #079baa;
  --med-brand-deep: #057b8b;
  --med-wash: #eaf9fb;
  --med-page: #ffffff;
  --med-border: #cdebf3;
  --med-divider: #e5f2f7;
  display: flex;
  height: calc(100vh - var(--window-top, 0px));
  min-height: 0;
  overflow: hidden;
  flex-direction: column;
  background: #fff;
}
.dialogue-page.is-dialogue {
  background: #fff;
}
.dialogue-page.is-keyboard-open :deep(.student-primary-nav) {
  display: none;
}
.launch-scroll {
  height: 0;
  padding: 28rpx 24rpx 180rpx;
  box-sizing: border-box;
  flex: 1;
}
.launch-card,
.welcome {
  display: flex;
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
  box-sizing: border-box;
  flex-direction: column;
}
.launch-card {
  padding: 28rpx;
  gap: 24rpx;
  background: var(--med-surface);
  border: 1rpx solid var(--med-border);
  border-radius: var(--med-radius-md);
}
.launch-heading,
.field-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
}
.launch-heading > view:first-child,
.field-group,
.starter-note {
  display: flex;
  flex-direction: column;
  gap: 14rpx;
}
.eyebrow {
  color: var(--med-clinical);
  font-size: 21rpx;
  font-weight: 750;
  letter-spacing: 3rpx;
}
.launch-title {
  margin-top: 8rpx;
  color: var(--med-ink);
  font-size: 34rpx;
  font-weight: 800;
  line-height: 1.35;
}
.section-title {
  color: var(--med-ink);
  font-size: 29rpx;
  font-weight: 750;
}
.field-label {
  color: var(--med-text);
  font-size: 26rpx;
  font-weight: 700;
}
.field-hint,
.muted {
  color: var(--med-muted);
  font-size: 24rpx;
  line-height: 1.6;
}
.field-error {
  color: var(--med-danger, #b42318);
  font-size: 24rpx;
  line-height: 1.55;
}
.field-picker {
  min-height: 80rpx;
  padding: 20rpx;
  box-sizing: border-box;
  color: var(--med-text);
  background: var(--med-page);
  border: 1rpx solid var(--med-border);
  border-radius: var(--med-radius-sm);
  font-size: 26rpx;
}
.point-grid,
.phase-steps {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
}
.choice-chip {
  width: auto;
  min-height: 70rpx;
  margin: 0;
  padding: 12rpx 20rpx;
  color: var(--med-text-secondary);
  background: var(--med-page);
  border: 1rpx solid var(--med-border);
  border-radius: 99rpx;
  font-size: 24rpx;
}
.choice-chip.selected {
  color: var(--med-clinical);
  background: var(--med-wash);
  border-color: var(--med-clinical);
}
.starter-note {
  padding: 20rpx;
  background: var(--med-wash);
  border-radius: var(--med-radius-sm);
  font-size: 25rpx;
  line-height: 1.6;
}
.primary-action {
  width: 100%;
  min-height: 88rpx;
  margin: 0;
  color: #fff;
  background: var(--med-clinical);
  border-radius: var(--med-radius-sm);
  font-size: 27rpx;
  font-weight: 700;
}
.primary-action[disabled] {
  opacity: 0.45;
}
.primary-action.compact {
  width: fit-content;
  padding: 0 30rpx;
}
.text-action,
.new-action {
  width: auto;
  margin: 0;
  color: var(--med-clinical);
  background: transparent;
  font-size: 24rpx;
}
.dialogue-toolbar {
  display: flex;
  padding: 16rpx 22rpx 18rpx;
  flex-direction: column;
  gap: 12rpx;
  background: rgba(255, 255, 255, 0.98);
  border-bottom: 1rpx solid var(--med-border);
  box-shadow: 0 8rpx 24rpx rgba(7, 155, 170, 0.035);
}
.toolbar-heading {
  display: flex;
  width: 100%;
  max-width: 800px;
  min-width: 0;
  margin: 0 auto;
  box-sizing: border-box;
  align-items: center;
  gap: 12rpx;
}
.topic-field {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
}
.session-picker {
  min-width: 0;
}
.session-selector {
  display: flex;
  min-height: 96rpx;
  padding: 0 14rpx 0 12rpx;
  box-sizing: border-box;
  align-items: center;
  justify-content: space-between;
  color: var(--med-ink);
  background: #fff;
  border: 1rpx solid var(--med-border);
  border-radius: 24rpx;
  box-shadow: 0 8rpx 24rpx rgba(12, 131, 164, 0.055);
  font-size: 29rpx;
  font-weight: 800;
  gap: 12rpx;
}
.session-leading {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 16rpx;
}
.session-book-icon {
  display: flex;
  width: 64rpx;
  height: 64rpx;
  flex: 0 0 64rpx;
  align-items: center;
  justify-content: center;
  color: var(--med-clinical);
  background: linear-gradient(145deg, #effbfc, #e2f6fa);
  border-radius: 20rpx;
}
.session-book-icon .student-nav-icon {
  width: 42rpx;
  height: 42rpx;
  font-size: 42rpx;
}
.session-topic {
  display: block;
  overflow: hidden;
  color: var(--med-ink);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.selector-icon {
  display: flex;
  width: 44rpx;
  height: 44rpx;
  flex: 0 0 44rpx;
  align-items: center;
  justify-content: center;
  color: var(--med-clinical);
  background: var(--med-wash);
  border-radius: 50%;
  font-size: 25rpx;
  line-height: 1;
}
.new-action {
  display: flex;
  min-height: 96rpx;
  padding: 0 22rpx;
  align-items: center;
  justify-content: center;
  gap: 4rpx;
  background: linear-gradient(135deg, #effbfd, #e5f6fa);
  border: 0;
  border-radius: 99rpx;
  font-size: 25rpx;
  font-weight: 700;
}
.toolbar-context {
  width: 100%;
  max-width: 800px;
  display: flex;
  margin: 0 auto;
  box-sizing: border-box;
  flex-wrap: wrap;
  align-items: center;
  color: var(--med-muted);
  color: var(--med-text-secondary);
  font-size: 22rpx;
  line-height: 1.45;
  gap: 9rpx;
}
.toolbar-context > text + text {
  padding-left: 10rpx;
  border-left: 1rpx solid var(--med-border);
}
.context-status {
  display: flex;
  align-items: center;
  color: var(--med-clinical);
  font-weight: 700;
  gap: 7rpx;
}
.status-dot {
  display: inline-block;
  width: 12rpx;
  height: 12rpx;
  background: currentColor;
  border-radius: 50%;
}
.chat-scroll {
  height: 0;
  min-height: 0;
  padding: 40rpx 24rpx 8rpx;
  box-sizing: border-box;
  flex: 1;
  background: #fff;
}
.welcome {
  margin-bottom: 24rpx;
  padding: 28rpx 22rpx 24rpx;
  gap: 13rpx;
  background: linear-gradient(135deg, #f2fbfd 0%, #f8fdfe 55%, #eef9fc 100%);
  border: 1rpx solid #edf8fa;
  border-radius: 28rpx;
  box-shadow: 0 10rpx 28rpx rgba(6, 129, 151, 0.055);
}
.welcome-title-row {
  display: flex;
  align-items: center;
  gap: 12rpx;
}
.welcome-title-row .section-title {
  font-size: 31rpx;
  font-weight: 800;
}
.welcome-accent {
  display: block;
  width: 8rpx;
  height: 38rpx;
  flex: 0 0 8rpx;
  background: linear-gradient(180deg, #12b8c6, #0696a7);
  border-radius: 99rpx;
}
.welcome .muted,
.welcome .field-hint {
  color: #7187ae;
  font-size: 23rpx;
  line-height: 1.7;
}
.example-card {
  display: flex;
  width: 100%;
  min-height: 82rpx;
  margin: 5rpx 0 0;
  padding: 10rpx 14rpx;
  box-sizing: border-box;
  align-items: center;
  justify-content: space-between;
  color: var(--med-text);
  background: rgba(255, 255, 255, 0.82);
  border: 1rpx solid #bfe9f0;
  border-radius: 18rpx;
  box-shadow: 0 5rpx 16rpx rgba(7, 155, 170, 0.035);
  font-size: 23rpx;
  text-align: left;
}
.example-leading {
  display: flex;
  min-width: 0;
  align-items: center;
  flex: 1;
  gap: 13rpx;
}
.example-icon {
  display: flex;
  width: 52rpx;
  height: 52rpx;
  flex: 0 0 52rpx;
  align-items: center;
  justify-content: center;
  color: #08a1b2;
  background: #e9f9fb;
  border-radius: 14rpx;
}
.example-icon .student-nav-icon {
  width: 31rpx;
  height: 31rpx;
  font-size: 31rpx;
}
.example-copy {
  display: block;
  min-width: 0;
  overflow: hidden;
  flex: 1;
  color: #607aa5;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.example-arrow {
  flex: none;
  padding-left: 12rpx;
  color: #7791b9;
  font-size: 30rpx;
  font-weight: 700;
}
.phase-steps {
  flex-wrap: nowrap;
  align-items: center;
  gap: 5rpx;
}
.phase-step {
  display: flex;
  min-width: 0;
  padding: 8rpx 11rpx;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: 8rpx;
  color: var(--med-muted);
  background: rgba(255, 255, 255, 0.76);
  border: 1rpx solid #ccecf2;
  border-radius: 99rpx;
  font-size: 20rpx;
  white-space: nowrap;
}
.phase-step.active {
  color: #fff;
  background: linear-gradient(135deg, #15b7c3, #078f9f);
  border-color: transparent;
  box-shadow: 0 5rpx 14rpx rgba(7, 143, 159, 0.18);
  font-weight: 700;
}
.phase-index {
  display: flex;
  width: 28rpx;
  height: 28rpx;
  align-items: center;
  justify-content: center;
  color: var(--med-clinical);
  background: #fff;
  border-radius: 50%;
  font-size: 18rpx;
}
.phase-step:not(.active) .phase-index {
  color: #35b7c4;
  background: #edf9fb;
}
.phase-label {
  overflow: hidden;
  text-overflow: ellipsis;
}
.phase-connector {
  flex: none;
  color: #65c7d2;
  font-size: 18rpx;
  line-height: 1;
}
.message-row {
  display: flex;
  width: 100%;
  max-width: 800px;
  margin: 38rpx auto;
  box-sizing: border-box;
  align-items: flex-start;
  gap: 12rpx;
}
.message-row.own {
  flex-direction: row-reverse;
}
.avatar {
  display: flex;
  width: 44rpx;
  height: 44rpx;
  flex: 0 0 44rpx;
  align-items: center;
  justify-content: center;
  color: #22b4c0;
  background: transparent;
  font-size: 30rpx;
  font-weight: 800;
  line-height: 1;
}
.assistant-mark {
  position: relative;
  display: block;
  width: 36rpx;
  height: 36rpx;
}
.assistant-mark__beam {
  position: absolute;
  top: 15.5rpx;
  left: 4rpx;
  display: block;
  width: 28rpx;
  height: 5rpx;
  background: currentColor;
  border-radius: 99rpx;
  transform-origin: center;
}
.assistant-mark__beam:nth-child(2) {
  transform: rotate(60deg);
}
.assistant-mark__beam:nth-child(3) {
  transform: rotate(120deg);
}
.message-content {
  position: relative;
  display: flex;
  min-width: 0;
  max-width: calc(100% - 56rpx);
  flex: 1;
  flex-direction: column;
  gap: 2rpx;
}
.message-selection {
  display: block;
  min-width: 0;
}
.own .message-content {
  max-width: 82%;
  flex: 0 1 auto;
  align-items: flex-end;
}
.bubble {
  display: block;
  padding: 2rpx 6rpx 0;
  color: #35558d;
  background: transparent;
  border: 0;
  border-radius: 0;
  font-size: 28rpx;
  line-height: 1.76;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
.own .bubble {
  padding: 20rpx 24rpx;
  color: var(--med-ink);
  background: linear-gradient(135deg, #edf9fc, #e7f4fb);
  border: 1rpx solid #d2ebf4;
  border-radius: 26rpx 26rpx 8rpx 26rpx;
  box-shadow: 0 7rpx 18rpx rgba(7, 155, 170, 0.045);
}
.selection-quote-action {
  position: fixed;
  z-index: 30;
  display: flex;
  width: 68px;
  min-height: 36px;
  margin: 0;
  padding: 0 16px;
  box-sizing: border-box;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: #087f90;
  border: 0;
  border-radius: 18px;
  box-shadow: 0 6px 18px rgba(3, 87, 103, 0.2);
  font-size: 14px;
  font-weight: 700;
  line-height: 1;
}
.composer-quote {
  display: flex;
  width: 100%;
  height: 58rpx;
  max-height: 58rpx;
  min-width: 0;
  margin: 0;
  padding: 0 8rpx;
  box-sizing: border-box;
  align-items: center;
  gap: 10rpx;
  color: var(--med-text);
  background: transparent;
  border: 0;
  border-bottom: 1rpx solid var(--med-border);
  font-size: 22rpx;
  overflow: hidden;
}
.composer-quote__mark {
  flex: none;
  color: var(--med-clinical);
  font-size: 26rpx;
  font-weight: 700;
}
.composer-quote__text {
  display: block;
  height: 32rpx;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
  flex: 1;
  line-height: 32rpx;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.composer-quote__close {
  display: flex;
  width: 48rpx;
  min-width: 48rpx;
  min-height: 48rpx;
  margin: 0;
  padding: 0;
  align-items: center;
  justify-content: center;
  color: var(--med-muted);
  background: transparent;
  border: 0;
  font-size: 28rpx;
}
.message-tools {
  display: flex;
  margin-left: -14rpx;
  gap: 0;
}
.message-tools button {
  width: auto;
  min-height: 88rpx;
  margin: 0;
  padding: 0 14rpx;
  color: #078f9f;
  background: transparent;
  font-size: 22rpx;
  font-weight: 650;
}
.secondary-action {
  width: fit-content;
  min-height: 76rpx;
  margin: 0;
  padding: 0 24rpx;
  color: var(--med-clinical);
  background: var(--med-wash);
  font-size: 24rpx;
}
.typing {
  color: var(--med-muted);
}
.scroll-spacer {
  height: 8rpx;
}
.completion-actions {
  display: flex;
  width: calc(100% - 44rpx);
  max-width: 800px;
  min-height: 68rpx;
  margin: 0 auto;
  padding: 8rpx 0;
  box-sizing: border-box;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8rpx 14rpx;
  background: #fff;
  border-top: 1rpx solid var(--med-border);
}
.completion-actions .text-action {
  min-height: 52rpx;
  padding: 0 6rpx;
  font-size: 21rpx;
}
.composer-context {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 12rpx;
}
.privacy-context {
  color: var(--med-muted);
  font-size: 20rpx;
  line-height: 1.4;
}
.locked-bar {
  display: flex;
  padding: 18rpx 24rpx calc(140rpx + env(safe-area-inset-bottom));
  flex-direction: column;
  gap: 14rpx;
  color: var(--med-text-secondary);
  background: var(--med-surface);
  border-top: 1rpx solid var(--med-border);
  font-size: 24rpx;
  line-height: 1.6;
}
.teacher-feedbacks {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
  padding: 16rpx 0;
  border-top: 1rpx solid var(--med-border);
}
.feedback-heading {
  color: var(--med-ink);
  font-weight: 700;
}
.teacher-feedback {
  color: var(--med-text);
  line-height: 1.6;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
.empty-state {
  display: flex;
  flex: 1;
  padding: 0 40rpx 180rpx;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 18rpx;
  text-align: center;
}
.dialogue-page :deep(.student-primary-nav) {
  background: rgba(255, 255, 255, 0.98);
  border-top-color: var(--med-border);
  box-shadow: 0 -8rpx 24rpx rgba(7, 91, 126, 0.035);
}
.dialogue-page :deep(.student-nav__item) {
  color: #7187b2;
}
.dialogue-page :deep(.student-nav__item.active) {
  color: #079baa;
}
@media screen and (min-width: 600px) {
  .launch-scroll {
    padding: 28px 32px 120px;
  }
  .chat-scroll {
    padding: 28px 32px 8px;
  }
  .launch-card {
    padding: 24px;
  }
  .launch-title {
    font-size: 24px;
  }
  .bubble {
    font-size: 16px;
  }
  .own .bubble {
    padding: 13px 16px;
  }
  .avatar {
    width: 28px;
    height: 28px;
    flex-basis: 28px;
    font-size: 19px;
  }
}
</style>
