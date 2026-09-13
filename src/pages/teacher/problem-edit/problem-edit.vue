<template>
  <view class="safe-page edit-page page-enter">
    <view
      v-if="isLoading"
      class="editor-state"
      role="status"
      aria-live="polite"
    >
      <text class="state-kicker">教学任务编写台</text>
      <text class="state-title">正在读取题目</text>
      <text class="state-copy">请稍候，正在载入可编辑内容。</text>
    </view>

    <view
      v-else-if="loadError"
      class="editor-state editor-unavailable"
      role="alert"
    >
      <text class="state-kicker">题目不可编辑</text>
      <text class="state-title">{{ loadError }}</text>
      <text class="state-copy">没有读取到原题目，因此不会创建一条新的题目。</text>
      <button
        class="return-button pressable"
        role="button"
        :tabindex="0"
        hover-class="is-pressed"
        :hover-start-time="0"
        :hover-stay-time="80"
        @keydown="activateButtonOnKey"
        @click="back"
      >
        返回问题列表
      </button>
    </view>

    <template v-else>
      <view class="editor-header">
        <view class="header-topline">
          <text class="editor-kicker">教学任务编写台</text>
          <view class="header-actions">
            <text class="draft-state">{{ isEdit ? '编辑草稿' : '新建草稿' }}</text>
            <button
              class="editor-return pressable"
              role="button"
              tabindex="0"
              hover-class="is-pressed"
              :hover-start-time="0"
              :hover-stay-time="80"
              @keydown="activateButtonOnKey"
              @click="back"
            >
              返回
            </button>
          </view>
        </view>
        <text
          class="page-title"
          role="heading"
          aria-level="1"
          >{{ isEdit ? '调整教学问题' : '新建教学问题' }}</text
        >
        <text class="page-description">先写清学生要完成的学习任务，再确定它会发送给谁。</text>
      </view>

      <view class="editor-layout">
        <view class="content-column">
          <view class="form">
            <view class="section-intro">
              <view>
                <text
                  class="section-title"
                  role="heading"
                  aria-level="2"
                  >题目内容</text
                >
                <text class="section-description">定义这次练习的学习方式与提问重点。</text>
              </view>
            </view>

            <view
              class="type-group"
              role="group"
              aria-label="问题类型"
            >
              <text class="field-label">问题类型</text>
              <view class="type-options">
                <button
                  v-for="option in availableTypes"
                  :key="option"
                  class="type-choice pressable"
                  :class="{ active: type === option }"
                  role="button"
                  :tabindex="saving ? -1 : 0"
                  :disabled="saving"
                  :aria-disabled="saving"
                  :aria-pressed="type === option"
                  hover-class="is-pressed"
                  :hover-start-time="0"
                  :hover-stay-time="80"
                  @keydown="activateButtonOnKey"
                  @click="type = option"
                >
                  {{ option }}
                </button>
              </view>
              <text class="field-help">{{ typeGuidance }}</text>
            </view>

            <view class="field-block">
              <label
                id="problem-title-label"
                class="field-label"
                for="problem-title"
                >问题标题</label
              >
              <input
                id="problem-title"
                v-model="title"
                class="editor-input"
                :class="{ invalid: Boolean(titleError) }"
                name="problem-title"
                data-native-name="problem-title"
                aria-labelledby="problem-title-label"
                :aria-describedby="titleError ? 'problem-title-error' : 'problem-title-help'"
                :aria-invalid="Boolean(titleError)"
                placeholder="例如：抗菌药物合理使用的基本原则有哪些？"
                :maxlength="200"
                :disabled="saving"
                :focus="titleFocused"
                @blur="titleFocused = false"
                @input="titleError = ''"
              />
              <view class="field-meta">
                <text
                  id="problem-title-help"
                  class="field-meta-help"
                  >用一句话说清学生要讨论或完成的事。</text
                >
                <text class="field-meta-count">{{ title.length }} / 200</text>
              </view>
              <text
                v-if="titleError"
                id="problem-title-error"
                class="field-error"
                role="alert"
                >{{ titleError }}</text
              >
            </view>

            <view class="field-block description-block">
              <label
                id="problem-description-label"
                class="field-label"
                for="problem-description"
                >任务说明 <text class="label-optional">选填</text></label
              >
              <textarea
                id="problem-description"
                v-model="description"
                class="editor-textarea"
                name="problem-description"
                data-native-name="problem-description"
                aria-labelledby="problem-description-label"
                aria-describedby="problem-description-help"
                placeholder="补充情境、回答要点或课堂讨论要求。学生会看到这段说明。"
                :maxlength="2000"
                :disabled="saving"
              />
              <view class="field-meta">
                <text
                  id="problem-description-help"
                  class="field-meta-help"
                  >避免写入病人身份信息或仅供教师查看的评分依据。</text
                >
                <text class="field-meta-count">{{ description.length }} / 2000</text>
              </view>
            </view>
          </view>
        </view>

        <view class="scope-column">
          <view class="scope-panel">
            <view class="section-intro scope-heading">
              <view>
                <text
                  class="section-title"
                  role="heading"
                  aria-level="2"
                  >发布范围</text
                >
                <text class="section-description">仅选择确实需要收到任务的学生。</text>
              </view>
            </view>

            <view
              class="target-options"
              role="group"
              aria-label="发布对象"
            >
              <button
                v-for="item in targetOptions"
                :key="item.value"
                class="target-choice pressable"
                :class="{ active: target === item.value }"
                role="button"
                :tabindex="saving ? -1 : 0"
                :disabled="saving"
                :aria-disabled="saving"
                :aria-pressed="target === item.value"
                hover-class="is-pressed"
                :hover-start-time="0"
                :hover-stay-time="80"
                @keydown="activateButtonOnKey"
                @click="selectTarget(item.value)"
              >
                <view class="target-copy">
                  <text>{{ item.label }}</text>
                  <text class="target-detail">{{ item.description }}</text>
                </view>
                <text
                  class="target-check"
                  aria-hidden="true"
                  >{{ target === item.value ? '✓' : '' }}</text
                >
              </button>
            </view>

            <view
              v-if="target !== 'all'"
              class="target-details"
            >
              <view class="field-block compact-field">
                <label
                  id="target-label-label"
                  class="field-label"
                  for="target-label"
                  >{{ target === 'class' ? '班级名称' : '学生范围说明' }}</label
                >
                <input
                  id="target-label"
                  v-model="targetLabel"
                  class="editor-input"
                  :class="{ invalid: Boolean(targetError) }"
                  name="target-label"
                  data-native-name="target-label"
                  aria-labelledby="target-label-label"
                  :aria-describedby="targetError ? 'target-error' : 'target-label-help'"
                  :aria-invalid="Boolean(targetError)"
                  :placeholder="target === 'class' ? '例如：临床一班' : '例如：补修学生'"
                  :disabled="saving"
                  :focus="targetLabelFocused"
                  @blur="targetLabelFocused = false"
                  @input="targetError = ''"
                />
                <text
                  id="target-label-help"
                  class="compact-help"
                  >{{ target === 'class' ? '用于教师识别班级。' : '用于教师识别学生范围。' }}</text
                >
              </view>

              <view class="field-block compact-field">
                <label
                  id="target-ids-label"
                  class="field-label"
                  for="target-ids"
                  >{{ target === 'class' ? '班级 ID' : '学生 OpenID' }}</label
                >
                <input
                  id="target-ids"
                  v-model="targetIdsInput"
                  class="editor-input"
                  :class="{ invalid: Boolean(targetError) }"
                  name="target-ids"
                  data-native-name="target-ids"
                  aria-labelledby="target-ids-label"
                  :aria-describedby="targetError ? 'target-error' : 'target-ids-help'"
                  :aria-invalid="Boolean(targetError)"
                  placeholder="多个 ID 使用英文逗号分隔"
                  :disabled="saving"
                  @input="targetError = ''"
                />
                <text
                  id="target-ids-help"
                  class="compact-help"
                  >Demo：班级 demo_class_1；学生 demo_student。</text
                >
              </view>
              <text
                v-if="targetError"
                id="target-error"
                class="field-error"
                role="alert"
                >{{ targetError }}</text
              >
            </view>
          </view>

          <view class="save-panel">
            <text class="save-kicker">审核流程</text>
            <text class="save-title">{{ saving ? '正在保存草稿…' : '保存后进入待审核' }}</text>
            <text
              v-if="saveError"
              class="save-error"
              role="alert"
              >{{ saveError }}</text
            >
            <text
              v-else
              class="save-description"
              >保存不会直接向学生发布，审核通过后才能发布。</text
            >
            <button
              class="primary-button save pressable"
              role="button"
              :tabindex="saving ? -1 : 0"
              :loading="saving"
              :disabled="saving"
              :aria-disabled="saving"
              hover-class="is-pressed"
              :hover-start-time="0"
              :hover-stay-time="80"
              @keydown="activateButtonOnKey"
              @click="save"
            >
              {{ saving ? '正在保存' : '保存为待审核' }}
            </button>
          </view>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { onBackPress, onLoad } from '@dcloudio/uni-app'
import { activateButtonOnKey } from '@/components/ui/keyboard'
import { requireRole } from '@/features/identity/public'
import { backOrRoute, handleBackPress, ROUTES } from '@/platform/navigation'
import { findProblemAsync, upsertProblemAsync } from '@/features/content/public'
import type { ProblemTarget, ProblemType } from '@/types/domain'

const knownTypes: ProblemType[] = ['医学常识', '模拟诊疗', '病例分析']
const targetOptions: Array<{ value: ProblemTarget; label: string; description: string }> = [
  { value: 'all', label: '全体学生', description: '所有可见学生' },
  { value: 'class', label: '指定班级', description: '按班级发送' },
  { value: 'individual', label: '指定学生', description: '定向补充练习' },
]

const isEdit = ref(false)
const isLoading = ref(false)
const loadError = ref('')
const problemId = ref('')
const type = ref<ProblemType>(knownTypes[0])
const title = ref('')
const description = ref('')
const target = ref<ProblemTarget>('all')
const targetLabel = ref('')
const targetIdsInput = ref('')
const saving = ref(false)
const titleError = ref('')
const targetError = ref('')
const saveError = ref('')
const titleFocused = ref(false)
const targetLabelFocused = ref(false)
const savedSnapshot = ref(problemSnapshot())

function back() {
  if (saving.value) {
    uni.showToast({ title: '正在保存，请稍候', icon: 'none' })
    return
  }
  if (hasUnsavedChanges.value) {
    uni.showModal({
      title: '离开问题编写？',
      content: '当前修改尚未保存，离开后不会保留。',
      confirmText: '离开',
      success: ({ confirm }) => {
        if (confirm) leaveEditor()
      },
    })
    return
  }
  leaveEditor()
}

function leaveEditor() {
  backOrRoute(ROUTES.teacherWorkspace, { tab: 'problems', section: 'resources' })
}

function problemSnapshot() {
  return JSON.stringify({
    type: type.value,
    title: title.value,
    description: description.value,
    target: target.value,
    targetLabel: targetLabel.value,
    targetIdsInput: targetIdsInput.value,
  })
}

const hasUnsavedChanges = computed(() => problemSnapshot() !== savedSnapshot.value)

function markSaved() {
  savedSnapshot.value = problemSnapshot()
}

const availableTypes = computed(() => (knownTypes.includes(type.value) ? knownTypes : [...knownTypes, type.value]))
const typeGuidance = computed(() => {
  const guidance: Record<string, string> = {
    医学常识: '适合知识要点梳理、概念辨析与规范说明。',
    模拟诊疗: '适合在给定情境下练习问诊、判断与处置思路。',
    病例分析: '适合围绕病例证据组织鉴别诊断与推理过程。',
  }
  return guidance[type.value] || '按当前题型组织学生需要完成的学习任务。'
})

onLoad((options) => {
  if (!requireRole('teacher')) return
  const id = typeof options?.id === 'string' ? options.id : ''
  void loadProblem(id)
})
onBackPress(({ from }) => {
  if (from === 'navigateBack') return false
  if (saving.value) {
    uni.showToast({ title: '正在保存，请稍候', icon: 'none' })
    return true
  }
  if (hasUnsavedChanges.value) {
    back()
    return true
  }
  return handleBackPress(from, ROUTES.teacherWorkspace, { tab: 'problems', section: 'resources' })
})

async function loadProblem(id: string) {
  if (!id) return
  isLoading.value = true
  loadError.value = ''
  try {
    const problem = await findProblemAsync(id)
    if (!problem) {
      loadError.value = '题目不存在或已被移除。'
      return
    }
    isEdit.value = true
    problemId.value = problem.id
    type.value = problem.type
    title.value = problem.title
    description.value = problem.description
    target.value = problem.target
    targetLabel.value = problem.targetLabel || problem.className || ''
    targetIdsInput.value = (problem.targetIds || []).join(', ')
    markSaved()
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '题目加载失败，请稍后重试。'
  } finally {
    isLoading.value = false
  }
}

function selectTarget(value: ProblemTarget) {
  target.value = value
  targetError.value = ''
}

function validate(): boolean {
  titleError.value = ''
  targetError.value = ''
  saveError.value = ''
  if (!title.value.trim()) {
    titleError.value = '请填写问题标题。'
    void nextTick(() => {
      titleFocused.value = true
    })
    return false
  }
  const targetIds = targetIdsInput.value
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean)
  if (target.value !== 'all' && (!targetLabel.value.trim() || targetIds.length === 0)) {
    targetError.value = '请同时填写发布对象名称和 ID。'
    void nextTick(() => {
      targetLabelFocused.value = true
    })
    return false
  }
  return true
}

async function save() {
  if (saving.value || !validate()) return
  const targetIds = targetIdsInput.value
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean)
  saving.value = true
  try {
    const existing = isEdit.value ? await findProblemAsync(problemId.value) : undefined
    if (isEdit.value && !existing) {
      saveError.value = '原题目已不存在，未保存任何修改。请返回列表刷新后重试。'
      return
    }
    await upsertProblemAsync({
      id: existing?.id || `prob_${Date.now()}`,
      type: type.value,
      title: title.value.trim(),
      description: description.value.trim(),
      target: target.value,
      targetIds: target.value === 'all' ? [] : targetIds,
      targetLabel: target.value === 'all' ? '全体学生' : targetLabel.value.trim(),
      status: '待审核',
      time: new Date().toISOString().slice(0, 10),
    })
    markSaved()
    uni.showToast({ title: '已保存为待审核', icon: 'success' })
    leaveEditor()
  } catch (error) {
    saveError.value = error instanceof Error ? error.message : '保存失败，请重试。当前填写内容仍保留。'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.edit-page {
  padding: 36rpx 28rpx calc(64rpx + env(safe-area-inset-bottom));
  background: var(--med-paper);
}
.editor-header {
  padding: 0 4rpx 32rpx;
  border-bottom: 2rpx solid var(--med-ink);
}
.header-topline {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16rpx;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 12rpx;
}
.editor-return {
  min-width: 84rpx;
  min-height: 56rpx;
  margin: 0;
  padding: 0 14rpx;
  color: var(--med-clinical);
  background: var(--med-wash);
  border-radius: var(--med-radius-sm);
  font-size: 22rpx;
  line-height: 56rpx;
}
.editor-kicker,
.save-kicker,
.state-kicker {
  color: var(--med-clinical);
  font-family: var(--med-font-utility);
  font-size: 22rpx;
  font-weight: 700;
  letter-spacing: 2rpx;
}
.draft-state {
  color: var(--med-safety);
  font-size: 22rpx;
  font-weight: 600;
}
.page-title,
.state-title {
  display: block;
  margin-top: 16rpx;
  color: var(--med-ink);
  font-size: 48rpx;
  font-weight: 800;
  line-height: 1.28;
}
.page-description,
.section-description,
.field-help,
.field-meta,
.compact-help,
.save-description,
.state-copy {
  display: block;
  color: var(--med-muted);
  font-size: 24rpx;
  line-height: 1.65;
}
.page-description {
  margin-top: 12rpx;
}
.editor-layout {
  padding-top: 36rpx;
}
.content-column,
.scope-column {
  min-width: 0;
}
.form,
.scope-panel {
  background: var(--med-surface);
  border-top: 4rpx solid var(--med-clinical);
}
.form {
  padding: 28rpx 24rpx 32rpx;
}
.scope-panel {
  margin-top: 32rpx;
  padding: 28rpx 24rpx 32rpx;
}
.section-intro {
  display: flex;
  align-items: flex-start;
  gap: 16rpx;
}
.section-title {
  display: block;
  color: var(--med-ink);
  font-size: 36rpx;
  font-weight: 750;
  line-height: 1.35;
}
.section-description {
  margin-top: 6rpx;
}
.type-group,
.field-block {
  margin-top: 32rpx;
}
.field-label {
  display: block;
  color: var(--med-text);
  font-size: 27rpx;
  font-weight: 650;
  line-height: 1.5;
}
.label-optional {
  margin-left: 8rpx;
  color: var(--med-muted);
  font-size: 22rpx;
  font-weight: 400;
}
.type-options {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12rpx;
  margin-top: 14rpx;
}
.type-choice,
.target-choice,
.return-button {
  box-sizing: border-box;
  color: var(--med-text-secondary);
  background: transparent;
  border: 1rpx solid var(--med-border);
  border-radius: var(--med-radius-sm);
  font: inherit;
}
.type-choice {
  width: 100%;
  min-height: 88rpx;
  margin: 0;
  padding: 12rpx 8rpx;
  font-size: 24rpx;
  line-height: 1.35;
}
.type-choice.active,
.target-choice.active {
  color: var(--med-clinical);
  background: var(--med-wash);
  border-color: var(--med-clinical);
  font-weight: 700;
}
.field-help {
  margin-top: 10rpx;
}
.editor-input,
.editor-textarea {
  width: 100%;
  box-sizing: border-box;
  margin-top: 12rpx;
  padding: 20rpx;
  color: var(--med-ink);
  background: var(--med-surface);
  border: 1rpx solid var(--med-border);
  border-radius: var(--med-radius-sm);
  font-size: 28rpx;
  line-height: 1.55;
}
.editor-input {
  min-height: 88rpx;
}
.editor-textarea {
  height: 264rpx;
}
.editor-input.invalid,
.editor-textarea.invalid {
  border-color: var(--med-danger);
}
.field-meta {
  display: flex;
  margin-top: 10rpx;
  justify-content: space-between;
  gap: 16rpx;
  font-size: 21rpx;
}
.field-meta-help {
  min-width: 0;
}
.field-meta-count {
  flex: none;
  font-family: var(--med-font-utility);
}
.field-error,
.save-error {
  display: block;
  margin-top: 10rpx;
  color: var(--med-danger);
  font-size: 23rpx;
  line-height: 1.55;
}
.target-options {
  display: grid;
  gap: 12rpx;
  margin-top: 28rpx;
}
.target-choice {
  display: flex;
  width: 100%;
  min-height: 112rpx;
  margin: 0;
  padding: 16rpx 18rpx;
  align-items: baseline;
  justify-content: space-between;
  gap: 16rpx;
  text-align: left;
  font-size: 26rpx;
}
.target-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 4rpx;
}
.target-detail {
  color: var(--med-muted);
  font-size: 21rpx;
  font-weight: 400;
}
.target-check {
  min-width: 32rpx;
  color: var(--med-clinical);
  font-family: var(--med-font-utility);
  font-size: 28rpx;
  font-weight: 700;
  text-align: right;
}
.target-choice.active .target-detail {
  color: var(--med-clinical);
}
.target-details {
  margin-top: 28rpx;
  padding-top: 4rpx;
  border-top: 1rpx solid var(--med-divider);
}
.compact-field {
  margin-top: 22rpx;
}
.compact-help {
  margin-top: 8rpx;
  font-size: 21rpx;
}
.save-panel {
  margin-top: 32rpx;
  padding: 28rpx 24rpx 0;
  border-top: 2rpx solid var(--med-ink);
}
.save-title {
  display: block;
  margin-top: 10rpx;
  color: var(--med-ink);
  font-size: 32rpx;
  font-weight: 750;
}
.save-description {
  margin-top: 8rpx;
}
.save {
  width: 100%;
  margin-top: 24rpx;
  border-radius: var(--med-radius-sm);
}
.editor-state {
  margin-top: 120rpx;
  padding: 0 12rpx;
}
.state-copy {
  margin-top: 12rpx;
}
.return-button {
  min-height: 80rpx;
  margin-top: 28rpx;
  padding: 0 28rpx;
  color: var(--med-clinical);
  font-size: 26rpx;
  font-weight: 650;
}
@media screen and (max-width: 360px) {
  .edit-page {
    padding-right: 16px;
    padding-left: 16px;
  }
  .editor-kicker,
  .save-kicker,
  .state-kicker,
  .draft-state,
  .label-optional,
  .field-meta,
  .compact-help,
  .field-error,
  .save-error,
  .target-detail {
    font-size: 12px;
  }
  .page-description,
  .section-description,
  .field-help,
  .save-description,
  .state-copy {
    font-size: 13px;
  }
  .page-title,
  .state-title {
    font-size: 25px;
  }
  .section-title {
    font-size: 18px;
  }
  .field-label,
  .target-choice,
  .return-button {
    font-size: 14px;
  }
  .type-choice {
    font-size: 13px;
  }
  .editor-input,
  .editor-textarea {
    font-size: 15px;
  }
  .save-title {
    font-size: 17px;
  }
}
@media screen and (min-width: 600px) {
  .edit-page {
    padding: 40px 48px calc(48px + env(safe-area-inset-bottom));
  }
  .editor-header {
    padding: 0 4px 28px;
    border-bottom-width: 1px;
  }
  .editor-kicker,
  .save-kicker,
  .state-kicker,
  .draft-state {
    font-size: 13px;
    letter-spacing: 1px;
  }
  .page-title,
  .state-title {
    margin-top: 12px;
    font-size: 32px;
  }
  .page-description,
  .section-description,
  .field-help,
  .save-description,
  .state-copy {
    font-size: 14px;
  }
  .editor-layout {
    padding-top: 32px;
  }
  .form,
  .scope-panel {
    border-top-width: 2px;
  }
  .form {
    padding: 24px 28px 28px;
  }
  .scope-panel {
    margin-top: 28px;
    padding: 24px 28px 28px;
  }
  .section-title {
    font-size: 20px;
  }
  .section-description {
    margin-top: 4px;
  }
  .type-group,
  .field-block {
    margin-top: 28px;
  }
  .field-label {
    font-size: 15px;
  }
  .label-optional,
  .field-meta,
  .compact-help,
  .field-error,
  .save-error,
  .target-detail {
    font-size: 13px;
  }
  .type-options {
    gap: 8px;
    margin-top: 8px;
  }
  .type-choice {
    min-height: 44px;
    padding: 6px;
    font-size: 14px;
  }
  .field-help {
    margin-top: 8px;
  }
  .editor-input,
  .editor-textarea {
    margin-top: 8px;
    padding: 12px;
    font-size: 16px;
  }
  .editor-input {
    min-height: 48px;
  }
  .editor-textarea {
    height: 176px;
  }
  .field-meta {
    margin-top: 8px;
    gap: 8px;
  }
  .field-error,
  .save-error {
    margin-top: 8px;
  }
  .target-options {
    gap: 8px;
    margin-top: 24px;
  }
  .target-choice {
    min-height: 56px;
    padding: 10px 12px;
    gap: 12px;
    font-size: 14px;
  }
  .target-details {
    margin-top: 24px;
  }
  .compact-field {
    margin-top: 18px;
  }
  .compact-help {
    margin-top: 6px;
  }
  .save-panel {
    margin-top: 28px;
    padding: 24px 0 0;
    border-top-width: 1px;
  }
  .save-title {
    margin-top: 8px;
    font-size: 18px;
  }
  .save {
    min-height: 48px;
    margin-top: 20px;
    font-size: 16px;
  }
  .editor-state {
    margin-top: 120px;
  }
  .return-button {
    min-height: 44px;
    margin-top: 24px;
    padding: 0 20px;
    font-size: 14px;
  }
}
@media screen and (min-width: 900px) {
  .editor-layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 304px;
    align-items: start;
    gap: 40px;
  }
  .scope-panel {
    margin-top: 0;
  }
  .scope-column {
    position: sticky;
    top: 32px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .page-enter {
    animation: none;
  }
}
</style>
