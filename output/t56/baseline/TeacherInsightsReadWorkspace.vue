<template>
  <view class="insights-read">
    <text class="basis">{{ basisText }}</text>
    <MedState
      v-if="loading"
      variant="loading"
      icon="report"
      title="正在读取学情"
      description="只统计当前教师有权查看的课堂事实。"
    />
    <template v-else>
      <MedState
        v-if="errors.primary"
        variant="error"
        icon="retry"
        title="学情读取失败"
        :description="errors.primary"
        action-label="重试"
        @action="refresh"
      />
      <view
        v-if="panel === 'overview' && overview"
        class="facts"
      >
        <text class="scope-note">{{ scopeLabel(overview.scope) }}</text>
        <text>发布批次路线 {{ overview.cohort.publishedRoutes }} 条</text>
        <text
          >该批次已完成测试 {{ overview.cohort.completedTests }} 份 · 完成率
          {{ percent(overview.cohort.completionRate) }}</text
        >
        <text>该批次判分中 {{ overview.cohort.gradingTests }} 份</text>
        <text
          >区间内完成测试 {{ overview.periodResults.completedTests }} 份 · 平均分
          {{ score(overview.periodResults.averageScore) }}</text
        >
        <text>区间内有效完成诊断 {{ overview.diagnosisCount }} 份 · 涉及学生 {{ overview.studentCount }} 人</text>
        <text class="muted">无完成结果时平均分显示“暂无结果”；真实 0 分保留为 0。</text>
      </view>
      <template v-if="(panel === 'students' || panel === 'progress') && students">
        <text class="scope-note">{{ scopeLabel(students.scope) }}</text>
        <MedState
          v-if="!students.items.length"
          variant="empty"
          icon="report"
          title="当前范围没有学生事实"
          description="可调整班级或日期范围。"
        />
        <view
          v-for="student in students.items"
          :key="student.studentId"
          class="record"
        >
          <text class="record-title">{{ student.studentName }}</text>
          <template v-if="panel === 'progress'">
            <text v-if="student.discussionProgress && student.discussionProgress.participated > 0">
              本区间参与研讨 {{ student.discussionProgress.participated }} 次 · 进行中
              {{ student.discussionProgress.active }} 次 · 已完成 {{ student.discussionProgress.completed }} 次
            </text>
            <text v-else>{{ student.discussionProgress ? '本区间无参与记录' : '研讨进度未提供' }}</text>
          </template>
          <text v-if="panel === 'progress'"
            >发布批次 {{ student.cohort.publishedRoutes }} 条路线 · 完成率
            {{ percent(student.cohort.completionRate) }} · 判分中 {{ student.cohort.gradingTests }}</text
          >
          <text v-else
            >区间内完成测试 {{ student.periodResults.completedTests }} 份 · 平均分
            {{ score(student.periodResults.averageScore) }} · 有效诊断 {{ student.diagnosisCount }} 份</text
          >
          <button
            v-for="id in student.classIds"
            :key="id"
            class="detail-action"
            @click="$emit('openStudent', { studentId: student.studentId, classId: id })"
          >
            查看 {{ classes.find((item) => item.id === id)?.name || `班级 ${id}` }} 的学生详情
          </button>
        </view>
        <TeacherPager
          :total="students.total"
          :offset="offset"
          @previous="paginate(-20)"
          @next="paginate(20)"
        />
      </template>
      <template v-if="panel === 'knowledge'">
        <template v-if="knowledge">
          <text class="scope-note"
            >{{ scopeLabel(knowledge.scope) }} · 完成结果样本 {{ knowledge.resultCount }} 份</text
          >
          <MedState
            v-if="!knowledge.items.length"
            variant="empty"
            icon="book"
            title="暂无知识点作答统计"
            description="学生完成测试后才形成结果统计。"
          />
          <view
            v-for="item in knowledge.items"
            :key="item.pointCode"
            class="record"
          >
            <text class="record-title">{{ pointLabel(item.pointCode) }}</text>
            <text
              >客观题 {{ item.correctCount }}/{{ item.objectiveCount }} 正确 · 正确率
              {{ percent(item.accuracyRate) }}</text
            >
            <text
              >简答 {{ item.shortAnswerCount }} 题 · {{ item.pointsAwarded }}/{{ item.pointsPossible }} 分 · 得分率
              {{ percent(item.shortAnswerScoreRate) }}</text
            >
            <text
              v-if="item.invalidObjectiveCount || item.invalidShortAnswerCount"
              class="muted"
              >无效客观题 {{ item.invalidObjectiveCount }}、无效简答
              {{ item.invalidShortAnswerCount }}，未计入分母。</text
            >
          </view>
          <text class="muted">多选按选项集合完全匹配计算；简答得分率与客观题正确率分别统计。</text>
        </template>
        <MedState
          v-if="errors.diagnoses"
          variant="error"
          icon="retry"
          title="诊断汇总读取失败"
          :description="errors.diagnoses"
          action-label="重试"
          @action="refresh"
        />
        <template v-if="diagnoses">
          <text class="record-title">固定诊断中的知识缺口与推理问题</text>
          <text class="scope-note">按研讨完成时间 · 有效冻结诊断 {{ diagnoses.total }} 份</text>
          <text
            v-if="!diagnoses.knowledgeGaps.length && !diagnoses.reasoningIssues.length"
            class="muted"
            >当前范围没有已记录的知识缺口或推理问题。</text
          >
          <view
            v-for="group in diagnoses.knowledgeGaps"
            :key="`knowledge:${group.code}`"
            class="record"
            ><text>知识缺口 · {{ findingLabel(group.code, 'knowledge') }}</text
            ><text class="muted">{{ group.studentCount }} 名学生 · {{ group.diagnosisCount }} 份诊断</text></view
          >
          <view
            v-for="group in diagnoses.reasoningIssues"
            :key="`reasoning:${group.code}`"
            class="record"
            ><text>推理问题 · {{ findingLabel(group.code, 'reasoning') }}</text
            ><text class="muted">{{ group.studentCount }} 名学生 · {{ group.diagnosisCount }} 份诊断</text></view
          >
        </template>
      </template>
    </template>
  </view>
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import MedState from '@/components/ui/MedState.vue'
import TeacherPager from '@/components/teacher/TeacherPager.vue'
import { getSession } from '@/features/identity/public'
import { getKnowledgeCatalog, learningGoalLabel, type KnowledgePoint } from '@/features/learning/public'
import {
  getTeacherInsightsOverview,
  getTeacherInsightsStudents,
  getTeacherInsightsKnowledge,
  getTeacherInsightsDiagnostics,
  type TeacherInsightsFilters,
  type TeacherInsightsOverview,
  type TeacherInsightsStudentPage,
  type TeacherInsightsKnowledgePage,
  type TeacherInsightsDiagnosisPage,
  type TeacherInsightsScope,
} from '@/features/analytics/public'
import type { TeacherInsightsPanel } from '@/platform/navigation/teacher'
const props = defineProps<{
  filters: TeacherInsightsFilters
  panel: TeacherInsightsPanel
  classes: Array<{ id: number; name: string }>
}>()
defineEmits<{ openStudent: [context: { studentId: number; classId: number }] }>()
const overview = ref<TeacherInsightsOverview>()
const students = ref<TeacherInsightsStudentPage>()
const knowledge = ref<TeacherInsightsKnowledgePage>()
const diagnoses = ref<TeacherInsightsDiagnosisPage>()
const catalog = ref<KnowledgePoint[]>([])
const errors = ref<{ primary?: string; diagnoses?: string }>({})
const loading = ref(false)
const offset = ref(0)
let request = 0
const basisText = computed(() =>
  props.panel === 'progress'
    ? '研讨按区间内开始参与的记录统计；路线按区间内发布批次统计。完成情况截至本次查询，两者不共用分母。'
    : props.panel === 'knowledge'
      ? '作答统计按测试完成时间；固定诊断按研讨完成时间。'
      : '发布批次进度与区间内完成成绩分别统计。',
)
const percent = (value: number | null) => (value === null ? '暂无样本' : `${value.toFixed(1)}%`)
const score = (value: number | null) => (value === null ? '暂无结果' : `${value.toFixed(1)} 分`)
const pointLabel = (code: string) => learningGoalLabel(code, catalog.value)
function scopeLabel(scope: TeacherInsightsScope) {
  return `${scope.className || '全部授权班级'} · ${scope.dateFrom} 至 ${scope.dateTo} · 上海时区`
}
function findingLabel(code: string, kind: 'knowledge' | 'reasoning') {
  const match = diagnoses.value?.items
    .flatMap((item) => (kind === 'knowledge' ? item.knowledgeGaps : item.reasoningIssues))
    .find((item) => item.code === code)
  return match?.summary || (kind === 'knowledge' ? pointLabel(code) : code)
}
async function refresh() {
  const token = ++request
  const actor = getSession()
  overview.value = undefined
  students.value = undefined
  knowledge.value = undefined
  diagnoses.value = undefined
  errors.value = {}
  if (actor?.role !== 'teacher') {
    loading.value = false
    return
  }
  loading.value = true
  const current = () => token === request && getSession()?.openid === actor.openid && getSession()?.role === 'teacher'
  async function receive<T>(key: 'primary' | 'diagnoses', promise: Promise<T>, apply: (value: T) => void) {
    try {
      const value = await promise
      if (current()) apply(value)
    } catch (reason) {
      if (current()) errors.value[key] = reason instanceof Error ? reason.message : '请稍后重试。'
    }
  }
  const filters = { ...props.filters }
  const queries: Promise<void>[] = []
  if (props.panel === 'overview')
    queries.push(
      receive('primary', getTeacherInsightsOverview(filters), (value) => {
        overview.value = value
      }),
    )
  else if (props.panel === 'progress' || props.panel === 'students')
    queries.push(
      receive('primary', getTeacherInsightsStudents(filters, 20, offset.value), (value) => {
        students.value = value
      }),
    )
  else {
    queries.push(
      receive('primary', getTeacherInsightsKnowledge(filters), (value) => {
        knowledge.value = value
      }),
    )
    queries.push(
      receive('diagnoses', getTeacherInsightsDiagnostics(filters, 20, 0), (value) => {
        diagnoses.value = value
      }),
    )
  }
  queries.push(
    getKnowledgeCatalog()
      .then((value) => {
        if (current()) catalog.value = value
      })
      .catch(() => {
        if (current()) catalog.value = []
      }),
  )
  await Promise.all(queries)
  if (current()) loading.value = false
}
function paginate(delta: number) {
  offset.value = Math.max(0, offset.value + delta)
  void refresh()
}
watch(
  () => [props.panel, props.filters.classId, props.filters.sessionId, props.filters.dateFrom, props.filters.dateTo],
  () => {
    offset.value = 0
    void refresh()
  },
)
onMounted(refresh)
onBeforeUnmount(() => {
  request += 1
})
defineExpose({ refresh })
</script>
<style scoped>
.insights-read,
.facts,
.record {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}
.insights-read {
  color: var(--med-text);
  font-size: 28rpx;
  line-height: 1.6;
}
.record {
  padding: 24rpx 0;
  border-bottom: 1rpx solid var(--med-divider);
}
.record-title {
  color: var(--med-ink);
  font-weight: 700;
}
.basis,
.scope-note,
.muted {
  color: var(--med-muted);
  font-size: 24rpx;
}
.detail-action {
  min-height: 44px;
  margin: 0;
  color: var(--med-clinical);
  background: var(--med-wash);
  font-size: 26rpx;
}
</style>
