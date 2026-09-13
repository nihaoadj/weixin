<template>
  <view class="analytics-overview">
    <view class="filters">
      <view>
        <text class="section-title">统计周期</text>
        <text class="muted">仅统计结构化病例训练，不混入自由问答评分。</text>
      </view>
      <view class="dates">
        <input
          v-model="dateFrom"
          type="date"
          aria-label="统计开始日期"
        />
        <text>至</text>
        <input
          v-model="dateTo"
          type="date"
          aria-label="统计结束日期"
        />
      </view>
      <button
        class="secondary"
        :loading="loading"
        :disabled="loading"
        :tabindex="loading ? -1 : 0"
        role="button"
        @keydown="activateButtonOnKey"
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
      <text class="scope-copy">统计范围：{{ data.scope.dateFrom }} 至 {{ data.scope.dateTo }}</text>
      <view class="metrics">
        <view
          v-for="item in metrics"
          :key="item.label"
          class="metric"
        >
          <text class="value">{{ item.value ?? '暂无数据' }}</text>
          <text class="muted">{{ item.label }}</text>
        </view>
      </view>
      <view class="analysis-section">
        <text class="section-title">六维能力</text>
        <view
          v-for="item in data.dimensions"
          :key="item.dimensionId"
          class="dimension"
        >
          <text>{{ item.label }}</text>
          <text>{{ item.averageScore ?? '暂无数据' }}</text>
          <view class="bar"><view :style="{ width: `${item.averageScore || 0}%` }" /></view>
        </view>
      </view>
      <view class="analysis-section">
        <text class="section-title">病例摘要</text>
        <text
          v-if="!data.cases.length"
          class="muted"
          >暂无可下钻病例</text
        >
        <button
          v-for="item in data.cases"
          :key="item.problemId"
          class="link-row"
          role="button"
          tabindex="0"
          @keydown="activateButtonOnKey"
          @click="openCase(item.problemId)"
        >
          <text>{{ item.title }}</text>
          <text>{{ item.completed }}/{{ item.assigned }} · {{ item.averageScore ?? '—' }} ›</text>
        </button>
      </view>
      <view class="analysis-section">
        <text class="section-title">学生摘要</text>
        <text
          v-if="!data.students.length"
          class="muted"
          >暂无学生数据</text
        >
        <button
          v-for="item in data.students"
          :key="item.studentId"
          class="link-row"
          role="button"
          tabindex="0"
          @keydown="activateButtonOnKey"
          @click="openStudent(item.studentId)"
        >
          <text>{{ item.nickname }}</text>
          <text>{{ item.completed }}/{{ item.assigned }} · {{ item.averageScore ?? '—' }} ›</text>
        </button>
      </view>
      <view class="analysis-section">
        <text class="section-title">薄弱项</text>
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
      <view class="analysis-section knowledge-section">
        <text class="section-title">知识巩固概览</text>
        <text
          v-if="!classId"
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
            class="knowledge-row"
          >
            <text>{{ item.pointCode }}</text>
            <text>{{ item.studentCount }} 人需巩固</text>
          </view>
        </template>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import MedState from '@/components/ui/MedState.vue'
import { activateButtonOnKey } from '@/components/ui/keyboard'
import {
  getAnalyticsKnowledge,
  getAnalyticsOverview,
  type AnalyticsKnowledge,
  type AnalyticsOverview,
} from '@/features/analytics/public'
import { goDetail, ROUTES } from '@/platform/navigation'

const props = defineProps<{ classId?: number; classScopeLoaded: boolean; hasClasses: boolean }>()
const emit = defineEmits<{ classes: []; resources: [] }>()

const today = new Date()
const iso = (date: Date) => date.toISOString().slice(0, 10)
const dateTo = ref(iso(today))
const dateFrom = ref(iso(new Date(today.getTime() - 29 * 86400000)))
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
let request = 0
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
  target: 'classes' | 'resources' | 'refresh'
} | null>(() => {
  if (props.classScopeLoaded && !props.hasClasses) {
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
      target: 'resources',
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
  const token = ++request
  loading.value = true
  error.value = ''
  try {
    const [overview, knowledgeOverview] = await Promise.all([
      getAnalyticsOverview(props.classId, dateFrom.value, dateTo.value),
      props.classId ? getAnalyticsKnowledge(props.classId) : Promise.resolve(null),
    ])
    if (token !== request) return
    data.value = overview
    knowledge.value = knowledgeOverview
  } catch (loadError) {
    if (token === request) error.value = loadError instanceof Error ? loadError.message : '请稍后重试'
  } finally {
    if (token === request) loading.value = false
  }
}
function handleEmptyAction() {
  if (emptyState.value?.target === 'classes') return emit('classes')
  if (emptyState.value?.target === 'resources') return emit('resources')
  void load()
}
function openCase(id: number) {
  goDetail(ROUTES.teacherAnalyticsCaseDetail, { problemId: id, classId: props.classId })
}
function openStudent(id: number) {
  goDetail(ROUTES.teacherAnalyticsStudentDetail, { studentId: id, classId: props.classId })
}
watch(
  () => props.classId,
  () => void load(),
)
onMounted(load)
defineExpose({ refresh: load })
</script>

<style scoped>
.analytics-overview,
.filters,
.analysis-section,
.knowledge-section {
  display: flex;
  flex-direction: column;
}
.analytics-overview {
  padding-top: 12rpx;
}
.filters,
.analysis-section {
  padding: 24rpx 0;
  gap: 14rpx;
  border-bottom: 1rpx solid var(--med-divider);
}
.section-title {
  display: block;
  color: var(--med-ink);
  font-size: 30rpx;
  font-weight: 750;
}
.muted,
.scope-copy {
  color: var(--med-muted);
  font-size: 22rpx;
  line-height: 1.5;
}
.scope-copy {
  padding: 18rpx 0 6rpx;
}
.dates,
.knowledge-metrics,
.knowledge-row {
  display: flex;
  align-items: center;
  gap: 12rpx;
}
.dates input {
  min-width: 0;
  min-height: 44px;
  padding: 0 12rpx;
  flex: 1;
  box-sizing: border-box;
  border: 1rpx solid var(--med-border);
}
.secondary {
  min-height: 44px;
  margin: 0;
  color: var(--med-clinical);
  background: var(--med-wash);
}
.metrics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  border-bottom: 1rpx solid var(--med-border);
}
.metric {
  display: flex;
  padding: 24rpx 14rpx;
  flex-direction: column;
  gap: 8rpx;
}
.metric:nth-child(odd) {
  border-right: 1rpx solid var(--med-divider);
}
.metric:nth-child(-n + 2) {
  border-bottom: 1rpx solid var(--med-divider);
}
.value {
  color: var(--med-brand);
  font-size: 40rpx;
  font-weight: 800;
}
.dimension {
  display: flex;
  padding: 12rpx 0;
  justify-content: space-between;
  flex-wrap: wrap;
}
.bar {
  width: 100%;
  height: 8rpx;
  margin-top: 8rpx;
  background: var(--med-divider);
}
.bar view {
  height: 100%;
  background: var(--med-clinical);
}
.link-row {
  display: flex;
  min-height: 44px;
  margin: 0;
  padding: 14rpx 0;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  color: var(--med-text);
  background: transparent;
  border-top: 1rpx solid var(--med-divider);
  border-radius: 0;
  text-align: left;
}
.weak {
  display: block;
}
.knowledge-section {
  gap: 14rpx;
}
.knowledge-metrics {
  flex-wrap: wrap;
}
.knowledge-row {
  min-height: 44px;
  justify-content: space-between;
  border-top: 1rpx solid var(--med-divider);
}
@media screen and (min-width: 768px) {
  .filters {
    display: grid;
    grid-template-columns: minmax(220px, 1fr) minmax(320px, 1fr) auto;
    align-items: center;
  }
  .metrics {
    grid-template-columns: repeat(4, 1fr);
  }
  .metric:nth-child(n) {
    border-right: 1rpx solid var(--med-divider);
    border-bottom: 0;
  }
  .metric:last-child {
    border-right: 0;
  }
}
@media screen and (min-width: 600px) {
  .section-title {
    font-size: 18px;
  }
  .muted,
  .scope-copy,
  .knowledge-metrics,
  .knowledge-row {
    font-size: 13px;
  }
  .value {
    font-size: 28px;
  }
  .link-row,
  .dimension,
  .weak {
    font-size: 14px;
  }
}
</style>
