<template>
  <view
    class="case-page"
    :class="{ 'chat-page': started }"
    :style="keyboardHeight ? { height: `calc(100vh - ${keyboardHeight}px)` } : {}"
  >
    <view
      class="case-navbar"
      :style="{ paddingTop: `${statusBarHeight}px` }"
    >
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
        <text class="navbar-title">病例学习</text>
      </view>
    </view>
    <view
      v-if="error && !caseRead"
      class="state error"
      role="alert"
    >
      <text>{{ error }}</text
      ><button @click="load">重新加载</button>
    </view>
    <view
      v-else-if="loading && !caseRead"
      class="state"
      role="status"
      >正在加载病例学习…</view
    >
    <template v-else-if="caseRead">
      <scroll-view
        v-if="!started"
        class="intro-scroll"
        scroll-y
      >
        <view class="intro">
          <view class="hero">
            <text class="eyebrow">AI 病例学习</text>
            <text class="title">{{ caseTitle }}</text>
            <text class="scenario">{{ caseRead.syntheticCase.publicScenario }}</text>
            <image
              class="hero-art"
              src="/static/case-learning-clipboard.png"
              mode="aspectFit"
              aria-hidden="true"
            />
          </view>
          <view class="intro-card facts-card">
            <view class="card-heading"
              ><view class="heading-icon mint"><image src="/static/case-learning-facts.svg" /></view
              ><text>病例事实</text></view
            >
            <view
              v-for="(fact, index) in caseRead.syntheticCase.caseFacts"
              :key="index"
              class="fact-row"
              ><text class="number">{{ index + 1 }}</text
              ><text>{{ fact }}</text></view
            >
          </view>
          <view class="intro-card instructions-card">
            <view class="card-heading"
              ><view class="heading-icon gold"><image src="/static/case-learning-bulb.svg" /></view
              ><text>学习说明</text></view
            >
            <view class="instruction"><text class="dot">•</text><text>这是一个用于学习的合成教学病例。</text></view>
            <view class="instruction"><text class="dot">•</text><text>请结合病例信息进行分析和回答。</text></view>
            <view class="instruction"
              ><text class="dot">•</text><text>你的每次回答都会得到 AI 的引导与反馈。</text></view
            >
          </view>
          <button
            class="start-button"
            @click="startLearning"
          >
            <text>{{ caseRead.phase === 'completed' ? '回顾病例学习' : '开始病例学习' }}</text
            ><text class="start-arrow">→</text>
          </button>
          <text class="intro-safety">{{ caseRead.safetyNotice }}</text>
        </view>
      </scroll-view>
      <template v-else>
        <view class="case-context">
          <button
            class="case-summary"
            :aria-expanded="factsExpanded"
            aria-label="展开或收起病例事实"
            @click="factsExpanded = !factsExpanded"
          >
            <image
              class="summary-art"
              src="/static/case-learning-clipboard.png"
              mode="aspectFit"
              aria-hidden="true"
            />
            <view class="summary-copy"
              ><text class="summary-title">合成教学病例：{{ caseTitle }}</text
              ><text class="summary-scenario">{{ caseRead.syntheticCase.publicScenario }}</text></view
            >
            <view
              class="expand-button"
              :class="{ expanded: factsExpanded }"
              ><view class="chevron"
            /></view>
          </button>
          <scroll-view
            v-if="factsExpanded"
            class="expanded-facts"
            scroll-y
          >
            <view
              v-for="(fact, index) in caseRead.syntheticCase.caseFacts"
              :key="index"
              class="fact-row"
              ><text class="number">{{ index + 1 }}</text
              ><text>{{ fact }}</text></view
            >
          </scroll-view>
        </view>
        <swiper
          class="stage-swiper"
          :current="selectedStage"
          :duration="180"
          @change="changeStage"
        >
          <swiper-item
            v-for="(stage, index) in unlockedStages"
            :id="`case-stage-chat-${index + 1}`"
            :key="stage.phase"
          >
            <scroll-view
              class="chat-scroll"
              scroll-y
              :show-scrollbar="false"
              :scroll-into-view="scrollTargets[stage.phase] || ''"
            >
              <view class="conversation">
                <view class="assistant-opening">
                  <view class="ai-heading"
                    ><image
                      class="ai-icon"
                      src="/static/case-learning-ai.svg"
                      aria-hidden="true"
                    /><text>AI 导师</text></view
                  >
                  <view class="ai-content">
                    <text class="opening-line"
                      >我们现在进入<text class="stage-emphasis"
                        >第 {{ index + 1 }} 个阶段：{{ stage.label }}。</text
                      ></text
                    >
                    <text class="goals-lead">在本阶段，你需要完成以下目标：</text>
                    <view class="goals-list"
                      ><view
                        v-for="(goal, goalIndex) in stage.goals"
                        :key="goal.goalId"
                        class="goal-row"
                        ><text class="number">{{ goalIndex + 1 }}</text
                        ><text>{{ goal.objective }}</text></view
                      ></view
                    >
                    <text class="stage-prompt">{{ stage.prompt }}</text>
                  </view>
                </view>
                <view
                  v-for="message in stageMessages(stage.phase)"
                  :key="message.id"
                  class="message"
                  :class="message.role"
                >
                  <view
                    v-if="message.role === 'assistant'"
                    class="ai-heading"
                    ><image
                      class="ai-icon"
                      src="/static/case-learning-ai.svg"
                      aria-hidden="true"
                    /><text>AI 导师</text></view
                  >
                  <text class="message-content">{{ message.content }}</text>
                </view>
                <view
                  v-if="index === unlockedStage && (caseRead.pendingMessage || pendingRetry)"
                  class="pending"
                  role="status"
                  ><text>{{
                    caseRead.pendingMessage?.processingState === 'processing'
                      ? 'AI 正在分析你的回答…'
                      : '上一条回复尚未确认。'
                  }}</text
                  ><button
                    :disabled="retryDisabled()"
                    @click="retryPending"
                  >
                    {{ sending ? '正在重试…' : '使用原请求重试' }}
                  </button></view
                >
                <view
                  v-if="index < unlockedStage"
                  class="stage-completed"
                  ><text>本阶段目标已达成</text
                  ><button @click="selectStage(index + 1)">进入{{ stages[index + 1].label }} →</button></view
                >
                <view
                  v-if="index === 3 && caseRead.phase === 'completed'"
                  class="complete-note"
                  ><text>病例学习已完成，分析记录已保存。</text><button @click="back">返回学习计划 →</button></view
                >
                <view
                  :id="`stage-tail-${caseRead.revision}-${index}`"
                  class="stage-tail"
                />
              </view>
            </scroll-view>
          </swiper-item>
        </swiper>
        <view class="chat-footer">
          <text
            v-if="stageNotice"
            class="stage-notice"
            role="status"
            >{{ stageNotice }}</text
          >
          <view class="stage-nav">
            <view
              v-for="(stage, index) in stages"
              :key="stage.phase"
              class="stage-step"
              ><button
                :id="`case-stage-${index + 1}`"
                class="stage-tab"
                :class="{
                  selected: index === selectedStage,
                  locked: index > unlockedStage,
                  done: index < unlockedStage || caseRead.phase === 'completed',
                }"
                :aria-label="`${stage.label}${index > unlockedStage ? '，尚未解锁' : index === selectedStage ? '，当前查看' : '，可查看'}`"
                :aria-controls="index <= unlockedStage ? `case-stage-chat-${index + 1}` : undefined"
                @click="selectStage(index)"
              >
                <text class="stage-number">{{ index + 1 }}</text
                ><text class="stage-label">{{ stage.label }}</text>
              </button></view
            >
          </view>
          <view
            v-if="caseRead.phase !== 'completed'"
            class="composer"
          >
            <textarea
              v-model="draft"
              maxlength="2000"
              :disabled="!canReply || sending || Boolean(caseRead.pendingMessage) || Boolean(pendingRetry)"
              :placeholder="canReply ? '继续输入你的分析，完善本阶段判断…' : '本阶段已完成，切换到当前阶段继续学习'"
              auto-height
              :adjust-position="false"
              :cursor-spacing="16"
              aria-label="病例推理回答"
              @keyboardheightchange="keyboardChanged"
            />
            <button
              class="send-button"
              :disabled="
                !canReply || sending || Boolean(caseRead.pendingMessage) || Boolean(pendingRetry) || !draft.trim()
              "
              :aria-label="sending ? '正在分析' : `发送${activeStage.label}回答`"
              @click="send"
            >
              <image
                src="/static/case-learning-send.svg"
                aria-hidden="true"
              />
            </button>
          </view>
          <button
            v-else
            class="finish-button"
            @click="back"
          >
            返回学习计划 →
          </button>
          <text
            v-if="error"
            class="inline-error"
            role="alert"
            >{{ error }}</text
          >
        </view>
      </template>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onBackPress, onHide, onLoad, onShow, onUnload } from '@dcloudio/uni-app'
import {
  ROUTE_CASE_STAGES,
  createLearningRequestId,
  getRouteCase,
  sendRouteCaseMessage,
  type RouteCaseRead,
} from '@/features/learning/public'
import { getSession, requireRole } from '@/features/identity/public'
import { backOrRoute, handleBackPress, ROUTES } from '@/platform/navigation'

const caseRead = ref<RouteCaseRead>()
const started = ref(false)
const factsExpanded = ref(false)
const selectedStage = ref(0)
const keyboardHeight = ref(0)
const statusBarHeight = ref(0)
const navigationHeight = ref(44)
const stageNotice = ref('')
const scrollTargets = ref<Record<string, string>>({})
const stages = computed(() =>
  ROUTE_CASE_STAGES.map((stage) => ({
    ...stage,
    goals: caseRead.value?.stages.find((item) => item.phase === stage.phase)?.goals ?? [],
    prompt: caseRead.value?.stages.find((item) => item.phase === stage.phase)?.prompt ?? '',
  })),
)
const caseTitle = computed(() => caseRead.value?.syntheticCase.title.replace(/^合成(?:教学)?病例[：:]\s*/, '') || '')
const unlockedStage = computed(() => {
  if (caseRead.value?.phase === 'completed') return 3
  return Math.max(
    0,
    stages.value.findIndex((stage) => stage.phase === caseRead.value?.phase),
  )
})
const unlockedStages = computed(() => stages.value.slice(0, unlockedStage.value + 1))
const activeStage = computed(() => stages.value[selectedStage.value])
const canReply = computed(() => selectedStage.value === unlockedStage.value && caseRead.value?.phase !== 'completed')
function startLearning() {
  started.value = true
  selectedStage.value = unlockedStage.value
}
function selectStage(index: number) {
  if (index > unlockedStage.value) {
    stageNotice.value = '完成当前阶段目标后，才能解锁下一阶段。'
    return
  }
  stageNotice.value = ''
  selectedStage.value = index
}
function changeStage(event: { detail: { current: number } }) {
  selectStage(event.detail.current)
}
function stageMessages(phase: string) {
  return (caseRead.value?.messages || []).filter((message) =>
    message.phase ? message.phase === phase : phase === 'pathology_recognition',
  )
}
function keyboardChanged(event: { detail: { height: number } }) {
  keyboardHeight.value = Math.max(0, event.detail.height)
}
const draft = ref('')
const error = ref('')
const loading = ref(false)
const sending = ref(false)
let routeId = ''
let caseId = ''
let identity = ''
let valid = false
let pendingRetry: { id: string; content: string; revision: number; submittedRevision?: number } | undefined
let contextVersion = 0
let requestVersion = 0
let visible = false
let pollStartedAt = 0
let pollTimer: ReturnType<typeof setTimeout> | undefined
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
function clearPoll() {
  if (pollTimer) clearTimeout(pollTimer)
  pollTimer = undefined
}
function schedulePoll() {
  clearPoll()
  const pending = caseRead.value?.pendingMessage
  if (!visible || !pending || !['pending', 'processing', 'queued'].includes(pending.processingState)) {
    pollStartedAt = 0
    return
  }
  if (!pollStartedAt) pollStartedAt = Date.now()
  if (Date.now() - pollStartedAt >= 120_000) {
    error.value = '仍在处理中，可刷新查看；不会自动重复发送。'
    return
  }
  pollTimer = setTimeout(() => {
    pollTimer = undefined
    void load()
  }, 3000)
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
    const value = await getRouteCase(caseId)
    if (!current(requestedIdentity, context) || token !== requestVersion) return
    if (value.routeId !== routeId || value.id !== caseId) throw new Error('该病例不属于当前学习路线。')
    const previousPhase = caseRead.value?.phase
    const previousMessageCount = caseRead.value?.messages.length
    caseRead.value = value
    if (!previousPhase) selectedStage.value = unlockedStage.value
    if (previousPhase && previousMessageCount !== undefined && value.messages.length > previousMessageCount)
      scrollTargets.value[previousPhase] =
        `stage-tail-${value.revision}-${stages.value.findIndex((stage) => stage.phase === previousPhase)}`
    const pending = value.pendingMessage
    if (pending) {
      const student = value.messages.find(
        (message) => message.role === 'student' && message.revision === pending.requestRevision,
      )
      if (student)
        pendingRetry = {
          id: pending.clientMessageId,
          content: student.content,
          revision: pending.requestRevision,
          submittedRevision: pending.requestRevision,
        }
    } else if (pendingRetry) {
      const confirmedStudent = value.messages.find(
        (message) =>
          message.role === 'student' &&
          message.content === pendingRetry?.content &&
          message.revision === (pendingRetry.submittedRevision ?? pendingRetry.revision + 1),
      )
      if (
        confirmedStudent &&
        value.messages.some((message) => message.role === 'assistant' && message.revision === confirmedStudent.revision)
      )
        pendingRetry = undefined
    }
    schedulePoll()
  } catch (reason) {
    if (current(requestedIdentity, context) && token === requestVersion)
      error.value = reason instanceof Error ? reason.message : '病例加载失败。'
  } finally {
    if (current(requestedIdentity, context) && token === requestVersion) loading.value = false
  }
}
async function sendWith(content: string, request: { id: string; revision: number; submittedRevision?: number }) {
  if (!caseRead.value || sending.value || !current()) return
  const requestedIdentity = identity
  const context = contextVersion
  const sentCaseId = caseId
  sending.value = true
  error.value = ''
  try {
    await sendRouteCaseMessage(sentCaseId, content, request.id, request.revision)
    if (current(requestedIdentity, context)) {
      draft.value = ''
      pendingRetry = undefined
      await load()
    }
  } catch (reason) {
    if (current(requestedIdentity, context)) {
      pendingRetry = { ...request, content }
      const message = reason instanceof Error ? reason.message : '回复未确认，可使用同一请求重试。'
      await load()
      if (current(requestedIdentity, context)) error.value ||= message
    }
  } finally {
    if (current(requestedIdentity, context)) sending.value = false
  }
}
function send() {
  if (!caseRead.value || !canReply.value || !draft.value.trim() || caseRead.value.pendingMessage || pendingRetry) return
  void sendWith(draft.value.trim(), { id: createLearningRequestId('case-message'), revision: caseRead.value.revision })
}
function retryPending() {
  if (!pendingRetry || (caseRead.value?.pendingMessage && !caseRead.value.pendingMessage.retryAllowed)) return
  void sendWith(pendingRetry.content, pendingRetry)
}
function retryDisabled() {
  return sending.value || Boolean(caseRead.value?.pendingMessage && !caseRead.value.pendingMessage.retryAllowed)
}
function resetIdentity(nextIdentity: string) {
  if (identity === nextIdentity) return
  identity = nextIdentity
  contextVersion += 1
  requestVersion += 1
  clearPoll()
  pollStartedAt = 0
  caseRead.value = undefined
  started.value = false
  factsExpanded.value = false
  selectedStage.value = 0
  keyboardHeight.value = 0
  stageNotice.value = ''
  scrollTargets.value = {}
  draft.value = ''
  pendingRetry = undefined
  error.value = ''
  loading.value = false
  sending.value = false
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
  caseId = String(query?.caseId || '')
  valid = uuid.test(routeId) && uuid.test(caseId)
  if (!valid) error.value = '病例学习链接无效。'
  if (requireRole('student')) identity = getSession()?.openid || ''
})
onShow(() => {
  const session = getSession()
  if (!requireRole('student') || session?.role !== 'student' || !session.openid) {
    visible = false
    resetIdentity('')
    return
  }
  resetIdentity(session.openid)
  visible = true
  if (valid) void load()
})
function hide() {
  keyboardHeight.value = 0
  visible = false
  clearPoll()
  requestVersion += 1
  loading.value = false
}
onHide(hide)
onUnload(hide)
onBackPress(({ from }) => handleBackPress(from, ROUTES.studentLearningPlanDetail, { routeId }))
</script>

<style scoped>
.case-page {
  display: flex;
  flex-direction: column;
  --case-ink: #081576;
  --case-text: #545d99;
  --case-cyan: #10bbd5;
  height: 100vh;
  box-sizing: border-box;
  overflow: hidden;
  background: linear-gradient(155deg, #e9f8ff 0%, #f6fcff 40%, #effaff 100%);
  color: var(--case-text);
  font-family: var(--med-font-body);
  font-size: 28rpx;
}
.case-navbar {
  flex-shrink: 0;
  box-sizing: border-box;
  background: #fff;
  margin: 0 -18rpx;
}
.navbar-row {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
}
.navbar-title {
  color: #111;
  font-size: 32rpx;
  font-weight: 700;
  line-height: 1.4;
}
.nav-back {
  position: absolute;
  left: 12rpx;
  top: 0;
  bottom: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  width: 84rpx;
  margin: 0;
  padding: 0;
  background: transparent;
}
.back-chevron {
  width: 20rpx;
  height: 20rpx;
  border-left: 4rpx solid #111;
  border-bottom: 4rpx solid #111;
  transform: rotate(45deg);
}
.intro-scroll {
  flex: 1;
  min-height: 0;
  height: 0;
}
.intro {
  position: relative;
  max-width: 920px;
  margin: 0 auto;
  padding: 28rpx 32rpx calc(42rpx + env(safe-area-inset-bottom));
}
.intro::after {
  content: '';
  position: absolute;
  z-index: 0;
  left: -15%;
  bottom: -65rpx;
  width: 130%;
  height: 145rpx;
  border-radius: 50% 50% 0 0;
  background: linear-gradient(160deg, #def4fe80, #d1f0ff99);
  transform: rotate(-5deg);
  pointer-events: none;
}
.intro > view,
.intro > button,
.intro > text {
  position: relative;
  z-index: 1;
}
.hero {
  position: relative;
  min-height: 370rpx;
  padding: 0 8rpx 30rpx;
}
.eyebrow {
  display: table;
  padding: 8rpx 22rpx;
  border-radius: 99rpx;
  background: #daf3ff;
  color: #009deb;
  font-size: 26rpx;
  font-weight: 500;
}
.title {
  position: relative;
  z-index: 1;
  display: block;
  margin: 22rpx 0 24rpx;
  color: var(--case-ink);
  font-size: 52rpx;
  font-weight: 700;
  line-height: 1.35;
  max-width: 72%;
}
.scenario {
  position: relative;
  z-index: 1;
  display: block;
  width: 65%;
  font-size: 28rpx;
  line-height: 1.9;
}
.hero-art {
  position: absolute;
  right: -18rpx;
  top: 42rpx;
  width: 290rpx;
  height: 340rpx;
}
.intro-card {
  margin: 0 0 32rpx;
  padding: 18rpx 26rpx 30rpx;
  background: linear-gradient(140deg, #fff, #f8fcff);
  border: 1rpx solid #e3f5ff;
  border-radius: 24rpx;
  box-shadow: 0 8rpx 26rpx #bceafa40;
}
.card-heading {
  display: flex;
  align-items: center;
  gap: 24rpx;
  margin-bottom: 16rpx;
  color: var(--case-ink);
  font-size: 36rpx;
  font-weight: 700;
}
.heading-icon {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 72rpx;
  height: 72rpx;
  flex-shrink: 0;
  border-radius: 50%;
}
.heading-icon image {
  width: 38rpx;
  height: 42rpx;
}
.mint {
  background: #e0fcf5;
}
.gold {
  background: #fff5dc;
}
.fact-row {
  display: flex;
  align-items: flex-start;
  gap: 26rpx;
  margin-top: 18rpx;
  line-height: 1.8;
}
.facts-card .fact-row {
  margin-left: 40rpx;
}
.number {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 64rpx;
  height: 64rpx;
  flex-shrink: 0;
  border-radius: 50%;
  background: #e8f8ff;
  color: #00a6e9;
  font-size: 30rpx;
  font-weight: 700;
  line-height: 1;
}
.fact-row > text:last-child {
  padding-top: 6rpx;
}
.instruction {
  display: flex;
  gap: 24rpx;
  margin: 20rpx 10rpx 0;
  line-height: 1.8;
}
.dot {
  font-size: 38rpx;
  line-height: 1.35;
}
.start-button {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 22rpx;
  min-height: 104rpx;
  margin-top: 42rpx;
  border-radius: 24rpx;
  background: linear-gradient(110deg, #77e1ee, #109fcb 64%, #10bfd1);
  color: #fff;
  font-size: 32rpx;
  font-weight: 700;
  line-height: 1.4;
  box-shadow: 0 10rpx 28rpx #b5eafb38;
}
.start-arrow {
  font-size: 42rpx;
  font-weight: 400;
}
.intro-safety {
  display: block;
  margin: 18rpx 8rpx 0;
  color: #65709a;
  font-size: 22rpx;
  line-height: 1.6;
  text-align: center;
}
.chat-page {
  display: flex;
  flex-direction: column;
  background: linear-gradient(#fff, #f3fcff);
  padding: 0 18rpx;
}
.case-context {
  flex-shrink: 0;
  width: 100%;
  max-width: 920px;
  margin: 22rpx auto 14rpx;
  overflow: hidden;
  background: #f2f9fd;
  border-radius: 22rpx;
}
.case-summary {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
  padding: 20rpx 18rpx;
  border-radius: 22rpx;
  background: transparent;
  text-align: left;
  font-size: 26rpx;
  line-height: 1.7;
}
.summary-art {
  flex-shrink: 0;
  width: 132rpx;
  height: 132rpx;
  margin-right: 24rpx;
  border-radius: 20rpx;
  background: #e2f4ff;
}
.summary-copy {
  flex: 1;
  min-width: 0;
  padding-right: 32rpx;
}
.summary-title {
  display: block;
  margin: 0 20rpx 10rpx 0;
  color: var(--case-ink);
  font-size: 30rpx;
  font-weight: 700;
  line-height: 1.5;
}
.summary-scenario {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  color: var(--case-text);
  font-size: 24rpx;
}
.expand-button {
  position: absolute;
  top: 22rpx;
  right: 12rpx;
  display: flex;
  justify-content: center;
  align-items: center;
  width: 48rpx;
  height: 48rpx;
  border: 1rpx solid #ceefff;
  border-radius: 50%;
  background: #fff;
}
.chevron {
  width: 15rpx;
  height: 15rpx;
  margin-top: -6rpx;
  border-right: 5rpx solid #12bfdc;
  border-bottom: 5rpx solid #12bfdc;
  transform: rotate(45deg);
}
.expanded .chevron {
  margin-top: 6rpx;
  transform: rotate(225deg);
}
.expanded-facts {
  max-height: 270rpx;
  height: 230rpx;
  box-sizing: border-box;
  padding: 0 24rpx 18rpx;
  border-top: 1rpx solid #e0f0f9;
  font-size: 25rpx;
}
.expanded-facts .number {
  width: 42rpx;
  height: 42rpx;
  font-size: 24rpx;
}
.expanded-facts .fact-row {
  gap: 18rpx;
  margin-top: 14rpx;
}
.expanded-facts .fact-row > text:last-child {
  padding-top: 0;
}
.stage-swiper {
  flex: 1;
  min-height: 0;
  width: 100%;
  max-width: 920px;
  margin: 0 auto;
}
.chat-scroll {
  height: 100%;
}
.conversation {
  padding: 24rpx 0 0;
  font-size: 28rpx;
  line-height: 1.85;
}
.ai-heading {
  display: flex;
  align-items: center;
  gap: 20rpx;
  margin: 0 14rpx 20rpx;
  color: var(--case-cyan);
  font-size: 28rpx;
  font-weight: 700;
}
.ai-icon {
  width: 48rpx;
  height: 48rpx;
  flex-shrink: 0;
}
.ai-content {
  padding-left: 82rpx;
  padding-right: 2rpx;
}
.opening-line,
.goals-lead,
.stage-prompt {
  display: block;
}
.stage-emphasis {
  color: var(--case-ink);
  font-weight: 700;
}
.goals-lead {
  margin-top: 22rpx;
}
.goals-list {
  margin: 20rpx 0 32rpx;
}
.goal-row {
  display: flex;
  align-items: flex-start;
  gap: 22rpx;
  margin: 6rpx 0 12rpx;
  font-size: 26rpx;
}
.goal-row:last-child {
  margin-bottom: 0;
}
.goal-row .number {
  width: 52rpx;
  height: 52rpx;
  background: #ddf6fe;
  color: #07b9da;
}
.goal-row > text:last-child {
  padding-top: 1rpx;
}
.message {
  margin: 28rpx 0 0;
}
.message-content {
  display: block;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.assistant .message-content {
  margin-left: 82rpx;
}
.student {
  margin-left: 82rpx;
  padding: 24rpx 28rpx;
  border-radius: 20rpx;
  background: #e8f7f9;
}
.stage-tail {
  height: 30rpx;
}
.chat-footer {
  flex-shrink: 0;
  width: 100%;
  max-width: 920px;
  box-sizing: border-box;
  margin: 0 auto;
  padding: 12rpx 0 calc(18rpx + env(safe-area-inset-bottom));
  background: linear-gradient(#f5fcff00, #f4fcff 28%);
}
.stage-nav {
  display: flex;
  padding: 8rpx 0 16rpx;
}
.stage-tab {
  position: relative;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 0;
  min-height: 96rpx;
  padding: 0;
  margin: 0;
  background: transparent;
  border-radius: 0;
  color: #626b99;
  line-height: 1.5;
}
.stage-step {
  position: relative;
  flex: 1;
  min-width: 0;
}
.stage-step:not(:last-child)::before {
  position: absolute;
  top: 29rpx;
  left: calc(50% + 40rpx);
  width: calc(100% - 80rpx);
  height: 2rpx;
  content: '';
  background: #bdcbdc;
}
.stage-number {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 60rpx;
  height: 60rpx;
  margin-bottom: 4rpx;
  background: #e8f1f7;
  border-radius: 50%;
  font-size: 30rpx;
  font-weight: 600;
  line-height: 1;
}
.stage-label {
  font-size: 24rpx;
  white-space: nowrap;
}
.selected {
  color: #007d9e;
  font-weight: 700;
}
.selected .stage-number {
  background: linear-gradient(135deg, #71d7e9, #009cb9);
  color: #fff;
  box-shadow: inset 0 0 0 1rpx #04b5ce;
}
.done:not(.selected) .stage-number {
  border: 1rpx solid #9cdde7;
  background: #e0f7fa;
  color: #087d97;
}
.composer {
  display: flex;
  align-items: center;
  gap: 12rpx;
  min-height: 92rpx;
  padding: 10rpx 14rpx 10rpx 24rpx;
  border: 1rpx solid #bfe6ef;
  border-radius: 34rpx;
  background: #fff;
  box-shadow: 0 8rpx 26rpx rgba(7, 155, 170, 0.085);
  box-sizing: border-box;
  transition:
    border-color var(--med-motion-settle) var(--med-ease-out),
    box-shadow var(--med-motion-settle) var(--med-ease-out);
}
.composer:focus-within {
  border-color: #7bd3df;
  box-shadow: 0 9rpx 28rpx rgba(7, 155, 170, 0.14);
}
.composer textarea {
  flex: 1;
  width: 0;
  min-height: 42rpx;
  max-height: 180rpx;
  padding: 6rpx 0;
  color: var(--case-text);
  font-size: 26rpx;
  line-height: 1.6;
}
.send-button {
  display: flex;
  justify-content: center;
  align-items: center;
  flex-shrink: 0;
  width: 72rpx;
  height: 72rpx;
  margin: 0;
  padding: 0;
  border-radius: 50%;
  background: linear-gradient(135deg, #51cddd, #029fbf);
}
.send-button image {
  width: 40rpx;
  height: 40rpx;
}
.send-button[disabled] {
  background: linear-gradient(135deg, #51cddd, #029fbf);
  opacity: 0.55;
}
.pending,
.stage-completed,
.complete-note {
  margin: 24rpx 0 0 82rpx;
  font-size: 24rpx;
}
.pending button,
.stage-completed button,
.complete-note button,
.finish-button {
  min-height: 80rpx;
  margin-top: 12rpx;
  background: #dff5fa;
  color: #087d97;
  border-radius: 16rpx;
  font-size: 25rpx;
  line-height: 1.6;
  display: flex;
  align-items: center;
  justify-content: center;
}
.finish-button {
  margin-top: 0;
}
.inline-error,
.stage-notice {
  display: block;
  margin: 8rpx 12rpx;
  font-size: 23rpx;
  line-height: 1.6;
}
.inline-error,
.error {
  color: #a0444a;
}
.state {
  display: flex;
  min-height: 260rpx;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 24rpx;
  margin: 32rpx;
  padding: 30rpx;
  border-radius: 24rpx;
  background: #fff;
  text-align: center;
}
.state button {
  color: #087d97;
  background: #eaf7f8;
}
@media (min-width: 768px) {
  .hero {
    min-height: 320px;
  }
  .hero-art {
    width: 300px;
    height: 300px;
  }
  .scenario {
    max-width: 600px;
  }
  .conversation {
    font-size: 28px;
  }
  .composer {
    border-radius: 22px;
  }
}
</style>
