<template>
  <view
    class="med-state"
    :class="[
      { card: size !== 'compact' },
      `med-state--${variant}`,
      { 'med-state--centered': centered, 'med-state--compact': size === 'compact' },
    ]"
    :role="variant === 'error' ? 'alert' : 'status'"
    :aria-live="variant === 'error' ? 'assertive' : 'polite'"
    :aria-busy="variant === 'loading' ? 'true' : undefined"
  >
    <view
      class="med-state__icon"
      :class="{ 'med-state__icon--loading': variant === 'loading' }"
    >
      <MedIcon
        :name="icon"
        size="lg"
      />
    </view>
    <view class="med-state__body">
      <text class="med-state__title">{{ title }}</text>
      <text class="med-state__description">{{ description }}</text>
      <view
        v-if="actionLabel || secondaryActionLabel"
        class="med-state__actions"
      >
        <button
          v-if="actionLabel"
          hover-class="is-pressed"
          :hover-start-time="0"
          :hover-stay-time="80"
          tabindex="0"
          role="button"
          class="med-state__action"
          @keydown="activateButtonOnKey"
          @click="$emit('action')"
        >
          {{ actionLabel }}
        </button>
        <button
          v-if="secondaryActionLabel"
          hover-class="is-pressed"
          :hover-start-time="0"
          :hover-stay-time="80"
          tabindex="0"
          role="button"
          class="med-state__secondary"
          @keydown="activateButtonOnKey"
          @click="$emit('secondaryAction')"
        >
          {{ secondaryActionLabel }}
        </button>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { activateButtonOnKey } from '@/components/ui/keyboard'
import MedIcon from '@/components/ui/MedIcon.vue'

withDefaults(
  defineProps<{
    variant?: 'loading' | 'empty' | 'error' | 'first-use'
    icon: 'history' | 'book' | 'retry' | 'report'
    title: string
    description: string
    actionLabel?: string
    secondaryActionLabel?: string
    centered?: boolean
    size?: 'default' | 'compact'
  }>(),
  { variant: 'empty', actionLabel: '', secondaryActionLabel: '', centered: false, size: 'default' },
)

defineEmits<{ action: []; secondaryAction: [] }>()
</script>

<style scoped>
.med-state {
  display: flex;
  padding: 68rpx 34rpx;
  align-items: center;
  flex-direction: column;
  text-align: center;
}
.med-state--centered {
  position: fixed;
  top: var(--window-top, 0px);
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 10;
  margin: 0;
  padding: 0 34rpx calc(180rpx + env(safe-area-inset-bottom));
  justify-content: center;
  background: var(--med-page);
  border: 0;
  border-radius: 0;
  box-sizing: border-box;
}
.med-state__icon {
  display: flex;
  width: 96rpx;
  height: 96rpx;
  align-items: center;
  justify-content: center;
  background: var(--med-brand-soft);
  border-radius: 28rpx;
}
.med-state__body {
  display: flex;
  min-width: 0;
  flex-direction: column;
  align-items: center;
}
.med-state__actions {
  display: flex;
  width: 100%;
  max-width: 320rpx;
  margin-top: 24rpx;
  flex-direction: column;
  align-items: center;
  gap: 16rpx;
}
.med-state--error .med-state__icon {
  background: var(--med-alert-soft);
}
.med-state--compact {
  padding: 20rpx 24rpx;
  align-items: center;
  flex-direction: row;
  gap: 20rpx;
  background: transparent;
  border: 0;
  border-radius: 0;
  text-align: left;
}
.med-state--compact .med-state__icon {
  width: 64rpx;
  height: 64rpx;
  flex: none;
  border-radius: 16rpx;
}
.med-state--compact .med-state__body {
  align-items: stretch;
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
}
.med-state--compact .med-state__title {
  margin-top: 0;
  font-size: 28rpx;
}
.med-state--compact .med-state__description {
  max-width: 100%;
  margin-top: 4rpx;
  font-size: 23rpx;
}
.med-state--compact .med-state__actions {
  margin-top: 12rpx;
  width: 100%;
  flex-direction: row;
  align-items: stretch;
  flex-wrap: wrap;
  gap: 16rpx;
}
.med-state--compact .med-state__action,
.med-state--compact .med-state__secondary {
  width: auto;
  flex: 1 1 180rpx;
  min-width: 0;
  min-height: 88rpx;
  margin-top: 0;
  padding: 0 28rpx;
  font-size: 26rpx;
}
.med-state--compact .med-state__secondary {
  background: transparent;
}
.med-state__icon--loading {
  animation: med-state-pulse 1.2s ease-in-out infinite alternate;
}
.med-state__title {
  margin-top: 24rpx;
  color: var(--med-navy);
  font-size: 31rpx;
  font-weight: 750;
}
.med-state__description {
  max-width: 520rpx;
  margin-top: 10rpx;
  color: var(--med-muted);
  font-size: 24rpx;
  line-height: 1.6;
}
.med-state__action {
  width: 100%;
  min-height: 88rpx;
  margin: 0;
  padding: 0 24rpx;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: var(--med-brand);
  border-radius: 18rpx;
  font-size: 24rpx;
  line-height: 1.4;
}
.med-state__secondary {
  width: 100%;
  min-height: 88rpx;
  margin: 0;
  padding: 0 24rpx;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--med-brand);
  background: var(--med-brand-soft);
  border-radius: 18rpx;
  font-size: 24rpx;
  line-height: 1.4;
}
.med-state__action::after,
.med-state__secondary::after {
  border: 0;
}
@keyframes med-state-pulse {
  from {
    opacity: 0.58;
  }

  to {
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .med-state__icon--loading {
    animation: none;
  }
}
</style>
