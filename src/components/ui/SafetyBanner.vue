<template>
  <view
    class="safety-banner"
    :class="{ 'safety-banner--compact': compact }"
    role="note"
    aria-label="医学学习安全提示"
  >
    <view
      v-if="!compact"
      class="safety-icon"
      ><MedIcon
        name="brand"
        size="sm"
    /></view>
    <MedIcon
      v-else
      class="safety-inline-icon"
      name="brand"
      size="sm"
    />
    <view class="safety-copy">
      <template v-if="compact">
        <text class="safety-line"
          ><text class="safety-strong">教学辅助 · 非临床诊疗</text>
          仅用于医学学习，紧急情况请立即联系专业医疗机构。</text
        >
      </template>
      <template v-else>
        <text class="safety-title">教学辅助 · 非临床诊疗</text>
        <text class="safety-description"><slot>内容仅用于医学学习，紧急情况请立即联系专业医疗机构。</slot></text>
      </template>
    </view>
  </view>
</template>

<script setup lang="ts">
import MedIcon from '@/components/ui/MedIcon.vue'

withDefaults(defineProps<{ compact?: boolean }>(), { compact: false })
</script>

<style scoped>
.safety-banner {
  display: flex;
  padding: 20rpx 22rpx;
  align-items: flex-start;
  color: var(--med-safety);
  background: var(--med-safety-soft);
  border: 1rpx solid var(--med-safety-border);
  border-left: 6rpx solid var(--med-safety);
  border-radius: var(--med-radius-md);
}
.safety-banner--compact {
  padding: 14rpx 20rpx;
  align-items: center;
  border-left-width: 4rpx;
  border-radius: var(--med-radius-sm);
}
.safety-inline-icon {
  flex: none;
  color: var(--med-safety);
}
.safety-icon {
  display: flex;
  width: 48rpx;
  height: 48rpx;
  align-items: center;
  justify-content: center;
  background: var(--med-surface);
  border-radius: var(--med-radius-sm);
}
.safety-copy {
  display: flex;
  min-width: 0;
  margin-left: 16rpx;
  flex: 1;
  flex-direction: column;
}
.safety-banner--compact .safety-copy {
  margin-left: 12rpx;
}
.safety-title {
  color: var(--med-safety);
  font-size: 24rpx;
  font-weight: 700;
}
.safety-line {
  color: var(--med-safety-text);
  font-size: 21rpx;
  line-height: 1.5;
}
.safety-strong {
  color: var(--med-safety);
  font-weight: 700;
}
.safety-description {
  margin-top: 4rpx;
  color: var(--med-safety-text);
  font-size: 24rpx;
  line-height: 1.55;
}
</style>
