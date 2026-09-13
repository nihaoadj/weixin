<template>
  <view class="composer">
    <view class="composer-inner">
      <label
        class="composer-label sr-only"
        for="medical-question"
        >你的问题</label
      >
      <text
        v-if="error"
        class="composer-error"
        >{{ error }}</text
      >
      <view
        v-if="canGenerateReport || canRetry"
        class="composer-actions"
      >
        <button
          v-if="canGenerateReport"
          hover-class="is-pressed"
          :hover-start-time="0"
          :hover-stay-time="80"
          :tabindex="loading ? -1 : 0"
          role="button"
          class="report-button"
          :disabled="loading"
          :aria-disabled="loading"
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
      <view class="composer-bar">
        <view class="input-shell">
          <textarea
            v-if="multiline"
            id="medical-question"
            v-model="inputValue"
            class="message-input is-textarea"
            name="medical-question"
            :aria-label="inputLabel"
            autocomplete="off"
            :placeholder="placeholder"
            :maxlength="2000"
            :disabled="loading"
            :cursor-spacing="24"
            auto-height
            :disable-default-padding="true"
          />
          <input
            v-else
            id="medical-question"
            v-model="inputValue"
            class="message-input"
            name="medical-question"
            :aria-label="inputLabel"
            autocomplete="off"
            confirm-type="send"
            :placeholder="placeholder"
            :maxlength="2000"
            :disabled="loading"
            :cursor-spacing="24"
            @confirm="$emit('send')"
          />
        </view>
        <button
          hover-class="is-pressed"
          :hover-start-time="0"
          :hover-stay-time="80"
          :tabindex="!modelValue.trim() || loading ? -1 : 0"
          role="button"
          class="send-button"
          :class="{ 'is-disabled': !modelValue.trim() || loading, 'is-retry': tone === 'retry' }"
          :disabled="!modelValue.trim() || loading"
          :aria-disabled="!modelValue.trim() || loading"
          :aria-label="sendAriaLabel"
          @keydown="activateButtonOnKey"
          @click="$emit('send')"
        >
          {{ sendLabel }}
        </button>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { activateButtonOnKey } from '@/components/ui/keyboard'
import { computed } from 'vue'
import MedIcon from '@/components/ui/MedIcon.vue'

const props = withDefaults(
  defineProps<{
    modelValue: string
    loading: boolean
    canGenerateReport?: boolean
    canRetry?: boolean
    multiline?: boolean
    tone?: 'primary' | 'retry'
    sendLabel?: string
    sendAriaLabel?: string
    inputLabel?: string
    placeholder?: string
    error?: string
  }>(),
  {
    canGenerateReport: false,
    canRetry: false,
    multiline: false,
    tone: 'primary',
    sendLabel: '发送',
    sendAriaLabel: '发送消息',
    inputLabel: '医学学习问题',
    placeholder: '例如：如何区分坏死与凋亡…',
    error: '',
  },
)
const emit = defineEmits<{ 'update:modelValue': [value: string]; send: []; report: []; retry: [] }>()
const inputValue = computed({
  get: () => props.modelValue,
  set: (value: string) => emit('update:modelValue', value),
})
</script>

<style scoped>
.composer {
  flex: none;
  padding: 12rpx 24rpx calc(140rpx + env(safe-area-inset-bottom));
  background: var(--med-surface);
  border-top: 1rpx solid var(--med-border);
}
.composer-inner {
  display: flex;
  max-width: 800px;
  margin: 0 auto;
  flex-direction: column;
}
.composer-label.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
.composer-error {
  margin-bottom: 10rpx;
  color: var(--med-safety);
  font-size: 22rpx;
  line-height: 1.5;
}
.composer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8rpx;
  margin-bottom: 10rpx;
}
.report-button,
.retry-button {
  display: flex;
  min-height: 40px;
  margin: 0;
  padding: 0 16rpx;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
  color: var(--med-clinical);
  background: transparent;
  border: 1rpx solid var(--med-border);
  border-radius: 99rpx;
  font-size: 22rpx;
}
.retry-button {
  color: var(--med-safety);
  background: var(--med-safety-soft);
  border-color: transparent;
}
.composer-bar {
  display: flex;
  align-items: flex-end;
  gap: 12rpx;
  padding: 8rpx 8rpx 8rpx 28rpx;
  background: var(--med-surface);
  border: 1rpx solid var(--med-border);
  border-radius: 28rpx;
  box-shadow: 0 4rpx 20rpx rgba(16, 42, 67, 0.05);
}
.input-shell {
  min-width: 0;
  flex: 1;
}
.message-input {
  width: 100%;
  height: 72rpx;
  color: var(--med-text);
  background: transparent;
  font-size: 28rpx;
}
.message-input.is-textarea {
  width: 100%;
  height: auto;
  min-height: 72rpx;
  max-height: 320rpx;
  padding: 15rpx 0;
  font-size: 28rpx;
  line-height: 1.5;
}
.send-button {
  display: flex;
  min-height: 72rpx;
  margin: 0;
  padding: 0 30rpx;
  flex: none;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: var(--med-clinical);
  border-radius: 18rpx;
  font-size: 26rpx;
  font-weight: 600;
  line-height: 1.2;
  box-shadow: 0 6rpx 14rpx rgba(10, 107, 102, 0.22);
}
.send-button.is-disabled {
  background: var(--med-border);
  color: var(--med-muted);
  box-shadow: none;
  opacity: 1;
}
.send-button.is-retry {
  color: var(--med-safety);
  background: var(--med-safety-soft);
  border: 1rpx solid var(--med-safety-border);
  box-shadow: none;
  opacity: 1;
}
@media screen and (max-width: 360px) {
  .message-input,
  .message-input.is-textarea {
    font-size: 14px;
  }
  .send-button {
    padding: 0 22rpx;
    font-size: 13px;
  }
  .report-button,
  .retry-button {
    font-size: 12px;
  }
  .composer-error {
    font-size: 12px;
  }
}
@media screen and (min-width: 600px) {
  .composer {
    padding: 10px 24px calc(96px + env(safe-area-inset-bottom));
  }
  .composer-actions {
    margin-bottom: 8px;
  }
  .report-button,
  .retry-button {
    font-size: 13px;
  }
  .composer-bar {
    gap: 10px;
    padding: 6px 6px 6px 18px;
    border-radius: 16px;
  }
  .message-input {
    height: 46px;
    font-size: 16px;
  }
  .message-input.is-textarea {
    min-height: 46px;
    max-height: 200px;
    padding: 11px 0;
    font-size: 16px;
  }
  .send-button {
    min-height: 40px;
    padding: 0 18px;
    border-radius: 10px;
    font-size: 15px;
  }
  .composer-error {
    font-size: 13px;
  }
}
</style>
