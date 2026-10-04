<template>
  <view class="page">
    <view
      v-if="accessDenied"
      class="state error"
      role="alert"
      >教师身份已变化，请重新从教师工作区进入。</view
    >
    <view
      v-else-if="invalid"
      class="state error"
      role="alert"
      >最终测试链接无效。</view
    >
    <view
      v-else-if="loading && !test"
      class="state"
      role="status"
      >正在读取教师审阅稿…</view
    >
    <view
      v-else-if="error && !test"
      class="state error"
      role="alert"
    >
      <text>{{ error }}</text
      ><button @click="reload">重新加载</button>
    </view>
    <template v-else-if="test">
      <view class="heading">
        <text class="eyebrow">课堂最终测试 · 固定研讨分析</text>
        <text class="title">{{ test.title }}</text>
        <text class="meta"
          >班级 {{ test.classId }} · 研讨 {{ test.sessionId }} · {{ isMixed ? '单目标混合题 v2' : '单选题 v1' }} ·
          测试版本 {{ test.version }}</text
        >
        <text class="status">{{ statusLabel }}</text>
      </view>

      <view
        v-if="!test.currentScopeActive"
        class="state"
        role="status"
      >
        班级已归档或学生已离班。保留历史测试供查看，当前不能修改、退改、重试生成或开放。
      </view>

      <view class="section">
        <text class="section-title">研讨分析</text>
        <text
          v-if="diagnosisOutcome"
          class="diagnosis"
          >{{ diagnosisOutcome }}</text
        >
        <view
          v-for="item in diagnosisItems"
          :key="item.key"
          class="diagnosis-row"
        >
          <text class="diagnosis-label">{{ item.label }}</text
          ><text>{{ item.value }}</text>
        </view>
        <text class="goals">主要目标：{{ test.goalPointCodes.map(goalLabel).join('、') }}</text>
      </view>

      <view
        v-if="test.generationState === 'pending' || test.generationState === 'generating'"
        class="state"
        role="status"
      >
        最终测试正在生成，页面保持打开时会自动刷新状态。
      </view>
      <view
        v-else-if="test.generationState === 'failed'"
        class="section warning"
        role="alert"
      >
        <text>{{
          test.currentScopeActive
            ? '最终测试生成失败。可重试同一份审阅单，不会创建新的课堂任务。'
            : '历史最终测试生成失败，当前范围已失效，不能重试生成。'
        }}</text>
        <button
          v-if="test.currentScopeActive"
          class="secondary"
          :disabled="busy"
          @click="retryGeneration"
        >
          {{ busy ? '正在重试…' : '重试生成测试' }}
        </button>
      </view>

      <view
        v-for="(question, index) in questions"
        :key="question.id || `new-${index}`"
        class="question"
      >
        <view class="question-head"
          ><text class="question-title">第 {{ index + 1 }} 题</text
          ><text
            v-if="isMixed"
            class="question-type"
            >{{ questionTypeLabel(question) }}</text
          ><view
            v-if="!isMixed"
            class="ordering"
            ><button
              :disabled="!canEdit || index === 0"
              @click="moveQuestion(index, -1)"
            >
              上移</button
            ><button
              :disabled="!canEdit || index === questions.length - 1"
              @click="moveQuestion(index, 1)"
            >
              下移</button
            ><button
              class="remove"
              :disabled="!canEdit || questions.length <= 1"
              @click="removeQuestion(index)"
            >
              删除
            </button></view
          ></view
        >
        <text class="field-label">主要目标</text>
        <picker
          :range="goalOptions"
          :value="goalIndex(question.primaryPointCode)"
          :disabled="!canEdit"
          @change="setGoal(index, $event)"
        >
          <view class="picker-value">{{ goalLabel(question.primaryPointCode) }} ⌄</view>
        </picker>
        <text class="field-label">题干</text
        ><textarea
          v-model="question.prompt"
          class="textarea"
          maxlength="2000"
          :disabled="!canEdit"
          :placeholder="isMixed ? '编辑题干' : '编辑单选题题干'"
        />
        <template v-if="question.questionType !== 'short_answer'">
          <text class="field-label">四个选项</text>
          <view
            v-for="(option, optionIndex) in question.options"
            :key="optionIndex"
            class="option-row"
          >
            <text>{{ ['A', 'B', 'C', 'D'][optionIndex] }}</text
            ><input
              v-model="question.options[optionIndex]"
              :disabled="!canEdit"
              :aria-label="`第 ${index + 1} 题选项 ${optionIndex + 1}`"
            />
          </view>
          <template v-if="question.questionType === 'multiple_choice'">
            <text class="field-label">正确答案（选择 2–3 项）</text>
            <checkbox-group
              class="answer-options"
              @change="setMultipleAnswers(index, $event)"
            >
              <label
                v-for="(option, optionIndex) in question.options"
                :key="optionIndex"
                class="answer-option"
              >
                <checkbox
                  :value="String(optionIndex)"
                  :checked="question.correctOptions.includes(optionIndex)"
                  :disabled="!canEdit"
                />
                <text>{{ ['A', 'B', 'C', 'D'][optionIndex] }} · {{ option }}</text>
              </label>
            </checkbox-group>
          </template>
          <template v-else>
            <text class="field-label">正确答案</text>
            <picker
              :range="answerLabels"
              :value="question.correctOption"
              :disabled="!canEdit"
              @change="setAnswer(index, $event)"
              ><view class="picker-value">{{ answerLabels[question.correctOption] }} ⌄</view></picker
            >
          </template>
        </template>
        <template v-else>
          <text class="field-label">参考答案</text
          ><textarea
            v-model="question.referenceAnswer"
            class="textarea"
            maxlength="2000"
            :disabled="!canEdit"
            placeholder="填写简答题标准答案"
          />
          <text class="field-label">评分要点（每项 10 分）</text>
          <view
            v-for="(criterion, criterionIndex) in question.rubric"
            :key="criterion.criterionId"
            class="rubric-row"
          >
            <text class="rubric-label">要点 {{ criterionIndex + 1 }} · 10 分</text>
            <textarea
              v-model="criterion.description"
              class="textarea rubric-input"
              maxlength="300"
              :disabled="!canEdit"
              :aria-label="`第 ${index + 1} 题评分要点 ${criterionIndex + 1}`"
              placeholder="描述一个可判定的得分要点"
            />
          </view>
        </template>
        <text class="field-label">解析</text
        ><textarea
          v-model="question.explanation"
          class="textarea explanation"
          maxlength="2000"
          :disabled="!canEdit"
          placeholder="说明答案依据"
        />
        <button
          v-if="canCopyToQuestionBank(question) && hasPersistedQuestionSource(question)"
          class="bank-link"
          :disabled="busy || dirty"
          @click="openBankCopy(question)"
        >
          保存到个人题库
        </button>
        <text
          v-else-if="canCopyToQuestionBank(question)"
          class="source-note"
          >{{ dirty ? '先保存测试，才能复制已确认的题目来源。' : '此题没有可用的已保存来源，暂不能复制。' }}</text
        >
        <text
          v-else
          class="source-note"
          >多选题和简答题暂不支持加入个人题库。</text
        >
      </view>

      <view
        v-if="editable"
        class="actions"
      >
        <button
          v-if="!isMixed"
          class="secondary"
          :disabled="!canEdit || questions.length >= 12"
          @click="addQuestion"
        >
          新增题目
        </button>
        <text class="field-label">审阅反馈</text>
        <textarea
          id="test-review-feedback"
          v-model="feedbackDraft"
          class="textarea"
          maxlength="1000"
          :disabled="!canEdit"
          placeholder="说明需要修改的题目或推理依据"
        />
        <button
          id="save-test-draft"
          class="secondary"
          :disabled="saving || Boolean(pendingRelease) || changing || Boolean(pendingChanges)"
          @click="saveDraft"
        >
          {{ saving ? '正在保存…' : pendingSave ? '重试同一保存请求' : dirty ? '保存测试草稿' : '草稿已保存' }}
        </button>
        <button
          id="request-test-changes"
          class="secondary"
          :disabled="
            changing ||
            saving ||
            releasing ||
            Boolean(pendingSave) ||
            Boolean(pendingRelease) ||
            questionsDirty ||
            !feedbackDraft.trim()
          "
          @click="requestChanges"
        >
          {{ changing ? '正在提交退改…' : pendingChanges ? '重试同一退改请求' : '反馈并退改' }}
        </button>
        <button
          id="release-test"
          class="primary"
          :disabled="
            saving ||
            releasing ||
            changing ||
            Boolean(pendingChanges) ||
            dirty ||
            Boolean(pendingSave) ||
            !readyToRelease
          "
          @click="confirmRelease"
        >
          {{ pendingRelease ? '重试开放请求' : '审核并开放测试' }}
        </button>
        <text class="action-help">保存只更新这份测试；开放后题目冻结。题库副本需单独确认，不会自动开放测试。</text>
      </view>
      <view
        v-else-if="test.reviewState === 'released'"
        class="released"
        >已开放 · {{ test.releasedAt ? formatDate(test.releasedAt) : '题目已冻结' }}</view
      >
      <view
        v-else
        class="released"
        >当前测试只读。生成状态：{{ test.generationState }}；审核状态：{{ test.reviewState }}</view
      >

      <text
        v-if="error"
        class="inline-error"
        role="alert"
        >{{ error }}</text
      >
      <view
        v-if="versionConflict"
        class="conflict"
        role="alert"
      >
        <text>服务端版本已变化。你的本地编辑仍保留；重新加载前请确认是否放弃本地更改。</text>
        <button
          class="quiet"
          @click="confirmReloadLatest"
        >
          重新加载最新版本
        </button>
      </view>
      <button
        class="quiet back"
        @click="back"
      >
        {{ pblReturn.section === 'diagnostics' ? '返回测试待办' : '返回课堂' }}
      </button>
    </template>
    <MedConfirmDialog
      v-if="pendingConfirmation"
      title="审核并开放测试"
      message="开放后学生可以作答，题目将被冻结。确认开放这份测试吗？"
      confirm-text="确认开放"
      cancel-text="继续检查"
      confirm-id="confirm-test-release"
      @cancel="pendingConfirmation = undefined"
      @confirm="acceptRelease"
    />
  </view>
</template>

<script setup lang="ts">
import { computed, ref, shallowRef } from 'vue'
import { onBackPress, onHide, onLoad, onShow, onUnload } from '@dcloudio/uni-app'
import MedConfirmDialog from '@/components/ui/MedConfirmDialog.vue'
import { getSession, requireRole } from '@/features/identity/public'
import {
  createLearningRequestId,
  getKnowledgeCatalog,
  getTeacherFinalTest,
  releaseTeacherFinalTest,
  requestTeacherTestChanges,
  retryTeacherTestGeneration,
  saveTeacherFinalTest,
  type FinalTestRubricCriterion,
  type KnowledgePoint,
  type TeacherFinalTest,
  type TeacherFinalTestQuestion,
  learningGoalLabel,
} from '@/features/learning/public'
import { backOrRoute, goDetail, handleBackPress, ROUTES } from '@/platform/navigation'
import { parseTeacherWorkspaceTarget, type TeacherReviewKind } from '@/platform/navigation/teacher'
let pblReturn: {
  section: 'classrooms' | 'diagnostics'
  classId?: number
  sessionId?: number | string
  reviewKind?: TeacherReviewKind
} = { section: 'diagnostics' }

type QuestionOptions = [string, string, string, string]
type RubricCriterion = FinalTestRubricCriterion
type ReviewQuestionFields = {
  id: string | null
  position: number
  primaryPointCode: string
  prompt: string
  explanation: string
  sourceDigest?: string
}
type NullableQuestionId<T> = T extends unknown ? Omit<T, 'id'> & { id: string | null } : never
type ReviewQuestion = NullableQuestionId<TeacherFinalTestQuestion>
type SingleChoiceReviewQuestion = Extract<ReviewQuestion, { questionType: 'single_choice' }>
type TeacherReviewTest = Omit<TeacherFinalTest, 'questions'> & { questions: ReviewQuestion[] }
type PendingSave = { id: string; version: number; questions: ReviewQuestion[]; feedback: string }
type PendingRelease = { id: string; version: number; digest: string; feedback: string }
type PendingChanges = { id: string; version: number; note: string }
const answerLabels = ['A', 'B', 'C', 'D']
const expectedMixedTypes = [
  'single_choice',
  'single_choice',
  'single_choice',
  'multiple_choice',
  'short_answer',
] as const
const test = ref<TeacherReviewTest>()
const catalog = ref<KnowledgePoint[]>([])
const questions = ref<ReviewQuestion[]>([])
const goalOptions = computed(() => test.value?.goalPointCodes.map(goalLabel) || [])
const isMixed = computed(() => test.value?.formatVersion === 'mixed_v2')
const feedbackDraft = ref('')
const loading = ref(false)
const saving = ref(false)
const releasing = ref(false)
const changing = ref(false)
const pendingChanges = ref<PendingChanges>()
const busy = computed(
  () =>
    saving.value ||
    releasing.value ||
    changing.value ||
    Boolean(pendingChanges.value) ||
    Boolean(pendingSave.value) ||
    Boolean(pendingRelease.value),
)
const error = ref('')
const accessDenied = ref(false)
const invalid = ref(false)
const versionConflict = ref(false)
const pendingSave = ref<PendingSave>()
const pendingRelease = ref<PendingRelease>()
const pendingConfirmation = shallowRef<{
  identity: string
  context: number
  test: TeacherReviewTest
  version: number
  digest: string
  feedback: string
}>()
const editable = computed(() =>
  Boolean(
    test.value?.currentScopeActive && test.value.reviewState !== 'released' && test.value.generationState === 'ready',
  ),
)
const canEdit = computed(() => editable.value && !busy.value)
const questionsDirty = computed(() =>
  Boolean(test.value && JSON.stringify(questions.value) !== JSON.stringify(toEditable(test.value.questions))),
)
const dirty = computed(() =>
  Boolean(
    test.value &&
    (JSON.stringify(questions.value) !== JSON.stringify(toEditable(test.value.questions)) ||
      feedbackDraft.value !== test.value.feedbackDraft),
  ),
)
const readyToRelease = computed(() =>
  Boolean(
    editable.value &&
    test.value &&
    test.value.generationState === 'ready' &&
    (isMixed.value
      ? test.value.goalPointCodes.length === 1 &&
        questions.value.length === expectedMixedTypes.length &&
        questions.value.every((question, index) => question.questionType === expectedMixedTypes[index])
      : questions.value.length > 0 &&
        questions.value.length <= 12 &&
        test.value.goalPointCodes.every((goal) =>
          questions.value.some((question) => question.primaryPointCode === goal),
        )),
  ),
)
function goalLabel(code: string) {
  return learningGoalLabel(code, catalog.value)
}
function isSingleChoiceQuestion(question: ReviewQuestion): question is SingleChoiceReviewQuestion {
  return !question.questionType || question.questionType === 'single_choice'
}
function canCopyToQuestionBank(question: ReviewQuestion) {
  return isSingleChoiceQuestion(question)
}
function hasPersistedQuestionSource(question: ReviewQuestion) {
  const original = test.value?.questions.find((item) => item.id === question.id)
  if (dirty.value || !original?.id || !uuid.test(original.id)) return false
  return isSingleChoiceQuestion(original) && Boolean(original.sourceDigest)
}
function questionTypeLabel(question: ReviewQuestion) {
  if (question.questionType === 'multiple_choice') return '多选题'
  if (question.questionType === 'short_answer') return '简答题'
  return '单选题'
}
const statusLabel = computed(() => {
  if (test.value?.reviewState === 'released') return '已开放 · 题目已冻结'
  if (test.value?.generationState === 'failed') return '测试生成失败'
  if (test.value?.reviewState === 'needs_changes') return '待修改'
  return test.value?.reviewState === 'pending_review' ? '待教师审阅' : '草稿'
})
const diagnosisOutcome = computed(() =>
  String(test.value?.diagnosisSummary.diagnosis_outcome || test.value?.diagnosisSummary.outcome || ''),
)
const diagnosisItems = computed(() => {
  const summary = test.value?.diagnosisSummary || {}
  const entries: Array<{ key: string; label: string; value: string }> = []
  for (const [field, label] of [
    ['gaps', '知识目标'],
    ['reasoning_issues', '推理关注'],
  ] as const) {
    const value = summary[field]
    if (!Array.isArray(value)) continue
    value.forEach((row, index) => {
      if (!row || typeof row !== 'object') return
      const item = row as Record<string, unknown>
      const description = String(item.summary || item.point_code || item.issue || '')
      if (description) entries.push({ key: `${field}-${index}`, label, value: description })
    })
  }
  return entries
})
let testId = ''
let identity = ''
let contextVersion = 0
let requestToken = 0
let visible = false
let pollTimer: ReturnType<typeof setTimeout> | undefined
let pollStartedAt = 0
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
function current(token = contextVersion) {
  return visible && token === contextVersion && requireRole('teacher') && getSession()?.openid === identity
}
function normalizeOptions(value: unknown): QuestionOptions {
  const options = Array.isArray(value) ? value : []
  return [0, 1, 2, 3].map((index) => (typeof options[index] === 'string' ? options[index] : '')) as QuestionOptions
}
function normalizeRubric(value: unknown): RubricCriterion[] {
  const rubric = Array.isArray(value) ? value : []
  return [0, 1, 2].map((index) => {
    const source = rubric[index]
    const row = source && typeof source === 'object' ? (source as Record<string, unknown>) : {}
    return {
      criterionId: typeof row.criterionId === 'string' && row.criterionId ? row.criterionId : `criterion-${index + 1}`,
      description: typeof row.description === 'string' ? row.description : '',
      maxPoints: 10,
    }
  })
}
function adaptTeacherTest(value: TeacherFinalTest): TeacherReviewTest {
  const raw = value as unknown as Record<string, unknown>
  const rawQuestions = Array.isArray(raw.questions) ? raw.questions : []
  const questions = rawQuestions.map((source, index): ReviewQuestion => {
    const row = source && typeof source === 'object' ? (source as Record<string, unknown>) : {}
    const common: ReviewQuestionFields = {
      id: typeof row.id === 'string' ? row.id : null,
      position: Number.isInteger(row.position) ? Number(row.position) : index + 1,
      primaryPointCode: typeof row.primaryPointCode === 'string' ? row.primaryPointCode : '',
      prompt: typeof row.prompt === 'string' ? row.prompt : '',
      explanation: typeof row.explanation === 'string' ? row.explanation : '',
      ...(typeof row.sourceDigest === 'string' ? { sourceDigest: row.sourceDigest } : {}),
    }
    if (row.questionType === 'short_answer') {
      return {
        ...common,
        questionType: 'short_answer',
        referenceAnswer: typeof row.referenceAnswer === 'string' ? row.referenceAnswer : '',
        rubric: normalizeRubric(row.rubric),
      }
    }
    if (row.questionType === 'multiple_choice') {
      return {
        ...common,
        questionType: 'multiple_choice',
        options: normalizeOptions(row.options),
        correctOptions: Array.isArray(row.correctOptions)
          ? row.correctOptions.filter((item): item is number => typeof item === 'number')
          : [],
      }
    }
    const singleChoice: SingleChoiceReviewQuestion = {
      ...common,
      questionType: 'single_choice',
      options: normalizeOptions(row.options),
      correctOption: typeof row.correctOption === 'number' ? row.correctOption : -1,
    }
    return singleChoice
  })
  return {
    ...(value as TeacherReviewTest),
    formatVersion: raw.formatVersion === 'mixed_v2' ? 'mixed_v2' : 'single_choice_v1',
    questions,
  }
}
function toEditable(value: ReviewQuestion[]): ReviewQuestion[] {
  return value.map((question): ReviewQuestion => {
    if (question.questionType === 'short_answer') {
      return {
        id: question.id,
        position: question.position,
        primaryPointCode: question.primaryPointCode,
        prompt: question.prompt,
        questionType: 'short_answer',
        explanation: question.explanation,
        referenceAnswer: question.referenceAnswer,
        rubric: question.rubric.map((item) => ({ ...item })),
      }
    }
    if (question.questionType === 'multiple_choice') {
      return {
        id: question.id,
        position: question.position,
        primaryPointCode: question.primaryPointCode,
        prompt: question.prompt,
        questionType: 'multiple_choice',
        options: [...question.options] as QuestionOptions,
        correctOptions: [...question.correctOptions],
        explanation: question.explanation,
      }
    }
    return {
      id: question.id,
      position: question.position,
      primaryPointCode: question.primaryPointCode,
      prompt: question.prompt,
      questionType: 'single_choice',
      options: [...question.options] as QuestionOptions,
      correctOption: question.correctOption,
      explanation: question.explanation,
    }
  })
}
function clearPoll() {
  if (pollTimer) clearTimeout(pollTimer)
  pollTimer = undefined
}
function schedulePoll() {
  clearPoll()
  if (!visible || !test.value || !['pending', 'generating'].includes(test.value.generationState)) return
  if (!pollStartedAt) pollStartedAt = Date.now()
  if (Date.now() - pollStartedAt >= 120_000) {
    error.value = '测试仍在处理中，可返回后重新打开查看。'
    return
  }
  pollTimer = setTimeout(() => {
    pollTimer = undefined
    void load(false)
  }, 3000)
}
async function load(force = true) {
  if (!testId || !current() || loading.value) return
  const token = ++requestToken
  loading.value = true
  error.value = ''
  try {
    const value = adaptTeacherTest(await getTeacherFinalTest(testId))
    if (!current() || token !== requestToken) return
    if (value.id !== testId) throw new Error('测试编号与当前链接不一致。')
    if (force || !dirty.value) {
      test.value = value
      questions.value = toEditable(value.questions)
      feedbackDraft.value = value.feedbackDraft
      pendingSave.value = undefined
      pendingRelease.value = undefined
      pendingChanges.value = undefined
      changing.value = false
      versionConflict.value = false
    } else if (test.value) {
      test.value.currentScopeActive = value.currentScopeActive
      test.value.generationState = value.generationState
      test.value.reviewState = value.reviewState
      test.value.reviewKind = value.reviewKind
    }
    schedulePoll()
  } catch (reason) {
    if (current() && token === requestToken)
      error.value = reason instanceof Error ? reason.message : '最终测试读取失败。'
  } finally {
    if (current() && token === requestToken) loading.value = false
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
function reload() {
  void load(true)
}
function reloadLatest() {
  void load(true)
}
function confirmReloadLatest() {
  uni.showModal({
    title: '重新加载最新版本',
    content: '重新加载会放弃当前页面的本地编辑，是否继续？',
    success: (result) => {
      if (result.confirm) reloadLatest()
    },
  })
}
function goalIndex(code: string) {
  const index = test.value?.goalPointCodes.indexOf(code) ?? -1
  return Math.max(0, index)
}
function setGoal(index: number, event: { detail?: { value?: string | number } }) {
  const code = test.value?.goalPointCodes[Number(event.detail?.value)]
  if (code && questions.value[index]) questions.value[index].primaryPointCode = code
}
function setAnswer(index: number, event: { detail?: { value?: string | number } }) {
  const question = questions.value[index]
  if (question && isSingleChoiceQuestion(question)) question.correctOption = Number(event.detail?.value)
}
function setMultipleAnswers(index: number, event: { detail?: { value?: string[] } }) {
  const question = questions.value[index]
  if (question?.questionType !== 'multiple_choice') return
  const selected = (event.detail?.value || [])
    .map(Number)
    .filter((option) => Number.isInteger(option) && option >= 0 && option <= 3)
  question.correctOptions = [...new Set(selected)].sort((left, right) => left - right)
}
function moveQuestion(index: number, direction: -1 | 1) {
  const target = index + direction
  if (!canEdit.value || isMixed.value || target < 0 || target >= questions.value.length) return
  const copy = [...questions.value]
  ;[copy[index], copy[target]] = [copy[target], copy[index]]
  questions.value = copy.map((item, position) => ({ ...item, position: position + 1 }))
}
function removeQuestion(index: number) {
  if (canEdit.value && !isMixed.value && questions.value.length > 1)
    questions.value = questions.value
      .filter((_, i) => i !== index)
      .map((item, position) => ({ ...item, position: position + 1 }))
}
function addQuestion() {
  if (!canEdit.value || isMixed.value || !test.value || questions.value.length >= 12) return
  const point =
    test.value.goalPointCodes.find((goal) => !questions.value.some((question) => question.primaryPointCode === goal)) ||
    test.value.goalPointCodes[0] ||
    ''
  questions.value = [
    ...questions.value,
    {
      id: null,
      position: questions.value.length + 1,
      primaryPointCode: point,
      prompt: '',
      questionType: 'single_choice',
      options: ['', '', '', ''],
      correctOption: 0,
      explanation: '',
    },
  ]
}
function payloadValid(value: ReviewQuestion[]) {
  if (!readyToRelease.value) return false
  if (!isMixed.value) {
    return value.every(
      (question, index) =>
        isSingleChoiceQuestion(question) &&
        question.position === index + 1 &&
        question.prompt.trim() &&
        question.options.every((option) => option.trim()) &&
        question.explanation.trim() &&
        question.correctOption >= 0 &&
        question.correctOption <= 3,
    )
  }
  const prompts = new Set<string>()
  return value.every((question, index) => {
    if (
      question.position !== index + 1 ||
      question.primaryPointCode !== test.value?.goalPointCodes[0] ||
      !question.prompt.trim() ||
      !question.explanation.trim() ||
      prompts.has(question.prompt.trim().toLocaleLowerCase())
    )
      return false
    prompts.add(question.prompt.trim().toLocaleLowerCase())
    if (question.questionType === 'short_answer') {
      return (
        Boolean(question.referenceAnswer.trim()) &&
        question.rubric.length === 3 &&
        question.rubric.every(
          (criterion) => criterion.criterionId.trim() && criterion.description.trim() && criterion.maxPoints === 10,
        ) &&
        new Set(question.rubric.map((criterion) => criterion.criterionId)).size === 3
      )
    }
    const optionsAreValid =
      question.options.every((option) => option.trim()) &&
      new Set(question.options.map((option) => option.trim().toLocaleLowerCase())).size === 4
    if (!optionsAreValid) return false
    if (question.questionType === 'multiple_choice') {
      return (
        question.correctOptions.length >= 2 &&
        question.correctOptions.length <= 3 &&
        question.correctOptions.every((option) => Number.isInteger(option) && option >= 0 && option <= 3) &&
        new Set(question.correctOptions).size === question.correctOptions.length
      )
    }
    return question.correctOption >= 0 && question.correctOption <= 3
  })
}
async function saveDraft() {
  const currentTest = test.value
  if (!currentTest || !editable.value || saving.value || pendingRelease.value || changing.value || pendingChanges.value)
    return
  if (pendingSave.value) return sendSave(pendingSave.value)
  if (!canEdit.value) return
  const payload = toEditable(questions.value)
  if (!payloadValid(payload)) {
    error.value = isMixed.value
      ? '请保持三道单选、一题多选、一题简答的顺序，并补全选项、标准答案、解析及三条评分要点。'
      : '请补全题干、四个选项、答案、解析，并覆盖全部主要目标。'
    return
  }
  const pending = {
    id: createLearningRequestId('teacher-test-save'),
    version: currentTest.version,
    questions: payload,
    feedback: feedbackDraft.value,
  }
  pendingSave.value = pending
  await sendSave(pending)
}
async function requestChanges() {
  if (
    !test.value ||
    !editable.value ||
    questionsDirty.value ||
    changing.value ||
    saving.value ||
    releasing.value ||
    pendingSave.value ||
    pendingRelease.value ||
    !current()
  )
    return
  if (!pendingChanges.value) {
    const note = feedbackDraft.value.trim()
    if (!note) return
    pendingChanges.value = { id: createLearningRequestId('teacher-test-changes'), version: test.value.version, note }
  }
  const pending = pendingChanges.value
  const token = contextVersion
  changing.value = true
  error.value = ''
  try {
    const saved = adaptTeacherTest(await requestTeacherTestChanges(testId, pending.id, pending.version, pending.note))
    if (!current(token)) return
    test.value = saved
    questions.value = toEditable(saved.questions)
    feedbackDraft.value = saved.feedbackDraft
    pendingChanges.value = undefined
    versionConflict.value = false
  } catch (reason) {
    if (current(token)) {
      error.value = reason instanceof Error ? reason.message : '退改结果暂未确认，可重试同一请求。'
      if (/VERSION_CONFLICT|版本/.test(error.value)) versionConflict.value = true
    }
  } finally {
    if (current(token)) changing.value = false
  }
}
async function sendSave(pending: PendingSave) {
  if (saving.value) return
  saving.value = true
  error.value = ''
  const token = contextVersion
  try {
    const saved = adaptTeacherTest(
      await saveTeacherFinalTest(
        testId,
        pending.id,
        pending.version,
        pending.questions as unknown as TeacherFinalTest['questions'],
        pending.feedback,
      ),
    )
    if (!current(token)) return
    test.value = saved
    questions.value = toEditable(saved.questions)
    feedbackDraft.value = saved.feedbackDraft
    pendingSave.value = undefined
    versionConflict.value = false
  } catch (reason) {
    if (current(token)) {
      error.value = reason instanceof Error ? reason.message : '草稿保存未确认；可使用同一请求重试。'
      if (/VERSION_CONFLICT|版本/.test(error.value)) versionConflict.value = true
    }
  } finally {
    if (current(token)) saving.value = false
  }
}
function confirmRelease() {
  if (
    !test.value ||
    !readyToRelease.value ||
    dirty.value ||
    saving.value ||
    releasing.value ||
    pendingSave.value ||
    changing.value ||
    pendingChanges.value ||
    pendingConfirmation.value
  )
    return
  pendingConfirmation.value = {
    identity,
    context: contextVersion,
    test: test.value,
    version: test.value.version,
    digest: test.value.draftDigest,
    feedback: feedbackDraft.value,
  }
}
function acceptRelease() {
  const pending = pendingConfirmation.value
  pendingConfirmation.value = undefined
  if (
    !pending ||
    pending.identity !== identity ||
    !current(pending.context) ||
    test.value !== pending.test ||
    test.value.version !== pending.version ||
    test.value.draftDigest !== pending.digest ||
    feedbackDraft.value !== pending.feedback ||
    !readyToRelease.value ||
    dirty.value ||
    saving.value ||
    releasing.value ||
    pendingSave.value ||
    changing.value ||
    pendingChanges.value
  )
    return
  void release()
}
async function release() {
  const currentTest = test.value
  if (
    !currentTest ||
    !readyToRelease.value ||
    dirty.value ||
    saving.value ||
    releasing.value ||
    changing.value ||
    pendingChanges.value ||
    pendingSave.value
  )
    return
  if (!pendingRelease.value)
    pendingRelease.value = {
      id: createLearningRequestId('teacher-test-release'),
      version: currentTest.version,
      digest: currentTest.draftDigest,
      feedback: feedbackDraft.value,
    }
  const pending = pendingRelease.value
  releasing.value = true
  error.value = ''
  const token = contextVersion
  try {
    await releaseTeacherFinalTest(testId, pending.id, pending.version, pending.digest, pending.feedback)
    if (!current(token)) return
    pendingRelease.value = undefined
    pendingConfirmation.value = undefined
    await load(true)
  } catch (reason) {
    if (current(token)) error.value = reason instanceof Error ? reason.message : '开放状态暂未确认，可重试同一请求。'
  } finally {
    if (current(token)) releasing.value = false
  }
}
async function retryGeneration() {
  if (!test.value?.currentScopeActive || test.value.reviewState === 'released' || busy.value) return
  const token = contextVersion
  try {
    await retryTeacherTestGeneration(testId, createLearningRequestId('teacher-test-retry'))
    if (current(token)) {
      pollStartedAt = Date.now()
      await load(true)
    }
  } catch (reason) {
    if (current(token)) error.value = reason instanceof Error ? reason.message : '测试重试未成功。'
  }
}
function openBankCopy(question: ReviewQuestion) {
  const currentTest = test.value
  const original = currentTest?.questions.find((item) => item.id === question.id)
  if (
    !currentTest ||
    dirty.value ||
    !original?.id ||
    !uuid.test(original.id) ||
    !isSingleChoiceQuestion(original) ||
    !original.sourceDigest
  )
    return
  goDetail(ROUTES.teacherQuestionBankImport, { sourceId: original.id, finalTestId: currentTest.id })
}
function formatDate(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleString('zh-CN')
}
function back() {
  backOrRoute(pblReturn.section === 'diagnostics' ? ROUTES.teacherTestQueue : ROUTES.teacherPbl, {
    ...pblReturn,
    classId: test.value?.classId ?? pblReturn.classId,
  })
}
onLoad((query) => {
  const target = parseTeacherWorkspaceTarget({
    ...query,
    tab: 'pbl',
    section: query?.returnSection === 'classrooms' ? 'classrooms' : 'diagnostics',
  })
  if (target.workspace === 'pbl')
    pblReturn = {
      section: target.section || 'diagnostics',
      classId: target.classId,
      sessionId: target.sessionId,
      reviewKind: target.reviewKind,
    }
  testId = String(query?.finalTestId || '')
  invalid.value = !uuid.test(testId)
})
onShow(() => {
  const session = getSession()
  if (!requireRole('teacher') || session?.role !== 'teacher' || !session.openid) {
    contextVersion += 1
    identity = ''
    pendingChanges.value = undefined
    pendingSave.value = undefined
    pendingRelease.value = undefined
    changing.value = false
    saving.value = false
    releasing.value = false
    loading.value = false
    feedbackDraft.value = ''
    accessDenied.value = true
    pendingConfirmation.value = undefined
    test.value = undefined
    questions.value = []
    catalog.value = []
    visible = false
    clearPoll()
    requestToken += 1
    return
  }
  if (identity && identity !== session.openid) {
    contextVersion += 1
    requestToken += 1
    test.value = undefined
    questions.value = []
    catalog.value = []
    loading.value = false
    feedbackDraft.value = ''
    pendingChanges.value = undefined
    changing.value = false
    saving.value = false
    releasing.value = false
    pendingSave.value = undefined
    pendingRelease.value = undefined
    pendingConfirmation.value = undefined
  }
  identity = session.openid
  accessDenied.value = false
  visible = true
  void loadCatalog(identity, contextVersion)
  if (!invalid.value) {
    pollStartedAt = 0
    void load(!test.value)
  }
})
onHide(() => {
  changing.value = false
  saving.value = false
  releasing.value = false
  loading.value = false
  pendingConfirmation.value = undefined
  visible = false
  contextVersion += 1
  requestToken += 1
  clearPoll()
})
onUnload(() => {
  changing.value = false
  pendingConfirmation.value = undefined
  visible = false
  contextVersion += 1
  requestToken += 1
  clearPoll()
})
onBackPress(({ from }) =>
  handleBackPress(from, pblReturn.section === 'diagnostics' ? ROUTES.teacherTestQueue : ROUTES.teacherPbl, {
    ...pblReturn,
    classId: test.value?.classId ?? pblReturn.classId,
  }),
)
</script>

<style scoped>
.page {
  min-height: 100vh;
  box-sizing: border-box;
  padding: 24rpx 24rpx calc(40rpx + env(safe-area-inset-bottom));
  background: var(--med-page, #f5f8fb);
  color: var(--med-ink, #173052);
}
.heading,
.section,
.question,
.state,
.actions,
.released,
.conflict {
  max-width: 920px;
  margin: 0 auto 20rpx;
}
.heading {
  display: flex;
  flex-direction: column;
  gap: 9rpx;
  padding: 4rpx 2rpx 16rpx;
}
.eyebrow {
  color: #087f91;
  font-size: 22rpx;
  font-weight: 700;
}
.title {
  font-size: 34rpx;
  font-weight: 750;
  line-height: 1.4;
}
.meta,
.source-note,
.action-help {
  color: #687d91;
  font-size: 22rpx;
  line-height: 1.6;
}
.status {
  align-self: flex-start;
  padding: 7rpx 13rpx;
  color: #78541a;
  background: #fff4da;
  border-radius: 8rpx;
  font-size: 21rpx;
}
.section,
.question,
.state,
.conflict {
  box-sizing: border-box;
  padding: 22rpx;
  background: #fff;
  border: 1px solid #dce5ed;
  border-radius: 14rpx;
}
.section-title {
  display: block;
  margin-bottom: 14rpx;
  font-size: 25rpx;
  font-weight: 700;
}
.diagnosis {
  display: block;
  margin-bottom: 12rpx;
  line-height: 1.65;
}
.diagnosis-row {
  display: flex;
  gap: 12rpx;
  padding: 12rpx 0;
  border-top: 1px solid #edf1f4;
  font-size: 23rpx;
  line-height: 1.55;
}
.diagnosis-label {
  flex: 0 0 120rpx;
  color: #6d8192;
}
.goals {
  display: block;
  margin-top: 14rpx;
  color: #087f91;
  font-size: 22rpx;
}
.question-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12rpx;
  margin-bottom: 14rpx;
}
.question-title {
  font-size: 25rpx;
  font-weight: 700;
}
.question-type {
  flex: none;
  padding: 6rpx 10rpx;
  color: #087f91;
  background: #e8f5f6;
  border-radius: 6rpx;
  font-size: 20rpx;
}
.ordering {
  display: flex;
  gap: 6rpx;
}
.ordering button {
  margin: 0;
  padding: 0 12rpx;
  min-height: 48rpx;
  color: #45627d;
  background: #edf3f6;
  font-size: 20rpx;
}
.ordering .remove {
  color: #a14f4c;
}
.field-label {
  display: block;
  margin: 14rpx 0 8rpx;
  color: #526b82;
  font-size: 22rpx;
  font-weight: 650;
}
.picker-value,
.input,
.textarea,
.option-row {
  box-sizing: border-box;
  min-height: 72rpx;
  padding: 14rpx 16rpx;
  background: #f8fafb;
  border: 1px solid #dfe7ed;
  border-radius: 8rpx;
  font-size: 23rpx;
}
.picker-value {
  display: flex;
  align-items: center;
}
.textarea {
  width: 100%;
  min-height: 150rpx;
  line-height: 1.6;
}
.explanation {
  min-height: 110rpx;
}
.option-row {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-top: 8rpx;
}
.option-row > text {
  width: 34rpx;
  color: #087f91;
  font-weight: 700;
}
.answer-options {
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}
.answer-option {
  display: flex;
  min-height: 64rpx;
  align-items: center;
  gap: 10rpx;
  color: #37556f;
  font-size: 22rpx;
  line-height: 1.5;
}
.rubric-row {
  margin-top: 10rpx;
}
.rubric-label {
  display: block;
  margin-bottom: 6rpx;
  color: #526b82;
  font-size: 21rpx;
  font-weight: 650;
}
.rubric-input {
  min-height: 96rpx;
}
.option-row input {
  flex: 1;
}
.bank-link {
  margin: 14rpx 0 0;
  min-height: 88rpx;
  padding: 0 8rpx;
  color: var(--med-brand, #0b716b);
  background: transparent;
  text-align: left;
  font-size: 24rpx;
}
.source-note {
  display: block;
  margin-top: 12rpx;
}
.actions {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
}
.actions button,
.state button,
.conflict button,
.back {
  width: 100%;
  min-height: 76rpx;
  margin: 0;
  border-radius: 10rpx;
  font-size: 24rpx;
  font-weight: 700;
}
.primary {
  color: #fff;
  background: #078995;
}
.secondary {
  color: #087f91;
  background: #e8f5f6;
}
.quiet {
  color: #526b82;
  background: #edf2f5;
}
.action-help {
  padding: 4rpx 2rpx;
}
.released {
  padding: 17rpx 19rpx;
  color: #16695f;
  background: #e8f6f1;
  border: 1px solid #cce9dd;
  border-radius: 10rpx;
  font-size: 22rpx;
}
.warning {
  color: #8a5a18;
  background: #fff9ed;
}
.state {
  display: flex;
  min-height: 140rpx;
  align-items: center;
  flex-direction: column;
  justify-content: center;
  gap: 12rpx;
  text-align: center;
}
.state button {
  margin-top: 4rpx;
}
.error,
.inline-error {
  color: #a34349;
}
.inline-error {
  display: block;
  max-width: 920px;
  margin: 10rpx auto;
  font-size: 22rpx;
}
.conflict {
  color: #8a5a18;
  background: #fff9ed;
}
.conflict text {
  display: block;
  line-height: 1.55;
}
.conflict button {
  margin-top: 12rpx;
}
.back {
  display: block;
  max-width: 920px;
  margin: 22rpx auto 0;
}
</style>
