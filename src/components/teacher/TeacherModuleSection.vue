<template>
  <view
    class="tms"
    :class="[`tms--${tone}`, { 'tms--compact': compact }]"
  >
    <view class="tms__header">
      <view class="tms__title-tab">
        <text
          class="tms__title"
          role="heading"
          :aria-level="headingLevel"
          >{{ title }}</text
        >
      </view>
      <slot name="meta" />
    </view>
    <view class="tms__surface">
      <text
        v-if="description"
        class="tms__description"
        >{{ description }}</text
      >
      <view class="tms__body">
        <slot />
      </view>
      <view
        v-if="$slots.actions"
        class="tms__actions"
      >
        <slot name="actions" />
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
// Shared teacher module surface: owns visual structure only — surface,
// padding, heading semantics, tone identity and slot layout. It never accepts
// domain objects, loads data, translates business states or decides actions.
withDefaults(
  defineProps<{
    title: string
    description?: string
    tone?: 'default' | 'focus' | 'reference' | 'editor' | 'safety'
    headingLevel?: 2 | 3
    compact?: boolean
  }>(),
  { description: '', tone: 'default', headingLevel: 2, compact: false },
)
</script>

<style scoped>
.tms {
  --tms-tab-edge: var(--med-clinical);
  position: relative;
  display: flex;
  overflow: visible;
  flex-direction: column;
}
.tms--focus,
.tms--editor {
  --tms-tab-edge: var(--med-clinical);
}
.tms--reference,
.tms--safety {
  --tms-tab-edge: var(--med-safety-border);
}
.tms__surface {
  display: flex;
  min-width: 0;
  padding: 24rpx 28rpx 28rpx;
  flex-direction: column;
  background: var(--med-surface);
  border: 1rpx solid var(--med-border);
  border-top-color: var(--tms-tab-edge);
  border-radius: 0 18rpx 18rpx 18rpx;
  box-shadow: 0 8rpx 22rpx rgba(11, 113, 107, 0.035);
}
.tms--compact .tms__surface {
  padding: 20rpx 24rpx 24rpx;
}
.tms--safety .tms__surface {
  background: var(--med-safety-soft);
  border-color: var(--med-safety-border);
}
.tms__header {
  position: relative;
  display: flex;
  min-height: 62rpx;
  padding-right: 20rpx;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
}
.tms__title-tab {
  position: relative;
  display: flex;
  min-width: 0;
  min-height: 62rpx;
  padding: 12rpx 32rpx 10rpx 20rpx;
  box-sizing: border-box;
  align-self: flex-end;
  align-items: center;
  background: var(--med-surface);
  border: 2rpx solid var(--tms-tab-edge);
  border-right: 0;
  border-bottom: 0;
  border-radius: 16rpx 0 0 0;
}
.tms--safety .tms__title-tab {
  background: var(--med-safety-soft);
}
.tms__title-tab::after {
  position: absolute;
  top: -2rpx;
  right: -28rpx;
  height: 64rpx;
  width: 32rpx;
  content: '';
  background: inherit;
  border-top: 2rpx solid var(--tms-tab-edge);
  border-right: 2rpx solid var(--tms-tab-edge);
  transform: skewX(24deg);
  transform-origin: left bottom;
}
.tms__title {
  position: relative;
  z-index: 1;
  color: var(--med-ink);
  font-size: 30rpx;
  font-weight: 700;
  line-height: 1.4;
}
.tms__description {
  color: var(--med-muted);
  font-size: 24rpx;
  line-height: 1.5;
}
.tms__body {
  margin-top: 18rpx;
  min-width: 0;
}
.tms__actions {
  margin-top: 20rpx;
  padding-top: 20rpx;
  border-top: 1rpx solid var(--med-divider);
}
@media screen and (max-width: 359px) {
  .tms__description {
    font-size: 12px;
  }
}
@media screen and (min-width: 600px) {
  .tms__header {
    min-height: 34px;
    padding-right: 10px;
  }
  .tms__surface {
    padding: 12px;
  }
  .tms__title-tab {
    min-height: 34px;
    padding: 6px 16px 5px 10px;
  }
  .tms__title {
    font-size: 15px;
  }
  .tms__description {
    font-size: 12px;
  }
}
</style>
