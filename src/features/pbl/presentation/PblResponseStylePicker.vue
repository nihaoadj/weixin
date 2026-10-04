<template>
  <picker
    class="response-style-picker"
    :range="options"
    range-key="label"
    :value="currentIndex"
    :disabled="disabled"
    :aria-label="`本轮回应方式，当前为${currentLabel}`"
    @change="changeStyle"
  >
    <view
      class="response-style-control"
      :class="{ disabled }"
    >
      <view
        class="response-style-search"
        aria-hidden="true"
      />
      <text>{{ currentLabel }}</text>
    </view>
  </picker>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { InteractionStyle } from '@/features/pbl/public'

const options = [
  { value: 'guided' as const, label: '探究引导' },
  { value: 'direct' as const, label: '直接讲解' },
]
const props = defineProps<{ modelValue: InteractionStyle; disabled?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: InteractionStyle]; change: [value: InteractionStyle] }>()
const currentIndex = computed(() => (props.modelValue === 'direct' ? 1 : 0))
const currentLabel = computed(() => options[currentIndex.value].label)

function changeStyle(event: { detail: { value: string | number } }) {
  if (props.disabled) return
  const next = options[Number(event.detail.value)]?.value
  if (!next || next === props.modelValue) return
  emit('update:modelValue', next)
  emit('change', next)
}
</script>

<style scoped>
.response-style-picker {
  display: flex;
  min-height: 88rpx;
  align-items: center;
}
.response-style-control {
  display: flex;
  min-height: 64rpx;
  box-sizing: border-box;
  align-items: center;
  padding: 10rpx 20rpx 10rpx 18rpx;
  gap: 13rpx;
  border: 0;
  border-radius: 999rpx;
  background: var(--med-wash);
  color: var(--med-brand-deep);
  font-size: 25rpx;
  font-weight: 750;
}
.response-style-search {
  position: relative;
  width: 25rpx;
  height: 25rpx;
  box-sizing: border-box;
  border: 4rpx solid currentColor;
  border-radius: 50%;
}
.response-style-search::after {
  position: absolute;
  right: -9rpx;
  bottom: -7rpx;
  width: 12rpx;
  height: 4rpx;
  background: currentColor;
  border-radius: 99rpx;
  content: '';
  transform: rotate(45deg);
}
.response-style-control.disabled {
  opacity: 0.55;
}
@media (min-width: 600px) {
  .response-style-picker {
    min-height: 44px;
  }
  .response-style-control {
    min-height: 36px;
    padding: 5px 11px 5px 10px;
    gap: 8px;
    font-size: 13px;
  }
  .response-style-search {
    width: 14px;
    height: 14px;
    border-width: 2px;
  }
  .response-style-search::after {
    right: -5px;
    bottom: -4px;
    width: 7px;
    height: 2px;
  }
}
</style>
