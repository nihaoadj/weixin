<template>
  <view
    class="composer"
    :class="{ 'is-dialogue': appearance === 'dialogue', 'is-keyboard-open': keyboardHeight > 0 }"
  >
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
        <view
          v-if="appearance === 'dialogue'"
          class="composer-quote-slot"
        >
          <slot name="quote" />
        </view>
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
            :adjust-position="false"
            auto-height
            :disable-default-padding="true"
            @keyboardheightchange="handleKeyboardHeightChange"
            @blur="resetKeyboardOffset"
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
            :adjust-position="false"
            @keyboardheightchange="handleKeyboardHeightChange"
            @blur="resetKeyboardOffset"
            @confirm="$emit('send')"
          />
        </view>
        <view class="composer-controls">
          <slot
            v-if="appearance === 'dialogue'"
            name="context"
          >
            <text class="composer-context">阶段作答</text>
          </slot>
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
            <text
              v-if="appearance === 'dialogue'"
              class="send-button-surface"
              aria-hidden="true"
            >
              <text class="send-glyph">{{ tone === 'retry' ? '↻' : '↑' }}</text>
            </text>
            <text :class="{ 'sr-only': appearance === 'dialogue' }">{{ sendLabel }}</text>
          </button>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { activateButtonOnKey } from '@/components/ui/keyboard'
import { computed, ref } from 'vue'
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
    appearance?: 'default' | 'dialogue'
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
    appearance: 'default',
  },
)
const emit = defineEmits<{
  'update:modelValue': [value: string]
  'keyboard-height-change': [height: number]
  send: []
  report: []
  retry: []
}>()
const keyboardHeight = ref(0)
const inputValue = computed({
  get: () => props.modelValue,
  set: (value: string) => emit('update:modelValue', value),
})
function handleKeyboardHeightChange(event: { detail?: { height?: number } }) {
  keyboardHeight.value = Math.max(0, Number(event.detail?.height ?? 0))
  emit('keyboard-height-change', keyboardHeight.value)
}
function resetKeyboardOffset() {
  keyboardHeight.value = 0
  emit('keyboard-height-change', 0)
}
</script>

<style scoped>
.composer {
  position: relative;
  z-index: 20;
  flex: none;
  padding: 12rpx 24rpx calc(140rpx + env(safe-area-inset-bottom));
  background: var(--med-surface);
  border-top: 1rpx solid var(--med-border);
}
.composer.is-dialogue {
  padding: 0 22rpx calc(140rpx + env(safe-area-inset-bottom));
  background: #fff;
  border-top: 0;
  border-radius: 0;
  box-shadow: none;
  pointer-events: none;
}
.composer.is-keyboard-open {
  padding-bottom: 12rpx;
}
.composer.is-dialogue.is-keyboard-open {
  padding: 0 22rpx 12rpx;
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
.composer.is-dialogue .composer-actions {
  pointer-events: auto;
}
.composer-quote {
  display: flex;
  width: 100%;
  height: 64rpx;
  min-width: 0;
  margin: 0;
  padding: 0 8rpx;
  box-sizing: border-box;
  align-items: center;
  gap: 10rpx;
  color: var(--med-text);
  background: transparent;
  border: 0;
  border-bottom: 1rpx solid var(--med-border);
  font-size: 22rpx;
  overflow: hidden;
}
.composer-quote__mark {
  color: var(--med-clinical);
  font-size: 26rpx;
  font-weight: 700;
}
.composer-quote__text {
  overflow: hidden;
  flex: 1;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.composer-quote__close {
  display: flex;
  width: 48rpx;
  min-width: 48rpx;
  min-height: 48rpx;
  margin: 0;
  padding: 0;
  align-items: center;
  justify-content: center;
  color: var(--med-muted);
  background: transparent;
  font-size: 28rpx;
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
.is-dialogue .composer-bar {
  padding: 22rpx 16rpx 14rpx 22rpx;
  align-items: stretch;
  flex-direction: column;
  gap: 4rpx;
  background: var(--med-surface);
  border-color: #bfe6ef;
  border-radius: 34rpx;
  box-shadow: 0 8rpx 26rpx rgba(7, 155, 170, 0.085);
  pointer-events: auto;
  transition:
    border-color var(--med-motion-settle) var(--med-ease-out),
    box-shadow var(--med-motion-settle) var(--med-ease-out);
}
.is-dialogue .composer-bar:focus-within {
  border-color: #7bd3df;
  box-shadow: 0 9rpx 28rpx rgba(7, 155, 170, 0.14);
}
.composer-quote-slot {
  width: 100%;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
}
.input-shell {
  min-width: 0;
  flex: 1;
}
.is-dialogue .input-shell {
  width: 100%;
}
.message-input {
  width: 100%;
  height: 72rpx;
  color: var(--med-text);
  background: transparent;
  border: 0;
  outline: 0;
  box-shadow: none;
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
.is-dialogue .message-input.is-textarea {
  min-height: 58rpx;
  max-height: 260rpx;
  padding: 4rpx 4rpx 10rpx;
  color: #35558d;
  font-size: 27rpx;
  line-height: 1.58;
}
.is-dialogue .message-input:focus,
.is-dialogue .message-input:focus-visible,
.is-dialogue .message-input:focus-within {
  border: 0 !important;
  outline: 0 !important;
  box-shadow: none !important;
}
.composer-controls {
  display: flex;
  flex: none;
  align-items: center;
  justify-content: flex-end;
}
.is-dialogue .composer-controls {
  width: 100%;
  justify-content: space-between;
  gap: 16rpx;
}
.composer-context {
  display: flex;
  min-height: 52rpx;
  padding: 0 16rpx;
  align-items: center;
  color: #596360;
  background: #f4f5f2;
  border: 0;
  border-radius: 99rpx;
  font-size: 21rpx;
  font-weight: 650;
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
.is-dialogue .send-button {
  width: 88rpx;
  min-width: 88rpx;
  min-height: 88rpx;
  padding: 0;
  color: inherit;
  background: transparent;
  border: 0;
  border-radius: 0;
  box-shadow: none;
}
.send-button-surface {
  display: flex;
  width: 72rpx;
  height: 72rpx;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: linear-gradient(135deg, #8adfe6 0%, #49c5d0 100%);
  border: 0;
  border-radius: 50%;
  box-shadow: 0 8rpx 18rpx rgba(7, 155, 170, 0.2);
}
.send-glyph {
  font-size: 28rpx;
  font-weight: 700;
  line-height: 1;
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
.is-dialogue .send-button.is-disabled {
  color: inherit;
  background: transparent;
  border-color: transparent;
}
.is-dialogue .send-button.is-disabled .send-button-surface {
  color: rgba(255, 255, 255, 0.9);
  background: linear-gradient(135deg, #c5e9ed 0%, #91d4dc 100%);
  border-color: transparent;
  box-shadow: none;
}
.is-dialogue .send-button.is-retry {
  color: inherit;
  background: transparent;
  border-color: transparent;
}
.is-dialogue .send-button.is-retry .send-button-surface {
  color: var(--med-safety);
  background: var(--med-safety-soft);
  border-color: var(--med-safety-border);
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
  .composer.is-dialogue {
    padding: 0 24px calc(96px + env(safe-area-inset-bottom));
    border-radius: 0;
  }
  .composer-actions {
    margin-bottom: 8px;
  }
  .composer-quote {
    height: 32px;
    margin: 0;
    padding: 0 4px;
    gap: 6px;
    font-size: 12px;
  }
  .composer-quote__mark {
    font-size: 15px;
  }
  .composer-quote__close {
    width: 28px;
    min-width: 28px;
    min-height: 28px;
    font-size: 18px;
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
  .is-dialogue .composer-bar {
    gap: 2px;
    padding: 13px 10px 8px 14px;
    border-radius: 22px;
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
  .is-dialogue .message-input.is-textarea {
    min-height: 38px;
    max-height: 180px;
    padding: 3px 2px 8px;
    font-size: 15px;
  }
  .send-button {
    min-height: 40px;
    padding: 0 18px;
    border-radius: 10px;
    font-size: 15px;
  }
  .is-dialogue .send-button {
    width: 44px;
    min-width: 44px;
    min-height: 44px;
    padding: 0;
    border-radius: 11px;
  }
  .send-button-surface {
    width: 36px;
    height: 36px;
    border-radius: 50%;
  }
  .composer-context {
    min-height: 28px;
    padding: 0 10px;
    font-size: 12px;
  }
  .send-glyph {
    font-size: 20px;
  }
  .composer-error {
    font-size: 13px;
  }
}
</style>
