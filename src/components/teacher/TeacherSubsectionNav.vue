<template>
  <view
    class="record-index"
    role="navigation"
    :aria-label="navLabel"
  >
    <button
      v-for="item in items"
      :key="item.key"
      class="record-index__item"
      :class="{ active: active === item.key }"
      :aria-current="active === item.key ? 'page' : undefined"
      :aria-controls="`${panelPrefix}-${item.key}`"
      role="button"
      tabindex="0"
      hover-class="is-pressed"
      :hover-start-time="0"
      :hover-stay-time="80"
      @keydown="activateButtonOnKey"
      @click="$emit('change', item.key)"
    >
      <text>{{ item.label }}</text>
      <text
        v-if="item.count !== undefined"
        class="record-index__count"
        >{{ item.count }}</text
      >
    </button>
  </view>
</template>

<script setup lang="ts">
import { activateButtonOnKey } from '@/components/ui/keyboard'

export type TeacherSubsectionItem = { key: string; label: string; count?: number }

defineProps<{
  active: string
  items: TeacherSubsectionItem[]
  navLabel: string
  panelPrefix: string
}>()
defineEmits<{ change: [section: string] }>()
</script>

<style scoped>
.record-index {
  display: flex;
  min-width: 0;
  border-bottom: 1rpx solid var(--med-border);
}
.record-index__item {
  position: relative;
  display: flex;
  min-width: 0;
  min-height: 48px;
  margin: 0;
  padding: 0 12rpx;
  flex: 1;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
  color: var(--med-text-secondary);
  background: transparent;
  border-radius: 0;
  font-size: 24rpx;
  line-height: 1.35;
}
.record-index__item.active {
  color: var(--med-clinical);
  background: var(--med-wash);
  box-shadow: inset 0 -3px 0 var(--med-clinical);
  font-weight: 700;
}
.record-index__count {
  min-width: 18px;
  padding: 1px 5px;
  box-sizing: border-box;
  color: var(--med-surface);
  background: var(--med-clinical);
  border-radius: 999px;
  font-family: var(--med-font-utility);
  font-size: 20rpx;
  line-height: 1.35;
  text-align: center;
}
.record-index__item:focus-visible {
  outline: 2px solid var(--med-clinical);
  outline-offset: -4px;
}
@media screen and (max-width: 360px) {
  .record-index__item {
    padding: 0 6rpx;
    font-size: 12px;
  }
  .record-index__count {
    font-size: 10px;
  }
}
@media screen and (min-width: 600px) {
  .record-index__item {
    padding: 0 16px;
    font-size: 14px;
  }
  .record-index__count {
    font-size: 11px;
  }
}
</style>
