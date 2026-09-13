<template>
  <view
    class="work-item-list"
    :class="{ 'work-item-list--detail-open': Boolean(selectedSnapshotId) }"
  >
    <view class="filters">
      <picker
        :range="statusOptions"
        range-key="label"
        role="button"
        tabindex="0"
        @keydown="activatePickerOnKey"
        @change="changeStatus"
        ><view class="filter-field">状态：{{ statusLabel }}</view></picker
      >
      <picker
        :range="sourceOptions"
        range-key="label"
        role="button"
        tabindex="0"
        @keydown="activatePickerOnKey"
        @change="changeSource"
        ><view class="filter-field">来源：{{ sourceLabel }}</view></picker
      >
      <input
        class="filter-input"
        :value="sessionId"
        inputmode="numeric"
        placeholder="课堂编号"
        aria-label="按课堂编号筛选"
        :aria-invalid="Boolean(filterError)"
        @input="updateFilter('sessionId', $event)"
      />
      <input
        class="filter-input"
        :value="studentId"
        inputmode="numeric"
        placeholder="学生编号"
        aria-label="按学生编号筛选"
        :aria-invalid="Boolean(filterError)"
        @input="updateFilter('studentId', $event)"
      />
      <button
        class="filter-submit"
        role="button"
        tabindex="0"
        @keydown="activateButtonOnKey"
        @click="$emit('applyFilters')"
      >
        筛选
      </button>
    </view>
    <text
      v-if="filterError"
      class="filter-error"
      role="alert"
      >{{ filterError }}</text
    >
    <view
      v-if="error"
      class="state-copy"
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
    <text v-else-if="loading">正在加载诊断建议…</text>
    <template v-else>
      <text
        v-if="!items.length"
        class="empty-copy"
        >当前筛选范围没有诊断建议，可切换状态或来源继续查看。</text
      >
      <button
        v-for="item in items"
        :key="item.snapshotId"
        class="row"
        :class="{ 'row--selected': selectedSnapshotId === item.snapshotId }"
        role="button"
        tabindex="0"
        :aria-current="selectedSnapshotId === item.snapshotId ? 'true' : undefined"
        @keydown="activateButtonOnKey"
        @click="$emit('open', item)"
      >
        <text class="row-title"
          >{{ item.student.name }} · {{ item.source === 'student_submission' ? '学生主动提交' : '课堂诊断' }}</text
        >
        <text class="row-meta">{{ item.class.name }} · {{ item.topic }} · 课堂 {{ item.sessionId }}</text>
        <text class="row-action">{{ displayStatus(item.status) }} · {{ item.nextAction }}</text>
        <text class="row-meta"
          >{{ item.knowledgeGapCount }} 个知识薄弱点 · {{ item.reasoningIssueCount }} 个推理问题</text
        >
      </button>
      <view
        v-if="total > 0"
        class="pager"
      >
        <button
          :disabled="offset === 0"
          :tabindex="offset === 0 ? -1 : 0"
          role="button"
          @keydown="activateButtonOnKey"
          @click="$emit('previousPage')"
        >
          上一页
        </button>
        <text>{{ offset + 1 }}–{{ Math.min(offset + 20, total) }}/{{ total }}</text>
        <button
          :disabled="offset + 20 >= total"
          :tabindex="offset + 20 >= total ? -1 : 0"
          role="button"
          @keydown="activateButtonOnKey"
          @click="$emit('nextPage')"
        >
          下一页
        </button>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { activateButtonOnKey, activatePickerOnKey } from '@/components/ui/keyboard'
import type { PblWorkItem, PblWorkStatus } from '@/features/pbl/public'

type WorkItemSource = PblWorkItem['source']
type FilterName = 'sessionId' | 'studentId'

const props = defineProps<{
  items: PblWorkItem[]
  total: number
  offset: number
  loading: boolean
  error: string
  filterError: string
  status?: PblWorkStatus
  source?: WorkItemSource
  sessionId: string
  studentId: string
  selectedSnapshotId?: string
}>()
const emit = defineEmits<{
  statusChange: [value: PblWorkStatus | undefined]
  sourceChange: [value: WorkItemSource | undefined]
  'update:sessionId': [value: string]
  'update:studentId': [value: string]
  applyFilters: []
  retry: []
  open: [item: PblWorkItem]
  previousPage: []
  nextPage: []
}>()

const statusOptions: Array<{ label: string; value?: PblWorkStatus }> = [
  { label: '全部状态' },
  { label: '待处理', value: 'pending' },
  { label: '已反馈', value: 'responded' },
  { label: '已发布', value: 'task_published' },
  { label: '已关闭', value: 'closed' },
]
const sourceOptions: Array<{ label: string; value?: WorkItemSource }> = [
  { label: '全部来源' },
  { label: '学生主动提交', value: 'student_submission' },
  { label: '课堂诊断', value: 'classroom_diagnostic' },
]
const statusLabel = computed(() => statusOptions.find((item) => item.value === props.status)?.label || '全部状态')
const sourceLabel = computed(() => sourceOptions.find((item) => item.value === props.source)?.label || '全部来源')

function changeStatus(event: { detail: { value: string } }) {
  emit('statusChange', statusOptions[Number(event.detail.value)]?.value)
}
function changeSource(event: { detail: { value: string } }) {
  emit('sourceChange', sourceOptions[Number(event.detail.value)]?.value)
}
function updateFilter(name: FilterName, event: unknown) {
  const value =
    (event as { detail?: { value?: unknown }; target?: { value?: unknown } })?.detail?.value ??
    (event as { target?: { value?: unknown } })?.target?.value
  const normalized = String(value ?? '').trim()
  if (name === 'sessionId') emit('update:sessionId', normalized)
  else emit('update:studentId', normalized)
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
.work-item-list,
.filters {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}
.filters {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: stretch;
}
.filters picker,
.filter-input,
.filter-submit {
  min-width: 0;
  min-height: 88rpx;
  box-sizing: border-box;
}
.filter-field,
.filter-input {
  display: flex;
  width: 100%;
  min-height: 88rpx;
  box-sizing: border-box;
  align-items: center;
  padding: 0 18rpx;
  border: 1rpx solid var(--med-divider);
  border-radius: 8rpx;
  background: var(--med-surface);
  color: var(--med-text);
  font-size: 26rpx;
  line-height: 1.35;
}
.filter-input {
  outline: none;
}
.filter-input:focus,
.filters picker:focus .filter-field {
  border-color: var(--med-clinical);
  box-shadow: 0 0 0 2rpx var(--med-wash);
}
.filter-submit {
  margin: 0;
  padding: 0 18rpx;
  color: var(--med-clinical);
  background: var(--med-wash);
  border-radius: 8rpx;
  font-size: 28rpx;
  font-weight: 700;
}
.row {
  display: flex;
  margin: 0;
  padding: 24rpx 2rpx;
  flex-direction: column;
  gap: 10rpx;
  text-align: left;
  background: transparent;
  border-top: 1rpx solid var(--med-divider);
  border-radius: 0;
}
.row--selected {
  border-left: 4rpx solid var(--med-clinical);
  padding-left: 14rpx;
}
.row-title,
.row-action {
  color: var(--med-text);
  font-size: 28rpx;
  font-weight: 700;
  line-height: 1.45;
}
.row-action {
  color: var(--med-clinical);
  font-size: 25rpx;
  font-weight: 600;
}
.row-meta {
  color: var(--med-muted);
  font-size: 24rpx;
  line-height: 1.5;
  overflow-wrap: anywhere;
}
.pager {
  display: flex;
  min-height: 44px;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
}
.pager button,
.state-copy button {
  min-height: 44px;
}
.empty-copy,
.filter-error {
  display: block;
  padding: 24rpx 0;
  color: var(--med-muted);
  font-size: 26rpx;
  line-height: 1.6;
}
.filter-error {
  color: var(--med-danger);
}
@media screen and (max-width: 767px) {
  .work-item-list--detail-open {
    display: none;
  }
  .filter-submit {
    grid-column: span 2;
  }
}
@media screen and (min-width: 600px) {
  .filter-field,
  .filter-input,
  .filter-submit,
  .empty-copy,
  .filter-error {
    font-size: 14px;
  }
  .filters picker,
  .filter-input,
  .filter-submit,
  .filter-field {
    min-height: 44px;
  }
  .row {
    gap: 8px;
    padding: 14px 0;
  }
  .row-title {
    font-size: 15px;
  }
  .row-action,
  .row-meta {
    font-size: 13px;
  }
}
@media screen and (min-width: 768px) {
  .filters {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }
  .filter-submit {
    grid-column: auto;
  }
}
</style>
