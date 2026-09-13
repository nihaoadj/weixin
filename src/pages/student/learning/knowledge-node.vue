<template>
  <view class="safe-page node-page">
    <view
      v-if="loading"
      class="state-copy"
    >
      正在加载知识节点…
    </view>
    <view
      v-else-if="error"
      class="state-copy error-state"
      role="alert"
    >
      <text>{{ error }}</text>
      <button
        class="text-action"
        @click="returnToTree"
      >
        返回知识树
      </button>
    </view>
    <template v-else-if="point">
      <view class="node-head">
        <text class="eyebrow-label">{{ point.systemLabel }}</text>
        <view class="head-line">
          <text class="node-title">{{ point.title }}</text>
          <text :class="['status-pill', `status-${point.status}`]"
            >{{ statusMark(point.status) }} {{ statusLabel(point.status) }}</text
          >
        </view>
        <text class="objective">{{ point.objective }}</text>
        <text
          v-if="preparationNote"
          class="preparation-note"
        >
          {{ preparationNote }}
        </text>
      </view>

      <view class="content-section">
        <text class="section-kicker">学习目标</text>
        <text class="description">{{ study?.material?.objective || point.objective }}</text>
        <text class="section-kicker">待解释情境</text>
        <text class="description">{{ study?.material?.scenario || '请先围绕观察线索形成你的问题和假设。' }}</text>
      </view>

      <view
        v-if="study?.material"
        class="content-section"
      >
        <text class="section-kicker">研讨准备</text>
        <view
          v-for="section in study.material.background"
          :key="section.title"
          class="study-section"
        >
          <text class="relationship-label">{{ section.title }}</text>
          <text class="description">{{ section.text }}</text>
        </view>
        <view class="study-section">
          <text class="relationship-label">{{ study.material.example.title }}</text>
          <text class="description">{{ study.material.example.text }}</text>
        </view>
        <text class="source-note"
          >固定材料版本 {{ study.material.version }} ·
          {{ study.material.reviewStatus === 'unreviewed' ? '合成材料，待教师审核' : '' }}</text
        >
      </view>

      <view class="content-section relationship-section">
        <text class="section-kicker">学习位置</text>
        <view class="relationship-group">
          <text class="relationship-label">前置知识</text>
          <text
            v-if="!prerequisites.length"
            class="relationship-empty"
          >
            可以从这里直接开始。
          </text>
          <button
            v-for="item in prerequisites"
            :key="item.code"
            class="relation-row"
            @click="openPoint(item.code)"
          >
            <text :class="['relation-mark', `status-${item.status}`]">{{ statusMark(item.status) }}</text>
            <view>
              <text>{{ item.title }}</text>
              <text>{{ statusLabel(item.status) }}</text>
            </view>
            <text>›</text>
          </button>
        </view>
        <view class="relationship-group">
          <text class="relationship-label">关联知识</text>
          <text
            v-if="!related.length"
            class="relationship-empty"
          >
            暂无额外关联节点。
          </text>
          <button
            v-for="item in related"
            :key="item.code"
            class="relation-row"
            @click="openPoint(item.code)"
          >
            <text :class="['relation-mark', `status-${item.status}`]">{{ statusMark(item.status) }}</text>
            <view>
              <text>{{ item.title }}</text>
              <text>{{ item.systemLabel }} · {{ statusLabel(item.status) }}</text>
            </view>
            <text>›</text>
          </button>
        </view>
      </view>

      <view class="content-section source-section">
        <text class="section-kicker">资料来源</text>
        <text>{{ study?.material.reference || point.reference }}</text>
        <text class="source-note">学习状态只由客观练习、复习记录和已确认薄弱证据更新。</text>
      </view>

      <view
        v-if="study?.practiceUnlocked && study.path"
        class="content-section"
      >
        <text class="section-kicker">针对补学</text>
        <view
          v-for="section in study.material.remediation"
          :key="section.title"
          class="study-section"
        >
          <text class="relationship-label">{{ section.title }}</text>
          <text class="description">{{ section.text }}</text>
        </view>
        <text class="section-kicker">自主 AI 练习</text>
        <text class="source-note"
          >AI 生成 · 未经教师审核。仅供个人练习，按 AI 参考答案反馈，不计正式成绩或知识点达标。</text
        >
        <button
          v-if="!practiceGroup || practiceGroup.status === 'failed'"
          class="secondary-action"
          :disabled="practiceBusy"
          @click="createPrivatePractice"
        >
          {{ practiceBusy ? '正在生成…' : '生成本轮 3 题练习' }}
        </button>
        <template v-else-if="practiceGroup.status === 'generating'">
          <text class="source-note">正在生成练习，请稍后刷新本页。</text>
        </template>
        <template v-else-if="currentPrivateQuestion">
          <text class="relationship-label"
            >第 {{ currentPrivateQuestion.index + 1 }} / {{ practiceGroup.questions.length }} 题</text
          >
          <text class="description">{{ currentPrivateQuestion.prompt }}</text>
          <button
            v-for="(option, index) in currentPrivateQuestion.options"
            :key="option"
            class="practice-option"
            :disabled="practiceBusy || Boolean(privateFeedback)"
            @click="answerPrivatePracticeQuestion(index)"
          >
            {{ String.fromCharCode(65 + index) }}. {{ option }}
          </button>
          <view
            v-if="privateFeedback"
            class="practice-feedback"
          >
            <text>{{ privateFeedback.correct ? '按 AI 参考答案：正确' : '按 AI 参考答案：需要补学' }}</text>
            <text>{{ privateFeedback.explanation }}</text>
            <text>建议复习：{{ formatDue(privateFeedback.dueAt) }}</text>
            <button
              class="secondary-action"
              @click="nextPrivateQuestion"
            >
              {{ hasNextPrivateQuestion ? '下一题' : '查看本轮结果' }}
            </button>
          </view>
        </template>
        <template v-else>
          <text class="source-note"
            >本轮练习已完成。{{
              practiceGroup.canRetest ? '错题可生成一组变式再测。' : '请结合补学内容复习，或开启新的研讨。'
            }}</text
          >
          <button
            v-if="practiceGroup.canRetest"
            class="secondary-action"
            :disabled="practiceBusy"
            @click="createPrivatePractice"
          >
            生成变式再测
          </button>
        </template>
      </view>

      <view class="node-actions">
        <button
          class="primary-action"
          @click="startDiscussion"
        >
          {{ study?.path ? (study.phase === 'completed' ? '查看已完成研讨' : '继续研讨') : '开始研讨' }}
        </button>
        <button
          class="secondary-action"
          :disabled="!canPractice"
          @click="startReview"
        >
          {{ study?.legacyAccess ? '进入已有自测与巩固' : '进入自测与巩固' }}
        </button>
        <text
          v-if="!canPractice"
          class="action-note"
          >{{ study?.lockReason || '完成四阶段研讨后开放练习。' }}</text
        >
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onBackPress, onLoad, onShow } from '@dcloudio/uni-app'
import {
  getKnowledgeMap,
  getStudyPractices,
  getPrivatePractice,
  generateStudyPractice,
  answerPrivatePractice,
  getStudyPath,
  startStudyPath,
  type KnowledgeMapPoint,
  type PrivatePracticeFeedback,
  type PrivatePracticeGroup,
  type StudyPathState,
} from '@/features/learning/public'
import { createPblMessageId } from '@/features/pbl/public'
import { requireRole } from '@/features/identity/public'
import { goDetail, goReplace, handleBackPress, ROUTES } from '@/platform/navigation'

const requestedCode = ref('')
const points = ref<KnowledgeMapPoint[]>([])
const point = ref<KnowledgeMapPoint>()
const study = ref<StudyPathState>()
const practiceGroup = ref<PrivatePracticeGroup>()
const privateFeedback = ref<PrivatePracticeFeedback>()
const practiceBusy = ref(false)
const privateQuestionIndex = ref<number>()
const loading = ref(false)
const error = ref('')
const byCode = computed(() => new Map(points.value.map((item) => [item.code, item])))
const prerequisites = computed(() =>
  (point.value?.prerequisiteCodes || [])
    .map((code) => byCode.value.get(code))
    .filter((item): item is KnowledgeMapPoint => Boolean(item)),
)
const related = computed(() =>
  (point.value?.relatedCodes || [])
    .map((code) => byCode.value.get(code))
    .filter((item): item is KnowledgeMapPoint => Boolean(item)),
)
const preparationNote = computed(() => {
  const incomplete = prerequisites.value.filter((item) => item.status !== 'stable')
  if (!incomplete.length) return ''
  return `建议先回顾：${incomplete.map((item) => item.title).join('、')}。你仍可直接学习当前节点。`
})

function statusLabel(status: KnowledgeMapPoint['status']) {
  return {
    not_started: '未开始',
    weak: '薄弱',
    learning: '学习中',
    due: '待复习',
    stable: '相对稳定',
  }[status]
}

function statusMark(status: KnowledgeMapPoint['status']) {
  return {
    not_started: '○',
    weak: '!',
    learning: '·',
    due: '◷',
    stable: '✓',
  }[status]
}

async function load() {
  if (!requestedCode.value || loading.value) return
  loading.value = true
  error.value = ''
  try {
    points.value = await getKnowledgeMap()
    point.value = byCode.value.get(requestedCode.value)
    if (!point.value) error.value = '未找到这个知识节点，可能已不在当前目录中。'
    else {
      study.value = await getStudyPath(point.value.code)
      if (study.value.path && study.value.practiceUnlocked) {
        const groups = await getStudyPractices(study.value.path.id)
        practiceGroup.value = [...groups].reverse().find((group) => group.status === 'ready') || groups[0]
        privateQuestionIndex.value = undefined
        privateFeedback.value = undefined
      }
    }
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '知识节点加载失败，请稍后重试。'
  } finally {
    loading.value = false
  }
}

function openPoint(code: string) {
  if (code === requestedCode.value) return
  goReplace(ROUTES.studentKnowledgeNode, { topicCode: code })
}

function returnToTree() {
  goReplace(ROUTES.studentCases, { view: 'knowledge' })
}

const canPractice = computed(() => Boolean(study.value?.practiceUnlocked || study.value?.legacyAccess))
const currentPrivateQuestion = computed(() => {
  if (!practiceGroup.value || privateQuestionIndex.value !== undefined)
    return practiceGroup.value?.questions.find((question) => question.index === privateQuestionIndex.value)
  const attempted = new Set(practiceGroup.value.attempts.map((attempt) => attempt.questionIndex))
  return practiceGroup.value.questions.find((question) => !attempted.has(question.index))
})
const hasNextPrivateQuestion = computed(() => {
  if (!practiceGroup.value || !currentPrivateQuestion.value) return false
  return practiceGroup.value.questions.some(
    (question) =>
      question.index > currentPrivateQuestion.value!.index &&
      !practiceGroup.value!.attempts.some((attempt) => attempt.questionIndex === question.index),
  )
})

async function startDiscussion() {
  if (!point.value || loading.value) return
  loading.value = true
  error.value = ''
  try {
    const state = study.value?.path
      ? study.value
      : await startStudyPath({
          pointCode: point.value.code,
          clientId: createPblMessageId(),
          interactionStyle: 'guided',
        })
    study.value = state
    goDetail(ROUTES.studentPbl, { topicCode: point.value.code, dialogueId: state.path?.sessionId || '' })
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '无法开始研讨，请稍后重试。'
  } finally {
    loading.value = false
  }
}

function startReview() {
  if (point.value && canPractice.value) goDetail(ROUTES.studentKnowledgeLoop, { topicCode: point.value.code })
}

async function createPrivatePractice() {
  if (!study.value?.path || practiceBusy.value) return
  practiceBusy.value = true
  try {
    const cycle: 1 | 2 =
      practiceGroup.value?.status === 'failed' ? practiceGroup.value.cycle : practiceGroup.value?.canRetest ? 2 : 1
    practiceGroup.value = await generateStudyPractice(study.value.path.id, cycle, createPblMessageId())
    privateQuestionIndex.value = undefined
    privateFeedback.value = undefined
  } catch (reason) {
    uni.showToast({ title: reason instanceof Error ? reason.message : '练习生成失败，可稍后重试。', icon: 'none' })
  } finally {
    practiceBusy.value = false
  }
}

async function answerPrivatePracticeQuestion(selectedOption: number) {
  if (!practiceGroup.value || !currentPrivateQuestion.value || practiceBusy.value || privateFeedback.value) return
  practiceBusy.value = true
  try {
    privateFeedback.value = await answerPrivatePractice({
      groupId: practiceGroup.value.id,
      clientId: createPblMessageId(),
      questionIndex: currentPrivateQuestion.value.index,
      selectedOption,
    })
    practiceGroup.value.attempts.push(privateFeedback.value)
  } catch (reason) {
    uni.showToast({ title: reason instanceof Error ? reason.message : '作答未保存，请重试。', icon: 'none' })
  } finally {
    practiceBusy.value = false
  }
}

async function nextPrivateQuestion() {
  if (!practiceGroup.value || !currentPrivateQuestion.value) return
  const attempted = new Set(practiceGroup.value.attempts.map((attempt) => attempt.questionIndex))
  privateQuestionIndex.value = practiceGroup.value.questions.find(
    (question) => question.index > currentPrivateQuestion.value!.index && !attempted.has(question.index),
  )?.index
  privateFeedback.value = undefined
  if (privateQuestionIndex.value === undefined) practiceGroup.value = await getPrivatePractice(practiceGroup.value.id)
}

function formatDue(value: string) {
  return value.replace('T', ' ').slice(0, 16)
}

onLoad((options) => {
  requestedCode.value = typeof options?.topicCode === 'string' ? options.topicCode : ''
  if (!requestedCode.value) error.value = '缺少知识节点参数。'
})
onShow(() => {
  if (requireRole('student')) void load()
})
onBackPress(({ from }) => handleBackPress(from, ROUTES.studentCases, { view: 'knowledge' }))
</script>

<style scoped>
.node-page {
  min-height: 100vh;
  padding: 30rpx 28rpx 48rpx;
  background: var(--med-page);
}
.state-copy {
  display: flex;
  min-height: 300rpx;
  align-items: center;
  justify-content: center;
  color: var(--med-muted);
  font-size: 26rpx;
}
.error-state {
  flex-direction: column;
  gap: 20rpx;
  color: var(--med-danger);
  text-align: center;
}
.text-action {
  min-height: 64rpx;
  margin: 0;
  padding: 0 18rpx;
  color: var(--med-clinical);
  background: var(--med-wash);
  font-size: 24rpx;
}
.node-head {
  display: flex;
  max-width: 920px;
  margin: 0 auto;
  padding: 8rpx 0 28rpx;
  flex-direction: column;
  gap: 14rpx;
  border-bottom: 1rpx solid var(--med-border);
}
.head-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
}
.node-title {
  color: var(--med-ink);
  font-size: 42rpx;
  font-weight: 800;
  letter-spacing: -1rpx;
  line-height: 1.2;
}
.status-pill {
  padding: 8rpx 12rpx;
  flex: none;
  color: var(--med-clinical);
  background: var(--med-wash);
  border-radius: 99rpx;
  font-size: 21rpx;
}
.status-pill.status-weak {
  color: #fff;
  background: var(--med-danger);
}
.status-pill.status-due {
  color: #fff;
  background: var(--med-warning);
}
.status-pill.status-learning {
  color: #fff;
  background: var(--med-accent);
}
.status-pill.status-stable {
  color: #fff;
  background: var(--med-success);
}
.objective {
  color: var(--med-text-secondary);
  font-size: 27rpx;
  line-height: 1.65;
}
.preparation-note {
  padding: 14rpx 16rpx;
  color: var(--med-safety-text);
  background: var(--med-safety-soft);
  border-left: 4rpx solid var(--med-safety);
  font-size: 23rpx;
  line-height: 1.55;
}
.content-section {
  display: flex;
  max-width: 920px;
  margin: 0 auto;
  padding: 30rpx 0;
  flex-direction: column;
  gap: 14rpx;
  border-bottom: 1rpx solid var(--med-divider);
}
.section-kicker {
  color: var(--med-clinical);
  font-family: var(--med-font-utility);
  font-size: 21rpx;
  font-weight: 700;
  letter-spacing: 2rpx;
}
.description {
  color: var(--med-text);
  font-size: 28rpx;
  line-height: 1.8;
}
.study-section {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}
.relationship-section {
  gap: 26rpx;
}
.relationship-group {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
}
.relationship-label {
  color: var(--med-ink);
  font-size: 27rpx;
  font-weight: 700;
}
.relationship-empty,
.source-note {
  color: var(--med-muted);
  font-size: 23rpx;
  line-height: 1.55;
}
.relation-row {
  display: flex;
  width: 100%;
  min-height: 76rpx;
  margin: 0;
  padding: 10rpx 0;
  align-items: center;
  gap: 14rpx;
  color: var(--med-text);
  background: transparent;
  border-bottom: 1rpx solid var(--med-divider);
  border-radius: 0;
  font-size: 26rpx;
  text-align: left;
}
.relation-row > view {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 2rpx;
}
.relation-row > view text:last-child {
  color: var(--med-muted);
  font-size: 21rpx;
}
.relation-mark {
  display: inline-flex;
  width: 34rpx;
  height: 34rpx;
  flex: 0 0 34rpx;
  align-items: center;
  justify-content: center;
  color: var(--med-clinical);
  background: var(--med-wash);
  border-radius: 50%;
  font-family: var(--med-font-utility);
  font-weight: 700;
}
.relation-mark.status-weak,
.relation-mark.status-due,
.relation-mark.status-learning,
.relation-mark.status-stable {
  color: #fff;
}
.relation-mark.status-weak {
  background: var(--med-danger);
}
.relation-mark.status-due {
  background: var(--med-warning);
}
.relation-mark.status-learning {
  background: var(--med-accent);
}
.relation-mark.status-stable {
  background: var(--med-success);
}
.source-section {
  color: var(--med-text-secondary);
  font-size: 23rpx;
  line-height: 1.6;
}
.node-actions {
  display: flex;
  max-width: 920px;
  margin: 0 auto;
  padding: 32rpx 0;
  flex-direction: column;
  gap: 12rpx;
}
.action-note {
  color: var(--med-muted);
  font-size: 23rpx;
  line-height: 1.55;
}
.practice-option {
  width: 100%;
  margin: 0;
  padding: 16rpx;
  color: var(--med-text);
  background: var(--med-surface);
  border: 1rpx solid var(--med-border);
  border-radius: var(--med-radius-sm);
  font-size: 25rpx;
  line-height: 1.5;
  text-align: left;
}
.practice-feedback {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
  padding: 16rpx 0 0;
  color: var(--med-text-secondary);
  border-top: 1rpx solid var(--med-divider);
  font-size: 24rpx;
  line-height: 1.55;
}
.primary-action,
.secondary-action {
  min-height: 88rpx;
  margin: 0;
  border-radius: var(--med-radius-sm);
  font-size: 28rpx;
}
.primary-action {
  color: #fff;
  background: var(--med-clinical);
}
.secondary-action {
  color: var(--med-clinical);
  background: var(--med-wash);
}
@media screen and (min-width: 600px) {
  .node-page {
    padding: 28px 32px 56px;
  }
  .node-title {
    font-size: 30px;
  }
  .objective {
    font-size: 17px;
  }
  .section-kicker {
    font-size: 13px;
  }
  .description {
    font-size: 18px;
  }
  .relationship-label {
    font-size: 17px;
  }
  .relation-row {
    min-height: 58px;
    font-size: 16px;
  }
  .primary-action,
  .secondary-action {
    min-height: 52px;
    font-size: 16px;
  }
}
</style>
