<template>
  <view
    ref="fieldRoot"
    class="feedback-form"
  >
    <view class="section-heading">
      <text
        class="section-number"
        aria-hidden="true"
        >03</text
      >
      <text
        class="section-title"
        role="heading"
        aria-level="2"
        >教师评价</text
      >
    </view>
    <text class="form-description">结合原文判断，给学生一个明确的下一步。</text>
    <label
      class="field-label"
      for="teacher-score"
      >评分 <text class="field-hint">0–100 分</text></label
    >
    <input
      id="teacher-score"
      v-model="scoreValue"
      class="score-input"
      :class="{ invalid: Boolean(scoreError) }"
      name="teacher-score"
      type="number"
      inputmode="decimal"
      aria-label="教师评分（0–100）"
      :aria-invalid="Boolean(scoreError)"
      :aria-describedby="scoreError ? 'teacher-score-error' : undefined"
      :focus="scoreFocused"
      :disabled="submitting"
      placeholder="填写分数"
      @blur="scoreFocused = false"
    />
    <text
      v-if="scoreError"
      id="teacher-score-error"
      class="field-error"
      role="alert"
      >{{ scoreError }}</text
    >
    <label
      class="field-label feedback-label"
      for="teacher-feedback"
      >给学生的反馈 <text class="field-hint">选填</text></label
    >
    <textarea
      id="teacher-feedback"
      v-model="feedbackValue"
      class="feedback-input"
      name="teacher-feedback"
      aria-label="给学生的反馈"
      aria-describedby="teacher-feedback-help"
      :disabled="submitting"
      placeholder="例如：已能抓住主要症状，下一步请补充支持鉴别诊断的证据…"
      :maxlength="1000"
    />
    <view class="feedback-help">
      <text id="teacher-feedback-help">反馈将随评分一同提交</text>
      <text>{{ feedback.length }} / 1000</text>
    </view>
    <view class="submit-bar">
      <text
        v-if="submitError"
        class="submit-error"
        role="alert"
        >{{ submitError }}</text
      >
      <view class="submit-row">
        <view class="submit-copy">
          <text class="save-state">{{ submitting ? '正在保存…' : reviewed ? '已批阅 · 可更新' : '尚未提交' }}</text>
          <text class="submit-hint">提交后学生可查看</text>
        </view>
        <button
          hover-class="is-pressed"
          :hover-start-time="0"
          :hover-stay-time="80"
          class="primary-button submit-button"
          role="button"
          :tabindex="submitting ? -1 : 0"
          :disabled="submitting"
          :aria-disabled="submitting"
          :loading="submitting"
          @keydown="activateButtonOnKey"
          @click="requestSubmit"
        >
          {{ reviewed ? '更新批阅' : '提交批阅' }}
        </button>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { activateButtonOnKey } from '@/components/ui/keyboard'
// #ifdef H5
import { useNativeFieldA11y } from '@/components/ui/nativeFieldA11y'
// #endif
const fieldRoot = ref(null)
// #ifdef H5
useNativeFieldA11y(fieldRoot)
// #endif
const props = defineProps<{
  score: string
  feedback: string
  scoreError: string
  submitError: string
  submitting: boolean
  reviewed: boolean
}>()
const emit = defineEmits<{ 'update:score': [value: string]; 'update:feedback': [value: string]; submit: [] }>()
const scoreValue = computed({
  get: () => props.score,
  set: (value: string | number) => emit('update:score', String(value)),
})
const feedbackValue = computed({ get: () => props.feedback, set: (value: string) => emit('update:feedback', value) })
const scoreFocused = ref(false)
function requestSubmit() {
  if (props.submitting) return
  scoreFocused.value = false
  emit('submit')
  void nextTick(() => {
    scoreFocused.value = Boolean(props.scoreError)
  })
}
</script>

<style scoped>
.section-heading {
  display: flex;
  align-items: baseline;
  gap: 16rpx;
}
.section-number {
  color: var(--med-muted);
  font-family: var(--med-font-utility);
  font-size: 24rpx;
}
.section-title {
  color: var(--med-ink);
  font-size: 36rpx;
  font-weight: 700;
}
.form-description {
  display: block;
  margin-top: 16rpx;
  color: var(--med-muted);
  font-size: 24rpx;
  line-height: 1.7;
}
.field-label {
  display: block;
  margin: 32rpx 0 12rpx;
  color: var(--med-text);
  font-size: 28rpx;
  font-weight: 600;
}
.field-hint {
  margin-left: 12rpx;
  color: var(--med-muted);
  font-size: 24rpx;
  font-weight: 400;
}
.score-input,
.feedback-input {
  box-sizing: border-box;
  padding: 20rpx;
  color: var(--med-ink);
  background: var(--med-surface);
  border: 1px solid var(--med-muted);
  border-radius: 4px;
  font-size: 30rpx;
  line-height: 1.7;
}
.score-input {
  width: 240rpx;
  height: 96rpx;
  min-width: 120px;
  min-height: 48px;
  font-family: var(--med-font-utility);
}
.score-input.invalid {
  border-color: var(--med-danger);
}
.feedback-input {
  width: 100%;
  height: 320rpx;
  min-height: 176px;
}
.feedback-help {
  display: flex;
  margin-top: 12rpx;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 8rpx;
  color: var(--med-muted);
  font-size: 22rpx;
  line-height: 1.5;
}
.field-error,
.submit-error {
  display: block;
  margin-top: 8rpx;
  color: var(--med-danger);
  font-size: 24rpx;
  line-height: 1.5;
}
.submit-bar {
  position: fixed;
  z-index: 5;
  left: 50%;
  bottom: 0;
  width: 100%;
  max-width: 1080px;
  box-sizing: border-box;
  padding: 20rpx 32rpx calc(20rpx + env(safe-area-inset-bottom));
  transform: translateX(-50%);
  background: var(--med-surface);
  border-top: 1px solid var(--med-border);
}
.submit-error {
  margin: 0 0 12rpx;
}
.submit-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24rpx;
}
.submit-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 4rpx;
}
.save-state {
  color: var(--med-text);
  font-size: 26rpx;
  font-weight: 600;
}
.submit-hint {
  color: var(--med-muted);
  font-size: 22rpx;
}
.submit-button {
  display: flex;
  min-width: 240rpx;
  min-height: 48px;
  margin: 0;
  padding: 20rpx 32rpx;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  font-size: 28rpx;
  line-height: 1.3;
}
@media screen and (max-width: 360px) {
  .form-description,
  .section-number,
  .field-hint,
  .field-error,
  .submit-error,
  .feedback-help,
  .submit-hint {
    font-size: 12px;
  }
  .field-label,
  .save-state,
  .submit-button {
    font-size: 14px;
  }
  .score-input,
  .feedback-input {
    font-size: 15px;
  }
}
@media screen and (min-width: 600px) {
  .section-heading {
    gap: 12px;
  }
  .section-title {
    font-size: 20px;
  }
  .form-description {
    margin-top: 12px;
    font-size: 14px;
  }
  .field-label {
    margin: 24px 0 8px;
    font-size: 15px;
  }
  .section-number,
  .field-hint,
  .field-error,
  .submit-error,
  .feedback-help,
  .submit-hint {
    font-size: 13px;
  }
  .field-hint {
    margin-left: 8px;
  }
  .score-input,
  .feedback-input {
    padding: 12px;
    font-size: 16px;
  }
  .score-input {
    width: 128px;
    height: 48px;
  }
  .feedback-input {
    height: 208px;
  }
  .feedback-help {
    margin-top: 8px;
    gap: 4px;
  }
  .submit-bar {
    padding: 16px 32px calc(16px + env(safe-area-inset-bottom));
  }
  .save-state {
    font-size: 15px;
  }
  .submit-button {
    min-width: 176px;
    padding: 12px 24px;
    font-size: 16px;
  }
}
</style>
