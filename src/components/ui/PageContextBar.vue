<template>
  <view
    class="context-bar"
    :aria-label="ariaLabel || label"
  >
    <view class="context-copy">
      <text class="context-label">{{ label }}</text>
      <text
        v-if="description"
        class="context-description"
        >{{ description }}</text
      >
      <slot />
    </view>
    <view
      v-if="$slots.actions"
      class="context-actions"
    >
      <slot name="actions" />
    </view>
  </view>
</template>

<script setup lang="ts">
defineProps<{
  label: string
  description?: string
  ariaLabel?: string
}>()
</script>

<style scoped>
.context-bar {
  display: flex;
  min-height: 88rpx;
  padding: 14rpx 28rpx;
  box-sizing: border-box;
  align-items: center;
  justify-content: space-between;
  gap: 20rpx;
  background: var(--med-surface);
  border-bottom: 1rpx solid var(--med-border);
}
.context-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 4rpx;
}
.context-label {
  color: var(--med-ink);
  font-size: 29rpx;
  font-weight: 750;
  line-height: 1.35;
}
.context-description {
  color: var(--med-muted);
  font-size: 21rpx;
  line-height: 1.4;
}
.context-actions {
  display: flex;
  flex: none;
  align-items: center;
  gap: 4rpx;
}
@media screen and (max-width: 360px) {
  .context-label {
    font-size: 14px;
  }
  .context-description {
    font-size: 11px;
  }
}
@media screen and (min-width: 600px) {
  .context-bar {
    min-height: 68px;
    padding: 12px 28px;
    gap: 20px;
  }
  .context-label {
    font-size: 19px;
  }
  .context-description {
    font-size: 13px;
  }
}
</style>
