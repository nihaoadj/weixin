<template>
  <view
    class="teacher-pager"
    role="navigation"
    :aria-label="label"
  >
    <template v-if="paged">
      <button
        class="teacher-pager__button"
        :disabled="offset === 0"
        :tabindex="offset === 0 ? -1 : 0"
        role="button"
        aria-label="上一页"
        @keydown.enter.prevent="$emit('previous')"
        @keydown.space.prevent="$emit('previous')"
        @click="$emit('previous')"
      >
        上一页
      </button>
      <text
        class="teacher-pager__count"
        aria-live="polite"
        >第 {{ offset + 1 }}–{{ Math.min(offset + pageSize, total) }} 项 · 共 {{ total }} 项</text
      >
      <button
        class="teacher-pager__button"
        :disabled="!hasNext"
        :tabindex="hasNext ? 0 : -1"
        role="button"
        aria-label="下一页"
        @keydown.enter.prevent="$emit('next')"
        @keydown.space.prevent="$emit('next')"
        @click="$emit('next')"
      >
        下一页
      </button>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    total: number
    offset: number
    pageSize?: number
    label?: string
  }>(),
  { pageSize: 20, label: '列表分页' },
)
defineEmits<{ previous: []; next: [] }>()

// A result set that fits on one page never renders disabled pager controls.
const paged = computed(() => props.total > props.pageSize)
const hasNext = computed(() => props.offset + props.pageSize < props.total)
</script>

<style scoped>
.teacher-pager {
  display: flex;
  min-height: 44px;
  align-items: center;
  justify-content: flex-end;
  gap: 24rpx;
}
.teacher-pager__button {
  min-width: 132rpx;
  min-height: 72rpx;
  margin: 0;
  padding: 0 24rpx;
  color: var(--med-clinical);
  background: transparent;
  border: 1rpx solid var(--med-border);
  border-radius: 8rpx;
  font-size: 25rpx;
  font-weight: 600;
}
.teacher-pager__button[disabled] {
  color: var(--med-muted);
  background: transparent;
  border-color: var(--med-divider);
}
.teacher-pager__count {
  color: var(--med-muted);
  font-size: 24rpx;
  font-variant-numeric: tabular-nums;
}
@media screen and (max-width: 360px) {
  .teacher-pager__button {
    font-size: 13px;
  }
  .teacher-pager__count {
    font-size: 12px;
  }
}
@media screen and (min-width: 600px) {
  .teacher-pager__button {
    min-height: 44px;
    font-size: 14px;
  }
  .teacher-pager__count {
    font-size: 13px;
  }
}
</style>
