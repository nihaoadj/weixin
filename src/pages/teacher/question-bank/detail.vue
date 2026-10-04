<template>
  <view class="safe-page bank-detail">
    <MedState
      v-if="scopeExpired"
      variant="error"
      icon="retry"
      title="教师账号已变更"
      description="为保护教师题库内容，已清除原账号读取的数据。"
      action-label="返回个人题库"
      @action="backToCurrentBank"
    />
    <MedState
      v-else-if="loading && !item"
      variant="loading"
      icon="history"
      title="正在读取题库题目"
      description="核对当前教师的题目与版本。"
    />
    <MedState
      v-else-if="loadError && !item"
      variant="error"
      icon="retry"
      title="题库题目暂不可用"
      :description="loadError"
      action-label="重试"
      secondary-action-label="返回个人题库"
      @action="load"
      @secondary-action="back"
    />
    <template v-else-if="item">
      <view class="detail-head">
        <text class="eyebrow">教师个人副本</text>
        <text class="page-title">{{ item.title }}</text>
        <text class="meta">{{ taskTypeLabel(item.taskType) }} · 版本 v{{ item.version }}</text>
      </view>

      <view class="form-section">
        <text class="section-title">题目内容</text>
        <text class="field-label">标题</text>
        <input
          v-model="form.title"
          class="field"
          maxlength="200"
          :disabled="busy"
          @input="markDirty"
        />
        <text class="field-label">题干</text>
        <textarea
          v-model="form.prompt"
          class="field textarea"
          maxlength="2000"
          :disabled="busy"
          @input="markDirty"
        />
        <template v-if="isObjective">
          <text class="field-label">选项（每行一项）</text>
          <textarea
            v-model="form.optionsText"
            class="field textarea options"
            maxlength="3000"
            :disabled="busy"
            @input="markDirty"
          />
          <text class="field-label">正确答案</text>
          <picker
            :range="options"
            :disabled="busy || !options.length"
            @change="setCorrectOption"
          >
            <view class="field picker-field">{{ correctOptionLabel }}<text>⌄</text></view>
          </picker>
        </template>
        <template v-else>
          <text class="field-label">答案 / 评分依据（JSON）</text>
          <textarea
            v-model="form.answerJson"
            class="field textarea answer"
            maxlength="5000"
            :disabled="busy"
            @input="markDirty"
          />
        </template>
        <text class="field-label">解析 / 反馈要点</text>
        <textarea
          v-model="form.explanation"
          class="field textarea"
          maxlength="2000"
          :disabled="busy"
          @input="markDirty"
        />
      </view>

      <view class="form-section target-section">
        <text class="section-title">学习目标</text>
        <text class="field-label">知识点编码（逗号分隔）</text>
        <textarea
          v-model="form.pointCodesText"
          class="field textarea short"
          :disabled="busy"
          @input="markDirty"
        />
        <text class="field-label">能力维度（逗号分隔，可空）</text>
        <textarea
          v-model="form.dimensionIdsText"
          class="field textarea short"
          :disabled="busy"
          @input="markDirty"
        />
        <text class="hint">知识点必须是系统目录中的有效编码；保存时服务端会再次校验。</text>
      </view>

      <view
        v-if="loadError"
        class="error-inline"
        role="alert"
        >{{ loadError }}</view
      >
      <view
        v-if="actionError"
        class="error-inline"
        role="alert"
        >{{ actionError }}</view
      >
      <view
        v-if="item"
        class="actions"
      >
        <button
          class="primary-button"
          :disabled="busy || !dirty"
          @click="save"
        >
          {{ busy && action === 'save' ? '正在保存…' : '保存修改' }}
        </button>
        <button
          class="delete-button"
          :disabled="busy"
          @click="confirmDelete"
        >
          {{ busy && action === 'delete' ? '正在删除…' : '删除题目' }}
        </button>
      </view>
      <button
        v-if="dirty"
        class="reload-button"
        :disabled="busy"
        @click="confirmReload"
      >
        取回服务器最新版
      </button>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref } from 'vue'
import { onBackPress, onLoad, onShow } from '@dcloudio/uni-app'
import MedState from '@/components/ui/MedState.vue'
import {
  deleteTeacherQuestionBankItem,
  getTeacherQuestionBankItem,
  updateTeacherQuestionBankItem,
  type TeacherQuestionBankContent,
  type TeacherQuestionBankItem,
  type TeacherQuestionBankTaskType,
} from '@/features/content/public'
import { getSession, requireRole } from '@/features/identity/public'
import { backOrRoute, handleBackPress, ROUTES } from '@/platform/navigation'
import { teacherContentReturnParams } from '@/platform/navigation/teacher'

const item = ref<TeacherQuestionBankItem>()
const loading = ref(false)
const loadError = ref('')
const actionError = ref('')
const busy = ref(false)
const action = ref<'save' | 'delete' | ''>('')
const dirty = ref(false)
const scopeExpired = ref(false)
const form = reactive({
  title: '',
  prompt: '',
  optionsText: '',
  correctOption: -1,
  answerJson: '{}',
  explanation: '',
  pointCodesText: '',
  dimensionIdsText: '',
})
let itemId = 0
let contentReturn = teacherContentReturnParams({}, 'question-bank')
let teacherOpenid = ''
let version = 0
let disposed = false
onBeforeUnmount(() => {
  disposed = true
  version += 1
})

const isObjective = computed(() => item.value?.taskType === 'retest' || item.value?.taskType === 'knowledge_review')
const options = computed(() =>
  form.optionsText
    .split('\n')
    .map((value) => value.trim())
    .filter(Boolean),
)
const correctOptionLabel = computed(() =>
  form.correctOption >= 0 && options.value[form.correctOption]
    ? `${String.fromCharCode(65 + form.correctOption)}. ${options.value[form.correctOption]}`
    : '请选择正确答案',
)

function taskTypeLabel(value: TeacherQuestionBankTaskType) {
  return {
    retest: '目标验证再测',
    knowledge_review: '知识点巩固',
    discussion: '结构化讨论',
    micro_drill: '推理微训练',
  }[value]
}
function fillForm(value: TeacherQuestionBankItem) {
  item.value = value
  form.title = value.title
  form.prompt = value.prompt
  form.optionsText = value.options.join('\n')
  form.correctOption = typeof value.answer.correct_option === 'number' ? value.answer.correct_option : -1
  form.answerJson = JSON.stringify(value.answer, null, 2)
  form.explanation = value.explanation
  form.pointCodesText = value.pointCodes.join(', ')
  form.dimensionIdsText = value.dimensionIds.join(', ')
  dirty.value = false
  actionError.value = ''
}
function markDirty() {
  dirty.value = true
  actionError.value = ''
}
function setCorrectOption(event: { detail: { value: string | number } }) {
  form.correctOption = Number(event.detail.value)
  markDirty()
}
function parseCodes(value: string) {
  return [
    ...new Set(
      value
        .split(/[\n,，]/)
        .map((part) => part.trim())
        .filter(Boolean),
    ),
  ]
}
function contentToSave(): TeacherQuestionBankContent {
  const current = item.value
  if (!current) throw new Error('题库题目尚未加载。')
  let answer: Record<string, unknown>
  if (isObjective.value) {
    if (form.correctOption < 0 || form.correctOption >= options.value.length) throw new Error('请选择有效的正确答案。')
    answer = { correct_option: form.correctOption }
  } else {
    try {
      const parsed: unknown = JSON.parse(form.answerJson || '{}')
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error()
      answer = parsed as Record<string, unknown>
    } catch {
      throw new Error('答案 / 评分依据必须是有效 JSON 对象。')
    }
  }
  return {
    taskType: current.taskType,
    title: form.title,
    prompt: form.prompt,
    options: isObjective.value ? options.value : [],
    answer,
    explanation: form.explanation,
    pointCodes: parseCodes(form.pointCodesText),
    dimensionIds: parseCodes(form.dimensionIdsText),
  }
}
async function load() {
  if (!itemId || !verifyTeacherSession() || loading.value) return
  const current = ++version
  loading.value = true
  loadError.value = ''
  try {
    const loaded = await getTeacherQuestionBankItem(itemId)
    if (current !== version || !verifyTeacherSession()) return
    fillForm(loaded)
  } catch (reason) {
    if (current === version && verifyTeacherSession())
      loadError.value = reason instanceof Error ? reason.message : '读取题库题目失败。'
  } finally {
    if (current === version) loading.value = false
  }
}
async function save() {
  const current = item.value
  if (!current || !verifyTeacherSession() || busy.value || !dirty.value) return
  const requestVersion = version
  busy.value = true
  action.value = 'save'
  actionError.value = ''
  try {
    const saved = await updateTeacherQuestionBankItem(current.id, current.version, contentToSave())
    if (requestVersion !== version || !verifyTeacherSession()) return
    fillForm(saved)
    uni.showToast({ title: '题目已保存', icon: 'success' })
  } catch (reason) {
    if (requestVersion === version && verifyTeacherSession())
      actionError.value = reason instanceof Error ? reason.message : '保存失败；当前编辑内容仍保留。'
  } finally {
    if (requestVersion === version) {
      busy.value = false
      action.value = ''
    }
  }
}
function confirmDelete() {
  const current = item.value
  if (!current || !verifyTeacherSession() || busy.value) return
  busy.value = true
  action.value = 'delete'
  uni.showModal({
    title: '删除这道题？',
    content: '删除后从个人题库移除，原测试及历史作答仍会保留。',
    confirmText: '删除',
    success: ({ confirm }) => {
      if (!verifyTeacherSession()) return
      if (confirm) void removeItem(current)
      else {
        busy.value = false
        action.value = ''
      }
    },
    fail: () => {
      if (verifyTeacherSession()) {
        busy.value = false
        action.value = ''
      }
    },
  })
}
async function removeItem(current: TeacherQuestionBankItem) {
  if (!verifyTeacherSession()) return
  const requestVersion = version
  actionError.value = ''
  try {
    await deleteTeacherQuestionBankItem(
      current.id,
      current.version,
      `t64-bank-delete-${current.id}-v${current.version}`,
    )
    if (requestVersion !== version || !verifyTeacherSession()) return
    item.value = undefined
    dirty.value = false
    uni.showToast({ title: '题目已删除', icon: 'success' })
    backOrRoute(ROUTES.teacherContent, contentReturn)
  } catch (reason) {
    if (requestVersion === version && verifyTeacherSession())
      actionError.value = reason instanceof Error ? reason.message : '删除失败，题目仍保留。'
  } finally {
    if (requestVersion === version) {
      busy.value = false
      action.value = ''
    }
  }
}
function confirmReload() {
  if (dirty.value) {
    uni.showModal({
      title: '取回最新版',
      content: '当前未保存的编辑将被放弃。确定继续吗？',
      success: ({ confirm }) => {
        if (confirm) void load()
      },
    })
  } else void load()
}
function back() {
  if (busy.value) return
  if (dirty.value && verifyTeacherSession()) {
    uni.showModal({
      title: '离开题目编辑？',
      content: '当前修改尚未保存，离开后不会保留。',
      confirmText: '离开',
      success: ({ confirm }) => {
        if (confirm && verifyTeacherSession()) backOrRoute(ROUTES.teacherContent, contentReturn)
      },
    })
    return
  }
  backOrRoute(ROUTES.teacherContent, contentReturn)
}
function backToCurrentBank() {
  backOrRoute(ROUTES.teacherContent, { resource: 'question-bank' })
}
function verifyTeacherSession(): boolean {
  if (scopeExpired.value || disposed) return false
  const session = getSession()
  if (session?.role === 'teacher' && session.openid === teacherOpenid) return true

  version += 1
  scopeExpired.value = true
  item.value = undefined
  loading.value = false
  busy.value = false
  action.value = ''
  dirty.value = false
  loadError.value = ''
  actionError.value = ''
  form.title = ''
  form.prompt = ''
  form.optionsText = ''
  form.correctOption = -1
  form.answerJson = '{}'
  form.explanation = ''
  form.pointCodesText = ''
  form.dimensionIdsText = ''
  if (session?.role !== 'teacher') requireRole('teacher')
  return false
}
onLoad((query) => {
  if (!requireRole('teacher')) {
    scopeExpired.value = true
    return
  }
  const session = getSession()
  if (!session || session.role !== 'teacher') {
    scopeExpired.value = true
    requireRole('teacher')
    return
  }
  teacherOpenid = session.openid
  itemId = Number(query?.id)
  contentReturn = teacherContentReturnParams(query, 'question-bank')
  if (!Number.isSafeInteger(itemId) || itemId <= 0) {
    loadError.value = '题目编号无效。'
    return
  }
  void load()
})
onShow(() => {
  if (teacherOpenid) verifyTeacherSession()
})
onBackPress(({ from }) => {
  if (from === 'navigateBack') return false
  if (busy.value) return true
  if (dirty.value) {
    back()
    return true
  }
  return handleBackPress(from, ROUTES.teacherContent, contentReturn)
})
</script>

<style scoped>
.bank-detail {
  display: flex;
  padding: 28rpx 24rpx calc(56rpx + env(safe-area-inset-bottom));
  flex-direction: column;
  gap: 24rpx;
  color: var(--med-ink);
}
.detail-head {
  display: flex;
  padding: 8rpx 4rpx 20rpx;
  flex-direction: column;
  gap: 10rpx;
  border-bottom: 1rpx solid var(--med-line);
}
.eyebrow {
  color: var(--med-primary);
  font-size: 22rpx;
  font-weight: 700;
}
.page-title {
  font-size: 34rpx;
  font-weight: 750;
  line-height: 1.4;
}
.meta,
.hint,
.warning,
.read-only-note {
  color: var(--med-muted);
  font-size: 22rpx;
  line-height: 1.55;
}
.warning {
  color: #9a5a19;
}
.form-section {
  display: flex;
  padding: 22rpx;
  flex-direction: column;
  gap: 12rpx;
  background: var(--med-surface);
  border: 1rpx solid var(--med-line);
  border-radius: 16rpx;
}
.section-title {
  margin-bottom: 4rpx;
  font-size: 28rpx;
  font-weight: 700;
}
.field-label {
  margin-top: 8rpx;
  color: var(--med-muted);
  font-size: 22rpx;
}
.field {
  min-height: 76rpx;
  padding: 14rpx 16rpx;
  box-sizing: border-box;
  color: var(--med-ink);
  background: #f7f9fc;
  border: 1rpx solid var(--med-line);
  border-radius: 10rpx;
  font-size: 24rpx;
  line-height: 1.55;
}
.textarea {
  width: 100%;
  min-height: 180rpx;
}
.textarea.options {
  min-height: 210rpx;
}
.textarea.answer {
  min-height: 220rpx;
  font-family: monospace;
}
.textarea.short {
  min-height: 105rpx;
}
.picker-field {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.target-section {
  background: #f7fafc;
}
.actions {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}
.primary-button,
.delete-button {
  min-height: 84rpx;
  margin: 0;
  color: #fff;
  background: var(--med-primary);
  border-radius: 12rpx;
  font-size: 25rpx;
}
.delete-button {
  color: #8e3f3b;
  background: #fff;
  border: 1rpx solid #e6c6c3;
}
.reload-button {
  min-height: 72rpx;
  color: var(--med-primary);
  background: transparent;
  font-size: 23rpx;
}
.error-inline {
  padding: 14rpx 16rpx;
  color: #9c3f3a;
  background: #fff5f4;
  border-radius: 10rpx;
  font-size: 23rpx;
  line-height: 1.5;
}
.read-only-note {
  padding: 16rpx 4rpx;
}
</style>
