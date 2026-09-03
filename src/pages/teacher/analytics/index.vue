<template>
  <view class="safe-page page">
    <view class="card intro">
      <text class="title">教学学情分析</text>
      <text class="muted"
        >仅统计结构化病例训练，不混入自由问答评分。范围：{{ data.scope.dateFrom }} 至 {{ data.scope.dateTo }}</text
      >
    </view>
    <view class="card filters">
      <text class="section">班级与日期</text>
      <view class="class-tabs">
        <text
          class="class-tab"
          :class="{ active: !selectedClassId }"
          @click="selectClass(undefined)"
          >全部负责班级</text
        >
        <text
          v-for="item in classes"
          :key="item.id"
          class="class-tab"
          :class="{ active: selectedClassId === item.id }"
          @click="selectClass(item.id)"
          >{{ item.name }}</text
        >
      </view>
      <view class="dates"
        ><input
          v-model="dateFrom"
          type="date" /><text>至</text
        ><input
          v-model="dateTo"
          type="date"
      /></view>
      <button
        class="secondary"
        :loading="loading"
        @click="load"
      >
        刷新统计
      </button>
    </view>
    <MedState
      v-if="loading"
      variant="loading"
      icon="retry"
      title="正在生成学情概览"
      description="正在汇总班级、病例与学生训练数据。"
    />
    <MedState
      v-else-if="error"
      variant="error"
      icon="retry"
      title="学情加载失败"
      :description="error"
      action-label="重新加载"
      @action="load"
    />
    <MedState
      v-else-if="emptyState"
      variant="first-use"
      :icon="emptyState.icon"
      :title="emptyState.title"
      :description="emptyState.description"
      :action-label="emptyState.action"
      secondary-action-label="重新加载"
      @action="handleEmptyAction"
      @secondary-action="load"
    />
    <template v-else>
      <view class="metrics">
        <view
          v-for="item in metrics"
          :key="item.label"
          class="card metric"
          ><text class="value">{{ item.value ?? '暂无数据' }}</text
          ><text class="muted">{{ item.label }}</text></view
        >
      </view>
      <view class="card">
        <text class="section">六维能力</text>
        <view
          v-for="item in data.dimensions"
          :key="item.dimensionId"
          class="dimension"
          ><text>{{ item.label }}</text
          ><text>{{ item.averageScore ?? '暂无数据' }}</text
          ><view class="bar"><view :style="{ width: `${item.averageScore || 0}%` }" /></view
        ></view>
      </view>
      <view class="card">
        <text class="section">病例摘要</text>
        <text
          v-if="!data.cases.length"
          class="muted"
          >暂无可下钻病例</text
        >
        <view
          v-for="item in data.cases"
          :key="item.problemId"
          class="link-row"
          @click="openCase(item.problemId)"
          ><text>{{ item.title }}</text
          ><text>{{ item.completed }}/{{ item.assigned }} · {{ item.averageScore ?? '—' }} ›</text></view
        >
      </view>
      <view class="card">
        <text class="section">学生摘要</text>
        <text
          v-if="!data.students.length"
          class="muted"
          >暂无学生数据</text
        >
        <view
          v-for="item in data.students"
          :key="item.studentId"
          class="link-row"
          @click="openStudent(item.studentId)"
          ><text>{{ item.nickname }}</text
          ><text>{{ item.completed }}/{{ item.assigned }} · {{ item.averageScore ?? '—' }} ›</text></view
        >
      </view>
      <view class="card">
        <text class="section">薄弱项</text>
        <text
          v-if="!data.weakDimensions.length"
          class="muted"
          >暂无薄弱维度</text
        >
        <text
          v-for="item in data.weakDimensions"
          :key="item.dimensionId"
          class="weak"
          >{{ item.label }} · {{ item.rate ?? '暂无数据' }}%</text
        >
      </view>
      <view class="card knowledge-card">
        <text class="section">知识巩固概览</text>
        <text
          v-if="!selectedClassId"
          class="muted"
          >选择一个具体班级后可查看复习参与、到期积压与匿名薄弱主题。</text
        >
        <template v-else-if="knowledge">
          <view class="knowledge-metrics">
            <text>参与复习 {{ knowledge.participantCount }} 人</text>
            <text>到期积压 {{ knowledge.dueBacklog }} 张</text>
            <text
              >客观正确率
              {{ knowledge.objectiveCorrectRate == null ? '—' : `${knowledge.objectiveCorrectRate}%` }}</text
            >
          </view>
          <text
            v-if="knowledge.rankingsSuppressed"
            class="muted"
            >少于 5 名参与学生，已隐藏薄弱主题排名以保护学习隐私。</text
          >
          <view
            v-for="item in knowledge.weakPoints"
            :key="item.pointCode"
            class="link-row"
          >
            <text>{{ item.pointCode }}</text
            ><text>{{ item.studentCount }} 人需巩固</text>
          </view>
        </template>
      </view>
    </template>
  </view>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { onBackPress, onShow } from '@dcloudio/uni-app'
import MedState from '@/components/ui/MedState.vue'
import { requireRole } from '@/features/identity/public'
import { goDetail, handleBackPress, relaunchTo, ROUTES } from '@/platform/navigation'
import {
  getAnalyticsKnowledge,
  getAnalyticsOverview,
  type AnalyticsKnowledge,
  type AnalyticsOverview,
} from '@/features/analytics/public'
import { getTeacherClasses, type TeacherClass } from '@/features/classroom/public'

const today = new Date()
const iso = (date: Date) => date.toISOString().slice(0, 10)
const dateTo = ref(iso(today))
const dateFrom = ref(iso(new Date(today.getTime() - 29 * 86400000)))
const selectedClassId = ref<number>()
const classes = ref<TeacherClass[]>([])
const loading = ref(false)
const error = ref('')
const knowledge = ref<AnalyticsKnowledge | null>(null)
const data = ref<AnalyticsOverview>({
  scope: { classId: null, className: null, dateFrom: '', dateTo: '' },
  studentCount: 0,
  publishedCaseCount: 0,
  eligiblePairs: 0,
  startedPairs: 0,
  completedPairs: 0,
  completionRate: null,
  currentAverageScore: null,
  averageImprovement: null,
  dimensions: [],
  weakDimensions: [],
  cases: [],
  students: [],
})
const metrics = computed(() => [
  { label: '学生数', value: data.value.studentCount },
  { label: '可完成病例', value: data.value.publishedCaseCount },
  { label: '完成率', value: data.value.completionRate == null ? null : `${data.value.completionRate}%` },
  { label: '当前平均分', value: data.value.currentAverageScore },
])
const emptyState = computed<{
  icon: 'book' | 'report'
  title: string
  description: string
  action: string
  target: 'classes' | 'problems' | 'refresh'
} | null>(() => {
  if (!classes.value.length) {
    return {
      icon: 'report',
      title: '先建立班级范围',
      description: '创建班级并加入学生后，才能按负责范围汇总训练学情。',
      action: '管理班级',
      target: 'classes',
    }
  }
  if (!data.value.publishedCaseCount) {
    return {
      icon: 'book',
      title: '还没有可统计的病例',
      description: '发布结构化病例后，系统会开始统计分配、完成率和六维能力。',
      action: '管理教学内容',
      target: 'problems',
    }
  }
  if (!data.value.completedPairs) {
    return {
      icon: 'report',
      title: '等待学生完成首次训练',
      description: '病例已经可用，学生提交训练报告后，这里会生成班级与个人学情。',
      action: '重新加载',
      target: 'refresh',
    }
  }
  return null
})
async function load() {
  if (loading.value) return
  loading.value = true
  error.value = ''
  try {
    const [overview, knowledgeOverview] = await Promise.all([
      getAnalyticsOverview(selectedClassId.value, dateFrom.value, dateTo.value),
      selectedClassId.value ? getAnalyticsKnowledge(selectedClassId.value) : Promise.resolve(null),
    ])
    data.value = overview
    knowledge.value = knowledgeOverview
  } catch (loadError) {
    error.value = loadError instanceof Error ? loadError.message : '请稍后重试'
  } finally {
    loading.value = false
  }
}
function handleEmptyAction() {
  if (emptyState.value?.target === 'classes') {
    goDetail(ROUTES.teacherClasses)
    return
  }
  if (emptyState.value?.target === 'problems') {
    relaunchTo(ROUTES.teacherWorkspace, { tab: 'problems' })
    return
  }
  void load()
}
function selectClass(id?: number) {
  selectedClassId.value = id
  void load()
}
function openCase(id: number) {
  goDetail(ROUTES.teacherAnalyticsCaseDetail, { problemId: id, classId: selectedClassId.value })
}
function openStudent(id: number) {
  goDetail(ROUTES.teacherAnalyticsStudentDetail, { studentId: id, classId: selectedClassId.value })
}
onBackPress(({ from }) => handleBackPress(from, ROUTES.teacherWorkspace))
onShow(async () => {
  if (!requireRole('teacher')) return
  try {
    classes.value = await getTeacherClasses()
  } finally {
    await load()
  }
})
</script>
<style scoped>
.page {
  min-height: 100vh;
  padding: 28rpx;
  background: var(--med-page);
}
.intro,
.filters,
.metric,
.page > .card {
  margin-bottom: 18rpx;
  padding: 28rpx;
}
.title,
.section {
  display: block;
  font-size: 32rpx;
  font-weight: 750;
}
.muted {
  color: var(--med-muted);
  font-size: 22rpx;
  line-height: 1.5;
}
.filters {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}
.class-tabs {
  display: flex;
  gap: 14rpx;
  flex-wrap: wrap;
}
.class-tab {
  padding: 10rpx 16rpx;
  color: var(--med-muted);
  background: var(--med-divider);
  border-radius: 99rpx;
  font-size: 22rpx;
}
.class-tab.active {
  color: #fff;
  background: var(--med-brand);
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
  border: 1rpx solid var(--med-border);
  border-radius: 10rpx;
  font-size: 21rpx;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16rpx;
}
.metric {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}
.value {
  color: var(--med-brand);
  font-size: 42rpx;
  font-weight: 800;
}
.dimension {
  display: flex;
  padding: 16rpx 0;
  justify-content: space-between;
  flex-wrap: wrap;
  border-bottom: 1rpx solid var(--med-divider);
}
.bar {
  width: 100%;
  height: 10rpx;
  margin-top: 10rpx;
  background: #e2e8f0;
  border-radius: 99rpx;
}
.bar view {
  height: 100%;
  background: #0d8f9c;
  border-radius: 99rpx;
}
.link-row {
  display: flex;
  padding: 18rpx 0;
  justify-content: space-between;
  border-bottom: 1rpx solid var(--med-divider);
  font-size: 23rpx;
}
.weak {
  display: block;
  padding-top: 14rpx;
}
.secondary {
  color: var(--med-brand);
  background: var(--med-brand-soft);
}
.knowledge-card {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}
.knowledge-metrics {
  display: flex;
  gap: 16rpx;
  flex-wrap: wrap;
  color: var(--med-text);
  font-size: 23rpx;
}
</style>
