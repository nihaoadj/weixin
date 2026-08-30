<template>
  <view
    class="med-state card"
    :class="`med-state--${variant}`"
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
      class="med-state__action"
      @click="$emit('action')"
    >
      {{ actionLabel }}
    </button>
    <button
      v-if="secondaryActionLabel"
      class="med-state__secondary"
      @click="$emit('secondaryAction')"
    >
      {{ secondaryActionLabel }}
    </button>
  </view>
</template>

<script setup lang="ts">
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
  background: #eaf7f5;
  border-radius: 28rpx;
}
.med-state--error .med-state__icon {
  background: #fff1f2;
}
.med-state__icon--loading {
  animation: med-state-spin 1.2s linear infinite;
}
.med-state__title {
  margin-top: 24rpx;
  color: #0b2239;
  font-size: 31rpx;
  font-weight: 750;
}
.med-state__description {
  max-width: 520rpx;
  margin-top: 10rpx;
  color: #637985;
  font-size: 23rpx;
  line-height: 1.6;
}
.med-state__action {
  min-width: 180rpx;
  margin-top: 24rpx;
  color: #fff;
  background: #0f8b8d;
  border-radius: 18rpx;
  font-size: 24rpx;
}
.med-state__secondary {
  min-width: 180rpx;
  margin-top: 12rpx;
  color: #0f777b;
  background: #eaf7f5;
  border-radius: 18rpx;
  font-size: 24rpx;
}
@keyframes med-state-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
