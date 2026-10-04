<template>
  <view
    class="phase-track"
    role="list"
    aria-label="PBL 四阶段证据"
  >
    <view
      v-for="(item, index) in phases"
      :key="item.phase"
      class="phase"
      :class="item.state"
      role="listitem"
    >
      <view class="phase-index">{{ index + 1 }}</view>
      <view class="phase-content">
        <view class="phase-heading"
          ><text class="phase-title">{{ item.label }}</text
          ><text class="phase-state">{{ stateLabel[item.state] }}</text></view
        >
        <text
          v-if="item.evidenceSummary"
          class="evidence"
          >{{ item.evidenceSummary }}</text
        >
        <text
          v-if="item.missingElements.length"
          class="missing"
          >还需补充：{{ item.missingElements.join('；') }}</text
        >
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import type { PblLearningReport } from '@/features/pbl/public'

defineProps<{ phases: PblLearningReport['phaseProgress'] }>()
const stateLabel = { completed: '已有证据', current: '当前阶段', pending: '尚未开始' }
</script>

<style scoped>
.phase-track {
  display: flex;
  flex-direction: column;
}
.phase {
  position: relative;
  display: grid;
  min-height: 104rpx;
  grid-template-columns: 52rpx minmax(0, 1fr);
  gap: 18rpx;
}
.phase:not(:last-child)::before {
  position: absolute;
  top: 48rpx;
  bottom: 0;
  left: 25rpx;
  width: 2rpx;
  content: '';
  background: var(--med-divider);
}
.phase-index {
  z-index: 1;
  display: flex;
  width: 50rpx;
  height: 50rpx;
  align-items: center;
  justify-content: center;
  color: var(--med-muted);
  background: var(--med-paper);
  border: 1rpx solid var(--med-border);
  border-radius: 50%;
  font-family: var(--med-font-utility);
  font-size: 22rpx;
}
.phase.completed .phase-index {
  color: var(--med-clinical);
  background: var(--med-wash);
  border-color: var(--med-clinical);
}
.phase.current .phase-index {
  color: white;
  background: var(--med-clinical);
  border-color: var(--med-clinical);
}
.phase-content {
  display: flex;
  min-width: 0;
  padding: 4rpx 12rpx 24rpx 0;
  flex-direction: column;
  gap: 8rpx;
}
.phase-heading {
  display: flex;
  min-width: 0;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16rpx;
}
.phase-title {
  min-width: 0;
  flex: 1 1 180rpx;
  color: var(--med-ink);
  font-size: 27rpx;
  font-weight: 750;
  line-height: 1.45;
}
.phase-state {
  flex: none;
  padding-top: 3rpx;
  color: var(--med-muted);
  font-size: 21rpx;
}
.evidence,
.missing {
  color: var(--med-text-secondary);
  font-size: 23rpx;
  line-height: 1.55;
}
.missing {
  color: var(--med-alert, #9f2f2f);
}
</style>
