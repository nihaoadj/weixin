<template>
  <view class="page">
    <MedState
      v-if="accessDenied"
      variant="error"
      icon="history"
      title="教师身份已变化"
      description="课堂结果只对有权教师开放。"
    />
    <MedState
      v-else-if="invalid"
      variant="error"
      icon="retry"
      title="学习结果链接无效"
      description="请从课堂进度或学情详情重新进入。"
    />
    <MedState
      v-else-if="loading && !result"
      variant="loading"
      icon="report"
      title="正在读取课堂学习结果"
      description="只读取当前教师有权查看的已提交结果。"
    />
    <MedState
      v-else-if="error && !result"
      variant="error"
      icon="retry"
      title="学习结果暂不可用"
      :description="error"
      action-label="重新加载"
      secondary-action-label="返回学情"
      @action="load"
      @secondary-action="back"
    />
    <template v-else-if="result">
      <view class="heading">
        <text class="eyebrow">课堂最终测试 · 只读结果</text>
        <text class="title">学习结果</text>
        <text class="format-label">{{ formatLabel }}</text>
        <text class="meta">班级 {{ result.classId }} · 课堂 {{ result.sessionId }} · 学生 {{ result.studentId }}</text>
        <view class="score-summary">
          <view class="score">
            <text>{{ result.score }}</text>
            <text>分</text>
          </view>
          <text class="meta">答对 {{ result.correctCount }} / {{ result.questionCount }} 题</text>
        </view>
        <text
          v-if="!hasCompleteMixedGrade"
          class="grade-unavailable"
          role="status"
          >部分逐题判分记录缺失或不一致；保留结果快照中已记录的分值。</text
        >
        <text class="meta">提交时间：{{ formatDate(result.submittedAt) }}</text>
      </view>
      <view
        v-for="(question, index) in result.questions"
        :key="question.id"
        class="question"
      >
        <view class="question-heading">
          <text class="question-title">第 {{ index + 1 }} 题 · {{ questionTypeLabel(question.questionType) }}</text>
          <text class="question-goal">{{ goalLabel(question.pointCode) }}</text>
        </view>
        <text class="question-points"
          >本题得分：{{ formatPoints(questionPoints(question).earned) }} /
          {{ formatPoints(questionPoints(question).possible) }} 分</text
        >
        <text class="prompt">{{ question.prompt }}</text>
        <template v-if="question.questionType === 'single_choice' || question.questionType === 'multiple_choice'">
          <view class="answer-summary">
            <view class="answer-line"
              ><text class="answer-label">学生选择：</text><text>{{ choiceSetLabel(question, false) }}</text></view
            >
            <view class="answer-line"
              ><text class="answer-label">正确答案：</text><text>{{ choiceSetLabel(question, true) }}</text></view
            >
          </view>
          <view
            v-if="question.questionType === 'multiple_choice'"
            class="match-note"
            :class="
              multipleChoiceMatches(question) === true
                ? 'match-note--correct'
                : multipleChoiceMatches(question) === false
                  ? 'match-note--incorrect'
                  : ''
            "
          >
            <text v-if="multipleChoiceMatches(question) === true">选择集合与正确答案完全一致。</text>
            <text v-else-if="multipleChoiceMatches(question) === false"
              >选择集合与正确答案不完全一致；多选题按完整集合匹配。</text
            >
            <text v-else>作答或正确答案集合未记录，无法判断是否完全匹配。</text>
          </view>
          <view
            v-for="(option, optionIndex) in question.options"
            :key="optionIndex"
            class="option"
            :class="{
              correct: isCorrectOption(question, optionIndex),
              selected: isSelectedOption(question, optionIndex),
            }"
          >
            <text class="option-label">{{ optionLabel(optionIndex) }}</text>
            <text class="option-copy">{{ option }}</text>
            <view class="option-states">
              <text
                v-if="isSelectedOption(question, optionIndex)"
                class="option-state option-state--selected"
                >学生选择</text
              >
              <text
                v-if="isCorrectOption(question, optionIndex)"
                class="option-state option-state--correct"
                >正确答案</text
              >
            </view>
          </view>
        </template>
        <template v-else>
          <view class="answer-block">
            <text class="answer-label">学生原答案</text>
            <text class="answer-copy">{{ shortAnswerText(question.selectedText) }}</text>
          </view>
          <view class="answer-block">
            <text class="answer-label">参考答案</text>
            <text class="answer-copy">{{ optionalText(question.referenceAnswer) }}</text>
          </view>
          <view class="rubric-block">
            <text class="answer-label">评分要点</text>
            <text
              v-if="question.rubricResults?.length"
              class="rubric-note"
              >结果快照逐项记录得分与反馈；单项满分和描述未随结果提供，题目满分见本题得分。</text
            >
            <text
              v-else
              class="missing-copy"
              >结果中未提供评分要点。</text
            >
            <view
              v-for="item in question.rubricResults || []"
              :key="item.criterionId"
              class="rubric-row"
            >
              <text class="rubric-title">{{ item.criterionId }} · 得分 {{ formatPoints(item.earnedPoints) }}</text>
              <text class="rubric-evidence">{{ optionalText(item.evidence) }}</text>
            </view>
            <text
              v-if="question.gradingFeedback"
              class="grading-feedback"
              >判分反馈：{{ question.gradingFeedback }}</text
            >
          </view>
        </template>
        <view class="explanation-block">
          <text class="answer-label">解释</text>
          <text class="explanation">{{ optionalText(question.explanation) }}</text>
        </view>
      </view>
      <view
        v-if="error"
        class="inline-error"
        role="alert"
      >
        <text>{{ error }}</text>
        <button
          class="retry-inline"
          @click="load"
        >
          重新加载结果
        </button>
      </view>
      <button
        class="back"
        @click="back"
      >
        返回学情
      </button>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onBackPress, onHide, onLoad, onShow, onUnload } from '@dcloudio/uni-app'
import MedState from '@/components/ui/MedState.vue'
import { getSession, requireRole } from '@/features/identity/public'
import {
  getKnowledgeCatalog,
  getTeacherRouteResult,
  type KnowledgePoint,
  type TeacherLearningResult,
  learningGoalLabel,
} from '@/features/learning/public'
import {
  backFromTeacherDetail,
  parseTeacherWorkspaceTarget,
  type TeacherDetailFallback,
} from '@/platform/navigation/teacher'

const labels = ['A', 'B', 'C', 'D']
const result = ref<TeacherLearningResult>()
const catalog = ref<KnowledgePoint[]>([])
const loading = ref(false)
const error = ref('')
const accessDenied = ref(false)
const invalid = ref(true)
const formatLabel = computed(() =>
  result.value?.formatVersion === 'mixed_v2' ? '新制混合题型 · 单选、多选与简答' : '历史单选题型',
)
const hasCompleteMixedGrade = computed(
  () =>
    !result.value ||
    result.value.formatVersion !== 'mixed_v2' ||
    result.value.questions.every(hasReliableQuestionScore),
)
const returnTarget = ref<TeacherDetailFallback>({ workspace: 'insights', panel: 'progress' })
let resultId = ''
let identity = ''
let contextVersion = 0
let requestVersion = 0
let visible = false
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
function goalLabel(code: string) {
  return learningGoalLabel(code, catalog.value)
}

function current(token = contextVersion) {
  return visible && token === contextVersion && requireRole('teacher') && getSession()?.openid === identity
}
function targetWithResultContext(): TeacherDetailFallback {
  const context = returnTarget.value
  const classId = context.workspace === 'insights' ? (context.classId ?? result.value?.classId) : result.value?.classId
  const sessionId =
    context.workspace === 'insights' ? (context.sessionId ?? result.value?.sessionId) : result.value?.sessionId
  return {
    workspace: 'insights',
    panel: context.workspace === 'insights' ? context.panel || 'progress' : 'progress',
    ...(classId ? { classId } : {}),
    ...(sessionId !== undefined ? { sessionId } : {}),
    ...(context.workspace === 'insights' && context.dateFrom ? { dateFrom: context.dateFrom } : {}),
    ...(context.workspace === 'insights' && context.dateTo ? { dateTo: context.dateTo } : {}),
  }
}
function back() {
  backFromTeacherDetail(targetWithResultContext())
}
function formatDate(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleString('zh-CN')
}
function formatPoints(value: number | undefined) {
  if (value == null) return '未提供'
  return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(2)))
}
function questionPoints(question: TeacherLearningResult['questions'][number]) {
  return { earned: question.pointsAwarded, possible: question.pointsPossible }
}
function hasReliableQuestionScore(question: TeacherLearningResult['questions'][number]) {
  if (question.pointsAwarded == null || question.pointsPossible == null) return false
  if (result.value?.formatVersion !== 'mixed_v2') return true
  if (question.pointsPossible <= 0) return false
  if (question.questionType === 'single_choice') {
    if (question.selectedOption == null || question.correctOption == null) return false
    return question.selectedOption === question.correctOption
      ? question.pointsAwarded === question.pointsPossible
      : question.pointsAwarded === 0
  }
  if (question.questionType === 'multiple_choice') {
    if (!question.selectedOptions || !question.correctOptions) return false
    const matches = multipleChoiceMatches(question)
    if (matches === undefined) return false
    return matches ? question.pointsAwarded === question.pointsPossible : question.pointsAwarded === 0
  }
  const rubricResults = question.rubricResults
  if (question.selectedText === undefined || question.referenceAnswer === undefined || !rubricResults?.length)
    return false
  const rubricEarned = rubricResults.reduce((total, item) => total + item.earnedPoints, 0)
  return rubricEarned >= 0 && rubricEarned <= question.pointsPossible && question.pointsAwarded === rubricEarned
}
function optionLabel(index: number) {
  return labels[index] || String(index + 1)
}
function optionChoiceLabel(question: TeacherLearningResult['questions'][number], index: number) {
  const label = optionLabel(index)
  const option = question.options[index]
  return option ? `${label}（${option}）` : label
}
function questionTypeLabel(type: TeacherLearningResult['questions'][number]['questionType']) {
  return { single_choice: '单选题', multiple_choice: '多选题', short_answer: '简答题' }[type]
}
function choiceSetLabel(question: TeacherLearningResult['questions'][number], correct: boolean) {
  if (question.questionType === 'single_choice') {
    const option = correct ? question.correctOption : question.selectedOption
    return option == null ? '未记录' : optionChoiceLabel(question, option)
  }
  const values = correct ? question.correctOptions : question.selectedOptions
  if (!values) return '未记录'
  return values.length ? values.map((index) => optionChoiceLabel(question, index)).join('、') : '未选择'
}
function isSelectedOption(question: TeacherLearningResult['questions'][number], index: number) {
  return question.questionType === 'single_choice'
    ? question.selectedOption === index
    : question.questionType === 'multiple_choice' && Boolean(question.selectedOptions?.includes(index))
}
function isCorrectOption(question: TeacherLearningResult['questions'][number], index: number) {
  return question.questionType === 'single_choice'
    ? question.correctOption === index
    : question.questionType === 'multiple_choice' && Boolean(question.correctOptions?.includes(index))
}
function multipleChoiceMatches(question: TeacherLearningResult['questions'][number]): boolean | undefined {
  if (question.questionType !== 'multiple_choice' || !question.selectedOptions || !question.correctOptions)
    return undefined
  const selected = [...question.selectedOptions].sort((left, right) => left - right)
  const correct = [...question.correctOptions].sort((left, right) => left - right)
  return selected.length === correct.length && selected.every((value, index) => value === correct[index])
}
function shortAnswerText(value: string | undefined) {
  return value === undefined ? '未记录' : value.length ? value : '未作答'
}
function optionalText(value: string | undefined) {
  return value === undefined ? '未提供' : value.length ? value : '未填写'
}
async function load() {
  if (!resultId || !current() || loading.value) return
  const token = ++requestVersion
  loading.value = true
  error.value = ''
  try {
    const value = await getTeacherRouteResult(resultId)
    if (!current() || token !== requestVersion) return
    if (value.id !== resultId) throw new Error('结果编号与当前链接不一致。')
    if (value.sourceKind !== 'classroom') throw new Error('仅能查看已授权课堂的最终测试结果。')
    result.value = value
  } catch (reason) {
    if (current() && token === requestVersion)
      error.value = reason instanceof Error ? reason.message : '学习结果读取失败。'
  } finally {
    if (current() && token === requestVersion) loading.value = false
  }
}
async function loadCatalog(requestedIdentity: string, context: number) {
  try {
    const points = await getKnowledgeCatalog()
    if (current(context) && getSession()?.openid === requestedIdentity) catalog.value = points
  } catch {
    if (current(context) && getSession()?.openid === requestedIdentity) catalog.value = []
  }
}
onLoad((query) => {
  resultId = String(query?.resultId || '')
  invalid.value = !uuid.test(resultId)
  const target = parseTeacherWorkspaceTarget({
    ...(query as Record<string, string | undefined>),
    tab: 'insights',
  })
  returnTarget.value =
    target.workspace === 'insights'
      ? {
          workspace: 'insights',
          panel: target.panel || 'progress',
          ...(target.classId ? { classId: target.classId } : {}),
          ...(target.sessionId !== undefined ? { sessionId: target.sessionId } : {}),
          ...(target.dateFrom ? { dateFrom: target.dateFrom } : {}),
          ...(target.dateTo ? { dateTo: target.dateTo } : {}),
        }
      : { workspace: 'insights', panel: 'progress' }
})
onShow(() => {
  const session = getSession()
  if (!requireRole('teacher') || session?.role !== 'teacher' || !session.openid) {
    visible = false
    contextVersion += 1
    requestVersion += 1
    result.value = undefined
    catalog.value = []
    loading.value = false
    error.value = ''
    accessDenied.value = true
    return
  }
  if (identity && identity !== session.openid) {
    contextVersion += 1
    requestVersion += 1
    result.value = undefined
    catalog.value = []
    loading.value = false
    error.value = ''
  }
  identity = session.openid
  accessDenied.value = false
  visible = true
  if (!invalid.value) {
    void loadCatalog(identity, contextVersion)
    void load()
  }
})
onHide(() => {
  visible = false
  contextVersion += 1
  requestVersion += 1
  loading.value = false
})
onUnload(() => {
  visible = false
  contextVersion += 1
  requestVersion += 1
  loading.value = false
})
onBackPress(({ from }) => {
  if (from === 'navigateBack') return false
  back()
  return true
})
</script>

<style scoped>
.page {
  min-height: 100vh;
  box-sizing: border-box;
  padding: 24rpx 24rpx calc(40rpx + env(safe-area-inset-bottom));
  background: var(--med-page);
  color: var(--med-text);
}
.heading,
.question {
  max-width: 920px;
  margin: 0 auto 18rpx;
  padding: 24rpx;
  background: var(--med-surface);
  border: 1px solid var(--med-border);
  border-radius: 14px;
}
.heading {
  display: flex;
  align-items: flex-start;
  flex-direction: column;
  gap: 8rpx;
}
.eyebrow {
  color: var(--med-brand);
  font-size: 22rpx;
  font-weight: 700;
}
.title {
  color: var(--med-text);
  font-size: 34rpx;
  font-weight: 750;
}
.format-label {
  display: inline-flex;
  min-height: 32px;
  padding: 0 14rpx;
  align-items: center;
  color: var(--med-brand);
  background: var(--med-wash);
  border-radius: 20px;
  font-size: 22rpx;
  font-weight: 650;
}
.meta {
  color: var(--med-muted);
  font-size: 22rpx;
}
.score-summary {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 16rpx;
}
.score {
  display: flex;
  align-items: baseline;
  gap: 5rpx;
  color: var(--med-brand);
  font-size: 24rpx;
}
.score text:first-child {
  font-size: 56rpx;
  font-weight: 800;
}
.grade-unavailable,
.missing-copy {
  color: var(--med-muted);
  font-size: 23rpx;
  line-height: 1.55;
}
.question {
  display: flex;
  flex-direction: column;
  gap: 14rpx;
}
.question-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8rpx 18rpx;
}
.question-title {
  color: var(--med-text);
  font-size: 24rpx;
  font-weight: 700;
}
.question-goal {
  color: var(--med-muted);
  font-size: 22rpx;
}
.question-points {
  color: var(--med-brand);
  font-size: 23rpx;
  font-weight: 650;
}
.prompt {
  font-size: 25rpx;
  line-height: 1.6;
}
.answer-summary,
.answer-block,
.rubric-block,
.explanation-block {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}
.answer-summary {
  padding: 14rpx 16rpx;
  background: var(--med-page);
  border-radius: 10px;
  font-size: 23rpx;
  line-height: 1.55;
}
.answer-line {
  display: flex;
  flex-wrap: wrap;
  gap: 4rpx;
}
.answer-label {
  color: var(--med-muted);
  font-size: 22rpx;
  font-weight: 700;
}
.answer-copy,
.rubric-evidence,
.explanation {
  color: var(--med-text);
  font-size: 23rpx;
  line-height: 1.6;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
.match-note {
  padding: 10rpx 14rpx;
  color: var(--med-muted);
  background: var(--med-page);
  border-radius: 8px;
  font-size: 22rpx;
  line-height: 1.5;
}
.match-note--correct {
  color: #17685c;
  background: #e2f2ed;
}
.match-note--incorrect {
  color: #805400;
  background: #fff2cc;
}
.option {
  display: flex;
  gap: 12rpx;
  align-items: flex-start;
  padding: 14rpx;
  color: var(--med-text);
  background: var(--med-page);
  border: 1px solid var(--med-border);
  border-radius: 9px;
  font-size: 23rpx;
  line-height: 1.5;
}
.option.correct {
  border-color: #65aa99;
  background: #edf7f3;
}
.option.selected {
  color: #725022;
}
.option-label {
  flex: none;
  font-weight: 700;
}
.option-copy {
  min-width: 0;
  flex: 1;
  overflow-wrap: anywhere;
}
.option-states {
  display: flex;
  flex: none;
  flex-direction: column;
  align-items: flex-end;
  gap: 4rpx;
}
.option-state {
  padding: 2rpx 8rpx;
  border-radius: 14px;
  font-size: 20rpx;
  white-space: nowrap;
}
.option-state--selected {
  color: #725022;
  background: #fff0d7;
}
.option-state--correct {
  color: #17685c;
  background: #e2f2ed;
}
.answer-block,
.rubric-block,
.explanation-block {
  padding-top: 10rpx;
  border-top: 1px solid var(--med-border);
}
.rubric-note {
  color: var(--med-muted);
  font-size: 22rpx;
  line-height: 1.5;
}
.rubric-row {
  display: flex;
  flex-direction: column;
  gap: 4rpx;
  padding: 12rpx 14rpx;
  background: var(--med-page);
  border-radius: 8px;
}
.rubric-title {
  color: var(--med-text);
  font-size: 23rpx;
  font-weight: 700;
}
.grading-feedback {
  color: var(--med-muted);
  font-size: 23rpx;
  line-height: 1.6;
  white-space: pre-wrap;
}
.explanation {
  margin-top: 2rpx;
}
.inline-error {
  display: flex;
  max-width: 920px;
  margin: 0 auto 12rpx;
  padding: 10rpx 0;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8rpx 16rpx;
  color: #8b3d3d;
  font-size: 22rpx;
}
.retry-inline {
  min-height: 44px;
  margin: 0;
  padding: 0 14rpx;
  color: var(--med-brand);
  background: var(--med-wash);
  border-radius: 8px;
  font-size: 22rpx;
}
.retry-inline::after {
  border: 0;
}
.back {
  display: block;
  max-width: 920px;
  width: 100%;
  min-height: 48px;
  margin: 18rpx auto;
  color: var(--med-brand);
  background: var(--med-wash);
  border-radius: 10px;
  font-size: 24rpx;
}
.back::after {
  border: 0;
}
@media screen and (max-width: 360px) {
  .page {
    padding-inline: 18rpx;
  }
  .heading,
  .question {
    padding: 20rpx;
  }
  .title {
    font-size: 19px;
  }
  .prompt,
  .answer-copy,
  .rubric-evidence,
  .grading-feedback {
    font-size: 14px;
  }
  .meta,
  .format-label,
  .question-goal,
  .answer-label,
  .retry-inline,
  .question-points,
  .option,
  .match-note,
  .inline-error,
  .rubric-title,
  .rubric-note,
  .grade-unavailable,
  .missing-copy {
    font-size: 13px;
  }
  .option-states {
    align-items: flex-start;
  }
}
@media screen and (min-width: 600px) {
  .page {
    padding: 24px 32px calc(48px + env(safe-area-inset-bottom));
  }
  .heading,
  .question {
    margin-bottom: 20px;
    padding: 24px;
  }
  .title {
    font-size: 24px;
  }
  .meta,
  .format-label,
  .question-title,
  .question-goal,
  .question-points,
  .answer-summary,
  .answer-label,
  .answer-copy,
  .rubric-note,
  .rubric-title,
  .rubric-evidence,
  .grading-feedback,
  .explanation,
  .match-note,
  .grade-unavailable,
  .missing-copy,
  .back {
    font-size: 14px;
  }
}
</style>
