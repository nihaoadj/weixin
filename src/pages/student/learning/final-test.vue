<template>
  <view
    class="page"
    :style="{ paddingTop: `${navigationOffset}px` }"
  >
    <view
      class="page-navbar"
      :style="{ paddingTop: `${statusBarHeight}px`, height: `${navigationOffset + 2}px` }"
    >
      <image
        class="navbar-art"
        src="/static/final-test-background.svg"
        mode="widthFix"
        aria-hidden="true"
      />
      <view
        class="navbar-row"
        :style="{ height: `${navigationHeight}px` }"
      >
        <button
          class="nav-back"
          aria-label="返回学习计划"
          @click="back"
        >
          <view class="back-chevron" />
        </button>
        <text class="navbar-title">最终测试</text>
      </view>
    </view>
    <image
      class="page-art"
      src="/static/final-test-background.svg"
      mode="widthFix"
      aria-hidden="true"
    />
    <view
      v-if="grading && !test"
      class="grading-state"
      role="status"
    >
      <text class="grading-title">{{ grading.retryAllowed ? '判分暂未完成' : '正在综合判分' }}</text>
      <text>{{
        grading.retryAllowed ? '答案已提交，请重试判分。' : '答案已提交，简答题正按开放时冻结的参考答案判分。'
      }}</text>
      <text
        v-if="error"
        class="inline-error"
        role="alert"
        >{{ error }}</text
      >
      <button
        v-if="grading.retryAllowed"
        class="secondary"
        :disabled="submitting"
        @click="retryGrading"
      >
        重新判分
      </button>
    </view>
    <view
      v-else-if="error && !test"
      class="state error"
      role="alert"
      ><text>{{ error }}</text
      ><button @click="load">重新加载</button></view
    >
    <view
      v-else-if="loading && !test"
      class="state"
      role="status"
      >正在准备最终测试…</view
    >
    <template v-else-if="test">
      <view class="intro">
        <image
          class="hero-art"
          src="/static/final-test-hero.png"
          mode="aspectFit"
          aria-hidden="true"
        />
        <text class="eyebrow">学习路线最终测试</text>
        <text class="title">{{ test.title }}</text>
        <text class="muted">{{ questionSummary }} · 已保存 {{ answeredCount }}/{{ test.questions.length }} 题</text>
        <view
          v-if="test.reviewKind === 'ai_direct'"
          class="review-note"
        >
          <text class="review-symbol">✦</text><text>AI 生成 · 未经教师审阅</text>
        </view>
      </view>
      <view
        v-for="question in test.questions"
        :id="`question-${question.position}`"
        :key="question.id"
        class="question panel"
      >
        <view class="question-heading">
          <view class="question-heading-copy">
            <text class="question-number">第 {{ question.position }} 题</text>
            <text class="question-goal">· {{ goalLabel(question.pointCode) }}</text>
          </view>
          <view class="question-icon"
            ><image
              src="/static/final-test-question.svg"
              mode="aspectFit"
              aria-hidden="true"
          /></view>
        </view>
        <text class="prompt">{{ question.prompt }}</text>
        <view
          v-if="question.questionType === 'short_answer'"
          class="short-answer"
        >
          <text class="answer-label">你的回答</text>
          <textarea
            class="answer-input"
            :value="textAnswer(question.id)"
            :disabled="locked"
            maxlength="2000"
            placeholder="结合病例线索写出你的判断和依据"
            @input="updateText(question.id, $event)"
          />
        </view>
        <template v-else>
          <view
            v-for="(option, index) in question.options"
            :key="index"
            class="option"
            :class="{ selected: isSelected(question.id, index) }"
            :aria-disabled="locked"
            @click="choose(question.id, index, question.questionType)"
            ><text class="option-mark">{{ ['A', 'B', 'C', 'D'][index] }}</text
            ><text class="option-label">{{ option }}</text
            ><text
              v-if="isSelected(question.id, index)"
              class="selected-mark"
              >✓</text
            ></view
          >
        </template>
        <text
          v-if="question.questionType === 'multiple_choice'"
          class="answer-hint"
          >多选题，可选择多个选项</text
        >
      </view>
      <view
        v-if="grading"
        class="grading-state"
        role="status"
      >
        <text class="grading-title">{{ grading.retryAllowed ? '判分暂未完成' : '正在综合判分' }}</text>
        <text>{{
          grading.retryAllowed ? '答案已提交，请重试判分。' : '答案已提交，简答题正按开放时冻结的参考答案判分。'
        }}</text>
        <button
          v-if="grading.retryAllowed"
          class="secondary"
          :disabled="submitting"
          @click="retryGrading"
        >
          重新判分
        </button>
      </view>
      <view
        v-else
        class="submit-footer"
      >
        <view
          class="save-state"
          role="status"
          >{{ saveMessage }}</view
        >
        <text
          v-if="error"
          class="inline-error"
          role="alert"
          >{{ error }}</text
        >
        <button
          v-if="pendingSave"
          class="secondary"
          :disabled="saving"
          @click="saveDraftNow"
        >
          {{ saving ? '正在保存…' : '重试保存答案' }}
        </button>
        <button
          v-if="!submissionId"
          class="primary"
          :disabled="!canSubmit"
          @click="confirmSubmit"
        >
          {{ submitting ? '正在提交…' : '提交并查看结果' }}
        </button>
        <button
          v-else
          class="primary"
          :disabled="submitting"
          @click="retrySubmit"
        >
          {{ submitting ? '正在提交…' : '使用同一请求重试提交' }}
        </button>
      </view>
    </template>
    <MedConfirmDialog
      v-if="pendingConfirmation"
      title="提交最终测试"
      message="提交后不能修改答案，是否确认提交？"
      confirm-text="确认提交"
      cancel-text="继续检查"
      confirm-id="confirm-test-submit"
      @cancel="pendingConfirmation = undefined"
      @confirm="acceptSubmit"
    />
  </view>
</template>

<script setup lang="ts">
import { computed, ref, shallowRef } from 'vue'
import { onBackPress, onHide, onLoad, onShow, onUnload } from '@dcloudio/uni-app'
import MedConfirmDialog from '@/components/ui/MedConfirmDialog.vue'
import {
  createLearningRequestId,
  getKnowledgeCatalog,
  getFinalTestGrading,
  retryFinalTestGrading,
  saveFinalTestDraft,
  startFinalTest,
  submitFinalTest,
  type KnowledgePoint,
  type StudentFinalTest,
  type FinalTestAnswer,
  type FinalTestGradingStatus,
  type FinalTestQuestionType,
  learningGoalLabel,
} from '@/features/learning/public'
import { getSession, requireRole } from '@/features/identity/public'
import { backOrRoute, goReplace, handleBackPress, ROUTES } from '@/platform/navigation'

type PendingSave = { id: string; version: number; answers: Record<string, FinalTestAnswer> }
const test = ref<StudentFinalTest>()
const statusBarHeight = ref(0)
const navigationHeight = ref(44)
const navigationOffset = computed(() => statusBarHeight.value + navigationHeight.value)
const catalog = ref<KnowledgePoint[]>([])
const answers = ref<Record<string, FinalTestAnswer>>({})
const grading = ref<FinalTestGradingStatus>()
const loading = ref(false)
const saving = ref(false)
const submitting = ref(false)
const dirty = ref(false)
const error = ref('')
const saveMessage = ref('')
const pendingSave = ref<PendingSave>()
const submissionId = ref('')
const pendingConfirmation = shallowRef<{
  identity: string
  context: number
  test: StudentFinalTest
  attemptId: string
  attemptVersion: number
  answers: string
}>()
const answeredCount = computed(
  () =>
    test.value?.questions.filter((question) => {
      const value = answers.value[question.id]
      return (
        typeof value === 'number' ||
        (Array.isArray(value) && value.length > 0) ||
        (typeof value === 'string' && value.trim().length > 0)
      )
    }).length || 0,
)
const questionSummary = computed(() => {
  const questions = test.value?.questions || []
  const single = questions.filter(
    (question) => !question.questionType || question.questionType === 'single_choice',
  ).length
  const multiple = questions.filter((question) => question.questionType === 'multiple_choice').length
  const short = questions.filter((question) => question.questionType === 'short_answer').length
  return [single && `${single} 单选`, multiple && `${multiple} 多选`, short && `${short} 简答`]
    .filter(Boolean)
    .join(' · ')
})
function goalLabel(code: string) {
  return learningGoalLabel(code, catalog.value)
}
const locked = computed(
  () =>
    Boolean(submissionId.value) ||
    Boolean(grading.value) ||
    submitting.value ||
    test.value?.attempt?.status === 'submitted',
)
const canSubmit = computed(() =>
  Boolean(
    test.value?.attempt?.status === 'in_progress' &&
    !locked.value &&
    !pendingSave.value &&
    !saving.value &&
    !dirty.value &&
    answeredCount.value === test.value.questions.length,
  ),
)
let routeId = ''
let testId = ''
let identity = ''
let valid = false
let contextVersion = 0
let requestVersion = 0
let startRequestId = ''
let saveTimer: ReturnType<typeof setTimeout> | undefined
let gradingTimer: ReturnType<typeof setTimeout> | undefined
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
function current(requestedIdentity = identity, context = contextVersion) {
  return (
    valid &&
    context === contextVersion &&
    requireRole('student') &&
    getSession()?.role === 'student' &&
    getSession()?.openid === requestedIdentity
  )
}
function back() {
  backOrRoute(ROUTES.studentLearningPlanDetail, { routeId })
}
function clearTimer() {
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = undefined
}
function clearGradingTimer() {
  if (gradingTimer) clearTimeout(gradingTimer)
  gradingTimer = undefined
}
function scheduleGrading() {
  clearGradingTimer()
  gradingTimer = setTimeout(() => void refreshGrading(), 2500)
}
async function refreshGrading() {
  if (!current()) return
  const requestedIdentity = identity
  const context = contextVersion
  try {
    const value = await getFinalTestGrading(testId)
    if (!current(requestedIdentity, context)) return
    grading.value = value
    error.value = ''
    if (value.status === 'completed' && value.resultId) {
      clearGradingTimer()
      goReplace(ROUTES.studentLearningResult, { routeId, resultId: value.resultId })
    } else if (!value.retryAllowed) scheduleGrading()
  } catch (reason) {
    if (current(requestedIdentity, context))
      error.value = reason instanceof Error ? reason.message : '判分状态读取失败。'
  }
}
async function retryGrading() {
  if (!current() || submitting.value) return
  submitting.value = true
  error.value = ''
  try {
    grading.value = await retryFinalTestGrading(testId, createLearningRequestId('test-grade'))
    scheduleGrading()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '重试判分失败。'
  } finally {
    submitting.value = false
  }
}
async function load() {
  const session = getSession()
  if (!valid || !requireRole('student') || session?.role !== 'student' || !session.openid) return
  resetIdentity(session.openid)
  const requestedIdentity = session.openid
  const context = contextVersion
  const token = ++requestVersion
  if (!startRequestId) startRequestId = createLearningRequestId('test-start')
  loading.value = true
  error.value = ''
  saveMessage.value = ''
  try {
    const value = await startFinalTest(testId, startRequestId)
    if (!current(requestedIdentity, context) || token !== requestVersion) return
    if (value.id !== testId) throw new Error('最终测试编号与学习路线不匹配。')
    test.value = value
    startRequestId = ''
    answers.value = { ...(value.attempt?.answers || {}) }
    dirty.value = false
    if (value.attempt?.status === 'grading') {
      void refreshGrading()
      return
    }
    if (!value.attempt || value.attempt.status === 'submitted')
      throw new Error('本次测试已提交或尚未开放，请返回学习计划查看状态。')
    saveMessage.value = value.attempt.savedAt ? '草稿已同步' : '答案会自动保存；提交前请确认全部题目已作答。'
  } catch (reason) {
    if (current(requestedIdentity, context) && token === requestVersion) {
      error.value = reason instanceof Error ? reason.message : '最终测试无法开始。'
      void refreshGrading()
    }
  } finally {
    if (current(requestedIdentity, context) && token === requestVersion) loading.value = false
  }
}
async function loadCatalog(requestedIdentity: string, context: number) {
  try {
    const points = await getKnowledgeCatalog()
    if (current(requestedIdentity, context)) catalog.value = points
  } catch {
    if (current(requestedIdentity, context)) catalog.value = []
  }
}
function isSelected(questionId: string, index: number) {
  const value = answers.value[questionId]
  return Array.isArray(value) ? value.includes(index) : value === index
}
function textAnswer(questionId: string) {
  const value = answers.value[questionId]
  return typeof value === 'string' ? value : ''
}
function choose(questionId: string, value: number, type: FinalTestQuestionType) {
  if (locked.value) return
  const previous = answers.value[questionId]
  const next =
    type === 'multiple_choice'
      ? (Array.isArray(previous)
          ? previous.includes(value)
            ? previous.filter((item) => item !== value)
            : [...previous, value]
          : [value]
        ).sort((a, b) => a - b)
      : value
  if (JSON.stringify(previous) === JSON.stringify(next)) return
  const updated = { ...answers.value }
  if (Array.isArray(next) && next.length === 0) delete updated[questionId]
  else updated[questionId] = next
  answers.value = updated
  markDirty()
}
function updateText(questionId: string, event: unknown) {
  if (locked.value) return
  const input = event as { detail?: { value?: string }; target?: { value?: string } }
  const value = input.detail?.value ?? input.target?.value ?? ''
  const updated = { ...answers.value }
  if (value.trim()) updated[questionId] = value
  else delete updated[questionId]
  answers.value = updated
  markDirty()
}
function markDirty() {
  dirty.value = true
  error.value = ''
  saveMessage.value = '正在保存更改…'
  clearTimer()
  saveTimer = setTimeout(() => {
    saveTimer = undefined
    void saveDraftNow()
  }, 600)
}
async function saveDraftNow() {
  clearTimer()
  if (!test.value?.attempt || !current() || saving.value) return
  const pending = pendingSave.value || {
    id: createLearningRequestId('test-draft'),
    version: test.value.attempt.version,
    answers: { ...answers.value },
  }
  const requestedIdentity = identity
  const context = contextVersion
  pendingSave.value = pending
  saving.value = true
  error.value = ''
  try {
    const attempt = await saveFinalTestDraft(
      testId,
      pending.id,
      pending.version,
      test.value.releasedDigest,
      pending.answers,
    )
    if (!current(requestedIdentity, context) || !test.value) return
    test.value.attempt = attempt
    pendingSave.value = undefined
    dirty.value = JSON.stringify(answers.value) !== JSON.stringify(pending.answers)
    saveMessage.value = dirty.value ? '有新答案待保存' : '草稿已同步'
    if (dirty.value) {
      clearTimer()
      saveTimer = setTimeout(() => {
        saveTimer = undefined
        void saveDraftNow()
      }, 200)
    }
  } catch (reason) {
    if (current(requestedIdentity, context)) {
      error.value = reason instanceof Error ? reason.message : '答案暂未确认保存；可重试同一请求。'
      saveMessage.value = '保存状态待确认'
    }
  } finally {
    if (current(requestedIdentity, context)) saving.value = false
  }
}
function confirmSubmit() {
  if (!canSubmit.value || pendingConfirmation.value) return
  const requestedTest = test.value
  const requestedAttempt = requestedTest?.attempt
  if (!requestedTest || !requestedAttempt) return
  pendingConfirmation.value = {
    identity,
    context: contextVersion,
    test: requestedTest,
    attemptId: requestedAttempt.id,
    attemptVersion: requestedAttempt.version,
    answers: JSON.stringify(answers.value),
  }
}
function acceptSubmit() {
  const pending = pendingConfirmation.value
  pendingConfirmation.value = undefined
  if (
    !pending ||
    !current(pending.identity, pending.context) ||
    test.value !== pending.test ||
    test.value.attempt?.id !== pending.attemptId ||
    test.value.attempt.version !== pending.attemptVersion ||
    !canSubmit.value ||
    JSON.stringify(answers.value) !== pending.answers
  )
    return
  submissionId.value = createLearningRequestId('test-submit')
  void doSubmit()
}
function retrySubmit() {
  if (submissionId.value && !submitting.value) void doSubmit()
}
async function doSubmit() {
  if (!test.value?.attempt || !current() || !submissionId.value || submitting.value) return
  const requestedIdentity = identity
  const context = contextVersion
  submitting.value = true
  error.value = ''
  try {
    const result = await submitFinalTest(
      testId,
      submissionId.value,
      test.value.attempt.version,
      test.value.releasedDigest,
      { ...answers.value },
    )
    if (current(requestedIdentity, context)) {
      if ('status' in result && result.status === 'grading') {
        grading.value = result
        if (!result.retryAllowed) scheduleGrading()
      } else if ('id' in result) goReplace(ROUTES.studentLearningResult, { routeId, resultId: result.id })
    }
  } catch (reason) {
    if (current(requestedIdentity, context))
      error.value = reason instanceof Error ? reason.message : '提交状态暂未确认。可以使用同一请求重试。'
  } finally {
    if (current(requestedIdentity, context)) submitting.value = false
  }
}
function resetIdentity(nextIdentity: string) {
  if (identity === nextIdentity) return
  identity = nextIdentity
  contextVersion += 1
  requestVersion += 1
  clearTimer()
  clearGradingTimer()
  test.value = undefined
  answers.value = {}
  dirty.value = false
  pendingSave.value = undefined
  submissionId.value = ''
  grading.value = undefined
  pendingConfirmation.value = undefined
  startRequestId = ''
  error.value = ''
  loading.value = false
  catalog.value = []
  saving.value = false
  submitting.value = false
}
function hide() {
  pendingConfirmation.value = undefined
  clearTimer()
  clearGradingTimer()
  if (!submissionId.value && !submitting.value && (dirty.value || pendingSave.value)) void saveDraftNow()
  requestVersion += 1
  loading.value = false
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
  testId = String(query?.testId || '')
  valid = uuid.test(routeId) && uuid.test(testId)
  if (!valid) error.value = '最终测试链接无效。'
  if (requireRole('student')) identity = getSession()?.openid || ''
})
onShow(() => {
  const session = getSession()
  if (!requireRole('student') || session?.role !== 'student' || !session.openid) {
    resetIdentity('')
    return
  }
  resetIdentity(session.openid)
  void loadCatalog(session.openid, contextVersion)
  if (grading.value) void refreshGrading()
  else if (!test.value) void load()
})
onHide(hide)
onUnload(hide)
onBackPress(({ from }) => handleBackPress(from, ROUTES.studentLearningPlanDetail, { routeId }))
</script>

<style scoped>
.page {
  position: relative;
  min-height: 100vh;
  box-sizing: border-box;
  padding: 0 24rpx calc(80rpx + env(safe-area-inset-bottom));
  background: linear-gradient(180deg, #f1faff, #edf8ff 680rpx, #f5fbff 100%);
  color: #071653;
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'HarmonyOS Sans SC', 'Microsoft YaHei', sans-serif;
}
.page-navbar {
  position: fixed;
  top: 0;
  right: 0;
  left: 0;
  z-index: 10;
  box-sizing: border-box;
  overflow: hidden;
  background: #fafdff;
}
.navbar-art {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  pointer-events: none;
}
.navbar-row {
  position: relative;
  z-index: 1;
  display: flex;
  max-width: 920px;
  align-items: center;
  justify-content: center;
  margin: 0 auto;
}
.navbar-title {
  color: #071653;
  font-size: 32rpx;
  font-weight: 700;
}
.nav-back {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 12rpx;
  display: flex;
  width: 88rpx;
  align-items: center;
  justify-content: center;
  margin: 0;
  padding: 0;
  background: transparent;
}
.nav-back::after {
  border: 0;
}
.back-chevron {
  width: 22rpx;
  height: 22rpx;
  border-bottom: 4rpx solid #111b37;
  border-left: 4rpx solid #111b37;
  transform: rotate(45deg);
}
.page-art {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  pointer-events: none;
}
.intro,
.panel,
.state,
.grading-state,
.submit-footer,
.primary,
.secondary,
.save-state,
.inline-error {
  position: relative;
  z-index: 1;
  max-width: 920px;
  margin-left: auto;
  margin-right: auto;
}
.intro {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 10rpx;
  min-height: 255rpx;
  box-sizing: border-box;
  justify-content: center;
  margin-bottom: 12rpx;
  padding: 33rpx 18rpx 23rpx;
}
.hero-art {
  position: absolute;
  top: 4rpx;
  right: -18rpx;
  width: 300rpx;
  height: 250rpx;
  pointer-events: none;
}
.intro > text,
.review-note {
  position: relative;
  z-index: 1;
}
.eyebrow {
  color: #068caa;
  font-size: 26rpx;
  font-weight: 700;
}
.title {
  max-width: 71%;
  color: #071653;
  font-size: 42rpx;
  font-weight: 700;
  line-height: 1.3;
}
.muted {
  color: #405c9e;
  font-size: 25rpx;
  line-height: 1.5;
}
.review-note {
  display: flex;
  width: fit-content;
  align-items: center;
  gap: 9rpx;
  margin-top: 2rpx;
  padding: 7rpx 16rpx;
  color: #405c9e;
  background: rgba(224, 238, 255, 0.9);
  border-radius: 999rpx;
  font-size: 22rpx;
}
.review-symbol {
  color: #6671f2;
  font-size: 27rpx;
  line-height: 1;
}
.panel {
  margin-bottom: 22rpx;
  padding: 22rpx 22rpx 23rpx;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(255, 255, 255, 0.92);
  border-radius: 23rpx;
  box-shadow: 0 12rpx 28rpx rgba(64, 143, 206, 0.1);
}
.question-heading,
.question-heading-copy {
  display: flex;
  align-items: center;
}
.question-heading {
  justify-content: space-between;
  gap: 12rpx;
}
.question-heading-copy {
  min-width: 0;
  flex-wrap: wrap;
  gap: 13rpx;
}
.question-number {
  flex: 0 0 auto;
  padding: 9rpx 19rpx;
  color: #088cb0;
  background: linear-gradient(100deg, #d8f7fb, #e5faff);
  border-radius: 999rpx;
  font-size: 25rpx;
  font-weight: 700;
}
.question-goal {
  min-width: 0;
  color: #0789ad;
  font-size: 23rpx;
  font-weight: 600;
  line-height: 1.45;
}
.question-icon {
  display: flex;
  width: 50rpx;
  height: 50rpx;
  flex: 0 0 50rpx;
  align-items: center;
  justify-content: center;
  background: #ebf7ff;
  border-radius: 11rpx;
}
.question-icon image {
  width: 44rpx;
  height: 44rpx;
}
.prompt {
  display: block;
  margin: 15rpx 0 17rpx;
  color: #071653;
  font-size: 29rpx;
  font-weight: 700;
  line-height: 1.46;
}
.option {
  display: flex;
  min-height: 72rpx;
  box-sizing: border-box;
  align-items: center;
  gap: 17rpx;
  margin-top: 9rpx;
  padding: 7rpx 15rpx;
  color: #405c9e;
  background: #f3f9ff;
  border: 1px solid #cae5fc;
  border-radius: 15rpx;
  font-size: 26rpx;
  line-height: 1.43;
}
.option.selected {
  color: #09529b;
  background: #e3f3ff;
  border-color: #2f9dfa;
  box-shadow: 0 0 0 2rpx rgba(67, 163, 246, 0.16);
}
.option-mark {
  display: flex;
  width: 50rpx;
  height: 50rpx;
  flex: 0 0 50rpx;
  justify-content: center;
  align-items: center;
  color: #0762bd;
  background: linear-gradient(135deg, #cce8ff, #e2f2ff);
  border-radius: 50%;
  font-size: 28rpx;
  font-weight: 700;
}
.option-label {
  min-width: 0;
  flex: 1;
}
.selected-mark {
  margin-left: auto;
  color: #067fe5;
  font-size: 29rpx;
  font-weight: 700;
}
.answer-hint,
.answer-label {
  display: block;
  margin-top: 18rpx;
  color: #4a6ab1;
  font-size: 24rpx;
}
.answer-input {
  box-sizing: border-box;
  width: 100%;
  min-height: 220rpx;
  margin-top: 16rpx;
  padding: 19rpx;
  color: #153667;
  background: #f2f9ff;
  border: 1px solid #bddffb;
  border-radius: 17rpx;
  font-size: 26rpx;
  line-height: 1.6;
}
.grading-state {
  display: flex;
  max-width: 920px;
  flex-direction: column;
  gap: 15rpx;
  margin: 26rpx auto;
  padding: 26rpx;
  color: #405c9e;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid #d3eaff;
  border-radius: 23rpx;
  font-size: 26rpx;
  line-height: 1.55;
}
.grading-title {
  color: #071653;
  font-size: 30rpx;
  font-weight: 700;
}
.submit-footer {
  padding: 19rpx 4rpx 0;
}
.save-state {
  padding: 15rpx 0 19rpx;
  color: #4d6caf;
  font-size: 24rpx;
  line-height: 1.5;
  text-align: center;
}
.primary,
.secondary {
  display: flex;
  width: 100%;
  min-height: 88rpx;
  box-sizing: border-box;
  align-items: center;
  justify-content: center;
  margin: 14rpx 0 0;
  border-radius: 999rpx;
  font-size: 30rpx;
  font-weight: 700;
  line-height: 1.3;
}
.primary::after,
.secondary::after {
  border: 0;
}
.primary {
  color: #fff;
  background: linear-gradient(105deg, #63cfff, #329bf5 55%, #1868f2);
  box-shadow: 0 10rpx 22rpx rgba(42, 128, 241, 0.15);
}
.primary[disabled] {
  color: #fff;
  opacity: 0.62;
}
.secondary {
  color: #1673c9;
  background: #e2f4ff;
  font-size: 25rpx;
}
.inline-error {
  display: block;
  margin-top: 12rpx;
  color: #a0444a;
  font-size: 24rpx;
  line-height: 1.5;
}
.state {
  display: flex;
  min-height: 210rpx;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  gap: 16rpx;
  margin-top: 24rpx;
  padding: 30rpx;
  color: #405c9e;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 23rpx;
  text-align: center;
}
.state button {
  color: #1673c9;
  background: #e2f4ff;
  border-radius: 14rpx;
}
</style>
