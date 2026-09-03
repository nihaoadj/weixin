<template>
  <view
    ref="fieldRoot"
    class="composer"
  >
    <view class="composer-inner">
      <view class="feature-row">
        <label
          class="composer-label"
          for="medical-question"
          >你的问题</label
        >
        <view class="composer-actions">
          <button
            hover-class="is-pressed"
            :hover-start-time="0"
            :hover-stay-time="80"
            :tabindex="!canGenerateReport || loading ? -1 : 0"
            role="button"
            class="report-button"
            :disabled="!canGenerateReport || loading"
            :aria-disabled="!canGenerateReport || loading"
            @keydown="activateButtonOnKey"
            @click="$emit('report')"
          >
            <MedIcon
              name="report"
              size="sm"
            />生成学习报告
          </button>
          <button
            v-if="canRetry"
            hover-class="is-pressed"
            :hover-start-time="0"
            :hover-stay-time="80"
            :tabindex="loading ? -1 : 0"
            role="button"
            class="retry-button"
            :disabled="loading"
            :aria-disabled="loading"
            @keydown="activateButtonOnKey"
            @click="$emit('retry')"
          >
            <MedIcon
              name="retry"
              size="sm"
            />重试
          </button>
        </view>
      </view>
      <view class="input-row">
        <input
          id="medical-question"
          v-model="inputValue"
          class="message-input"
          name="medical-question"
          aria-label="医学学习问题"
          autocomplete="off"
          confirm-type="send"
          placeholder="例如：如何区分不同类型的胸痛…"
          :maxlength="2000"
          :disabled="loading"
          :cursor-spacing="24"
          @confirm="$emit('send')"
        />
        <button
          hover-class="is-pressed"
          :hover-start-time="0"
          :hover-stay-time="80"
          :tabindex="!modelValue.trim() || loading ? -1 : 0"
          role="button"
          class="send-button"
          aria-label="发送消息"
          :disabled="!modelValue.trim() || loading"
          :aria-disabled="!modelValue.trim() || loading"
          @keydown="activateButtonOnKey"
          @click="$emit('send')"
        >
          <MedIcon name="send" />
        </button>
      </view>
      <StudentNav active="chat" />
    </view>
  </view>
</template>

<script setup lang="ts">
import { activateButtonOnKey } from '@/components/ui/keyboard'
import { computed, ref } from 'vue'
import MedIcon from '@/components/ui/MedIcon.vue'
import StudentNav from '@/components/ui/StudentNav.vue'
// #ifdef H5
import { useNativeFieldA11y } from '@/components/ui/nativeFieldA11y'
// #endif
const fieldRoot = ref(null)
// #ifdef H5
useNativeFieldA11y(fieldRoot)
// #endif

const props = defineProps<{ modelValue: string; loading: boolean; canGenerateReport: boolean; canRetry: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: string]; send: []; report: []; retry: [] }>()
const inputValue = computed({
  get: () => props.modelValue,
  set: (value: string) => emit('update:modelValue', value),
})
</script>

<style scoped>
.composer {
  padding: 8rpx 24rpx calc(12rpx + env(safe-area-inset-bottom));
  flex: none;
  background: var(--med-surface);
  border-top: 1rpx solid var(--med-border);
}
.composer-inner {
  max-width: 800px;
  margin: 0 auto;
}
.feature-row,
.composer-actions,
.input-row {
  display: flex;
  align-items: center;
}
.feature-row {
  justify-content: space-between;
  gap: 12rpx;
}
.composer-label {
  flex: none;
  color: var(--med-ink);
  font-size: 24rpx;
  font-weight: 700;
}
.composer-actions {
  gap: 8rpx;
}
.report-button,
.retry-button {
  display: flex;
  min-height: 44px;
  margin: 0;
  padding: 0 12rpx;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
  color: var(--med-clinical);
  background: transparent;
  border-radius: var(--med-radius-sm);
  font-size: 22rpx;
}
.retry-button {
  color: var(--med-safety);
  background: var(--med-safety-soft);
}
.input-row {
  margin: 0 0 8rpx;
  gap: 12rpx;
}
.message-input {
  min-width: 0;
  height: 88rpx;
  min-height: 44px;
  padding: 0 24rpx;
  flex: 1;
  color: var(--med-text);
  background: var(--med-paper);
  border: 1rpx solid var(--med-border);
  border-radius: var(--med-radius-md);
  font-size: 26rpx;
}
.send-button {
  display: flex;
  width: 88rpx;
  min-width: 44px;
  height: 88rpx;
  min-height: 44px;
  margin: 0;
  padding: 0;
  flex: none;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: var(--med-clinical);
  border-radius: var(--med-radius-md);
}
@media screen and (max-width: 360px) {
  .message-input {
    font-size: 14px;
  }
  .composer-label,
  .report-button,
  .retry-button {
    font-size: 12px;
  }
}
@media screen and (min-width: 600px) {
  .composer {
    padding: 8px 24px calc(12px + env(safe-area-inset-bottom));
  }
  .composer-label,
  .report-button,
  .retry-button {
    font-size: 14px;
  }
  .input-row {
    gap: 12px;
  }
  .message-input,
  .send-button {
    height: 52px;
  }
  .message-input {
    font-size: 16px;
  }
  .send-button {
    width: 56px;
  }
}
</style>
