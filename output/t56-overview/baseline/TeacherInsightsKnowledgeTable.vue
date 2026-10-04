<template>
  <view
    class="knowledge-table"
    :class="{ 'knowledge-table--preview': preview }"
    role="table"
    aria-label="知识点作答表现"
  >
    <view
      class="knowledge-table__row knowledge-table__head"
      role="row"
      ><text
        class="knowledge-table__first-heading"
        role="columnheader"
        >知识点</text
      ><text role="columnheader">客观题正确率</text><text role="columnheader">简答得分率</text></view
    >
    <view
      v-for="item in items"
      :key="item.pointCode"
      class="knowledge-table__row"
      role="row"
    >
      <view
        class="knowledge-table__point"
        role="cell"
        ><view
          v-if="!preview"
          class="knowledge-table__dot"
          :class="{ 'knowledge-table__dot--low': low(item.accuracyRate) || low(item.shortAnswerScoreRate) }"
        /><text>{{ label(item.pointCode) }}</text></view
      >
      <text
        class="knowledge-table__metric"
        :class="{
          'knowledge-table__metric--low': low(item.accuracyRate),
          'knowledge-table__metric--empty': item.accuracyRate === null,
        }"
        role="cell"
        >{{ percent(item.accuracyRate) }}</text
      >
      <text
        class="knowledge-table__metric"
        :class="{
          'knowledge-table__metric--low': low(item.shortAnswerScoreRate),
          'knowledge-table__metric--empty': item.shortAnswerScoreRate === null,
        }"
        role="cell"
        >{{ percent(item.shortAnswerScoreRate) }}</text
      >
    </view>
  </view>
</template>
<script setup lang="ts">
import type { TeacherInsightsKnowledgeRow } from '@/features/analytics/public'
defineProps<{ items: TeacherInsightsKnowledgeRow[]; preview?: boolean; label: (code: string) => string }>()
const low = (value: number | null) => value !== null && value < 60
const percent = (value: number | null) => (value === null ? '暂无样本' : `${Math.round(value * 10) / 10}%`)
</script>
<style scoped>
.knowledge-table {
  overflow: hidden;
  border: 1rpx solid #daeeff;
  border-radius: 12rpx;
  color: var(--insights-ink, #0000b4);
}
.knowledge-table__row {
  display: grid;
  grid-template-columns: 37% 32% 31%;
  align-items: stretch;
  min-height: 72rpx;
  margin: 0 6rpx;
  border-bottom: 1rpx solid #d1eaff;
}
.knowledge-table__row:last-child {
  border-bottom: 0;
}
.knowledge-table__row > text,
.knowledge-table__point {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 7rpx 0;
  padding: 4rpx 8rpx;
  border-left: 1rpx solid #d1eaff;
}
.knowledge-table__row .knowledge-table__first-heading,
.knowledge-table__point {
  border-left: 0;
  justify-content: flex-start;
}
.knowledge-table__point {
  gap: 14rpx;
  font-size: 24rpx;
  font-weight: 650;
  line-height: 1.5;
  overflow-wrap: anywhere;
}
.knowledge-table__head {
  min-height: 50rpx;
  margin: 0;
  border: 0;
  background: #e9f6ff;
  color: #7282c3;
  font-size: 21rpx;
  font-weight: 650;
}
.knowledge-table__head > text {
  border-color: #fff;
  white-space: nowrap;
}
.knowledge-table__head .knowledge-table__first-heading {
  padding-left: 24rpx;
}
.knowledge-table__dot {
  flex: none;
  width: 12rpx;
  height: 12rpx;
  border-radius: 50%;
  background: #178dff;
}
.knowledge-table__dot--low {
  background: #ff531d;
}
.knowledge-table__metric {
  font-size: 30rpx;
  font-weight: 700;
}
.knowledge-table__metric--low {
  color: #ff531d;
}
.knowledge-table__metric--empty {
  color: #7b88aa;
  font-size: 22rpx;
  font-weight: 500;
}
.knowledge-table--preview .knowledge-table__row {
  margin: 0;
  min-height: 66rpx;
}
.knowledge-table--preview .knowledge-table__head {
  min-height: 46rpx;
  color: var(--insights-ink, #0000b4);
}
.knowledge-table--preview .knowledge-table__row > text,
.knowledge-table--preview .knowledge-table__point {
  margin: 0;
  padding: 12rpx 18rpx;
}
.knowledge-table--preview .knowledge-table__metric {
  font-size: 28rpx;
}
.knowledge-table--preview .knowledge-table__metric--empty {
  font-size: 22rpx;
}
</style>
