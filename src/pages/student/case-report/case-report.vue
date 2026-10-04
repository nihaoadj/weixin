<template>
  <view class="safe-page page">
    <MedState
      v-if="accessDenied"
      variant="error"
      icon="history"
      title="学生身份已变化"
      description="个人训练分析已清除。请使用当前学生账号重新进入。"
    />
    <template v-else>
      <MedState
        v-if="error"
        icon="retry"
        title="报告加载失败"
        :description="error"
        :action-label="id ? '重新加载' : returnLabel"
        :secondary-action-label="id ? returnLabel : ''"
        @action="id ? load() : back()"
        @secondary-action="back"
      />
      <view
        v-if="report"
        class="card hero"
        ><text class="eyebrow-label">{{ report.fallbackUsed ? '确定性兜底报告' : '模型报告' }}</text
        ><text class="score">{{ report.totalScore }}</text
        ><text>总分 / 100</text><text class="muted">{{ report.summary }}</text></view
      >
      <view
        v-if="report"
        class="card body"
        ><text class="section">六维评价</text
        ><view
          v-for="dimension in report.dimensions"
          :key="dimension.dimensionId"
          class="dimension"
          ><view
            ><text>{{ dimension.label }}</text
            ><text>{{ dimension.score }}</text></view
          ><view class="bar"><view :style="{ width: `${dimension.score}%` }" /></view
          ><text class="muted">{{ dimension.feedback }}</text
          ><text class="evidence">{{ dimension.evidence.join('；') }}</text
          ><text class="muted">下一步：{{ dimension.nextStep }}</text></view
        ></view
      >
      <view
        v-if="report"
        class="card body"
        ><text class="section">优势</text><text>{{ report.strengths.join('、') || '继续完成更多高质量推理。' }}</text
        ><text class="section">薄弱点</text><text>{{ report.weaknesses.join('、') || '暂无明显薄弱维度。' }}</text
        ><view
          v-if="report.comparison"
          class="comparison"
          ><text class="section">较上次</text><text>总分 {{ signed(report.comparison.totalDelta) }}</text
          ><text
            v-for="item in report.comparison.dimensions"
            :key="item.dimensionId"
            >{{ item.dimensionId }}：{{ signed(item.delta) }}</text
          ></view
        ><button
          class="primary"
          @click="retry"
        >
          继续病例训练
        </button>
        <button
          class="secondary"
          @click="back"
        >
          返回病例列表
        </button></view
      ></template
    >
  </view>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { onBackPress, onLoad, onShow } from '@dcloudio/uni-app'
import MedState from '@/components/ui/MedState.vue'
import { getSession, requireRole } from '@/features/identity/public'
import { getCaseAssessmentAsync, getCaseAttemptAsync, startCaseAttemptAsync } from '@/features/training/public'
import { backOrRoute, goReplace, handleBackPress, ROUTES } from '@/platform/navigation'
import type { CaseAssessment } from '@/types/case'
const report = ref<CaseAssessment>()
const error = ref('')
const accessDenied = ref(false)
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

function clearReportData() {
  pageContextVersion += 1
  report.value = undefined
  error.value = ''
  id = ''
}

function denyStudentPage() {
  clearReportData()
  identityInitialized = false
  accessDenied.value = true
}
const returnLabel = '返回病例列表'
async function load() {
  const identity = studentIdentity
  const contextVersion = pageContextVersion
  if (!identity || accessDenied.value || !id) return
  try {
    const value = await getCaseAssessmentAsync(id)
    if (!isCurrentStudentPage(contextVersion, identity)) return
    report.value = value
    if (!report.value) error.value = '报告尚未生成'
  } catch (e) {
    if (isCurrentStudentPage(contextVersion, identity)) error.value = e instanceof Error ? e.message : '请重试'
  }
}
const signed = (value: number) => (value > 0 ? `+${value}` : String(value))
async function retry() {
  const identity = studentIdentity
  const contextVersion = pageContextVersion
  if (!identity || accessDenied.value) return
  const attempt = await getCaseAttemptAsync(id)
  if (!isCurrentStudentPage(contextVersion, identity) || !attempt) return
  const next = await startCaseAttemptAsync(attempt.problemId, id)
  if (!isCurrentStudentPage(contextVersion, identity)) return
  goReplace(ROUTES.studentCaseTraining, { id: next.id })
}
function back() {
  backOrRoute(ROUTES.studentCases)
}
onLoad((query) => {
  const session = getSession()
  if (!requireRole('student') || session?.role !== 'student' || !session.openid) {
    denyStudentPage()
    return
  }
  studentIdentity = session.openid
  identityInitialized = true
  accessDenied.value = false
  id = String(query?.attemptId || '')
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
    denyStudentPage()
    return
  }
  if (initialShowPending) {
    initialShowPending = false
    return
  }
  void load()
})

onBackPress(({ from }) => handleBackPress(from, ROUTES.studentCases))
</script>
<style scoped>
.page {
  padding: 28rpx;
}
.hero,
.body {
  display: flex;
  margin-bottom: 20rpx;
  padding: 30rpx;
  flex-direction: column;
  gap: 14rpx;
}
.score {
  color: var(--med-brand);
  font-size: 80rpx;
  font-weight: 800;
}
.section {
  margin-top: 8rpx;
  color: var(--med-navy);
  font-size: 29rpx;
  font-weight: 700;
}
.muted {
  color: var(--med-muted);
  font-size: 22rpx;
  line-height: 1.5;
}
.context-error {
  color: #9c3f3a;
  font-size: 23rpx;
  line-height: 1.5;
}
.dimension {
  display: flex;
  padding: 18rpx 0;
  flex-direction: column;
  gap: 8rpx;
  border-bottom: 1rpx solid var(--med-divider);
}
.dimension > view:first-child {
  display: flex;
  justify-content: space-between;
}
.bar {
  height: 12rpx;
  background: var(--med-divider);
  border-radius: 99rpx;
}
.bar view {
  height: 100%;
  background: var(--med-brand);
  border-radius: 99rpx;
}
.evidence {
  font-size: 22rpx;
  white-space: pre-wrap;
}
.comparison {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}
.primary,
.secondary {
  height: 78rpx;
  line-height: 78rpx;
  color: #fff;
  background: var(--med-brand);
}
.secondary {
  color: var(--med-brand);
  background: var(--med-brand-soft);
}
</style>
