<template>
  <view
    class="page"
    :class="{
      'page-three-steps': timeline.length === 3,
      'page-multi-steps': timeline.length > 3,
    }"
    :style="{ paddingTop: `${navigationOffset}px` }"
  >
    <view
      class="page-navbar"
      :style="{ paddingTop: `${statusBarHeight}px`, height: `${navigationOffset + 2}px` }"
    >
      <image
        class="navbar-art"
        src="/static/learning-plan-hero.svg"
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
        <text class="navbar-title">学习计划详情</text>
      </view>
    </view>
    <image
      class="page-art"
      src="/static/learning-plan-hero.svg"
      mode="widthFix"
      aria-hidden="true"
    />
    <image
      class="hero-document"
      src="/static/learning-plan-document.png"
      mode="aspectFit"
      aria-hidden="true"
    />
    <view
      v-if="loading && !detail"
      class="state"
      >正在读取学习计划…</view
    >
    <view
      v-else-if="error && !detail"
      class="state error"
      ><text>{{ error }}</text
      ><button @click="load">重新加载</button
      ><button
        class="quiet"
        @click="back"
      >
        返回学习计划
      </button></view
    >
    <template v-else-if="detail">
      <view class="intro">
        <view class="meta"
          ><text>{{ detail.summary.sourceKind === 'classroom' ? '课堂研讨' : '自主研讨' }}</text
          ><text class="meta-divider">|</text><text>{{ detail.summary.sessionLocator }}</text></view
        >
        <text class="title">{{ detail.summary.title }}</text>
        <text class="summary">{{ diagnosisText }}</text>
      </view>
      <view
        class="action"
        :class="{ 'action-empty': !detail.steps.length }"
      >
        <image
          v-if="detail.steps.length"
          class="action-art"
          src="/static/learning-plan-journey.png"
          mode="aspectFit"
          aria-hidden="true"
        />
        <text class="eyebrow">当前行动</text>
        <text class="action-title">{{ actionTitle }}</text>
        <text class="hint">{{ actionDescription }}</text>
        <button
          v-if="detail.summary.nextAction === 'retry_route' || detail.summary.nextAction === 'retry_test'"
          class="primary"
          :disabled="busy"
          @click="retry"
        >
          {{
            busy ? '正在重试…' : detail.summary.nextAction === 'retry_route' ? '重试生成学习计划' : '重试生成最终测试'
          }}
        </button>
        <button
          v-else-if="detail.summary.nextAction === 'reading' || detail.summary.nextAction === 'case'"
          class="primary"
          @click="openCurrentStep"
        >
          {{ detail.summary.nextAction === 'reading' ? '继续资料学习' : '继续病例学习' }}
          <text class="button-arrow">→</text>
        </button>
        <button
          v-else-if="detail.summary.nextAction === 'test' && detail.canStartTest"
          class="primary"
          @click="startTest"
        >
          开始最终测试 <text class="button-arrow">→</text>
        </button>
        <button
          v-else-if="detail.summary.nextAction === 'wait_grade'"
          class="primary"
          @click="openGrading"
        >
          查看判分进度 <text class="button-arrow">→</text>
        </button>
        <button
          v-else-if="detail.summary.nextAction === 'view_result' && detail.summary.resultId"
          class="primary"
          @click="openResult"
        >
          查看学习结果 <text class="button-arrow">→</text>
        </button>
        <button
          v-else
          class="primary"
          disabled
        >
          {{ actionButtonLabel }}
        </button>
        <view
          v-if="error"
          class="inline-error"
          role="alert"
          >{{ error }}</view
        >
      </view>
      <view class="route-section">
        <view class="section-head"
          ><view class="section-heading"
            ><view class="section-mark" /><text class="section-title">顺序学习路线</text></view
          ><text class="route-progress">{{
            progress ? `${progress.completed}/${progress.total}` : '等待生成'
          }}</text></view
        >
        <scroll-view
          class="route-scroll"
          :scroll-y="timeline.length > 3"
          enhanced
          :show-scrollbar="false"
        >
          <view
            v-if="!detail.steps.length"
            class="empty-route"
            >学习计划暂未生成步骤。请等待生成，或使用上方操作重试。</view
          >
          <view
            v-for="(item, index) in timeline"
            :id="`plan-step-${item.number}`"
            :key="item.kind === 'test' ? 'final-test' : item.step.id"
            class="timeline-item"
            :class="{
              'timeline-last': index === timeline.length - 1,
              'timeline-done': item.state === 'completed',
              'timeline-active': item.state === 'active',
              'timeline-locked': item.state === 'locked',
            }"
          >
            <view class="timeline-axis"
              ><view class="step-index">{{ item.state === 'completed' ? '✓' : item.number }}</view
              ><view
                v-if="index < timeline.length - 1"
                class="timeline-line"
            /></view>
            <view class="step-body">
              <view class="step-heading">
                <view class="step-copy">
                  <view class="step-title-row"
                    ><text class="step-title">{{ item.kind === 'test' ? '最终测试' : item.step.title }}</text
                    ><text
                      v-if="item.kind === 'test'"
                      class="review-tag"
                      >{{ reviewLabel }}</text
                    ></view
                  >
                  <text class="step-meta">{{
                    item.kind === 'test'
                      ? `${detail.testSummary.questionCount} 道题 · ${testState}`
                      : `${item.step.kind === 'reading' ? '资料学习' : 'AI 合成病例'} · ${stepStatus(item.step.status)}`
                  }}</text>
                </view>
                <button
                  v-if="item.kind === 'resource'"
                  class="step-link"
                  :disabled="item.state === 'locked'"
                  :aria-label="`${item.state === 'completed' ? '回看' : '进入'}${item.step.title}`"
                  @click="openStep(item.step)"
                >
                  <view class="step-link-pill">
                    {{ item.state === 'completed' ? '回看' : item.state === 'locked' ? '未解锁' : '进入' }}
                    <text class="link-arrow">›</text>
                  </view>
                </button>
                <button
                  v-else
                  class="step-link"
                  :disabled="item.state === 'locked'"
                  :aria-label="item.state === 'completed' ? '查看学习结果' : '进入最终测试'"
                  @click="item.state === 'completed' ? openResult() : startTest()"
                >
                  <view class="step-link-pill">
                    {{ item.state === 'completed' ? '回看' : '进入' }} <text class="link-arrow">›</text>
                  </view>
                </button>
              </view>
              <text
                v-if="item.kind === 'test' && item.state === 'locked' && detail.lockReasons.length"
                class="lock-reason"
                >{{ testLockText }}</text
              >
              <view
                class="step-preview"
                aria-hidden="true"
                ><view class="preview-icon"
                  ><image
                    :src="
                      item.kind === 'test'
                        ? '/static/learning-plan-test.svg'
                        : item.step.kind === 'reading'
                          ? '/static/learning-plan-reading.svg'
                          : '/static/learning-plan-case.svg'
                    "
                    mode="aspectFit" /></view
                ><view class="preview-lines"><view class="preview-line short" /><view class="preview-line" /></view
                ><image
                  v-if="
                    item.state === 'locked' ||
                    (item.kind === 'resource' && item.step.kind === 'case' && item.state === 'active')
                  "
                  class="preview-lock"
                  :src="
                    item.state === 'active'
                      ? '/static/learning-plan-lock-open.svg'
                      : '/static/learning-plan-lock-closed.svg'
                  "
                  mode="aspectFit"
                />
                <text
                  v-else
                  class="preview-state"
                  >{{ item.state === 'completed' ? '✓' : '›' }}</text
                ></view
              >
            </view>
          </view>
        </scroll-view>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onBackPress, onHide, onLoad, onShow, onUnload } from '@dcloudio/uni-app'
import {
  createLearningRequestId,
  getLearningRoute,
  retryLearningRouteGeneration,
  type LearningRouteDetail,
  type LearningRouteStep,
} from '@/features/learning/public'
import { getSession, requireRole } from '@/features/identity/public'
import { backOrRoute, goDetail, handleBackPress, ROUTES } from '@/platform/navigation'
import { planProgress, planTimeline } from './planTimeline'

const detail = ref<LearningRouteDetail>()
const statusBarHeight = ref(0)
const navigationHeight = ref(44)
const navigationOffset = computed(() => statusBarHeight.value + navigationHeight.value)
const error = ref('')
const loading = ref(false)
const busy = ref(false)
let routeId = ''
let valid = false
let identity = ''
let contextVersion = 0
let requestVersion = 0
let pollTimer: ReturnType<typeof setTimeout> | undefined
let pollStarted = 0
let retryRequest: { component: 'route' | 'test'; id: string } | undefined
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
const timeline = computed(() => (detail.value ? planTimeline(detail.value) : []))
const progress = computed(() => planProgress(timeline.value))
const currentStep = computed(() => {
  const item = timeline.value.find((entry) => entry.kind === 'resource' && entry.state === 'active')
  return item?.kind === 'resource' ? item.step : undefined
})
const reviewLabel = computed(() =>
  detail.value?.testSummary.reviewKind === 'teacher'
    ? '教师审阅'
    : detail.value?.testSummary.reviewKind === 'ai_direct'
      ? 'AI 生成'
      : '待审阅',
)
const diagnosisText = computed(() => {
  const value = detail.value?.diagnosisSummary || {}
  const outcome = value.outcome ?? value.diagnosis_outcome
  if (typeof outcome === 'string' && outcome.trim()) return outcome
  return '这份学习计划根据本次研讨分析生成，按顺序完成资料学习、病例推理和最终测试。'
})
const actionTitle = computed(
  () =>
    ({
      reading: '先阅读计划资料',
      case: '继续 AI 病例学习',
      test: '学习路线已完成',
      wait_grade: '答案已提交，正在判分',
      wait_teacher: '等待教师开放测试',
      wait_generation: '学习计划正在生成',
      retry_route: '学习计划生成失败',
      retry_test: '最终测试生成失败',
      view_result: '本次学习已完成',
    })[detail.value?.summary.nextAction || ''] || '按顺序完成学习计划',
)
const actionDescription = computed(() =>
  detail.value?.summary.nextAction === 'wait_teacher'
    ? '你可以先完成路线学习；教师开放最终测试后，本页会显示开始入口。'
    : detail.value?.summary.nextAction === 'wait_grade'
      ? '简答题按已冻结的参考答案与要点评分。完成后可查看逐题解析。'
      : detail.value?.summary.nextAction === 'wait_generation'
        ? '路线和最终测试分别生成，已发布的学习内容仍可继续使用。'
        : detail.value?.summary.nextAction === 'retry_route' || detail.value?.summary.nextAction === 'retry_test'
          ? '可以安全重试未成功的部分，已生成内容和学习进度会保留。'
          : '每一步按路线顺序解锁，病例学习过程不计分。',
)
const actionButtonLabel = computed(() =>
  detail.value?.summary.nextAction === 'wait_teacher'
    ? '等待教师开放'
    : detail.value?.summary.nextAction === 'wait_generation'
      ? '正在处理中'
      : '暂不可开始',
)
const testState = computed(() =>
  detail.value?.summary.resultId || detail.value?.summary.status === 'completed'
    ? '已提交'
    : detail.value?.summary.nextAction === 'wait_grade'
      ? '判分中'
      : detail.value?.testSummary.reviewState === 'released' || detail.value?.testSummary.reviewState === 'not_required'
        ? detail.value?.testSummary.canStart
          ? '已开放'
          : '等待路线完成'
        : detail.value?.testSummary.reviewState === 'needs_changes'
          ? '等待教师修改'
          : '等待教师审阅开放',
)
const testLockText = computed(() =>
  detail.value?.lockReasons
    .map(
      (x) =>
        ({
          ROUTE_INCOMPLETE: '请先完成全部资料和病例步骤。',
          TEST_NOT_RELEASED: '课堂测试经教师审阅开放后才能作答。',
          TEST_NOT_GENERATED: '测试内容尚未生成。',
        })[x] || x,
    )
    .join(' '),
)
function stepStatus(value: string) {
  return value === 'completed'
    ? '已完成'
    : value === 'in_progress'
      ? '进行中'
      : value === 'available'
        ? '待开始'
        : '未解锁'
}
function openStep(step: LearningRouteStep) {
  if (step.status === 'locked') return
  goDetail(
    step.kind === 'reading' ? ROUTES.studentRouteReading : ROUTES.studentRouteCase,
    step.kind === 'reading' ? { routeId, stepId: step.id } : { routeId, caseId: step.caseId || '' },
  )
}
function openCurrentStep() {
  if (currentStep.value) openStep(currentStep.value)
}
function startTest() {
  if (detail.value?.canStartTest) goDetail(ROUTES.studentFinalTest, { routeId, testId: detail.value.testSummary.id })
}
function openGrading() {
  if (detail.value?.summary.nextAction === 'wait_grade')
    goDetail(ROUTES.studentFinalTest, { routeId, testId: detail.value.testSummary.id })
}
function openResult() {
  if (detail.value?.summary.resultId) goDetail(ROUTES.studentLearningResult, { routeId })
}
function back() {
  backOrRoute(ROUTES.studentLearningPlans)
}
async function retry() {
  if (!detail.value || busy.value) return
  const session = getSession()
  if (!session || session.role !== 'student' || session.openid !== identity) return
  const context = contextVersion
  const requestedIdentity = identity
  const component = detail.value.summary.nextAction === 'retry_route' ? 'route' : 'test'
  if (!retryRequest || retryRequest.component !== component)
    retryRequest = { component, id: createLearningRequestId('retry') }
  busy.value = true
  error.value = ''
  try {
    await retryLearningRouteGeneration(routeId, component, retryRequest.id)
    if (context !== contextVersion || getSession()?.openid !== requestedIdentity) return
    retryRequest = undefined
    await load()
  } catch (reason) {
    if (context === contextVersion && getSession()?.openid === requestedIdentity)
      error.value = reason instanceof Error ? reason.message : '重试失败，请稍后再试。'
  } finally {
    if (context === contextVersion && getSession()?.openid === requestedIdentity) busy.value = false
  }
}
async function load() {
  const session = getSession()
  if (!valid || !requireRole('student') || session?.role !== 'student' || !session.openid) return
  if (identity !== session.openid) resetIdentity(session.openid)
  if (loading.value) return
  const token = ++requestVersion
  const requestedIdentity = session.openid
  const context = contextVersion
  loading.value = true
  error.value = ''
  try {
    const value = await getLearningRoute(routeId)
    if (!isCurrent(token, requestedIdentity, context)) return
    detail.value = value
    schedulePoll()
  } catch (reason) {
    if (isCurrent(token, requestedIdentity, context))
      error.value = reason instanceof Error ? reason.message : '学习计划加载失败。'
  } finally {
    if (isCurrent(token, requestedIdentity, context)) loading.value = false
  }
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
function resetIdentity(nextIdentity: string) {
  identity = nextIdentity
  contextVersion += 1
  requestVersion += 1
  clearPoll()
  detail.value = undefined
  error.value = ''
  loading.value = false
  busy.value = false
  retryRequest = undefined
  pollStarted = 0
}
function clearPoll() {
  if (pollTimer) clearTimeout(pollTimer)
  pollTimer = undefined
}
function schedulePoll() {
  clearPoll()
  if (!detail.value || detail.value.summary.nextAction !== 'wait_generation') return
  if (!pollStarted) pollStarted = Date.now()
  if (Date.now() - pollStarted >= 120_000) {
    error.value = '仍在处理中，可手动刷新查看。'
    pollStarted = 0
    return
  }
  pollTimer = setTimeout(() => {
    pollTimer = undefined
    void load()
  }, 3000)
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
  valid = uuid.test(routeId)
  if (!valid) error.value = '学习计划编号无效。'
  requireRole('student')
})
onShow(() => {
  const session = getSession()
  if (!requireRole('student') || session?.role !== 'student' || !session.openid) {
    resetIdentity('')
    return
  }
  if (identity !== session.openid) resetIdentity(session.openid)
  if (valid) {
    pollStarted = 0
    void load()
  }
})
function hide() {
  clearPoll()
  requestVersion += 1
  loading.value = false
}
onHide(hide)
onUnload(hide)
onBackPress(({ from }) => handleBackPress(from, ROUTES.studentLearningPlans))
</script>

<style scoped>
.page {
  position: relative;
  min-height: 100vh;
  box-sizing: border-box;
  padding-bottom: calc(64rpx + env(safe-area-inset-bottom));
  color: #0a1676;
  background: linear-gradient(180deg, #eaf7ff 0, #f4fbff 430rpx, #f8fcff 100%);
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
  background: #f9fcff;
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
  align-items: center;
  justify-content: center;
  max-width: 920px;
  margin: 0 auto;
}
.navbar-title {
  color: #0a1676;
  font-size: 32rpx;
  font-weight: 700;
}
.nav-back {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 12rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 88rpx;
  margin: 0;
  padding: 0;
  background: transparent;
}
.back-chevron {
  width: 22rpx;
  height: 22rpx;
  border-bottom: 4rpx solid #121b36;
  border-left: 4rpx solid #121b36;
  transform: rotate(45deg);
}
.page-art {
  position: absolute;
  top: 0;
  right: 0;
  width: 100%;
  pointer-events: none;
}
.hero-document {
  position: absolute;
  top: 140rpx;
  right: 0;
  width: 285rpx;
  height: 240rpx;
  pointer-events: none;
}
.intro,
.action,
.route-section,
.state {
  position: relative;
  z-index: 1;
}
.intro,
.action,
.route-section,
.state {
  box-sizing: border-box;
  max-width: 920px;
  margin-right: auto;
  margin-left: auto;
}
.intro {
  display: flex;
  flex-direction: column;
  gap: 17rpx;
  padding: 44rpx 32rpx 46rpx;
}
.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  align-items: baseline;
  color: #535da4;
  font-size: 25rpx;
  line-height: 1.5;
}
.meta text:first-child {
  color: #1299e9;
}
.meta-divider {
  color: #8aa8d6;
}
.title {
  color: #0a1676;
  font-size: 44rpx;
  font-weight: 700;
  line-height: 1.32;
}
.summary {
  color: #515ca5;
  font-size: 28rpx;
  line-height: 1.62;
}
.action {
  width: calc(100% - 60rpx);
  margin: 0 auto 48rpx;
  padding: 25rpx 22rpx 22rpx;
  overflow: hidden;
  background: linear-gradient(
    118deg,
    rgba(235, 246, 255, 0.96),
    rgba(255, 255, 255, 0.92) 54%,
    rgba(205, 231, 255, 0.92)
  );
  border: 1px solid rgba(255, 255, 255, 0.94);
  border-radius: 25rpx;
  box-shadow: 0 12rpx 34rpx rgba(43, 125, 202, 0.11);
}
.action-art {
  position: absolute;
  top: -14rpx;
  right: -8rpx;
  width: 250rpx;
  height: 164rpx;
  pointer-events: none;
}
.eyebrow,
.action-title,
.hint {
  position: relative;
  z-index: 1;
}
.eyebrow {
  display: inline-block;
  width: fit-content;
  padding: 9rpx 16rpx;
  color: #fff;
  background: linear-gradient(105deg, #54caff, #0a9af3);
  border-radius: 11rpx;
  box-shadow:
    0 4rpx 8rpx rgba(5, 78, 170, 0.36),
    0 11rpx 20rpx rgba(7, 109, 236, 0.55),
    0 0 28rpx rgba(50, 166, 255, 0.68);
  font-size: 24rpx;
  font-weight: 700;
}
.action-title {
  display: block;
  max-width: 72%;
  margin-top: 20rpx;
  color: #081575;
  font-size: 38rpx;
  font-weight: 700;
  line-height: 1.35;
}
.action-empty .action-title {
  max-width: 100%;
}
.hint {
  display: block;
  margin-top: 12rpx;
  color: #525da4;
  font-size: 27rpx;
  line-height: 1.6;
}
.primary {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 88rpx;
  margin: 20rpx 0 0;
  color: #fff;
  background: linear-gradient(100deg, #02c2c9, #0bafd6 60%, #3f92fa);
  border-radius: 999rpx;
  box-shadow: 0 9rpx 19rpx rgba(22, 157, 226, 0.16);
  font-size: 31rpx;
  font-weight: 700;
  line-height: 1.3;
}
.primary[disabled] {
  color: #687eab;
  background: #dceaf1;
  box-shadow: none;
  opacity: 1;
}
.button-arrow {
  margin-left: 12rpx;
  font-size: 38rpx;
  font-weight: 400;
}
.route-section {
  padding: 0 32rpx;
}
.route-scroll {
  width: 100%;
}
.section-head,
.section-heading {
  display: flex;
  align-items: center;
}
.section-head {
  justify-content: space-between;
  gap: 20rpx;
  margin-bottom: 28rpx;
}
.section-heading {
  gap: 20rpx;
}
.section-mark {
  width: 10rpx;
  height: 38rpx;
  background: linear-gradient(180deg, #00e2e2, #0aaaf4);
  border-radius: 999rpx;
}
.section-title {
  color: #071579;
  font-size: 36rpx;
  font-weight: 700;
}
.route-progress {
  color: #5259a7;
  font-size: 29rpx;
  white-space: nowrap;
}
.empty-route {
  margin: 0 0 20rpx 70rpx;
  color: #596999;
  font-size: 25rpx;
  line-height: 1.6;
}
.timeline-item {
  display: flex;
  align-items: stretch;
  gap: 22rpx;
}
.timeline-axis {
  position: relative;
  display: flex;
  flex: 0 0 72rpx;
  justify-content: center;
}
.step-index {
  z-index: 1;
  display: flex;
  width: 60rpx;
  height: 60rpx;
  flex: 0 0 60rpx;
  align-items: center;
  justify-content: center;
  color: #11bbd3;
  background: #dbf8fb;
  border-radius: 50%;
  font-size: 29rpx;
  font-weight: 700;
}
.timeline-done .step-index {
  color: #02b8cb;
  background: #ddf7fa;
}
.timeline-active .step-index {
  color: #0fb9c9;
  background: linear-gradient(145deg, #e5fafb, #c8f3f6);
}
.timeline-locked .step-index {
  color: #6783b7;
  background: #e8f4f9;
}
.timeline-last.timeline-locked .step-index {
  color: #fff;
  background: linear-gradient(145deg, #13b8e9, #147ff5);
}
.timeline-last.timeline-active .step-index {
  color: #fff;
  background: linear-gradient(145deg, #13b8e9, #147ff5);
}
.timeline-line {
  position: absolute;
  top: 60rpx;
  bottom: 0;
  left: 34rpx;
  width: 4rpx;
  background: linear-gradient(180deg, #10c9d0, #168ef2);
  border-radius: 999rpx;
}
.step-body {
  min-width: 0;
  flex: 1;
  padding: 1rpx 0 26rpx;
}
.timeline-last .step-body {
  padding-bottom: 0;
}
.step-heading {
  display: flex;
  align-items: flex-start;
  gap: 12rpx;
  min-height: 65rpx;
}
.step-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 7rpx;
}
.step-title-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12rpx;
}
.step-title {
  color: #0a1676;
  font-size: 30rpx;
  font-weight: 700;
  line-height: 1.35;
  overflow-wrap: anywhere;
}
.step-meta {
  color: #5b62a4;
  font-size: 25rpx;
  line-height: 1.45;
}
.step-link {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  min-width: 98rpx;
  min-height: 88rpx;
  margin: 0;
  padding: 0;
  color: #02b9d0;
  background: transparent;
  border-radius: 999rpx;
  font-size: 22rpx;
  line-height: 1.2;
}
.step-link-pill {
  display: flex;
  min-width: 96rpx;
  min-height: 44rpx;
  box-sizing: border-box;
  align-items: center;
  justify-content: center;
  padding: 0 14rpx;
  background: #ddf8fa;
  border-radius: 999rpx;
}
.step-link[disabled] {
  color: #818db0;
  background: transparent !important;
  opacity: 1;
}
.step-link::after {
  border: 0;
}
.step-link[disabled] .step-link-pill {
  background: #e8edf2;
}
.link-arrow {
  margin-left: 6rpx;
  font-size: 28rpx;
  line-height: 0.7;
}
.review-tag {
  padding: 4rpx 14rpx;
  color: #04b6ce;
  background: #e0f8fb;
  border-radius: 999rpx;
  font-size: 22rpx;
  white-space: nowrap;
}
.lock-reason {
  display: block;
  margin-top: 8rpx;
  color: #db692d;
  font-size: 24rpx;
  line-height: 1.5;
}
.step-preview {
  display: flex;
  height: 112rpx;
  box-sizing: border-box;
  align-items: center;
  gap: 20rpx;
  margin-top: 18rpx;
  padding: 0 20rpx;
  background: rgba(237, 247, 254, 0.48);
  border: 1px solid #d9eaf7;
  border-radius: 17rpx;
}
.preview-icon {
  display: flex;
  width: 66rpx;
  height: 66rpx;
  flex: 0 0 66rpx;
  align-items: center;
  justify-content: center;
  background: #e0f4ff;
  border-radius: 12rpx;
}
.preview-icon image {
  width: 48rpx;
  height: 48rpx;
}
.preview-lines {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 13rpx;
}
.preview-line {
  width: 84%;
  height: 11rpx;
  background: #dce6f2;
  border-radius: 999rpx;
}
.preview-line.short {
  width: 66%;
}
.preview-state {
  color: #8adce7;
  font-size: 44rpx;
  font-weight: 700;
}
.preview-lock {
  width: 40rpx;
  height: 48rpx;
  flex: 0 0 40rpx;
}
.page-three-steps,
.page-multi-steps {
  padding-bottom: calc(24rpx + env(safe-area-inset-bottom));
}
.page-three-steps .intro,
.page-multi-steps .intro {
  padding-top: 28rpx;
  padding-bottom: 28rpx;
}
.page-three-steps .action,
.page-multi-steps .action {
  margin-bottom: 30rpx;
  padding-top: 20rpx;
  padding-bottom: 18rpx;
}
.page-three-steps .action-title,
.page-multi-steps .action-title {
  margin-top: 14rpx;
}
.page-three-steps .hint,
.page-multi-steps .hint {
  margin-top: 8rpx;
}
.page-three-steps .primary,
.page-multi-steps .primary {
  min-height: 78rpx;
  margin-top: 14rpx;
}
.page-three-steps .section-head,
.page-multi-steps .section-head {
  margin-bottom: 18rpx;
}
.page-three-steps .step-body,
.page-multi-steps .step-body {
  padding-bottom: 17rpx;
}
.page-three-steps .step-preview,
.page-multi-steps .step-preview {
  height: 100rpx;
  margin-top: 12rpx;
}
.page-multi-steps {
  display: flex;
  height: 100vh;
  min-height: 0;
  flex-direction: column;
  overflow: hidden;
}
.page-multi-steps .intro,
.page-multi-steps .action {
  flex: 0 0 auto;
}
.page-multi-steps .route-section {
  display: flex;
  width: 100%;
  min-height: 0;
  flex: 1 1 auto;
  flex-direction: column;
}
.page-multi-steps .section-head {
  flex: 0 0 auto;
}
.page-multi-steps .route-scroll {
  height: 0;
  min-height: 0;
  flex: 1 1 auto;
}
.state {
  display: flex;
  min-height: 220rpx;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 18rpx;
  margin: 32rpx;
  padding: 32rpx;
  color: #5d6a9b;
  text-align: center;
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid #dbeaf5;
  border-radius: 22rpx;
}
.state button {
  min-height: 88rpx;
  padding: 0 24rpx;
  color: #087fba;
  background: #e3f7fa;
  border-radius: 16rpx;
}
.state.error {
  color: #9c3f4b;
}
.state button.quiet {
  background: transparent;
}
.inline-error {
  position: relative;
  z-index: 1;
  margin-top: 12rpx;
  color: #a4464c;
  font-size: 23rpx;
}
</style>
