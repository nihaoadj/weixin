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
      :aria-label="`${item.label}，在 ${completedDiscussions} 次完成讨论中出现 ${item.occurrences} 次`"
    >
      <view class="target-line"
        ><text>{{ item.label }}</text
        ><text class="target-count">{{ item.occurrences }} / {{ completedDiscussions }} 次完成讨论</text></view
      >
      <view
        class="track"
        aria-hidden="true"
      >
        <view
          class="track-fill"
          :style="{ width: `${Math.min(100, (item.occurrences / completedDiscussions) * 100)}%` }"
        />
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import type { PblReportPage } from '@/features/pbl/public'

defineProps<{ items: PblReportPage['summary']['recurringTargets']; completedDiscussions: number }>()
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
.target-count {
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
.track-fill {
  height: 100%;
  background: var(--med-clinical);
}
</style>
