<template>
  <view class="case-setup">
    <view class="setup-content">
      <view class="setup-main">
        <view class="setup-heading">
          <text class="section-kicker">教学设定</text>
          <text class="setup-note">填写这三项后生成可继续编辑的病例草稿。</text>
        </view>

        <view class="setup-grid">
          <view class="field-block">
            <text
              id="case-topic-label"
              class="field-label"
              >病例主题</text
            >
            <input
              :value="topic"
              class="field-control"
              name="case-topic"
              data-native-name="case-topic"
              aria-labelledby="case-topic-label"
              placeholder="例如：细胞损伤与适应"
              :disabled="busy"
              @input="emitValue('update:topic', $event)"
            />
          </view>
          <view class="field-block">
            <text
              id="case-level-label"
              class="field-label"
              >学习层级</text
            >
            <input
              :value="level"
              class="field-control"
              name="case-level"
              data-native-name="case-level"
              aria-labelledby="case-level-label"
              placeholder="例如：临床医学本科生"
              :disabled="busy"
              @input="emitValue('update:level', $event)"
            />
          </view>
        </view>

        <view class="field-block objective-field">
          <text
            id="case-objectives-label"
            class="field-label"
            >教学目标</text
          >
          <textarea
            :value="objectives"
            class="field-control objectives-control"
            name="case-objectives"
            data-native-name="case-objectives"
            aria-labelledby="case-objectives-label"
            aria-describedby="case-objectives-help"
            placeholder="每行一个，例如：训练病史采集"
            :disabled="busy"
            @input="emitValue('update:objectives', $event)"
          />
          <text
            id="case-objectives-help"
            class="field-help"
            >每行一个目标，会用于组织病例阶段与评价量表。</text
          >
        </view>
      </view>

      <view
        class="setup-rail"
        aria-label="生成后核对内容"
      >
        <text class="rail-title">生成后逐步核对</text>
        <view
          v-for="item in reviewSteps"
          :key="item.title"
          class="rail-row"
        >
          <text class="rail-step">{{ item.step }}</text>
          <view
            ><text class="rail-label">{{ item.title }}</text
            ><text class="rail-copy">{{ item.copy }}</text></view
          >
        </view>
      </view>
    </view>

    <view
      v-if="error"
      class="setup-error"
      role="alert"
      ><text>未能生成草稿：{{ error }}</text></view
    >
    <text class="mobile-tip">生成后按五步核对公开信息、隐藏事实、参考推理和量表。</text>
    <view class="setup-action">
      <button
        role="button"
        :tabindex="busy ? -1 : 0"
        class="generate-button pressable"
        hover-class="is-pressed"
        :hover-start-time="0"
        :hover-stay-time="80"
        :loading="busy"
        :disabled="busy"
        :aria-disabled="busy"
        @click="$emit('generate')"
        @keydown="activateButtonOnKey"
      >
        {{ busy ? '正在生成教学草稿' : '生成病例草稿' }}
      </button>
      <text class="action-note">生成的内容只用于教学编排，不构成诊疗建议。</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { activateButtonOnKey } from '@/components/ui/keyboard'

defineProps<{ topic: string; level: string; objectives: string; busy: boolean; error: string }>()

const emit = defineEmits<{
  (event: 'update:topic' | 'update:level' | 'update:objectives', value: string): void
  (event: 'generate'): void
}>()

const reviewSteps = [
  { step: '01', title: '病例概况', copy: '确认学生的开场信息。' },
  { step: '02', title: '阶段与事实', copy: '核对触发条件与边界。' },
  { step: '03', title: '参考推理', copy: '审阅教师参考路径。' },
  { step: '04', title: '评价量表', copy: '检查评价语句与关键词。' },
  { step: '05', title: '预览核对', copy: '区分学生与教师内容。' },
]

function emitValue(eventName: 'update:topic' | 'update:level' | 'update:objectives', event: unknown) {
  const value =
    (event as { detail?: { value?: unknown }; target?: { value?: unknown } })?.detail?.value ??
    (event as { target?: { value?: unknown } })?.target?.value
  emit(eventName, String(value ?? ''))
}
</script>

<style scoped>
.case-setup {
  display: flex;
  padding: var(--med-space-3);
  flex-direction: column;
  gap: var(--med-space-3);
  background: var(--med-surface);
  border-top: 4rpx solid var(--med-clinical);
}
.setup-content {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--med-space-3);
}
.setup-main,
.setup-heading,
.field-block,
.setup-action {
  display: flex;
  flex-direction: column;
  gap: var(--med-space-2);
}
.setup-heading {
  padding-bottom: var(--med-space-2);
  border-bottom: 1rpx solid var(--med-divider);
}
.section-kicker,
.field-label {
  color: var(--med-ink);
  font-size: 30rpx;
  font-weight: 700;
}
.setup-note,
.field-help,
.action-note,
.mobile-tip {
  color: var(--med-muted);
  font-size: 24rpx;
  line-height: 1.6;
}
.setup-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--med-space-3);
}
.field-control {
  width: 100%;
  min-height: 88rpx;
  padding: 18rpx 20rpx;
  color: var(--med-text);
  background: var(--med-paper);
  border: 1rpx solid var(--med-border);
  border-radius: var(--med-radius-sm);
  font: inherit;
  font-size: 30rpx;
  line-height: 1.45;
}
.objectives-control {
  height: 256rpx;
  min-height: 256rpx;
}
.setup-rail {
  display: none;
}
.setup-error {
  padding: var(--med-space-2);
  color: var(--med-alert);
  background: var(--med-alert-soft);
  border-left: 6rpx solid var(--med-alert);
  font-size: 24rpx;
  line-height: 1.55;
}
.mobile-tip {
  display: block;
  padding-top: var(--med-space-1);
  border-top: 1rpx solid var(--med-divider);
}
.generate-button {
  width: 100%;
  min-height: 96rpx;
  margin: 0;
  color: #fff;
  background: var(--med-brand);
  border-radius: var(--med-radius-md);
  font-size: 30rpx;
  font-weight: 700;
  line-height: 96rpx;
}
@media screen and (min-width: 900px) {
  .case-setup {
    padding: 24px;
    gap: 24px;
    border-top-width: 2px;
  }
  .setup-content {
    grid-template-columns: minmax(0, 2fr) minmax(180px, 1fr);
    gap: 24px;
  }
  .setup-grid {
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }
  .section-kicker,
  .field-label {
    font-size: 15px;
  }
  .setup-note,
  .field-help,
  .action-note,
  .mobile-tip {
    font-size: 13px;
  }
  .field-control {
    min-height: 48px;
    padding: 12px;
    font-size: 15px;
  }
  .objectives-control {
    height: 128px;
    min-height: 128px;
  }
  .setup-rail {
    display: flex;
    padding-left: 20px;
    flex-direction: column;
    gap: 12px;
    border-left: 1px solid var(--med-divider);
  }
  .rail-title {
    color: var(--med-ink);
    font-size: 14px;
    font-weight: 700;
  }
  .rail-row {
    display: grid;
    grid-template-columns: 24px 1fr;
    gap: 8px;
  }
  .rail-step {
    color: var(--med-clinical);
    font-family: var(--med-font-utility);
    font-size: 11px;
    font-weight: 700;
  }
  .rail-label,
  .rail-copy {
    display: block;
    line-height: 1.45;
  }
  .rail-label {
    color: var(--med-text);
    font-size: 13px;
    font-weight: 700;
  }
  .rail-copy {
    color: var(--med-muted);
    font-size: 12px;
  }
  .mobile-tip {
    display: none;
  }
  .setup-action {
    align-items: flex-end;
  }
  .generate-button {
    width: 200px;
    min-height: 48px;
    font-size: 16px;
    line-height: 48px;
  }
  .action-note {
    align-self: stretch;
  }
}
@media screen and (min-width: 600px) and (max-width: 899px) {
  .case-setup {
    padding: 24px;
    border-top-width: 2px;
  }
  .setup-grid {
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }
  .section-kicker,
  .field-label {
    font-size: 15px;
  }
  .setup-note,
  .field-help,
  .action-note,
  .mobile-tip {
    font-size: 13px;
  }
  .field-control {
    min-height: 48px;
    padding: 12px;
    font-size: 15px;
  }
  .objectives-control {
    height: 128px;
    min-height: 128px;
  }
  .generate-button {
    min-height: 48px;
    font-size: 16px;
    line-height: 48px;
  }
}
</style>
