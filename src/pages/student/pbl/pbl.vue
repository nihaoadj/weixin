<template>
  <view class="safe-page dialogue-page">
    <text
      class="sr-only"
      role="heading"
      aria-level="1"
      >研讨</text
    >
    <view
      class="account-bar"
      aria-label="研讨辅助操作"
    >
      <button @click="goDetail(ROUTES.studentHistory)">历史答疑</button>
      <button
        aria-label="退出学生账号"
        @click="logout"
      >
        退出
      </button>
    </view>
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
            <text class="field-label">关联班级（可选）</text>
            <picker
              v-if="classes.length"
              :range="classOptions"
              range-key="label"
              :value="classIndex"
              aria-label="选择所属班级"
              @change="selectClass"
            >
              <view class="field-picker">{{ classOptions[classIndex]?.label }} ▾</view>
            </picker>
            <text
              v-else
              class="field-hint"
              >本次自主研讨默认仅自己可见；完成后如需提交教师，再选择有效班级。</text
            >
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
              ><text class="field-label">本次知识点</text><text class="field-hint">选择 1–3 个</text></view
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
          <view class="field-group">
            <text class="field-label">沟通方式</text>
            <view class="style-grid">
              <button
                v-for="option in styleOptions"
                :key="option.value"
                class="style-card"
                :class="{ selected: createStyle === option.value }"
                :aria-pressed="createStyle === option.value"
                @click="createStyle = option.value"
              >
                <text class="style-title">{{ option.label }}</text
                ><text class="style-desc">{{ option.description }}</text>
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
            <text class="topic-label">当前主题</text>
            <picker
              class="session-picker"
              :range="sessionOptions"
              :value="sessionIndex"
              aria-label="选择研讨主题"
              :disabled="sending"
              @change="selectSession"
            >
              <view class="session-selector"
                ><text class="session-topic">{{ sessionTopicLabel }}</text
                ><text
                  class="selector-icon"
                  aria-hidden="true"
                  >⌄</text
                ></view
              >
            </picker>
          </view>
          <button
            class="new-action"
            :disabled="sending"
            @click="openCreate"
          >
            <text aria-hidden="true">＋</text><text>新研讨</text>
          </button>
        </view>
        <view class="toolbar-context">
          <text class="context-status"><text class="status-dot" />{{ sessionStatusLabel }}</text
          ><text>{{ sessionKindLabel }}</text
          ><text v-if="session.interactionStyle">沟通方式：{{ styleLabel }}</text
          ><text>当前阶段：{{ phaseLabels[currentPhase] }}</text>
        </view>
      </view>
      <scroll-view
        class="chat-scroll"
        scroll-y
        :scroll-into-view="scrollTarget"
        aria-live="polite"
        aria-label="研讨消息与阶段证据"
      >
        <view class="case-brief">
          <text class="eyebrow">{{ session.sessionKind === 'classroom' ? '课堂病例' : '研讨主题' }}</text>
          <text class="case-title">{{ sessionDisplayTitle }}</text>
          <text
            v-if="session.caseContext?.opening"
            class="muted"
            >{{ session.caseContext.opening.patient_intro }}</text
          >
          <text class="muted">学习目标：{{ session.goalPointCodes.map(pointTitle).join('、') }}</text>
        </view>
        <view
          v-if="!participation"
          class="start-card"
        >
          <text class="section-title">选择这次研讨的沟通方式</text>
          <text class="muted"
            >方式只影响 AI 如何与你沟通，之后都进入同一四阶段证据、教师审核和巩固流程；选定后不可更改。</text
          >
          <view class="style-grid">
            <button
              v-for="option in styleOptions"
              :key="option.value"
              class="style-card"
              :class="{ selected: startStyle === option.value }"
              :aria-pressed="startStyle === option.value"
              @click="startStyle = option.value"
            >
              <text class="style-title">{{ option.label }}</text
              ><text class="style-desc">{{ option.description }}</text>
            </button>
          </view>
          <text
            v-if="sendError"
            class="field-error"
            >{{ sendError }}</text
          >
          <button
            class="primary-action compact"
            :disabled="submitting"
            @click="startClassroom"
          >
            {{ submitting ? '正在开始…' : '确认并开始' }}
          </button>
        </view>
        <view
          v-else-if="!messages.length"
          class="welcome"
        >
          <text class="section-title">从你的疑问开始</text><text class="muted">{{ welcomeDescription }}</text>
          <button
            class="example-card"
            aria-label="使用参考写法填入输入框"
            @click="useTemplate"
          >
            <text>{{
              session.interactionStyle === 'direct' ? '我想先了解：……' : '我的疑问是：…… 我目前的判断依据是：……'
            }}</text
            ><text aria-hidden="true">›</text>
          </button>
          <view
            class="phase-steps"
            aria-label="统一学习流程"
          >
            <view
              v-for="(step, index) in phaseSteps"
              :key="step.key"
              class="phase-step"
              :class="{ active: step.key === currentPhase }"
              ><text class="phase-index">{{ index + 1 }}</text
              ><text>{{ step.label }}</text></view
            >
          </view>
        </view>
        <view
          v-for="(item, index) in messages"
          :id="`message-${index}`"
          :key="item.id"
          class="message-row"
          :class="{ own: item.role === 'student' }"
        >
          <view class="avatar">{{ item.role === 'student' ? '我' : 'AI' }}</view>
          <view class="message-content">
            <text class="bubble">{{ item.content }}</text>
            <view
              v-if="item.role === 'assistant'"
              class="message-tools"
              ><button @click="copyMessage(item.content)">复制</button
              ><button @click="continueFrom(item.content)">继续问</button></view
            >
          </view>
        </view>
        <view
          v-if="diagnostic"
          id="dialogue-diagnostic"
          class="diagnostic-card"
        >
          <text class="section-title">{{
            diagnostic.diagnosticStatus === 'ready' ? '已形成学习线索' : '继续完成阶段证据'
          }}</text>
          <text
            v-if="diagnostic.phaseEvidenceSummary"
            class="muted"
            >阶段依据：{{ diagnostic.phaseEvidenceSummary }}</text
          >
          <text
            v-if="diagnostic.phaseMissingElements?.length"
            class="muted"
            >还需补充：{{ diagnostic.phaseMissingElements.join('；') }}</text
          >
          <text v-if="diagnostic.followUpQuestion">理解检验：{{ diagnostic.followUpQuestion }}</text>
          <text v-if="diagnostic.diagnosticStatus === 'unavailable'">本次没有形成可核对诊断，请重试或请教师帮助。</text>
          <view
            v-for="gap in diagnostic.knowledgeGaps"
            :key="gap.id"
            class="diagnostic-item"
            ><text>{{ pointTitle(gap.point_code) }}：{{ gap.summary }}</text
            ><text class="muted">依据：{{ gap.evidence_summary }}</text></view
          >
          <view
            v-for="issue in diagnostic.reasoningIssues"
            :key="issue.id"
            class="diagnostic-item"
            ><text>{{ issue.summary }}</text
            ><text class="muted">下一步：{{ issue.improvement }}</text></view
          >
          <text class="muted">{{ diagnostic.safetyNotice }}</text>
          <button
            v-if="diagnostic.diagnosticStatus === 'ready'"
            class="secondary-action"
            @click="goPrimary(ROUTES.studentLearning)"
          >
            查看后续学习
          </button>
        </view>
        <view
          v-if="sending"
          class="message-row"
          role="status"
          ><view class="avatar">AI</view><view class="bubble typing"><text>正在分析阶段证据…</text></view></view
        >
        <view
          :id="`stream-end-${messages.length}-${sending ? 1 : 0}`"
          class="scroll-spacer"
        />
      </scroll-view>
      <ChatComposer
        v-if="participation && session.status === 'active' && session.phaseStatus !== 'completed'"
        v-model="draft"
        :loading="sending"
        multiline
        :tone="retry ? 'retry' : 'primary'"
        :send-label="retry ? '重试' : '发送'"
        :send-aria-label="retry ? '重试提交研讨' : '提交研讨'"
        input-label="输入你的病理学问题或理解"
        :placeholder="session.interactionStyle === 'direct' ? '我想先了解……' : '我的疑问是……我目前的判断依据是……'"
        :error="sendError"
        @send="send"
      />
      <view
        v-else-if="session.phaseStatus === 'completed'"
        class="locked-bar"
      >
        <text>四阶段研讨已完成，输入已关闭。你现在可以回到知识点继续补学和练习。</text>
        <template v-if="session.sessionKind === 'student_initiated'">
          <text
            v-if="submission?.submission"
            class="submission-state"
            >{{ submissionStatusText }} 后续自主练习不会自动外发。</text
          >
          <view
            v-if="submission?.feedbacks?.length"
            class="teacher-feedbacks"
            aria-label="教师反馈"
          >
            <text class="feedback-heading">教师反馈</text>
            <view
              v-for="item in submission.feedbacks"
              :key="item.id"
              class="teacher-feedback"
              ><text>{{ feedbackActionLabel(item.actionType) }}</text
              ><text>{{ item.body }}</text
              ><text
                v-if="item.createdAt"
                class="field-hint"
                >{{ item.createdAt }}</text
              ></view
            >
            <text
              v-if="submission.nextAction"
              class="field-hint"
              >下一步：{{ submission.nextAction }}</text
            >
            <button
              v-if="submission.teacherStatus === 'responded'"
              class="text-action"
              @click="openCreate"
            >
              按反馈开启新研讨
            </button>
            <button
              v-if="submission.teacherStatus === 'task_published'"
              class="text-action"
              @click="openPublishedPlan"
            >
              查看正式任务
            </button>
          </view>
          <text
            v-else-if="!submission?.submission"
            class="submission-state"
            >自主研讨仍是私有的。提交后，教师只能查看本轮完成快照。</text
          >
          <picker
            v-if="!submission?.submission && classes.length"
            :range="classOptions"
            range-key="label"
            :value="classIndex"
            aria-label="选择提交研讨的班级"
            @change="selectClass"
            ><view class="field-picker">提交至：{{ classOptions[classIndex]?.label }} ▾</view></picker
          >
          <button
            v-if="!submission?.submission && classes.length"
            class="secondary-action"
            :disabled="submitting || !submission"
            @click="submitToTeacher"
          >
            {{ submitting ? '正在提交…' : '预览后提交教师' }}
          </button>
          <text
            v-else-if="!submission?.submission"
            class="field-hint"
            >你尚未加入有效班级，仍可继续个人学习。</text
          >
        </template>
        <button
          class="secondary-action"
          @click="goPrimary(ROUTES.studentLearning)"
        >
          查看后续学习
        </button>
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
      ><text class="field-hint">自主研讨默认私有；完成后可选择提交教师。</text>
    </view>
    <StudentPrimaryNav active="pbl" />
  </view>
</template>

<script setup lang="ts">
import { onLoad, onShow } from '@dcloudio/uni-app'
import { computed, nextTick, ref } from 'vue'
import ChatComposer from '@/components/chat/ChatComposer.vue'
import MedState from '@/components/ui/MedState.vue'
import StudentPrimaryNav from '@/components/ui/StudentPrimaryNav.vue'
import {
  createLearningDialogue,
  createPblMessageId,
  getLearningDialogue,
  getLearningDialogueSubmission,
  getLearningDialogues,
  getStudentClasses,
  sendPblMessage,
  submitLearningDialogue,
  startLearningDialogue,
  type InteractionStyle,
  type PblDiagnostic,
  type PblMessage,
  type PblParticipation,
  type PblSession,
  type LearningDialogueSubmission,
  type StudentClassSummary,
} from '@/features/pbl/public'
import { getKnowledgeCatalog, type KnowledgePoint } from '@/features/learning/public'
import { logout } from '@/features/identity/public'
import { goDetail, goPrimary, ROUTES } from '@/platform/navigation'

const loading = ref(true),
  sending = ref(false),
  submitting = ref(false),
  creating = ref(false)
const error = ref(''),
  createError = ref(''),
  sendError = ref('')
const sessions = ref<PblSession[]>([]),
  classes = ref<StudentClassSummary[]>([]),
  points = ref<KnowledgePoint[]>([])
const sessionIndex = ref(0),
  classIndex = ref(0),
  topicIndex = ref(0)
const selectedPointCodes = ref<string[]>([]),
  createStyle = ref<InteractionStyle>('guided'),
  startStyle = ref<InteractionStyle>('guided')
const participation = ref<PblParticipation>(),
  messages = ref<PblMessage[]>([]),
  diagnostic = ref<PblDiagnostic>(),
  submission = ref<LearningDialogueSubmission>()
const draft = ref(''),
  starter = ref(''),
  requestedPointCode = ref(''),
  requestedSessionId = ref(''),
  createRequestId = ref(''),
  scrollTarget = ref('')
const retry = ref<{ id: string; content: string; sessionId: string }>()
const styleOptions: Array<{ value: InteractionStyle; label: string; description: string }> = [
  { value: 'guided', label: '引导我思考', description: 'AI 用追问和提示帮助你逐步形成判断。' },
  { value: 'direct', label: '先直接解释', description: 'AI 先回答，再用理解检验推进同一学习流程。' },
]
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
const submissionStatusText = computed(() => {
  const status = submission.value?.teacherStatus
  return status === 'responded'
    ? '教师已发送反馈。'
    : status === 'task_published'
      ? '教师已反馈并发布正式任务。'
      : status === 'closed'
        ? '教师已给出本轮结论。'
        : '本轮已提交给教师，等待审阅。'
})
const currentPhase = computed(() => session.value?.studentPhase || session.value?.phase || 'problem_framing')
const classOptions = computed(() => classes.value.map((item) => ({ label: `${item.name} · ${item.code}` })))
const groupedTopics = computed(() => {
  const seen = new Set<string>()
  return points.value
    .filter((item) => !seen.has(item.systemCode) && Boolean(seen.add(item.systemCode)))
    .map((item) => ({ code: item.systemCode, label: item.systemLabel }))
})
const topicOptions = computed(() => groupedTopics.value)
const selectedTopic = computed(() => topicOptions.value[topicIndex.value]?.code || '')
const topicPoints = computed(() => points.value.filter((item) => item.systemCode === selectedTopic.value))
const canCreate = computed(() => selectedPointCodes.value.length >= 1 && selectedPointCodes.value.length <= 3)
const sessionOptions = computed(() =>
  sessions.value.map((item) => `${topicTitle(item.topicCode)} · ${item.status === 'active' ? '进行中' : '已结束'}`),
)
const sessionKindLabel = computed(() => (session.value?.sessionKind === 'student_initiated' ? '主动研讨' : '课堂研讨'))
const styleLabel = computed(() => (session.value?.interactionStyle === 'direct' ? '先直接解释' : '引导我思考'))
const sessionStatusLabel = computed(() => (session.value?.status === 'active' ? '进行中' : '已结束'))
const sessionTopicLabel = computed(() => (session.value ? topicTitle(session.value.topicCode) : '未选择主题'))
const sessionDisplayTitle = computed(() => {
  if (!session.value || session.value.sessionKind === 'student_initiated') return sessionTopicLabel.value
  return session.value.caseContext?.title || sessionTopicLabel.value
})
const welcomeDescription = computed(() =>
  session.value?.interactionStyle === 'direct'
    ? '写下你的问题。助手会先解释，再请你完成与当前阶段对应的理解检验。'
    : '写下你的疑问和当前想法。助手会通过追问帮助你逐步补齐判断依据。',
)
const topicTitle = (code: string) => points.value.find((item) => item.systemCode === code)?.systemLabel ?? code
const pointTitle = (code: string) => points.value.find((item) => item.code === code)?.title ?? code
const feedbackActionLabel = (action: string) =>
  (
    ({
      feedback_only: '教师反馈',
      task_published: '反馈并发布任务',
      closed: '教师关闭',
      follow_up: '补充支持',
    }) as Record<string, string>
  )[action] || '教师反馈'
function openPublishedPlan() {
  const planId = submission.value?.feedbacks?.find((item) => item.planId)?.planId
  if (planId) goDetail(ROUTES.studentLearningPlan, { planId })
  else goPrimary(ROUTES.studentLearning)
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
async function load() {
  loading.value = true
  error.value = ''
  try {
    const [page, classValues, catalog] = await Promise.all([
      getLearningDialogues(),
      getStudentClasses(),
      getKnowledgeCatalog(),
    ])
    sessions.value = page.items
    classes.value = classValues
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
  diagnostic.value = value.participation?.diagnostic
  submission.value = undefined
  if (value.session.sessionKind === 'student_initiated' && value.participation?.currentPhase === 'completed') {
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
function selectClass(event: { detail: { value: string | number } }) {
  classIndex.value = Number(event.detail.value)
}
function selectTopic(event: { detail: { value: string | number } }) {
  topicIndex.value = Number(event.detail.value)
  selectedPointCodes.value = []
}
function togglePoint(code: string) {
  if (selectedPointCodes.value.includes(code))
    selectedPointCodes.value = selectedPointCodes.value.filter((item) => item !== code)
  else if (selectedPointCodes.value.length < 3) selectedPointCodes.value = [...selectedPointCodes.value, code]
}
async function createDialogue() {
  const selectedClass = classes.value[classIndex.value]
  if (!canCreate.value || submitting.value) return
  submitting.value = true
  createError.value = ''
  if (!createRequestId.value) createRequestId.value = createPblMessageId()
  try {
    const value = await createLearningDialogue({
      clientSessionId: createRequestId.value,
      classId: selectedClass?.id,
      interactionStyle: createStyle.value,
      goalPointCodes: selectedPointCodes.value,
    })
    sessions.value = [value.session, ...sessions.value.filter((item) => item.id !== value.session.id)]
    sessionIndex.value = 0
    participation.value = value.participation
    messages.value = value.participation?.messages ?? []
    diagnostic.value = value.participation?.diagnostic
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
async function submitToTeacher() {
  const selectedClass = classes.value[classIndex.value]
  if (!session.value || !submission.value || !selectedClass || submitting.value) return
  submitting.value = true
  sendError.value = ''
  try {
    submission.value = await submitLearningDialogue({
      id: session.value.id,
      snapshotId: submission.value.snapshotId,
      classId: selectedClass.id,
      clientSubmissionId: createPblMessageId(),
    })
  } catch {
    sendError.value = '提交未确认，请重新预览后重试。'
  } finally {
    submitting.value = false
  }
}
async function startClassroom() {
  if (!session.value || submitting.value) return
  submitting.value = true
  sendError.value = ''
  try {
    const value = await startLearningDialogue(session.value.id, startStyle.value)
    sessions.value[sessionIndex.value] = value.session
    participation.value = value.participation
    messages.value = value.participation?.messages ?? []
    diagnostic.value = value.participation?.diagnostic
  } catch {
    sendError.value = '沟通方式未能确认，请重试。'
  } finally {
    submitting.value = false
  }
}
async function selectSession(event: { detail: { value: string | number } }) {
  sessionIndex.value = Number(event.detail.value)
  participation.value = undefined
  messages.value = []
  diagnostic.value = undefined
  draft.value = ''
  retry.value = undefined
  sendError.value = ''
  if (!session.value) return
  try {
    await loadDialogue(session.value.id)
  } catch {
    sendError.value = '研讨记录加载失败，请重试。'
  }
}
function useTemplate() {
  draft.value = session.value?.interactionStyle === 'direct' ? '我想先了解：' : '我的疑问是：\n我目前的判断依据是：'
}
function copyMessage(content: string) {
  uni.setClipboardData({ data: content, success: () => uni.showToast({ title: '已复制', icon: 'success' }) })
}
function continueFrom(content: string) {
  draft.value = `关于“${content.slice(0, 36)}${content.length > 36 ? '…' : ''}”，我还想问：`
}
async function refreshScroll() {
  await nextTick()
  scrollTarget.value = `stream-end-${messages.value.length}-${sending.value ? 1 : 0}`
}
async function send() {
  if (!session.value || !participation.value || sending.value || !draft.value.trim()) return
  sending.value = true
  sendError.value = ''
  const content = draft.value.trim()
  if (retry.value?.content !== content || retry.value.sessionId !== session.value.id)
    retry.value = { id: createPblMessageId(), content, sessionId: session.value.id }
  await refreshScroll()
  try {
    const result = await sendPblMessage(session.value.id, content, retry.value.id)
    participation.value = result
    messages.value = result.messages
    diagnostic.value = result.diagnostic
    session.value.studentPhase = result.currentPhase
    session.value.phaseStatus = result.phaseStatus
    session.value.interactionStyle = result.interactionStyle
    if (result.currentPhase === 'completed' && session.value.sessionKind === 'student_initiated') {
      try {
        submission.value = await getLearningDialogueSubmission(session.value.id)
      } catch {
        submission.value = undefined
      }
    }
    draft.value = ''
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
  display: flex;
  height: calc(100vh - var(--window-top, 0px));
  min-height: 0;
  overflow: hidden;
  flex-direction: column;
  background: var(--med-page);
}
.account-bar {
  display: flex;
  min-height: 58rpx;
  padding: 6rpx 22rpx;
  align-items: center;
  justify-content: flex-end;
  gap: 8rpx;
  background: var(--med-surface);
  border-bottom: 1rpx solid var(--med-border);
}
.account-bar button {
  width: auto;
  min-height: 48rpx;
  margin: 0;
  padding: 0 12rpx;
  color: var(--med-muted);
  background: transparent;
  font-size: 21rpx;
}
.launch-scroll {
  height: 0;
  padding: 28rpx 24rpx 180rpx;
  box-sizing: border-box;
  flex: 1;
}
.launch-card,
.start-card,
.case-brief,
.welcome,
.diagnostic-card {
  display: flex;
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
  box-sizing: border-box;
  flex-direction: column;
}
.launch-card,
.start-card,
.diagnostic-card {
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
.launch-title,
.case-title {
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
.style-grid,
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
.choice-chip.selected,
.style-card.selected {
  color: var(--med-clinical);
  background: var(--med-wash);
  border-color: var(--med-clinical);
}
.style-card {
  display: flex;
  min-width: 260rpx;
  margin: 0;
  padding: 22rpx;
  align-items: flex-start;
  flex: 1;
  flex-direction: column;
  gap: 8rpx;
  color: var(--med-text);
  background: var(--med-page);
  border: 1rpx solid var(--med-border);
  border-radius: var(--med-radius-md);
  text-align: left;
}
.style-title {
  font-size: 27rpx;
  font-weight: 750;
}
.style-desc {
  color: var(--med-muted);
  font-size: 23rpx;
  line-height: 1.5;
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
  padding: 18rpx 24rpx 16rpx;
  flex-direction: column;
  gap: 14rpx;
  background: var(--med-surface);
  border-bottom: 1rpx solid var(--med-border);
}
.toolbar-heading {
  display: flex;
  width: 100%;
  min-width: 0;
  align-items: flex-end;
  gap: 20rpx;
}
.topic-field {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 5rpx;
}
.topic-label {
  color: var(--med-muted);
  font-size: 20rpx;
  font-weight: 700;
  letter-spacing: 1rpx;
}
.session-picker {
  min-width: 0;
}
.session-selector {
  display: flex;
  min-height: 62rpx;
  padding: 0 2rpx 6rpx;
  align-items: center;
  justify-content: space-between;
  color: var(--med-clinical);
  border-bottom: 3rpx solid var(--med-clinical);
  font-size: 30rpx;
  font-weight: 800;
  gap: 12rpx;
}
.session-topic {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.selector-icon {
  display: flex;
  width: 38rpx;
  height: 38rpx;
  flex: 0 0 38rpx;
  align-items: center;
  justify-content: center;
  color: var(--med-surface);
  background: var(--med-clinical);
  border-radius: 50%;
  font-size: 25rpx;
  line-height: 1;
}
.toolbar-context {
  width: 100%;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  color: var(--med-muted);
  font-size: 21rpx;
  gap: 10rpx;
}
.toolbar-context > text + text {
  padding-left: 12rpx;
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
  padding: 26rpx 24rpx;
  box-sizing: border-box;
  flex: 1;
}
.case-brief {
  margin-bottom: 22rpx;
  gap: 10rpx;
}
.start-card,
.welcome {
  margin-bottom: 24rpx;
}
.welcome {
  gap: 14rpx;
}
.example-card {
  display: flex;
  width: 100%;
  min-height: 82rpx;
  margin: 4rpx 0 0;
  padding: 20rpx;
  align-items: center;
  justify-content: space-between;
  color: var(--med-text);
  background: var(--med-surface);
  border: 1rpx solid var(--med-border);
  border-radius: var(--med-radius-md);
  font-size: 24rpx;
  text-align: left;
}
.phase-step {
  display: flex;
  padding: 9rpx 14rpx;
  align-items: center;
  gap: 8rpx;
  color: var(--med-muted);
  background: var(--med-surface);
  border: 1rpx solid var(--med-border);
  border-radius: 99rpx;
  font-size: 22rpx;
}
.phase-step.active {
  color: #fff;
  background: var(--med-clinical);
  border-color: var(--med-clinical);
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
  width: 60rpx;
  height: 60rpx;
  flex: 0 0 60rpx;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: var(--med-clinical);
  border-radius: var(--med-radius-sm);
  font-size: 22rpx;
  font-weight: 700;
}
.own .avatar {
  background: var(--med-ink);
}
.message-content {
  display: flex;
  min-width: 0;
  max-width: 78%;
  margin: 0 14rpx;
  flex-direction: column;
  gap: 8rpx;
}
.own .message-content {
  align-items: flex-end;
}
.bubble {
  display: block;
  padding: 20rpx 22rpx;
  color: var(--med-text);
  background: var(--med-surface);
  border: 1rpx solid var(--med-border);
  border-radius: 6rpx var(--med-radius-md) var(--med-radius-md);
  font-size: 27rpx;
  line-height: 1.65;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
.own .bubble {
  color: #fff;
  background: var(--med-ink);
  border-color: var(--med-ink);
  border-radius: var(--med-radius-md) 6rpx var(--med-radius-md) var(--med-radius-md);
}
.message-tools {
  display: flex;
  gap: 10rpx;
}
.message-tools button {
  width: auto;
  min-height: 54rpx;
  margin: 0;
  padding: 4rpx 14rpx;
  color: var(--med-clinical);
  background: transparent;
  font-size: 21rpx;
}
.diagnostic-card {
  margin-top: 24rpx;
  font-size: 25rpx;
  line-height: 1.6;
}
.diagnostic-item {
  display: flex;
  flex-direction: column;
  gap: 5rpx;
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
  height: 28rpx;
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
@media screen and (min-width: 600px) {
  .launch-scroll,
  .chat-scroll {
    padding: 28px 32px 120px;
  }
  .launch-card,
  .start-card,
  .diagnostic-card {
    padding: 24px;
  }
  .launch-title,
  .case-title {
    font-size: 24px;
  }
  .bubble {
    padding: 14px 16px;
    font-size: 16px;
  }
  .avatar {
    width: 40px;
    height: 40px;
    flex-basis: 40px;
    font-size: 14px;
  }
}
</style>
