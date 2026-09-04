<template>
  <view
    class="targets"
    role="list"
    aria-label="反复出现的学习重点"
  >
    <view
      v-for="item in items"
      :key="`${item.targetType}:${item.targetCode}`"
      class="target"
      role="listitem"
      :aria-label="`${item.label}，在 ${item.occurrences} 次 PBL 中出现`"
    >
      <view class="target-line"
        ><text>{{ item.label }}</text
        ><text>{{ item.occurrences }} 次</text></view
      >
      <view
        class="track"
        aria-hidden="true"
      >
        <view :style="{ width: `${Math.max(12, (item.occurrences / maximum) * 100)}%` }" />
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { PblReportPage } from '@/features/pbl/public'

const props = defineProps<{ items: PblReportPage['summary']['recurringTargets'] }>()
const maximum = computed(() => Math.max(1, ...props.items.map((item) => item.occurrences)))
</script>

<style scoped>
.targets,
.target {
  display: flex;
  flex-direction: column;
}
.targets {
  gap: 20rpx;
}
.target {
  gap: 10rpx;
}
.target-line {
  display: flex;
  justify-content: space-between;
  gap: 18rpx;
  color: var(--med-text-secondary);
  font-size: 25rpx;
}
.target-line text:last-child {
  flex: none;
  color: var(--med-clinical);
  font-family: var(--med-font-utility);
  font-weight: 700;
}
.track {
  height: 8rpx;
  overflow: hidden;
  background: var(--med-divider);
  border-radius: 2rpx;
}
.track view {
  height: 100%;
  background: var(--med-clinical);
}
</style>
