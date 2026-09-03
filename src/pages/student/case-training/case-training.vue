<template>
  <view class="safe-page page"
    ><view
      v-if="attempt"
      class="card head"
      ><text class="title">{{ attempt.opening.chiefComplaint }}</text
      ><text class="muted">虚拟患者 · 合成教学病例，不构成诊疗建议</text
      ><view class="progress"
        ><text
          v-for="item in caseStages"
          :key="item.id"
          :class="{ active: item.id === attempt.currentStage, done: done(item.id) }"
          >{{ item.label }}</text
        ></view
      ></view
    ><MedState
      v-if="error"
      icon="retry"
      title="训练加载失败"
      :description="error"
      :action-label="id ? '重新加载' : '返回病例列表'"
      :secondary-action-label="id ? '返回病例列表' : ''"
      @action="id ? load() : back()"
      @secondary-action="back"
    /><view
      v-if="attempt"
      class="card form"
      ><template v-if="attempt.currentStage === 'history'"
        ><text class="section">虚拟患者对话</text
        ><view
          v-for="message in attempt.messages"
          :key="message.id"
          class="message"
          :class="message.role"
          >{{ message.content }}</view
        ><input
          v-model="question"
          placeholder="例如：发热多久、最高多少度？"
        /><button
          class="secondary"
          :disabled="sending"
          @click="ask"
        >
          询问患者</button
        ><textarea
          v-model="summary"
          placeholder="病史小结"
        /><textarea
          v-model="keyFindingsText"
          placeholder="关键发现，以逗号分隔"
        /></template
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
        @click="submit"
      >
        提交{{ stageLabel(attempt.currentStage) }}
      </button></view
    ></view
  >
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { onBackPress, onLoad } from '@dcloudio/uni-app'
import MedState from '@/components/ui/MedState.vue'
import { requireRole } from '@/features/identity/public'
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
let id = ''
const stageLabel = (stage: string) => caseStages.find((i) => i.id === stage)?.label || '报告'
const done = (stage: string) =>
  attempt.value
    ? caseStages.findIndex((i) => i.id === stage) < caseStages.findIndex((i) => i.id === attempt.value!.currentStage)
    : false
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
  try {
    attempt.value = await getCaseAttemptAsync(id)
    if (!attempt.value) error.value = '训练不存在或已不可用'
  } catch (e) {
    error.value = e instanceof Error ? e.message : '请重试'
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
  sending.value = true
  try {
    await sendPatientMessageAsync(id, question.value)
    question.value = ''
    await load()
  } finally {
    sending.value = false
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
  submitting.value = true
  try {
    await submitCaseStageAsync(id, answer())
    summary.value = ''
    keyFindingsText.value = ''
    safetyText.value = ''
    differentialItems.value = [
      { diagnosis: '', supportingEvidence: '', opposingEvidence: '' },
      { diagnosis: '', supportingEvidence: '', opposingEvidence: '' },
    ]
    testItems.value = [{ testName: '', rationale: '', priority: 'necessary' }]
    managementItems.value = [{ action: '', rationale: '' }]
    await load()
  } catch (e) {
    uni.showToast({ title: e instanceof Error ? e.message : '提交失败', icon: 'none' })
  } finally {
    submitting.value = false
  }
}
async function complete() {
  if (completing.value) return
  completing.value = true
  try {
    await completeCaseAttemptAsync(id)
    goReplace(ROUTES.studentCaseReport, { attemptId: id })
  } catch (e) {
    uni.showToast({ title: e instanceof Error ? e.message : '生成报告失败', icon: 'none' })
  } finally {
    completing.value = false
  }
}
onLoad((query) => {
  if (!requireRole('student')) return
  id = String(query?.id || '')
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
  padding: 24rpx 24rpx 150rpx;
}
.head,
.form {
  display: flex;
  padding: 28rpx;
  flex-direction: column;
  gap: 18rpx;
}
.title {
  font-size: 32rpx;
  font-weight: 700;
}
.muted {
  color: var(--med-muted);
  font-size: 22rpx;
}
.progress {
  display: flex;
  flex-wrap: wrap;
  gap: 8rpx;
}
.progress text {
  padding: 7rpx;
  color: var(--med-muted);
  background: var(--med-divider);
  border-radius: 99rpx;
  font-size: 19rpx;
}
.progress .active {
  color: #fff;
  background: var(--med-brand);
}
.progress .done {
  color: var(--med-brand);
  background: var(--med-brand-soft);
}
.section {
  font-size: 28rpx;
  font-weight: 700;
}
.message {
  margin: 4rpx 0;
  padding: 16rpx;
  border-radius: 16rpx;
  line-height: 1.5;
}
.message.user {
  background: var(--med-brand-soft);
}
.message.assistant {
  background: #f1f5f9;
}
.answer-card {
  display: flex;
  padding: 16rpx;
  flex-direction: column;
  gap: 12rpx;
  background: #f8fafc;
  border: 1rpx solid #e2e8f0;
  border-radius: 14rpx;
}
input,
textarea {
  width: auto;
  min-height: 80rpx;
  padding: 16rpx;
  border: 1rpx solid #cbd5e1;
  border-radius: 14rpx;
  background: #fff;
}
textarea {
  min-height: 160rpx;
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
.bottom {
  position: fixed;
  right: 24rpx;
  bottom: calc(18rpx + env(safe-area-inset-bottom));
  left: 24rpx;
}
.bottom .primary {
  width: 100%;
}
</style>
