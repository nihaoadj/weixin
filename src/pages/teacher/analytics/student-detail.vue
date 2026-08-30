<template>
  <view class="safe-page page"
    ><MedState
      v-if="error"
      icon="retry"
      title="档案加载失败"
      :description="error"
      action-label="重新加载"
      @action="load"
    /><view
      v-if="data.student"
      class="card panel"
      ><text class="title">{{ data.student.nickname }}的学习档案</text
      ><text class="muted"
        >完成 {{ data.completed || 0 }} / {{ data.assigned || 0 }} 项完整病例 · 当前均分
        {{ data.currentAverageScore ?? '—' }}</text
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
        刷新统计</button
      ><text class="section-title">训练计划</text
      ><text v-if="data.learningPlan"
        >{{ data.learningPlan.status }} · 目标 {{ data.learningPlan.targetDimensionIds?.join('、') }}</text
      ><text
        v-else
        class="muted"
        >暂无进行中的计划</text
      ></view
    ><view
      v-if="data.practiceMastery"
      class="card panel"
      ><text class="section-title">练习掌握度</text
      ><view
        v-for="(item, key) in data.practiceMastery"
        :key="key"
        class="row"
        ><text>{{ key }}</text
        ><text>{{ item.averageScore }} 分 / {{ item.attemptCount }} 次</text></view
      ></view
    ><view
      v-if="data.cases"
      class="card panel"
      ><text class="section-title">病例变化</text
      ><view
        v-for="item in data.cases"
        :key="item.problemId"
        class="row"
        ><text>{{ item.title }}</text
        ><text
          >{{ item.latestScore ?? '—'
          }}<text v-if="item.delta !== null"> ({{ item.delta > 0 ? '+' : '' }}{{ item.delta }})</text></text
        ></view
      ></view
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
      v-if="data.timeline?.length"
      class="card panel"
      ><text class="section-title">最近评估</text
      ><view
        v-for="item in data.timeline"
        :key="item.attemptId"
        class="row"
        ><text>#{{ item.attemptId }} · 病例 {{ item.problemId }}</text
        ><text>{{ item.score }}</text></view
      ></view
    ></view
  >
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import MedState from '@/components/ui/MedState.vue'
import { requireRole } from '@/services/auth'
import { getAnalyticsStudent, type AnalyticsStudent } from '@/services/teacherInsights'
const iso = (date: Date) => date.toISOString().slice(0, 10)
const today = new Date()
const dateTo = ref(iso(today))
const dateFrom = ref(iso(new Date(today.getTime() - 29 * 86400000)))
const data = ref<AnalyticsStudent>({
  student: { id: 0, nickname: '' },
  assigned: 0,
  started: 0,
  completed: 0,
  completionRate: null,
  currentAverageScore: null,
  averageImprovement: null,
  dimensions: [],
  cases: [],
  timeline: [],
  learningPlan: null,
  practiceMastery: {},
})
const error = ref('')
const loading = ref(false)
let studentId = 0
let classId: number | undefined
async function load() {
  loading.value = true
  try {
    error.value = ''
    data.value = await getAnalyticsStudent(studentId, classId, dateFrom.value, dateTo.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '请稍后重试'
  } finally {
    loading.value = false
  }
}
onLoad((query) => {
  if (!requireRole('teacher')) return
  studentId = Number(query?.studentId || 0)
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
