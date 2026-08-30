<template>
  <view class="safe-page page"
    ><MedState
      v-if="error"
      icon="retry"
      title="病例分析加载失败"
      :description="error"
      action-label="重新加载"
      @action="load"
    /><view
      v-if="data.problem"
      class="card panel"
      ><text class="title">{{ data.problem.title }}</text
      ><text class="muted"
        >完成 {{ data.completedPairs || 0 }} / {{ data.eligiblePairs || 0 }} · 当前均分
        {{ data.currentAverageScore ?? '—' }} · 平均用时 {{ data.averageDurationMinutes ?? '—' }} 分钟</text
      ></view
    ><view class="card panel filters"
      ><text class="section-title">统计范围</text
      ><view class="dates"
        ><input
          v-model="dateFrom"
          type="date" /><text>至</text
        ><input
          v-model="dateTo"
          type="date" /></view
      ><button
        class="secondary"
        :loading="loading"
        @click="load"
      >
        刷新统计
      </button></view
    ><view
      v-if="data.dimensions?.length"
      class="card panel"
      ><text class="section-title">六维变化</text
      ><view
        v-for="item in data.dimensions"
        :key="item.dimensionId"
        class="row"
        ><text>{{ item.label }}</text
        ><text
          >{{ item.currentScore ?? '—'
          }}<text v-if="item.delta !== null && item.delta !== undefined"
            >（{{ item.delta > 0 ? '+' : '' }}{{ item.delta }}）</text
          ></text
        ></view
      ></view
    ><view
      v-if="data.distribution"
      class="card panel"
      ><text class="section-title">成绩分布</text
      ><view
        v-for="(value, key) in data.distribution"
        :key="key"
        class="row"
        ><text>{{ key }}</text
        ><text>{{ value }}</text></view
      ></view
    ><view
      v-if="data.students"
      class="card panel"
      ><text class="section-title">学生下钻</text
      ><view
        v-for="item in data.students"
        :key="item.studentId"
        class="row"
        @click="openStudent(item.studentId)"
        ><text>{{ item.nickname }}</text
        ><text>{{ item.current ?? '未完成' }} ›</text></view
      ></view
    ></view
  >
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import MedState from '@/components/ui/MedState.vue'
import { requireRole } from '@/services/auth'
import { getAnalyticsCase, type AnalyticsCase } from '@/services/teacherInsights'
const iso = (date: Date) => date.toISOString().slice(0, 10)
const today = new Date()
const dateTo = ref(iso(today))
const dateFrom = ref(iso(new Date(today.getTime() - 29 * 86400000)))
const data = ref<AnalyticsCase>({
  problem: { id: 0, title: '', version: 1 },
  eligiblePairs: 0,
  startedPairs: 0,
  completedPairs: 0,
  completionRate: null,
  currentAverageScore: null,
  averageImprovement: null,
  averageDurationMinutes: null,
  dimensions: [],
  distribution: {},
  students: [],
})
const error = ref('')
const loading = ref(false)
let problemId = 0
let classId: number | undefined
async function load() {
  loading.value = true
  try {
    error.value = ''
    data.value = await getAnalyticsCase(problemId, classId, dateFrom.value, dateTo.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '请稍后重试'
  } finally {
    loading.value = false
  }
}
function openStudent(id: number) {
  uni.navigateTo({
    url: `/pages/teacher/analytics/student-detail?studentId=${id}${classId ? `&classId=${classId}` : ''}`,
  })
}
onLoad((query) => {
  if (!requireRole('teacher')) return
  problemId = Number(query?.problemId || 0)
  classId = query?.classId ? Number(query.classId) : undefined
  void load()
})
</script>
<style scoped>
.page {
  padding: 28rpx;
  background: #f4f8fa;
  min-height: 100vh;
}
.panel {
  display: flex;
  margin-bottom: 22rpx;
  padding: 28rpx;
  flex-direction: column;
  gap: 14rpx;
}
.title {
  font-size: 34rpx;
  font-weight: 750;
}
.section-title {
  font-size: 28rpx;
  font-weight: 750;
}
.muted {
  color: #718096;
  font-size: 22rpx;
}
.dates {
  display: flex;
  align-items: center;
  gap: 10rpx;
}
.dates input {
  flex: 1;
  min-height: 62rpx;
  padding: 0 12rpx;
  border: 1rpx solid #dbe7eb;
  border-radius: 10rpx;
  font-size: 21rpx;
}
.secondary {
  color: #087f8c;
  background: #e6f7f5;
}
.row {
  display: flex;
  padding: 14rpx 0;
  justify-content: space-between;
  border-bottom: 1rpx solid #e5edf0;
}
</style>
