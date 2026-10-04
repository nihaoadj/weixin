<template>
  <view class="page">
    <MedState
      v-if="accessDenied"
      variant="error"
      icon="history"
      title="教师身份已变化"
      description="已清除来源题目，请重新从教师工作区进入。"
      action-label="返回内容"
      @action="backToContent"
    />
    <MedState
      v-else-if="invalid"
      variant="error"
      icon="retry"
      title="题目来源链接无效"
      description="请从已保存的课堂单选题重新进入复制流程。"
      action-label="返回个人题库"
      @action="backToQuestionBank"
    />
    <MedState
      v-else-if="loading && !source"
      variant="loading"
      icon="history"
      title="正在读取授权来源"
      description="核对当前教师可访问的题目及其摘要。"
    />
    <MedState
      v-else-if="loadError && !source"
      variant="error"
      icon="retry"
      title="来源题目暂不可用"
      :description="loadError"
      action-label="重新读取来源"
      secondary-action-label="取消并返回"
      @action="loadSource"
      @secondary-action="cancel"
    />
    <template v-else-if="source">
      <view class="heading">
        <text class="eyebrow">个人题库 · 原样复制</text>
        <text class="title">检查授权来源</text>
        <text class="intro">此页只预览并复制已保存的单选题。首次入库保留来源内容，编辑请在副本详情完成。</text>
      </view>

      <view class="source-panel">
        <view class="source-heading">
          <view>
            <text class="source-label">课堂最终测试单选题 · {{ taskTypeLabel(source.taskType) }}</text>
            <text class="source-title">{{ source.title }}</text>
          </view>
          <text class="digest-state">来源已授权</text>
        </view>

        <view class="field-block">
          <text class="field-label">题干</text>
          <text class="field-value long-text">{{ source.prompt }}</text>
        </view>
        <view class="field-block">
          <text class="field-label">选项与答案</text>
          <view
            v-for="(option, index) in source.options"
            :key="`${index}-${option}`"
            class="option-row"
          >
            <text class="option-letter">{{ optionLabel(index) }}</text>
            <text class="option-text">{{ option }}</text>
            <text
              v-if="index === correctOptionIndex"
              class="answer-tag"
              >正确答案</text
            >
          </view>
        </view>
        <view class="field-block">
          <text class="field-label">解析</text>
          <text class="field-value long-text">{{ source.explanation }}</text>
        </view>
        <view class="target-fields">
          <view class="field-block">
            <text class="field-label">知识目标</text>
            <text class="field-value">{{ source.pointCodes.join('、') || '未提供' }}</text>
          </view>
          <view class="field-block">
            <text class="field-label">能力维度</text>
            <text class="field-value">{{ source.dimensionIds.join('、') || '未提供' }}</text>
          </view>
        </view>
      </view>

      <view
        v-if="loading"
        class="refresh-state"
        role="status"
        >正在重新核对来源摘要…</view
      >
      <view
        v-if="sourceChanged"
        class="notice"
        role="status"
        >来源内容已更新。请检查最新版并重新确认，原题不会被改写。</view
      >
      <view
        v-if="loadError"
        class="error-inline"
        role="alert"
        >{{ loadError }}</view
      >
      <view
        v-if="requiresReload"
        class="conflict"
        role="alert"
      >
        <text>来源或请求状态发生冲突。请重新读取授权来源后再确认；若摘要未变，会继续使用原请求标识重试。</text>
        <button
          class="secondary"
          :disabled="loading || importing"
          @click="loadSource"
        >
          重新读取授权来源
        </button>
      </view>
      <view
        v-if="importError"
        class="error-inline"
        role="alert"
        >{{ importError }}</view
      >

      <template v-if="!imported">
        <checkbox-group
          class="confirm-box"
          @change="setConfirmed"
        >
          <label class="confirm-label">
            <checkbox
              value="confirm"
              :checked="confirmed"
              :disabled="loading || importing || requiresReload"
            />
            <text>我已检查内容并确认这是去标识化的教学题目；将按当前来源原样加入个人题库。</text>
          </label>
        </checkbox-group>
        <view class="actions">
          <button
            id="import-source-question"
            class="primary"
            :disabled="!confirmed || loading || importing || requiresReload"
            @click="importSource"
          >
            {{ importing ? '正在加入…' : requestId ? '重试加入同一副本' : '确认原样加入个人题库' }}
          </button>
          <button
            class="quiet"
            :disabled="importing"
            @click="cancel"
          >
            {{ finalTestId ? '取消并返回来源测试' : '取消并返回个人题库' }}
          </button>
        </view>
      </template>
      <view
        v-else
        class="success-panel"
        role="status"
      >
        <text class="success-title">已加入独立题库副本</text>
        <text class="success-copy">{{ imported.title }} · 原题和来源测试保持不变。你可以在副本详情继续编辑。</text>
        <button
          class="primary"
          @click="openImportedItem"
        >
          编辑题库副本
        </button>
        <button
          class="quiet"
          @click="returnToSource"
        >
          {{ finalTestId ? '返回来源测试' : '返回个人题库' }}
        </button>
      </view>
    </template>
  </view>
</template>

<script lang="ts">
// Keep unresolved request receipts across page reentry without storing source content.
const requestIdsBySource = new Map<string, string>()
</script>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { onBackPress, onHide, onLoad, onShow, onUnload } from '@dcloudio/uni-app'
import MedState from '@/components/ui/MedState.vue'
import type {
  TeacherQuestionBankImportInput,
  TeacherQuestionBankItem,
  TeacherQuestionBankSource,
} from '@/features/content/public'
import { importTeacherQuestionBankItem, getTeacherQuestionBankSource } from '@/features/content/public'
import { createLearningRequestId } from '@/features/learning/public'
import { getSession, requireRole } from '@/features/identity/public'
import { backOrRoute, goDetail, handleBackPress, ROUTES } from '@/platform/navigation'

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
const source = ref<TeacherQuestionBankSource>()
const imported = ref<TeacherQuestionBankItem>()
const loading = ref(false)
const importing = ref(false)
const accessDenied = ref(false)
const invalid = ref(false)
const loadError = ref('')
const importError = ref('')
const confirmed = ref(false)
const requestId = ref('')
const requiresReload = ref(false)
const sourceChanged = ref(false)
const correctOptionIndex = computed(() => {
  const value = source.value?.answer.correct_option
  return typeof value === 'number' && Number.isInteger(value) ? value : -1
})

let sourceId = ''
let finalTestId = ''
let identity = ''
let pageVersion = 0
let loadVersion = 0
let importVersion = 0
let visible = false

function optionLabel(index: number) {
  return String.fromCharCode(65 + index)
}

function taskTypeLabel(value: TeacherQuestionBankSource['taskType']) {
  return {
    retest: '目标验证再测',
    knowledge_review: '知识点巩固',
    discussion: '结构化讨论',
    micro_drill: '推理微训练',
  }[value]
}

function current(version = pageVersion) {
  return visible && version === pageVersion && requireRole('teacher') && getSession()?.openid === identity
}

function resetSourceContext() {
  source.value = undefined
  imported.value = undefined
  confirmed.value = false
  requestId.value = ''
  requiresReload.value = false
  sourceChanged.value = false
  loadError.value = ''
  importError.value = ''
  loading.value = false
  importing.value = false
  loadVersion += 1
  importVersion += 1
}

async function loadSource() {
  if (invalid.value || !current() || loading.value || importing.value) return
  const version = pageVersion
  const request = ++loadVersion
  const oldDigest = source.value?.sourceDigest
  loading.value = true
  loadError.value = ''
  importError.value = ''
  try {
    const result = await getTeacherQuestionBankSource(sourceId)
    if (!current(version) || request !== loadVersion) return
    if (result.sourceType !== 'route_test_question' || result.sourceId.toLowerCase() !== sourceId.toLowerCase())
      throw new Error('授权来源与当前链接不一致。')
    const answerIndex = result.answer.correct_option
    if (
      result.options.length !== 4 ||
      typeof answerIndex !== 'number' ||
      !Number.isInteger(answerIndex) ||
      answerIndex < 0 ||
      answerIndex > 3
    )
      throw new Error('来源不是可复制的标准四选一题目。')
    const digestChanged = Boolean(oldDigest && oldDigest !== result.sourceDigest)
    source.value = result
    confirmed.value = false
    requiresReload.value = false
    sourceChanged.value = digestChanged
    if (digestChanged) requestId.value = ''
  } catch (reason) {
    if (current(version) && request === loadVersion)
      loadError.value = reason instanceof Error ? reason.message : '来源题目读取失败。'
  } finally {
    if (request === loadVersion) loading.value = false
  }
}

function setConfirmed(event: { detail?: { value?: string[] } }) {
  confirmed.value = Boolean(event.detail?.value?.includes('confirm')) && !requiresReload.value
}

function isStateConflict(reason: unknown) {
  return Boolean(reason && typeof reason === 'object' && 'code' in reason && reason.code === 'STATE_CONFLICT')
}

function makeImportInput(value: TeacherQuestionBankSource, clientRequestId: string): TeacherQuestionBankImportInput {
  return {
    sourceType: value.sourceType,
    sourceId: value.sourceId,
    sourceDigest: value.sourceDigest,
    taskType: value.taskType,
    title: value.title,
    prompt: value.prompt,
    options: [...value.options],
    answer: { ...value.answer },
    explanation: value.explanation,
    pointCodes: [...value.pointCodes],
    dimensionIds: [...value.dimensionIds],
    clientRequestId,
    deidentified: true,
  }
}

function requestIdForSource(value: TeacherQuestionBankSource) {
  const key = `${identity}\u0000${value.sourceId}\u0000${value.sourceDigest}`
  const existing = requestIdsBySource.get(key)
  if (existing) return existing
  const created = createLearningRequestId('question-bank-import')
  requestIdsBySource.set(key, created)
  return created
}

async function importSource() {
  const value = source.value
  if (!value || !confirmed.value || importing.value || loading.value || requiresReload.value || !current()) return
  const version = pageVersion
  if (!requestId.value) requestId.value = requestIdForSource(value)
  const request = ++importVersion
  const input = makeImportInput(value, requestId.value)
  importing.value = true
  importError.value = ''
  try {
    const result = await importTeacherQuestionBankItem(input)
    if (!current(version) || request !== importVersion) return
    imported.value = result
    requiresReload.value = false
    sourceChanged.value = false
  } catch (reason) {
    if (current(version) && request === importVersion) {
      importError.value = reason instanceof Error ? reason.message : '副本加入未确认，可使用同一请求重试。'
      if (isStateConflict(reason)) requiresReload.value = true
    }
  } finally {
    if (request === importVersion) importing.value = false
  }
}

function sourceReturn() {
  return uuid.test(finalTestId)
    ? { path: ROUTES.teacherLearningFinalTest, params: { finalTestId } }
    : { path: ROUTES.teacherQuestionBank, params: { status: 'active' } }
}

function cancel() {
  if (importing.value) return
  const target = sourceReturn()
  backOrRoute(target.path, target.params)
}

function returnToSource() {
  const target = sourceReturn()
  backOrRoute(target.path, target.params)
}

function openImportedItem() {
  if (imported.value) goDetail(ROUTES.teacherQuestionBankDetail, { id: imported.value.id, status: 'active' })
}

function backToContent() {
  backOrRoute(ROUTES.teacherContent)
}

function backToQuestionBank() {
  backOrRoute(ROUTES.teacherQuestionBank, { status: 'active' })
}

onLoad((query) => {
  sourceId = String(query?.sourceId || '')
  finalTestId = String(query?.finalTestId || '')
  invalid.value = !uuid.test(sourceId) || Boolean(finalTestId && !uuid.test(finalTestId))
})

onShow(() => {
  const session = getSession()
  if (!requireRole('teacher') || !session || session.role !== 'teacher' || !session.openid) {
    pageVersion += 1
    visible = false
    identity = ''
    resetSourceContext()
    accessDenied.value = true
    requireRole('teacher')
    return
  }
  if (identity && identity !== session.openid) {
    pageVersion += 1
    resetSourceContext()
  }
  identity = session.openid
  pageVersion += 1
  visible = true
  accessDenied.value = false
  if (!invalid.value && !source.value && !loading.value) void loadSource()
})

onHide(() => {
  visible = false
  pageVersion += 1
  loadVersion += 1
  loading.value = false
})

onUnload(() => {
  visible = false
  pageVersion += 1
  resetSourceContext()
})

onBackPress(({ from }) => {
  if (importing.value) return true
  const target = sourceReturn()
  return handleBackPress(from, target.path, target.params)
})
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
.source-panel,
.conflict,
.success-panel {
  max-width: 920px;
  margin: 0 auto 24rpx;
}
.heading {
  display: flex;
  flex-direction: column;
  gap: 9rpx;
  padding: 4rpx 2rpx 12rpx;
}
.eyebrow,
.source-label {
  color: var(--med-brand, #0b716b);
  font-size: 24rpx;
  font-weight: 700;
}
.title {
  color: var(--med-text, #29465a);
  font-size: 34rpx;
  font-weight: 750;
  line-height: 1.4;
}
.intro,
.field-label,
.digest-state,
.refresh-state {
  color: var(--med-muted, #5c7080);
  font-size: 24rpx;
  line-height: 1.6;
}
.source-panel,
.conflict,
.success-panel {
  box-sizing: border-box;
  padding: 24rpx;
  background: var(--med-surface, #fff);
  border: 1px solid var(--med-border, #d7e2de);
  border-radius: 12rpx;
}
.source-panel {
  border-left: 4rpx solid var(--med-brand, #0b716b);
}
.source-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16rpx;
  padding-bottom: 18rpx;
  border-bottom: 1px solid var(--med-border, #d7e2de);
}
.source-heading > view {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 6rpx;
}
.source-title {
  color: var(--med-text, #29465a);
  font-size: 28rpx;
  font-weight: 700;
  line-height: 1.5;
  overflow-wrap: anywhere;
}
.digest-state {
  flex: none;
  padding: 5rpx 10rpx;
  color: var(--med-brand, #0b716b);
  background: var(--med-wash, #e7f2f0);
  border-radius: 6rpx;
  font-size: 24rpx;
}
.field-block {
  margin-top: 20rpx;
}
.field-label {
  display: block;
  margin-bottom: 8rpx;
  font-weight: 650;
}
.field-value,
.option-text {
  color: var(--med-text, #29465a);
  font-size: 24rpx;
  line-height: 1.65;
  overflow-wrap: anywhere;
}
.long-text {
  white-space: pre-wrap;
}
.option-row {
  display: flex;
  min-height: 64rpx;
  align-items: center;
  gap: 12rpx;
  padding: 8rpx 0;
  border-top: 1px solid var(--med-border, #d7e2de);
}
.option-letter {
  width: 34rpx;
  flex: none;
  color: var(--med-muted, #5c7080);
  font-size: 24rpx;
  font-weight: 700;
}
.option-text {
  flex: 1;
  min-width: 0;
}
.answer-tag {
  flex: none;
  color: var(--med-brand, #0b716b);
  font-size: 24rpx;
  font-weight: 700;
}
.target-fields {
  display: flex;
  gap: 18rpx;
}
.target-fields .field-block {
  min-width: 0;
  flex: 1;
}
.refresh-state {
  max-width: 920px;
  margin: 0 auto 12rpx;
}
.notice,
.conflict,
.error-inline {
  max-width: 920px;
  margin: 0 auto 14rpx;
  font-size: 24rpx;
  line-height: 1.6;
}
.notice {
  box-sizing: border-box;
  padding: 16rpx 18rpx;
  color: #775519;
  background: #fff8e8;
  border: 1px solid #ecd9aa;
  border-radius: 8rpx;
}
.conflict {
  color: #775519;
  background: #fff8e8;
}
.conflict text {
  display: block;
  margin-bottom: 12rpx;
}
.error-inline {
  color: #a34349;
}
.confirm-box {
  max-width: 920px;
  margin: 0 auto 16rpx;
}
.confirm-label {
  display: flex;
  min-height: 88rpx;
  align-items: center;
  gap: 12rpx;
  color: var(--med-text, #29465a);
  font-size: 24rpx;
  line-height: 1.55;
}
.actions,
.success-panel {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}
.actions {
  max-width: 920px;
  margin: 0 auto;
}
.primary,
.secondary,
.quiet {
  width: 100%;
  min-height: 88rpx;
  margin: 0;
  padding: 0 24rpx;
  border-radius: 10rpx;
  font-size: 24rpx;
  font-weight: 700;
}
.primary {
  color: #fff;
  background: var(--med-brand, #0b716b);
}
.secondary {
  color: var(--med-brand, #0b716b);
  background: var(--med-wash, #e7f2f0);
}
.quiet {
  color: var(--med-text, #29465a);
  background: #edf2f5;
}
.primary[disabled],
.secondary[disabled],
.quiet[disabled] {
  opacity: 0.56;
}
.success-panel {
  color: var(--med-text, #29465a);
}
.success-title {
  color: var(--med-brand, #0b716b);
  font-size: 27rpx;
  font-weight: 750;
}
.success-copy {
  margin-bottom: 8rpx;
  color: var(--med-muted, #5c7080);
  font-size: 24rpx;
  line-height: 1.6;
}
@media screen and (max-width: 620px) {
  .target-fields {
    flex-direction: column;
    gap: 0;
  }
}
</style>
