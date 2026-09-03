<template>
  <view
    class="med-state card"
    :class="`med-state--${variant}`"
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
    <text class="med-state__title">{{ title }}</text>
    <text class="med-state__description">{{ description }}</text>
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
  }>(),
  { variant: 'empty', actionLabel: '', secondaryActionLabel: '' },
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
.med-state__icon {
  display: flex;
  width: 96rpx;
  height: 96rpx;
  align-items: center;
  justify-content: center;
  background: var(--med-brand-soft);
  border-radius: 28rpx;
}
.med-state--error .med-state__icon {
  background: var(--med-alert-soft);
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
  min-width: 180rpx;
  min-height: 88rpx;
  margin-top: 24rpx;
  color: #fff;
  background: var(--med-brand);
  border-radius: 18rpx;
  font-size: 24rpx;
}
.med-state__secondary {
  min-width: 180rpx;
  min-height: 88rpx;
  margin-top: 12rpx;
  color: var(--med-brand);
  background: var(--med-brand-soft);
  border-radius: 18rpx;
  font-size: 24rpx;
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
