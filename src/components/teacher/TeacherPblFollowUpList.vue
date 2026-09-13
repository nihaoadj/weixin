<template>
  <view
    class="follow-up-list"
    :class="{ 'follow-up-list--detail-open': selectedPlanId }"
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
    <text v-else-if="loading">正在加载 PBL 跟进…</text>
    <template v-else>
      <text
        v-if="!items.length"
        class="empty-copy"
        >当前筛选范围没有正式任务跟进记录。</text
      >
      <button
        v-for="item in items"
        :key="item.planId"
        class="follow-up-row"
        :class="{ 'follow-up-row--selected': selectedPlanId === item.planId }"
        role="button"
        tabindex="0"
        :aria-current="selectedPlanId === item.planId ? 'true' : undefined"
        @keydown="activateButtonOnKey"
        @click="$emit('open', item.planId)"
      >
        <text class="follow-up-row__title">{{ item.studentName }} · {{ item.className }}</text>
        <text class="follow-up-row__meta"
          >{{ item.sessionTopic }} · {{ displayStatus(item.status) }} · 第 {{ item.currentCycle }} 轮{{
            item.automationExhausted ? ' · 需人工支持' : ''
          }}</text
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
import type { PblFollowUp, PblFollowUpStatus } from '@/features/pbl/public'

type FilterName = 'sessionId' | 'studentId'

const props = defineProps<{
  items: PblFollowUp[]
  total: number
  offset: number
  loading: boolean
  error: string
  filterError: string
  status?: PblFollowUpStatus
  sessionId: string
  studentId: string
  selectedPlanId?: number
}>()
const emit = defineEmits<{
  statusChange: [value: PblFollowUpStatus | undefined]
  'update:sessionId': [value: string]
  'update:studentId': [value: string]
  applyFilters: []
  retry: []
  open: [planId: number]
  previousPage: []
  nextPage: []
}>()

const statusOptions: Array<{ label: string; value?: PblFollowUpStatus }> = [
  { label: '全部状态' },
  { label: '进行中', value: 'in_progress' },
  { label: '第二轮', value: 'cycle_2' },
  { label: '需要支持', value: 'support_needed' },
  { label: '已改善', value: 'improved' },
]
const statusLabel = computed(() => statusOptions.find((item) => item.value === props.status)?.label || '全部状态')

function changeStatus(event: { detail: { value: string } }) {
  emit('statusChange', statusOptions[Number(event.detail.value)]?.value)
}
function updateFilter(name: FilterName, event: unknown) {
  const value =
    (event as { detail?: { value?: unknown }; target?: { value?: unknown } })?.detail?.value ??
    (event as { target?: { value?: unknown } })?.target?.value
  const normalized = String(value ?? '').trim()
  if (name === 'sessionId') emit('update:sessionId', normalized)
  else emit('update:studentId', normalized)
}
function displayStatus(value: PblFollowUpStatus) {
  return {
    in_progress: '进行中',
    cycle_2: '第二轮',
    support_needed: '需要支持',
    improved: '已改善',
  }[value]
}
</script>

<style scoped>
.follow-up-list {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 16rpx;
}
.filters {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: stretch;
  gap: 16rpx;
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
.follow-up-row {
  display: flex;
  margin: 0;
  padding: 24rpx 2rpx;
  flex-direction: column;
  gap: 10rpx;
  background: transparent;
  border-top: 1rpx solid var(--med-divider);
  border-radius: 0;
  text-align: left;
}
.follow-up-row__title {
  color: var(--med-text);
  font-size: 28rpx;
  font-weight: 700;
  line-height: 1.45;
}
.follow-up-row__meta {
  color: var(--med-muted);
  font-size: 24rpx;
  line-height: 1.5;
  overflow-wrap: anywhere;
}
.follow-up-row--selected {
  padding-left: 14rpx;
  border-left: 4rpx solid var(--med-clinical);
}
.pager {
  display: flex;
  min-height: 44px;
  align-items: center;
  justify-content: space-between;
}
.pager button,
.follow-up-list [role='alert'] button {
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
  .follow-up-list--detail-open {
    display: none;
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
  .follow-up-row {
    padding: 14px 0;
  }
  .follow-up-row__title {
    font-size: 15px;
  }
  .follow-up-row__meta {
    font-size: 13px;
  }
}
@media screen and (min-width: 768px) {
  .filters {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}
</style>
