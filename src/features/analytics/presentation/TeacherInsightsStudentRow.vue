<template>
  <button
    class="student-row detail-action"
    :class="{ 'student-row--record': recordLayout, 'student-row--compact': compact }"
    @click="$emit('open', student)"
  >
    <image
      class="student-row__avatar"
      src="/static/insights-avatar.svg"
      mode="aspectFit"
    />
    <view class="student-row__body">
      <view class="student-row__heading">
        <text class="student-row__name">{{ student.studentName }}</text>
        <view class="student-row__result">
          <text class="student-row__label">区间平均分</text>
          <text
            class="student-row__score"
            :class="{
              'student-row__score--empty': student.periodResults.averageScore === null,
              'student-row__score--low':
                student.periodResults.averageScore !== null && student.periodResults.averageScore < 60,
            }"
            >{{
              student.periodResults.averageScore === null
                ? '暂无结果'
                : `${number(student.periodResults.averageScore)}分`
            }}</text
          >
        </view>
      </view>
      <view class="student-row__metrics">
        <view class="student-row__test"
          ><text>批次测试</text
          ><text class="student-row__value">{{
            student.cohort.completionRate === null
              ? '暂无样本'
              : `${student.cohort.completedTests}/${student.cohort.publishedRoutes} · ${number(student.cohort.completionRate)}%`
          }}</text></view
        >
        <view class="student-row__discussion"
          ><text>研讨</text
          ><template v-if="student.discussionProgress"
            ><text
              >完成 <text class="student-row__value">{{ student.discussionProgress.completed }}</text> · 进行中
              <text class="student-row__value">{{ student.discussionProgress.active }}</text></text
            ></template
          ><text v-else>暂无进度</text></view
        >
      </view>
    </view>
    <view class="student-row__arrow" />
  </button>
</template>
<script setup lang="ts">
import type { TeacherInsightsStudent } from '@/features/analytics/public'
defineProps<{ student: TeacherInsightsStudent; recordLayout?: boolean; compact?: boolean }>()
defineEmits<{ open: [student: TeacherInsightsStudent] }>()
const number = (value: number) => String(Math.round(value * 10) / 10)
</script>
<style scoped>
.student-row {
  display: flex;
  align-items: center;
  gap: 20rpx;
  width: 100%;
  min-height: 116rpx;
  margin: 0;
  padding: 16rpx 0;
  border-radius: 0;
  border-bottom: 1rpx solid #def0ff;
  background: transparent;
  color: var(--insights-ink, #20252d);
  text-align: left;
  line-height: 1.4;
}
.student-row::after {
  border: 0;
}
.student-row__avatar {
  flex: none;
  width: 76rpx;
  height: 76rpx;
}
.student-row__body {
  flex: 1;
  min-width: 0;
}
.student-row__heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12rpx;
}
.student-row__name {
  min-width: 0;
  font-size: 30rpx;
  font-weight: 700;
  overflow-wrap: anywhere;
}
.student-row__result {
  flex: none;
  display: flex;
  align-items: center;
  gap: 10rpx;
}
.student-row__label {
  font-size: 22rpx;
}
.student-row__score {
  color: #245dcc;
  padding: 3rpx 14rpx;
  border-radius: 12rpx;
  background: #e8f5ff;
  font-size: 26rpx;
  font-weight: 700;
  white-space: nowrap;
}
.student-row__score--low {
  background: #fff0ed;
  color: #ee251d;
}
.student-row__metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
  margin-top: 8rpx;
  font-size: 24rpx;
}
.student-row__test,
.student-row__discussion {
  display: flex;
  align-items: center;
  gap: 6rpx;
  padding: 5rpx 8rpx;
  border-radius: 9rpx;
}
.student-row__test {
  background: #edf6ff;
  color: #606873;
}
.student-row__test > .student-row__value {
  color: #245dcc;
}
.student-row__discussion {
  background: #eafcfb;
  color: #606873;
}
.student-row__value {
  color: #245dcc;
  font-weight: 700;
}
.student-row__arrow {
  flex: none;
  width: 12rpx;
  height: 12rpx;
  margin: 0 8rpx 0 0;
  border-top: 3rpx solid #178dff;
  border-right: 3rpx solid #178dff;
  transform: rotate(45deg);
}
@media screen and (max-width: 390px) {
  .student-row {
    gap: 12rpx;
  }
  .student-row__avatar {
    width: 64rpx;
    height: 64rpx;
  }
  .student-row__label {
    font-size: 22rpx;
  }
  .student-row__metrics {
    gap: 6rpx;
    font-size: 24rpx;
  }
  .student-row__test,
  .student-row__discussion {
    gap: 6rpx;
    padding-inline: 8rpx;
  }
}
.student-row--record {
  box-sizing: border-box;
  gap: 20rpx;
  min-height: var(--student-record-row-height, 122rpx);
  padding: 10rpx 12rpx;
}
.student-row--record .student-row__avatar {
  width: 80rpx;
  height: 80rpx;
}
.student-row--record .student-row__score {
  box-sizing: border-box;
  width: 106rpx;
  padding: 3rpx 8rpx;
  text-align: center;
  font-size: 28rpx;
}
.student-row--record .student-row__score--empty {
  color: #606873;
  font-size: 22rpx;
}
.student-row--record .student-row__metrics {
  gap: 12rpx;
  flex-wrap: nowrap;
  font-size: 22rpx;
}
.student-row--record .student-row__test,
.student-row--record .student-row__discussion {
  box-sizing: border-box;
  flex: 1;
  min-width: 0;
  align-items: baseline;
  justify-content: center;
  flex-wrap: wrap;
  gap: 6rpx;
  padding: 5rpx 10rpx;
}
.student-row--record .student-row__arrow {
  width: 16rpx;
  height: 16rpx;
  margin-right: 2rpx;
}
.student-row--compact {
  min-height: 110rpx;
  padding-block: 10rpx;
}
.student-row--compact .student-row__metrics {
  margin-top: 6rpx;
}
</style>
