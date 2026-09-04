<template>
  <view
    class="comparisons"
    role="list"
    aria-label="两轮目标改善对照"
  >
    <view
      v-for="item in targets"
      :key="`${item.planId}:${item.targetType}:${item.targetCode}`"
      class="comparison"
      role="listitem"
    >
      <text class="target-title">{{ item.label }}</text>
      <view class="cycles">
        <view
          v-for="cycle in item.cycles"
          :key="cycle.cycleNumber"
          class="cycle"
          :class="{ passed: cycle.passed }"
          :aria-label="cycleDescription(cycle)"
        >
          <text class="cycle-label">第 {{ cycle.cycleNumber }} 轮</text>
          <text class="score">{{ cycle.score ?? '—' }}</text>
          <text class="threshold">要求 {{ cycle.threshold ?? '完成' }}</text>
          <text class="result">{{ cycle.passed ? '已达标' : cycle.evidence_present ? '未达标' : '证据缺失' }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import type { PblLearningReport } from '@/features/pbl/public'

type Cycle = PblLearningReport['targetProgress'][number]['cycles'][number]
defineProps<{ targets: PblLearningReport['targetProgress'] }>()
const cycleDescription = (cycle: Cycle) =>
  `第 ${cycle.cycleNumber} 轮，成绩 ${cycle.score ?? '缺失'}，要求 ${cycle.threshold ?? '完成'}，${
    cycle.passed ? '已达标' : cycle.evidence_present ? '未达标' : '证据缺失'
  }`
</script>

<style scoped>
.comparisons,
.comparison {
  display: flex;
  flex-direction: column;
}
.comparisons {
  gap: 24rpx;
}
.comparison {
  padding-top: 20rpx;
  gap: 14rpx;
  border-top: 1rpx solid var(--med-divider);
}
.target-title {
  color: var(--med-ink);
  font-size: 27rpx;
  font-weight: 750;
}
.cycles {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12rpx;
}
.cycle {
  display: grid;
  padding: 18rpx;
  grid-template-columns: 1fr auto;
  gap: 7rpx 12rpx;
  background: var(--med-bg);
  border-left: 6rpx solid var(--med-alert, #9f2f2f);
  border-radius: var(--med-radius-sm);
}
.cycle.passed {
  border-left-color: var(--med-primary);
}
.cycle-label,
.threshold,
.result {
  color: var(--med-muted);
  font-size: 21rpx;
}
.score {
  color: var(--med-ink);
  font-family: var(--med-font-utility);
  font-size: 28rpx;
  font-weight: 800;
}
.threshold,
.result {
  grid-column: span 2;
}
.result {
  color: var(--med-text-secondary);
  font-weight: 700;
}
</style>
