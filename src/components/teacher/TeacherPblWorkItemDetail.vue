<template>
  <view
    v-if="selected"
    class="detail"
  >
    <button
      class="back"
      role="button"
      tabindex="0"
      @keydown="activateButtonOnKey"
      @click="$emit('back')"
    >
      返回列表
    </button>
    <view
      v-if="error"
      role="alert"
      >{{ error }}
      <button
        role="button"
        tabindex="0"
        @keydown="activateButtonOnKey"
        @click="$emit('retry')"
      >
        重试
      </button></view
    >
    <text v-else-if="loading">正在加载诊断详情…</text>
    <template v-else-if="detail">
      <text class="detail-heading">{{ detail.diagnostic.studentName }} · {{ detail.diagnostic.className }}</text>
      <text class="status-line">{{ displayStatus(selected.status) }} · {{ selected.nextAction }}</text>
      <text>固定诊断轨迹：学生提交 → 教师反馈/发布 → 学生完成 → 系统判定</text>
      <text class="evidence">诊断证据：{{ detail.diagnostic.phaseEvidenceSummary || '未提供阶段证据摘要' }}</text>
      <view class="finding-group">
        <text class="group-heading">知识薄弱点</text>
        <text
          v-if="!detail.diagnostic.knowledgeGaps.length"
          class="muted"
          >未识别到知识薄弱点。</text
        >
        <text
          v-for="gap in detail.diagnostic.knowledgeGaps"
          :key="gap.id"
          >{{ gap.summary }}</text
        >
      </view>
      <view class="finding-group">
        <text class="group-heading">推理问题</text>
        <text
          v-if="!detail.diagnostic.reasoningIssues.length"
          class="muted"
          >未识别到推理问题。</text
        >
        <text
          v-for="issue in detail.diagnostic.reasoningIssues"
          :key="issue.id"
          >{{ issue.summary }}<template v-if="issue.improvement">；建议：{{ issue.improvement }}</template></text
        >
      </view>
      <view class="finding-group">
        <text class="group-heading">建议题（AI 建议，须教师确认后发布）</text>
        <text
          v-if="!originalSuggestions.length"
          class="muted"
          >当前诊断没有可发布建议题。</text
        >
        <view
          v-for="suggestion in originalSuggestions"
          :key="suggestion.id"
          class="suggestion"
        >
          <text>{{ suggestion.title }}</text>
          <text class="muted">{{ suggestion.prompt }}</text>
        </view>
      </view>
      <view
        v-if="detail.feedbacks.length"
        class="finding-group"
      >
        <text class="group-heading">处置记录</text>
        <text
          v-for="feedback in detail.feedbacks"
          :key="feedback.id"
          >教师反馈：{{ feedback.body }}</text
        >
      </view>
      <view
        v-if="canAct"
        class="feedback-form"
      >
        <text class="group-heading">形成性反馈与处置</text>
        <textarea
          :value="body"
          maxlength="1000"
          aria-label="形成性反馈"
          :aria-invalid="Boolean(actionError)"
          placeholder="填写 1–1000 字形成性反馈"
          @input="updateBody"
        />
        <picker
          v-if="draftSuggestions.length"
          :range="draftSuggestions"
          range-key="title"
          role="button"
          tabindex="0"
          @keydown="activatePickerOnKey"
          @change="suggestionIndex = Number($event.detail.value)"
        >
          <view class="suggestion-picker">发布建议：{{ selectedSuggestion?.title || '请选择建议题' }}</view>
        </picker>
        <view
          v-if="selectedSuggestion"
          class="suggestion-editor"
        >
          <text class="editor-label">教师确认稿</text>
          <input
            v-model.trim="selectedSuggestion.title"
            maxlength="200"
            aria-label="正式任务标题"
            :aria-invalid="!selectedSuggestion.title.trim()"
            placeholder="填写正式任务标题"
          />
          <textarea
            v-model="selectedSuggestion.prompt"
            maxlength="2000"
            aria-label="正式任务题干"
            :aria-invalid="!selectedSuggestion.prompt.trim()"
            placeholder="填写正式任务题干"
          />
          <text
            v-if="!publishValid"
            class="action-error"
            role="alert"
            >正式任务标题和题干不能为空。</text
          >
          <text class="target-hint">编辑内容只会在本次“反馈并发布任务”中作为教师确认稿提交。</text>
        </view>
        <view
          v-if="!wholeClass"
          class="student-targets"
          aria-label="选择发布学生"
        >
          <text>发布对象</text>
          <text class="target-hint">默认来源学生；可改为同班学生</text>
          <label
            v-for="student in students"
            :key="student.id"
            class="student-option"
          >
            <checkbox
              :checked="selectedTargetIds.includes(student.id)"
              @click="$emit('toggleTarget', student.id)"
            />{{ student.nickname }}
          </label>
        </view>
        <label class="whole-class-option"
          ><checkbox
            :checked="wholeClass"
            @click="$emit('toggleWholeClass')"
          />发布给全班</label
        >
        <text
          v-if="actionError"
          class="action-error"
          role="alert"
          >{{ actionError }}</text
        >
        <view class="actions">
          <button
            :disabled="busy || !valid"
            :tabindex="busy || !valid ? -1 : 0"
            role="button"
            @keydown="activateButtonOnKey"
            @click="$emit('submit', 'feedback_only')"
          >
            仅发送反馈
          </button>
          <button
            :disabled="busy || !valid"
            :tabindex="busy || !valid ? -1 : 0"
            role="button"
            @keydown="activateButtonOnKey"
            @click="$emit('submit', 'closed')"
          >
            反馈后关闭
          </button>
          <button
            :disabled="busy || !valid || !publishValid || (!wholeClass && !selectedTargetIds.length)"
            :tabindex="busy || !valid || !publishValid || (!wholeClass && !selectedTargetIds.length) ? -1 : 0"
            role="button"
            @keydown="activateButtonOnKey"
            @click="$emit('submit', 'task_published', selectedSuggestion)"
          >
            反馈并发布任务
          </button>
        </view>
      </view>
      <text
        v-else
        class="terminal-copy"
        >该诊断已完成终态处置；可在状态筛选中回看来源与处置记录，正式任务请到“学情 / PBL 跟进”查看。</text
      >
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { activateButtonOnKey, activatePickerOnKey } from '@/components/ui/keyboard'
import type {
  PblDiagnostic,
  PblSuggestion,
  PblTeacherFeedback,
  PblWorkItem,
  PblWorkStatus,
} from '@/features/pbl/public'
import type { TeacherStudent } from '@/features/classroom/public'

type WorkItemDetail = {
  workItem?: PblWorkItem
  diagnostic: PblDiagnostic
  feedbacks: PblTeacherFeedback[]
}
type WorkItemAction = 'feedback_only' | 'closed' | 'task_published'

const props = defineProps<{
  selected?: PblWorkItem
  detail?: WorkItemDetail
  students: TeacherStudent[]
  selectedTargetIds: number[]
  wholeClass: boolean
  body: string
  loading: boolean
  busy: boolean
  error: string
  actionError: string
}>()
const emit = defineEmits<{
  back: []
  retry: []
  'update:body': [value: string]
  toggleTarget: [studentId: number]
  toggleWholeClass: []
  submit: [action: WorkItemAction, suggestion?: PblSuggestion]
}>()

const suggestionIndex = ref(0)
const originalSuggestions = computed(() => props.detail?.diagnostic.recommendedQuestions || [])
const draftSuggestions = ref<PblSuggestion[]>([])
const selectedSuggestion = computed(() => draftSuggestions.value[suggestionIndex.value])
const valid = computed(() => props.body.trim().length >= 1 && props.body.trim().length <= 1000)
const publishValid = computed(
  () =>
    Boolean(selectedSuggestion.value?.title.trim()) &&
    Boolean(selectedSuggestion.value?.prompt.trim()) &&
    selectedSuggestion.value!.title.trim().length <= 200 &&
    selectedSuggestion.value!.prompt.trim().length <= 2000,
)
const canAct = computed(() => props.selected?.status === 'pending' || props.selected?.status === 'responded')

watch(
  () => props.detail?.diagnostic.recommendedQuestions,
  (suggestions) => {
    draftSuggestions.value = (suggestions || []).map((suggestion) => ({ ...suggestion }))
    suggestionIndex.value = 0
  },
  { immediate: true },
)
watch(
  () => props.selected?.snapshotId,
  () => {
    suggestionIndex.value = 0
  },
)

function updateBody(event: unknown) {
  const value =
    (event as { detail?: { value?: unknown }; target?: { value?: unknown } })?.detail?.value ??
    (event as { target?: { value?: unknown } })?.target?.value
  emit('update:body', String(value ?? ''))
}
function displayStatus(value: PblWorkStatus) {
  return {
    pending: '待处理',
    responded: '已反馈',
    task_published: '已发布',
    closed: '已关闭',
  }[value]
}
</script>

<style scoped>
.detail,
.finding-group,
.feedback-form {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
}
.detail {
  min-width: 0;
  padding: 18rpx 0;
  border-top: 1rpx solid var(--med-border);
}
.detail-heading,
.group-heading {
  color: var(--med-ink);
  font-weight: 700;
}
.status-line,
.muted,
.target-hint,
.terminal-copy {
  color: var(--med-muted);
}
.finding-group,
.feedback-form {
  padding-top: 14rpx;
  border-top: 1rpx solid var(--med-divider);
}
.suggestion {
  display: flex;
  padding: 10rpx 0;
  flex-direction: column;
  gap: 4rpx;
}
.suggestion-editor {
  display: flex;
  padding: 14rpx 0;
  flex-direction: column;
  gap: 10rpx;
  border-top: 1rpx solid var(--med-divider);
}
.editor-label {
  color: var(--med-clinical);
  font-weight: 700;
}
.suggestion-editor input,
.suggestion-editor textarea {
  width: 100%;
  padding: 12rpx;
  box-sizing: border-box;
  border: 1rpx solid var(--med-border);
}
.suggestion-picker {
  min-height: 44px;
  padding: 12rpx 0;
  box-sizing: border-box;
  border-bottom: 1rpx solid var(--med-divider);
}
textarea {
  width: 100%;
  min-height: 180rpx;
  box-sizing: border-box;
  border: 1rpx solid var(--med-border);
}
.student-targets {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
  padding: 12rpx 0;
  border-top: 1rpx solid var(--med-divider);
}
.student-option,
.whole-class-option {
  display: flex;
  min-height: 44px;
  align-items: center;
  gap: 8rpx;
}
.actions {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10rpx;
}
.actions button,
.back,
.detail [role='alert'] button {
  min-height: 44px;
}
.action-error {
  color: var(--med-danger);
}
@media screen and (min-width: 600px) {
  .detail,
  .target-hint,
  .terminal-copy {
    font-size: 14px;
  }
}
@media screen and (min-width: 768px) {
  .detail {
    padding: 16px;
    border: 1px solid var(--med-border);
  }
  .back {
    display: none;
  }
  .actions {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
