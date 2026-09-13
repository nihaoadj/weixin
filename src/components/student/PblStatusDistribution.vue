<template>
  <view class="distribution">
    <view
      class="segments"
      role="img"
      :aria-label="description"
    >
      <view
        v-for="item in visible"
        :key="item.key"
        class="segment"
        :class="`segment--${item.key}`"
        :style="{ flexGrow: item.value }"
      />
    </view>
    <view
      class="legend"
      role="list"
    >
      <view
        v-for="item in items"
        :key="item.key"
        class="legend-item"
        role="listitem"
      >
        <text
          class="marker"
          :class="`marker--${item.key}`"
          aria-hidden="true"
        />
        <text>{{ item.label }}</text
        ><text class="count">{{ item.value }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { PblReportPage, PblReportStatus } from '@/features/pbl/public'

const props = defineProps<{ counts: PblReportPage['summary']['statusCounts'] }>()
const labels: Record<PblReportStatus, string> = {
  discussing: '讨论中',
  awaiting_learning: '待发布学习',
  learning_cycle_1: '第一轮',
  learning_cycle_2: '第二轮',
  improved: '已改善',
  support_needed: '需支持',
}
const items = computed(() =>
  (Object.keys(labels) as PblReportStatus[]).map((key) => ({ key, label: labels[key], value: props.counts[key] })),
)
const visible = computed(() => items.value.filter((item) => item.value > 0))
const description = computed(() => items.value.map((item) => `${item.label} ${item.value} 次`).join('，'))
</script>

<style scoped>
.distribution {
  display: flex;
  flex-direction: column;
  gap: 22rpx;
}
.segments {
  display: flex;
  height: 18rpx;
  overflow: hidden;
  gap: 4rpx;
  background: var(--med-divider);
  border-radius: 2rpx;
}
.segment {
  min-width: 8rpx;
  background: var(--med-muted);
}
.segment--discussing,
.marker--discussing {
  background: var(--med-clinical);
}
.segment--awaiting_learning,
.marker--awaiting_learning {
  background: var(--med-warning, #8a5a00);
}
.segment--learning_cycle_1,
.marker--learning_cycle_1 {
  background: var(--med-navy);
}
.segment--learning_cycle_2,
.marker--learning_cycle_2 {
  background: var(--med-alert, #9f2f2f);
}
.segment--improved,
.marker--improved {
  background: var(--med-accent);
}
.segment--support_needed,
.marker--support_needed {
  background: var(--med-muted);
}
.legend {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14rpx 22rpx;
}
.legend-item {
  display: grid;
  align-items: center;
  grid-template-columns: 14rpx 1fr auto;
  gap: 10rpx;
  color: var(--med-text-secondary);
  font-size: 23rpx;
}
.marker {
  width: 12rpx;
  height: 12rpx;
  background: var(--med-muted);
  border-radius: 2rpx;
}
.count {
  color: var(--med-ink);
  font-family: var(--med-font-utility);
  font-weight: 750;
}
@media (min-width: 768px) {
  .legend {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
