<template>
  <view class="safe-page page"
    ><MedState
      v-if="accessDenied"
      variant="error"
      icon="history"
      title="学生身份已变化"
      description="当前病例与作答内容已清除。请使用当前学生账号重新进入训练。"
    /><template v-else
      ><view
        v-if="attempt"
        class="case-heading"
        ><view class="case-meta"
          ><text class="eyebrow">模拟接诊 · {{ attempt.opening.setting || '病理病例研讨' }}</text
          ><text class="stage-count">阶段 {{ currentStageNumber }} / {{ caseStages.length }}</text></view
        ><text class="title">{{ attempt.opening.chiefComplaint }}</text
        ><view class="case-caption"
          ><text class="patient-intro">{{ attempt.opening.patientIntro || '虚拟患者' }}</text
          ><text class="caption-divider">·</text><text>合成教学病例，不构成诊疗建议</text></view
        ><view
          class="progress"
          aria-label="病例训练进度"
          ><view
            v-for="(item, index) in caseStages"
            :key="item.id"
            class="progress-step"
            :class="{ active: item.id === attempt.currentStage, done: done(item.id) }"
            ><text class="progress-index">{{ done(item.id) ? '✓' : index + 1 }}</text
            ><text class="progress-label">{{ item.label }}</text></view
          ></view
        ></view
      ><MedState
        v-if="error"
        icon="retry"
        title="训练加载失败"
        :description="error"
        :action-label="id ? '重新加载' : returnLabel"
        :secondary-action-label="id ? returnLabel : ''"
        @action="id ? load() : back()"
        @secondary-action="back"
      /><view
        v-if="attempt"
        class="stage-content"
        ><template v-if="attempt.currentStage === 'history'"
          ><text
            class="sr-only"
            role="heading"
            aria-level="2"
            >与虚拟患者交流</text
          ><view class="history-workspace"
            ><view class="dialogue-panel"
              ><view class="dialogue-header"
                ><view class="patient-profile"
                  ><view class="patient-avatar"><text>患</text><text class="presence-dot" /></view
                  ><view class="patient-copy"
                    ><text class="patient-name">虚拟患者</text
                    ><text class="patient-state">只回应你已经询问的内容</text></view
                  ></view
                ><text class="reply-count">{{ patientReplyCount }} 次回应</text></view
              ><scroll-view
                class="dialogue-stream"
                scroll-y
                scroll-with-animation
                :scroll-into-view="lastMessageAnchor"
                role="log"
                aria-live="polite"
                aria-label="虚拟患者对话记录"
                ><view
                  v-if="!attempt.messages.length"
                  id="case-message-welcome"
                  class="message assistant"
                  ><text class="message-avatar">患</text
                  ><view class="message-body"
                    ><text class="message-role">虚拟患者</text
                    ><text class="message-bubble">你好，请问你想先了解哪些不适和经过？</text></view
                  ></view
                ><view
                  v-for="message in attempt.messages"
                  :id="messageAnchor(message.id)"
                  :key="message.id"
                  class="message"
                  :class="message.role"
                  ><text class="message-avatar">{{ message.role === 'user' ? '你' : '患' }}</text
                  ><view class="message-body"
                    ><text class="message-role">{{ message.role === 'user' ? '你的提问' : '虚拟患者' }}</text
                    ><text class="message-bubble">{{ message.content }}</text></view
                  ></view
                ><view
                  v-if="sending"
                  id="case-message-typing"
                  class="message assistant is-typing"
                  role="status"
                  ><text class="message-avatar">患</text
                  ><view class="message-body"
                    ><text class="message-role">虚拟患者正在回应</text
                    ><view class="typing-bubble"><text /><text /><text /></view></view></view></scroll-view
              ><view class="question-guide"
                ><text class="guide-label">可以这样继续问</text
                ><view class="prompt-list"
                  ><button
                    v-for="prompt in promptSuggestions"
                    :key="prompt"
                    class="prompt-action"
                    :disabled="sending"
                    :aria-label="`填写问题：${prompt}`"
                    @click="usePrompt(prompt)"
                  >
                    {{ prompt }}
                  </button></view
                ></view
              ><view class="question-composer"
                ><view class="composer-row"
                  ><input
                    v-model="question"
                    aria-label="输入向患者提出的问题"
                    placeholder="输入一个具体问题…"
                    :disabled="sending"
                    confirm-type="send"
                    @confirm="ask"
                  /><button
                    class="ask-action"
                    :disabled="sending || !question.trim()"
                    @click="ask"
                  >
                    {{ sending ? '询问中' : '发送' }}
                  </button></view
                ><text class="composer-tip">一次询问一个线索，更容易判断回答的意义。</text></view
              ></view
            ><view
              class="history-notes"
              :class="{ expanded: notesExpanded }"
              ><button
                class="notes-toggle"
                :aria-expanded="notesExpanded"
                aria-controls="history-note-fields"
                @click="toggleNotes"
              >
                <view class="notes-copy"
                  ><text class="notes-kicker">临床笔记</text><text class="notes-title">整理问诊依据</text></view
                ><view class="notes-state"
                  ><text>{{ historyNoteStatus }}</text
                  ><text
                    class="notes-arrow"
                    :class="{ expanded: notesExpanded }"
                    >⌄</text
                  ></view
                ></button
              ><view
                v-if="notesExpanded"
                id="history-note-fields"
                class="notes-fields"
                ><text class="notes-hint">将对话提炼为症状、时间进程、关键阳性与阴性信息。</text
                ><label class="field-label"
                  ><text>病史小结</text
                  ><textarea
                    v-model="summary"
                    aria-label="病史小结"
                    placeholder="用自己的话概括本次问诊"
                  /></label
                ><label class="field-label"
                  ><text>关键发现</text
                  ><input
                    v-model="keyFindingsText"
                    aria-label="关键发现"
                    placeholder="例如：发热 3 天、咳嗽、无胸痛" /></label></view></view></view></template
        ><template v-else-if="attempt.currentStage === 'problem_representation'"
          ><text class="section">问题表征</text
          ><textarea
            v-model="summary"
            placeholder="患者特征—时间进程—核心阳性/阴性—主要问题"
          /></template
        ><template v-else-if="attempt.currentStage === 'differential'"
          ><text class="section">鉴别诊断卡片（至少两张）</text
          ><view
            v-for="(item, index) in differentialItems"
            :key="index"
            class="answer-card"
            ><input
              v-model="item.diagnosis"
              placeholder="诊断"
            /><textarea
              v-model="item.supportingEvidence"
              placeholder="支持证据"
            /><textarea
              v-model="item.opposingEvidence"
              placeholder="反对证据"
            /></view
          ><button
            class="secondary"
            @click="addDifferential"
          >
            新增诊断卡
          </button></template
        ><template v-else-if="attempt.currentStage === 'tests'"
          ><text class="section">检查决策卡片</text
          ><view
            v-for="(item, index) in testItems"
            :key="index"
            class="answer-card"
            ><input
              v-model="item.testName"
              placeholder="检查名称" /><textarea
              v-model="item.rationale"
              placeholder="检查理由" /><input
              v-model="item.priority"
              placeholder="necessary / optional / avoid" /></view
          ><button
            class="secondary"
            @click="addTest"
          >
            新增检查卡
          </button></template
        ><template v-else-if="attempt.currentStage === 'management'"
          ><text class="section">初步处置卡片</text
          ><view
            v-for="(item, index) in managementItems"
            :key="index"
            class="answer-card"
            ><input
              v-model="item.action"
              placeholder="行动"
            /><textarea
              v-model="item.rationale"
              placeholder="处置理由"
            /></view
          ><button
            class="secondary"
            @click="addManagement"
          >
            新增处置卡</button
          ><textarea
            v-model="safetyText"
            placeholder="安全考虑，以逗号分隔"
          /></template
        ><template v-else
          ><text class="section">五阶段已完成</text
          ><button
            class="primary"
            :loading="completing"
            :disabled="completing"
            @click="complete"
          >
            生成训练报告
          </button></template
        ></view
      ><view
        v-if="attempt && attempt.currentStage !== 'completed'"
        class="bottom"
        ><button
          class="primary"
          :loading="submitting"
          :disabled="submitting"
          @click="handlePrimaryAction"
        >
          {{ primaryActionLabel }}
        </button></view
      ></template
    ></view
  >
</template>
<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { onBackPress, onLoad, onShow } from '@dcloudio/uni-app'
import MedState from '@/components/ui/MedState.vue'
import { getSession, requireRole } from '@/features/identity/public'
import { backOrRoute, goReplace, handleBackPress, ROUTES } from '@/platform/navigation'
import {
  completeCaseAttemptAsync,
  getCaseAttemptAsync,
  sendPatientMessageAsync,
  submitCaseStageAsync,
} from '@/features/training/public'
import { caseStages, type CaseAttempt, type StageAnswer } from '@/types/case'
const attempt = ref<CaseAttempt>()
const error = ref('')
const question = ref('')
const summary = ref('')
const keyFindingsText = ref('')
const notesExpanded = ref(false)
const safetyText = ref('')
const differentialItems = ref<Array<{ diagnosis: string; supportingEvidence: string; opposingEvidence: string }>>([
  { diagnosis: '', supportingEvidence: '', opposingEvidence: '' },
  { diagnosis: '', supportingEvidence: '', opposingEvidence: '' },
])
const testItems = ref<Array<{ testName: string; rationale: string; priority: 'necessary' | 'optional' | 'avoid' }>>([
  { testName: '', rationale: '', priority: 'necessary' },
])
const managementItems = ref<Array<{ action: string; rationale: string }>>([{ action: '', rationale: '' }])
const sending = ref(false)
const submitting = ref(false)
const completing = ref(false)
const accessDenied = ref(false)
const promptSuggestions = ['症状从什么时候开始？', '症状是怎样变化的？', '还伴随哪些不适？']
let id = ''
let studentIdentity: string | undefined
let identityInitialized = false
let pageContextVersion = 0
let initialShowPending = false

function isCurrentStudentPage(contextVersion: number, identity: string): boolean {
  const session = getSession()
  return (
    contextVersion === pageContextVersion &&
    identityInitialized &&
    !accessDenied.value &&
    studentIdentity === identity &&
    session?.role === 'student' &&
    session.openid === identity
  )
}

function clearStudentCaseData() {
  pageContextVersion += 1
  attempt.value = undefined
  error.value = ''
  question.value = ''
  summary.value = ''
  keyFindingsText.value = ''
  notesExpanded.value = false
  safetyText.value = ''
  differentialItems.value = [
    { diagnosis: '', supportingEvidence: '', opposingEvidence: '' },
    { diagnosis: '', supportingEvidence: '', opposingEvidence: '' },
  ]
  testItems.value = [{ testName: '', rationale: '', priority: 'necessary' }]
  managementItems.value = [{ action: '', rationale: '' }]
  sending.value = false
  submitting.value = false
  completing.value = false
  id = ''
}

function denyStudentCasePage() {
  clearStudentCaseData()
  identityInitialized = false
  accessDenied.value = true
}
const returnLabel = '返回病例列表'
const stageLabel = (stage: string) => caseStages.find((i) => i.id === stage)?.label || '报告'
const currentStageNumber = computed(() => {
  if (!attempt.value || attempt.value.currentStage === 'completed') return caseStages.length
  return caseStages.findIndex((item) => item.id === attempt.value!.currentStage) + 1
})
const patientReplyCount = computed(
  () => attempt.value?.messages.filter((message) => message.role === 'assistant').length || 0,
)
const historyNoteStatus = computed(() => {
  if (summary.value.trim() || keyFindingsText.value.trim()) return '已记录'
  return notesExpanded.value ? '编辑中' : '待整理'
})
const primaryActionLabel = computed(() => {
  if (attempt.value?.currentStage === 'history' && !notesExpanded.value) return '整理本次问诊'
  return `提交${stageLabel(attempt.value?.currentStage || '')}`
})
const lastMessageAnchor = computed(() => {
  if (sending.value) return 'case-message-typing'
  const messages = attempt.value?.messages || []
  return messages.length ? messageAnchor(messages[messages.length - 1].id) : 'case-message-welcome'
})
const done = (stage: string) =>
  attempt.value
    ? caseStages.findIndex((i) => i.id === stage) < caseStages.findIndex((i) => i.id === attempt.value!.currentStage)
    : false
function messageAnchor(messageId: string) {
  return `case-message-${messageId.replace(/[^a-zA-Z0-9_-]/g, '-')}`
}
function usePrompt(prompt: string) {
  if (!sending.value) question.value = prompt
}
async function revealHistoryNotes() {
  notesExpanded.value = true
  await nextTick()
  uni.pageScrollTo({ selector: '#history-note-fields', duration: 180 })
}
function toggleNotes() {
  if (notesExpanded.value) {
    notesExpanded.value = false
    return
  }
  void revealHistoryNotes()
}
function handlePrimaryAction() {
  if (attempt.value?.currentStage === 'history' && !notesExpanded.value) {
    void revealHistoryNotes()
    return
  }
  void submit()
}
function addDifferential() {
  if (differentialItems.value.length < 12)
    differentialItems.value.push({ diagnosis: '', supportingEvidence: '', opposingEvidence: '' })
}
function addTest() {
  if (testItems.value.length < 12) testItems.value.push({ testName: '', rationale: '', priority: 'necessary' })
}
function addManagement() {
  if (managementItems.value.length < 12) managementItems.value.push({ action: '', rationale: '' })
}
async function load() {
  const identity = studentIdentity
  const contextVersion = pageContextVersion
  if (!id || !identity || accessDenied.value) return
  try {
    const value = await getCaseAttemptAsync(id)
    if (!isCurrentStudentPage(contextVersion, identity)) return
    attempt.value = value
    if (!attempt.value) error.value = '训练不存在或已不可用'
  } catch (e) {
    if (isCurrentStudentPage(contextVersion, identity)) error.value = e instanceof Error ? e.message : '请重试'
  }
}
function back() {
  if (hasUnsavedInput()) {
    uni.showModal({
      title: '离开本次训练？',
      content: '当前填写内容尚未提交，离开后不会保留。',
      confirmText: '离开',
      success: ({ confirm }) => {
        if (confirm) leaveTraining()
      },
    })
    return
  }
  leaveTraining()
}
function leaveTraining() {
  backOrRoute(ROUTES.studentCases)
}
function hasUnsavedInput() {
  return Boolean(
    question.value.trim() ||
    summary.value.trim() ||
    keyFindingsText.value.trim() ||
    safetyText.value.trim() ||
    differentialItems.value.some(
      (item) => item.diagnosis.trim() || item.supportingEvidence.trim() || item.opposingEvidence.trim(),
    ) ||
    testItems.value.some((item) => item.testName.trim() || item.rationale.trim()) ||
    managementItems.value.some((item) => item.action.trim() || item.rationale.trim()),
  )
}
async function ask() {
  if (!question.value.trim()) return
  const identity = studentIdentity
  const contextVersion = pageContextVersion
  if (!identity || accessDenied.value) return
  sending.value = true
  try {
    await sendPatientMessageAsync(id, question.value)
    if (!isCurrentStudentPage(contextVersion, identity)) return
    question.value = ''
    await load()
  } finally {
    if (isCurrentStudentPage(contextVersion, identity)) sending.value = false
  }
}
function answer(): StageAnswer {
  const stage = attempt.value!.currentStage
  if (stage === 'history')
    return {
      stageId: stage,
      summary: summary.value,
      keyFindings: keyFindingsText.value
        .split(/[，,]/)
        .map((i) => i.trim())
        .filter(Boolean),
    }
  if (stage === 'problem_representation') return { stageId: stage, summary: summary.value }
  if (stage === 'differential')
    return {
      stageId: stage,
      items: differentialItems.value
        .filter((item) => item.diagnosis.trim())
        .map((item) => ({
          diagnosis: item.diagnosis.trim(),
          supportingEvidence: item.supportingEvidence
            .split(/[，,]/)
            .map((value) => value.trim())
            .filter(Boolean),
          opposingEvidence: item.opposingEvidence
            .split(/[，,]/)
            .map((value) => value.trim())
            .filter(Boolean),
        })),
    }
  if (stage === 'tests')
    return {
      stageId: stage,
      items: testItems.value
        .filter((item) => item.testName.trim())
        .map((item) => ({
          testName: item.testName.trim(),
          rationale: item.rationale.trim() || '用于评估',
          priority: item.priority,
        })),
    }
  return {
    stageId: 'management',
    items: managementItems.value
      .filter((item) => item.action.trim())
      .map((item) => ({
        action: item.action.trim(),
        rationale: item.rationale.trim() || '保障安全',
      })),
    safetyConsiderations: safetyText.value.split(/[，,]/).filter(Boolean),
  }
}
async function submit() {
  const identity = studentIdentity
  const contextVersion = pageContextVersion
  if (!identity || accessDenied.value) return
  submitting.value = true
  try {
    await submitCaseStageAsync(id, answer())
    if (!isCurrentStudentPage(contextVersion, identity)) return
    summary.value = ''
    keyFindingsText.value = ''
    safetyText.value = ''
    differentialItems.value = [
      { diagnosis: '', supportingEvidence: '', opposingEvidence: '' },
      { diagnosis: '', supportingEvidence: '', opposingEvidence: '' },
    ]
    testItems.value = [{ testName: '', rationale: '', priority: 'necessary' }]
    managementItems.value = [{ action: '', rationale: '' }]
    notesExpanded.value = false
    await load()
  } catch (e) {
    if (isCurrentStudentPage(contextVersion, identity))
      uni.showToast({ title: e instanceof Error ? e.message : '提交失败', icon: 'none' })
  } finally {
    if (isCurrentStudentPage(contextVersion, identity)) submitting.value = false
  }
}
async function complete() {
  if (completing.value) return
  const identity = studentIdentity
  const contextVersion = pageContextVersion
  if (!identity || accessDenied.value) return
  completing.value = true
  try {
    await completeCaseAttemptAsync(id)
    if (!isCurrentStudentPage(contextVersion, identity)) return
    goReplace(ROUTES.studentCaseReport, { attemptId: id })
  } catch (e) {
    if (isCurrentStudentPage(contextVersion, identity))
      uni.showToast({ title: e instanceof Error ? e.message : '生成训练结果失败', icon: 'none' })
  } finally {
    if (isCurrentStudentPage(contextVersion, identity)) completing.value = false
  }
}
onLoad((query) => {
  const session = getSession()
  if (!requireRole('student') || session?.role !== 'student' || !session.openid) {
    denyStudentCasePage()
    return
  }
  studentIdentity = session.openid
  identityInitialized = true
  accessDenied.value = false
  id = String(query?.id || '')
  initialShowPending = true
  void load()
})

onShow(() => {
  if (accessDenied.value) return
  const session = getSession()
  if (
    !requireRole('student') ||
    session?.role !== 'student' ||
    !session.openid ||
    !identityInitialized ||
    studentIdentity !== session.openid
  ) {
    denyStudentCasePage()
    return
  }
  if (initialShowPending) {
    initialShowPending = false
    return
  }
  void load()
})

onBackPress(({ from }) => {
  if (from === 'navigateBack') return false
  if (sending.value || submitting.value || completing.value) {
    uni.showToast({ title: '正在保存训练内容，请稍候', icon: 'none' })
    return true
  }
  if (hasUnsavedInput()) {
    back()
    return true
  }
  return handleBackPress(from, ROUTES.studentCases)
})
</script>
<style scoped>
.page {
  padding: 24rpx 24rpx 190rpx;
}
.case-heading,
.stage-content {
  display: flex;
  width: 100%;
  max-width: 920px;
  margin: 0 auto;
  flex-direction: column;
}
.case-heading {
  padding-bottom: 22rpx;
  gap: 12rpx;
  border-bottom: 1rpx solid var(--med-border);
}
.stage-content {
  padding-top: 24rpx;
  gap: 26rpx;
}
.case-meta,
.case-caption,
.dialogue-header,
.patient-profile,
.notes-toggle,
.notes-state {
  display: flex;
  align-items: center;
}
.case-meta,
.dialogue-header,
.notes-toggle {
  justify-content: space-between;
}
.eyebrow {
  color: var(--med-clinical);
  font-family: var(--med-font-utility);
  font-size: 20rpx;
  font-weight: 750;
  letter-spacing: 2rpx;
}
.stage-count,
.reply-count {
  color: var(--med-muted);
  font-family: var(--med-font-utility);
  font-size: 20rpx;
}
.title {
  color: var(--med-ink);
  font-family: var(--med-font-display);
  font-size: 34rpx;
  font-weight: 800;
  line-height: 1.35;
}
.case-caption {
  flex-wrap: wrap;
  gap: 8rpx;
  color: var(--med-muted);
  font-size: 22rpx;
}
.classroom-return-note,
.context-warning {
  color: #315a75;
  font-size: 22rpx;
  line-height: 1.5;
}
.context-warning {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12rpx;
  color: #8c5519;
}
.context-warning button {
  flex: none;
  color: var(--med-brand);
  background: transparent;
  font-size: 22rpx;
}
.patient-intro {
  color: var(--med-text-secondary);
  font-weight: 700;
}
.caption-divider {
  color: var(--med-border);
}
.progress {
  display: flex;
  padding-top: 12rpx;
  align-items: flex-start;
}
.progress-step {
  position: relative;
  display: flex;
  min-width: 0;
  flex: 1;
  align-items: center;
  flex-direction: column;
  gap: 8rpx;
  text-align: center;
}
.progress-step:not(:last-child)::after {
  position: absolute;
  z-index: 0;
  top: 15rpx;
  right: calc(-50% + 18rpx);
  left: calc(50% + 18rpx);
  height: 1rpx;
  background: var(--med-border);
  content: '';
}
.progress-index {
  position: relative;
  z-index: 1;
  display: flex;
  width: 30rpx;
  height: 30rpx;
  align-items: center;
  justify-content: center;
  color: var(--med-muted);
  background: var(--med-page);
  border: 1rpx solid var(--med-border);
  border-radius: 50%;
  font-family: var(--med-font-utility);
  font-size: 17rpx;
  font-weight: 700;
}
.progress-label {
  max-width: 100%;
  color: var(--med-muted);
  font-size: 19rpx;
  line-height: 1.3;
}
.progress-step.active .progress-index {
  color: var(--med-surface);
  background: var(--med-clinical);
  border-color: var(--med-clinical);
}
.progress-step.active .progress-label {
  color: var(--med-clinical);
  font-weight: 800;
}
.progress-step.done .progress-index {
  color: var(--med-clinical);
  background: var(--med-wash);
  border-color: var(--med-clinical);
}
.progress-step.done::after {
  background: var(--med-clinical);
}
.section {
  color: var(--med-ink);
  font-size: 28rpx;
  font-weight: 800;
}
.history-workspace,
.dialogue-panel,
.patient-copy,
.question-guide,
.question-composer,
.history-notes,
.notes-copy,
.notes-fields,
.field-label {
  display: flex;
  flex-direction: column;
}
.history-workspace {
  gap: 22rpx;
}
.dialogue-panel {
  overflow: hidden;
  background: var(--med-surface);
  border-top: 4rpx solid var(--med-clinical);
  border-bottom: 1rpx solid var(--med-border);
}
.dialogue-header {
  min-height: 76rpx;
  padding: 14rpx 18rpx;
  box-sizing: border-box;
  border-bottom: 1rpx solid var(--med-divider);
}
.patient-profile {
  min-width: 0;
  gap: 12rpx;
}
.patient-avatar {
  position: relative;
  display: flex;
  width: 46rpx;
  height: 46rpx;
  flex: 0 0 46rpx;
  align-items: center;
  justify-content: center;
  color: var(--med-surface);
  background: var(--med-clinical);
  border-radius: 50%;
  font-size: 19rpx;
  font-weight: 800;
}
.presence-dot {
  position: absolute;
  right: -2rpx;
  bottom: -2rpx;
  width: 12rpx;
  height: 12rpx;
  background: var(--med-accent);
  border: 3rpx solid var(--med-surface);
  border-radius: 50%;
}
.patient-copy {
  min-width: 0;
  gap: 2rpx;
}
.patient-name {
  color: var(--med-ink);
  font-size: 23rpx;
  font-weight: 800;
}
.patient-state {
  overflow: hidden;
  color: var(--med-muted);
  font-size: 19rpx;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.dialogue-stream {
  height: 620rpx;
  padding: 24rpx 20rpx 8rpx;
  box-sizing: border-box;
  background: var(--med-page);
}
.message {
  display: flex;
  max-width: 88%;
  margin-bottom: 22rpx;
  align-items: flex-start;
  gap: 12rpx;
}
.message.user {
  margin-left: auto;
  align-self: flex-end;
  flex-direction: row-reverse;
}
.message-avatar {
  display: flex;
  width: 42rpx;
  height: 42rpx;
  flex: 0 0 42rpx;
  align-items: center;
  justify-content: center;
  color: var(--med-clinical);
  background: var(--med-wash);
  border: 1rpx solid var(--med-border);
  border-radius: 50%;
  font-size: 18rpx;
  font-weight: 800;
}
.message.user .message-avatar {
  color: var(--med-surface);
  background: var(--med-ink);
  border-color: var(--med-ink);
}
.message-body {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 5rpx;
}
.message.user .message-body {
  align-items: flex-end;
}
.message-role {
  color: var(--med-muted);
  font-size: 20rpx;
  font-weight: 700;
}
.message-bubble {
  display: block;
  padding: 17rpx 20rpx;
  color: var(--med-text);
  background: var(--med-surface);
  border: 1rpx solid var(--med-border);
  border-radius: 4rpx var(--med-radius-sm) var(--med-radius-sm);
  font-size: 25rpx;
  line-height: 1.6;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
.message.user {
  color: var(--med-surface);
}
.message.user .message-bubble {
  color: var(--med-surface);
  background: var(--med-ink);
  border-color: var(--med-ink);
  border-radius: var(--med-radius-sm) 6rpx var(--med-radius-sm) var(--med-radius-sm);
}
.typing-bubble {
  display: flex;
  height: 58rpx;
  padding: 0 20rpx;
  align-items: center;
  gap: 7rpx;
  background: var(--med-surface);
  border: 1rpx solid var(--med-border);
  border-radius: 4rpx var(--med-radius-sm) var(--med-radius-sm);
}
.typing-bubble text {
  width: 7rpx;
  height: 7rpx;
  background: var(--med-clinical);
  border-radius: 50%;
  animation: patient-thinking 900ms ease-in-out infinite alternate;
}
.typing-bubble text:nth-child(2) {
  animation-delay: 150ms;
}
.typing-bubble text:nth-child(3) {
  animation-delay: 300ms;
}
.question-guide {
  padding: 16rpx 20rpx 2rpx;
  gap: 10rpx;
  border-top: 1rpx solid var(--med-divider);
}
.guide-label {
  color: var(--med-muted);
  font-size: 19rpx;
  font-weight: 700;
}
.prompt-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8rpx;
}
.prompt-action {
  width: auto;
  min-height: 52rpx;
  margin: 0;
  padding: 0 14rpx;
  color: var(--med-clinical);
  background: transparent;
  border: 1rpx solid var(--med-border);
  border-radius: 6rpx;
  font-size: 19rpx;
  line-height: 50rpx;
}
.question-composer {
  padding: 14rpx 20rpx 20rpx;
  gap: 8rpx;
}
.composer-row {
  display: flex;
  padding: 6rpx;
  align-items: center;
  gap: 8rpx;
  background: var(--med-surface);
  border: 1rpx solid var(--med-border);
  border-radius: var(--med-radius-sm);
}
.composer-row input {
  min-width: 0;
  min-height: 66rpx;
  flex: 1;
  padding: 0 14rpx;
  border: 0;
  background: transparent;
}
.ask-action {
  width: auto;
  min-height: 62rpx;
  margin: 0;
  padding: 0 22rpx;
  color: var(--med-surface);
  background: var(--med-clinical);
  border-radius: 8rpx;
  font-size: 21rpx;
  font-weight: 800;
  line-height: 62rpx;
}
.ask-action[disabled] {
  color: var(--med-muted);
  background: var(--med-divider);
  opacity: 1;
}
.composer-tip {
  color: var(--med-muted);
  font-size: 18rpx;
  line-height: 1.5;
}
.history-notes {
  border-top: 1rpx solid var(--med-border);
  border-bottom: 1rpx solid var(--med-border);
}
.notes-toggle {
  width: 100%;
  min-height: 92rpx;
  margin: 0;
  padding: 18rpx 4rpx;
  color: var(--med-text);
  background: transparent;
  border-radius: 0;
  line-height: 1.3;
  text-align: left;
}
.notes-copy {
  gap: 3rpx;
}
.notes-kicker {
  color: var(--med-clinical);
  font-family: var(--med-font-utility);
  font-size: 17rpx;
  font-weight: 800;
  letter-spacing: 2rpx;
}
.notes-title {
  color: var(--med-ink);
  font-size: 24rpx;
  font-weight: 800;
}
.notes-state {
  flex: 0 0 auto;
  gap: 10rpx;
  color: var(--med-muted);
  font-size: 20rpx;
}
.notes-arrow {
  display: inline-block;
  color: var(--med-clinical);
  font-size: 28rpx;
  transition: transform var(--med-motion-settle) var(--med-ease-out);
}
.notes-arrow.expanded {
  transform: rotate(180deg);
}
.notes-fields {
  padding: 18rpx 0 8rpx 20rpx;
  gap: 18rpx;
  border-left: 3rpx solid var(--med-wash);
}
.notes-hint {
  color: var(--med-muted);
  font-size: 20rpx;
  line-height: 1.55;
}
.field-label {
  gap: 8rpx;
  color: var(--med-text-secondary);
  font-size: 21rpx;
  font-weight: 700;
}
.answer-card {
  display: flex;
  padding: 16rpx;
  flex-direction: column;
  gap: 12rpx;
  background: var(--med-surface);
  border: 1rpx solid var(--med-border);
  border-radius: var(--med-radius-sm);
}
input,
textarea {
  width: auto;
  min-height: 80rpx;
  padding: 16rpx;
  box-sizing: border-box;
  color: var(--med-text);
  border: 1rpx solid var(--med-border);
  border-radius: var(--med-radius-sm);
  background: var(--med-surface);
  font-size: 25rpx;
}
textarea {
  min-height: 140rpx;
}
.primary,
.secondary {
  height: 78rpx;
  line-height: 78rpx;
  color: var(--med-surface);
  background: var(--med-clinical);
}
.secondary {
  color: var(--med-clinical);
  background: var(--med-wash);
}
.bottom {
  position: fixed;
  z-index: 10;
  right: 0;
  bottom: 0;
  left: 0;
  padding: 14rpx 24rpx calc(14rpx + env(safe-area-inset-bottom));
  background: var(--med-page);
  border-top: 1rpx solid var(--med-border);
}
.bottom .primary {
  width: 100%;
  max-width: 920px;
  margin: 0 auto;
  border-radius: var(--med-radius-sm);
}
@media screen and (min-width: 600px) {
  .page {
    padding: 28px 32px 110px;
  }
  .title {
    font-size: 26px;
  }
  .stage-content {
    padding-top: 28px;
  }
  .history-workspace {
    display: grid;
    grid-template-columns: minmax(0, 1.7fr) minmax(260px, 0.75fr);
    align-items: start;
    gap: 32px;
  }
  .dialogue-stream {
    height: 460px;
    padding: 24px 22px 8px;
  }
  .history-notes {
    position: sticky;
    top: 24px;
  }
  .message-bubble,
  input,
  textarea {
    font-size: 16px;
  }
  .message-avatar {
    width: 34px;
    height: 34px;
    flex-basis: 34px;
    font-size: 13px;
  }
}
@keyframes patient-thinking {
  from {
    opacity: 0.35;
    transform: translateY(1rpx);
  }
  to {
    opacity: 1;
    transform: translateY(-2rpx);
  }
}
@media (prefers-reduced-motion: reduce) {
  .typing-bubble text {
    animation: none;
  }
  .notes-arrow {
    transition: none;
  }
}
</style>
