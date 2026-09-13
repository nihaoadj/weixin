<template>
  <view class="class-scope">
    <view class="class-scope__selection">
      <text class="class-scope__label">班级范围</text>
      <picker
        v-if="classes.length"
        class="class-scope__picker"
        :range="options"
        range-key="name"
        :value="selectedIndex"
        :disabled="loading"
        aria-label="切换教师班级范围"
        role="button"
        :tabindex="loading ? -1 : 0"
        @keydown="activatePickerOnKey"
        @change="change"
      >
        <view class="class-scope__value">
          <text>{{ options[selectedIndex]?.name || '全部负责班级' }}</text>
          <text class="class-scope__change">切换</text>
        </view>
      </picker>
      <text
        v-else
        class="class-scope__value"
        >{{ loading ? '正在读取班级…' : '全部负责班级' }}</text
      >
    </view>
    <view
      v-if="error"
      class="class-scope__error"
      role="alert"
    >
      <text>{{ error }}；当前仍可查看全部授权范围。</text>
      <button
        role="button"
        tabindex="0"
        @keydown="activateButtonOnKey"
        @click="$emit('retry')"
      >
        重试
      </button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { activateButtonOnKey, activatePickerOnKey } from '@/components/ui/keyboard'

const props = withDefaults(
  defineProps<{
    classes: Array<{ id: number; name: string }>
    modelValue?: number
    loading?: boolean
    error?: string
  }>(),
  { modelValue: undefined, loading: false, error: '' },
)
const emit = defineEmits<{ 'update:modelValue': [classId: number | undefined]; retry: [] }>()

const options = computed(() => [{ id: 0, name: '全部负责班级' }, ...props.classes])
const selectedIndex = computed(() => {
  const index = options.value.findIndex((item) => item.id === props.modelValue)
  return index >= 0 ? index : 0
})

function change(event: { detail: { value: string } }) {
  const selected = options.value[Number(event.detail.value)]
  emit('update:modelValue', selected?.id || undefined)
}
</script>

<style scoped>
.class-scope {
  padding: 10rpx 0 6rpx;
  border-bottom: 1rpx solid var(--med-divider);
}
.class-scope__selection,
.class-scope__value,
.class-scope__error {
  display: flex;
  align-items: center;
}
.class-scope__selection {
  min-height: 44px;
  gap: 20rpx;
}
.class-scope__label {
  flex: none;
  color: var(--med-muted);
  font-size: 22rpx;
}
.class-scope__picker {
  min-width: 0;
  flex: 1;
}
.class-scope__value {
  min-width: 0;
  flex: 1;
  justify-content: space-between;
  gap: 16rpx;
  color: var(--med-ink);
  font-size: 26rpx;
  font-weight: 650;
}
.class-scope__change {
  flex: none;
  color: var(--med-clinical);
  font-size: 22rpx;
  font-weight: 500;
}
.class-scope__error {
  min-height: 44px;
  justify-content: space-between;
  gap: 16rpx;
  color: var(--med-safety-text);
  font-size: 22rpx;
}
.class-scope__error button {
  min-width: 56px;
  min-height: 44px;
  margin: 0;
  padding: 0 16rpx;
  flex: none;
  color: var(--med-clinical);
  background: transparent;
  font-size: 22rpx;
}
@media screen and (max-width: 360px) {
  .class-scope__label,
  .class-scope__change,
  .class-scope__error,
  .class-scope__error button {
    font-size: 12px;
  }
  .class-scope__value {
    font-size: 13px;
  }
}
@media screen and (min-width: 600px) {
  .class-scope {
    padding: 8px 0 4px;
  }
  .class-scope__label,
  .class-scope__change,
  .class-scope__error,
  .class-scope__error button {
    font-size: 13px;
  }
  .class-scope__value {
    font-size: 15px;
  }
}
</style>
