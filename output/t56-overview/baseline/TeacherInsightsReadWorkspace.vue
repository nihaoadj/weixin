<template>
  <view class="insights-read">
    <MedState
      v-if="loading"
      variant="loading"
      icon="report"
      title="正在读取学情"
      description="请稍候。"
    />
    <template v-else>
      <view
        v-if="panel === 'overview'"
        class="insights-card overview-card"
      >
        <view class="section-heading"><text class="section-title">学习概况</text></view>
        <MedState
          v-if="errors.primary"
          variant="error"
          icon="retry"
          title="概况读取失败"
          :description="errors.primary"
          action-label="重试"
          @action="refresh"
        />
        <template v-else-if="overview">
          <view class="overview-metrics">
            <view class="overview-completion">
              <view
                class="completion-ring"
                :style="completionRingStyle"
                ><view class="completion-ring__inner" /><template
                  v-if="
                    overview.cohort.completionRate !== null &&
                    overview.cohort.completionRate > 0 &&
                    overview.cohort.completionRate < 100
                  "
                  ><view class="completion-ring__cap" /><view
                    class="completion-ring__cap-track"
                    :style="{ transform: `rotate(${overview.cohort.completionRate * 3.6}deg)` }"
                    ><view class="completion-ring__cap completion-ring__cap--end" /></view></template
              ></view>
              <text
                class="completion-value"
                :class="{ 'completion-value--empty': overview.cohort.completionRate === null }"
                >{{ percent(overview.cohort.completionRate) }}</text
              >
              <view class="completion-label"><text>发布批次</text><text>测试完成率</text></view>
            </view>
            <view class="overview-average"
              ><image
                src="/static/insights-active.svg"
                class="average-icon"
                mode="aspectFit"
              /><view
                ><text
                  class="average-value"
                  :class="{ 'average-value--empty': overview.periodResults.averageScore === null }"
                  >{{
                    overview.periodResults.averageScore === null
                      ? '暂无结果'
                      : number(overview.periodResults.averageScore)
                  }}<text
                    v-if="overview.periodResults.averageScore !== null"
                    class="average-unit"
                    >分</text
                  ></text
                ><text class="average-label">区间平均分</text></view
              ></view
            >
          </view>
          <view class="overview-counts"
            ><view class="count-pill"
              ><image
                src="/static/pbl-reference-document.svg"
                mode="aspectFit"
              /><text>已发布</text><text class="count-number">{{ overview.cohort.publishedRoutes }}</text
              ><text>条路线</text></view
            ><view class="count-pill count-pill--done"
              ><image
                src="/static/pbl-reference-done.svg"
                mode="aspectFit"
              /><text>已完成</text><text class="count-number">{{ overview.cohort.completedTests }}</text
              ><text>份测试</text></view
            ></view
          >
        </template>
      </view>
      <view
        v-if="panel === 'overview' || panel === 'knowledge'"
        class="insights-card"
      >
        <view class="section-heading"
          ><text class="section-title">知识点作答表现</text
          ><button
            v-if="panel === 'overview'"
            class="see-all"
            @click="$emit('selectPanel', 'knowledge')"
          >
            查看全部 <text>›</text>
          </button></view
        >
        <MedState
          v-if="errors.knowledge"
          variant="error"
          icon="retry"
          title="作答统计读取失败"
          :description="errors.knowledge"
          action-label="重试"
          @action="refresh"
        />
        <TeacherInsightsKnowledgeTable
          v-else-if="knowledge?.items.length"
          :items="knowledgeRows"
          :label="pointLabel"
          :preview="panel === 'overview'"
        />
        <MedState
          v-else
          variant="empty"
          icon="book"
          title="暂无知识点作答统计"
          description="学生完成测试后形成作答统计。"
        />
      </view>
      <view
        v-if="panel === 'knowledge'"
        class="insights-card"
      >
        <view class="section-heading"><text class="section-title">研讨诊断中的薄弱点</text></view>
        <MedState
          v-if="errors.diagnoses"
          variant="error"
          icon="retry"
          title="诊断汇总读取失败"
          :description="errors.diagnoses"
          action-label="重试"
          @action="refresh"
        />
        <template v-else-if="diagnoses">
          <MedState
            v-if="!findingGroups.length"
            variant="empty"
            icon="report"
            title="暂无已记录的薄弱点"
            description="当前范围内没有知识缺口或推理问题。"
          />
          <view
            v-for="group in findingGroups"
            :key="group.key"
            class="finding"
            :class="{ 'finding--reasoning': group.kind === 'reasoning' }"
          >
            <button
              class="finding__summary"
              :aria-expanded="expandedFinding === group.key"
              @click="toggleFinding(group)"
            >
              <view class="finding__icon"
                ><image
                  :src="
                    group.kind === 'knowledge' ? '/static/pbl-reference-document.svg' : '/static/insights-reasoning.svg'
                  "
                  mode="aspectFit"
              /></view>
              <view class="finding__text"
                ><text class="finding__title"
                  ><text class="finding__kind">{{ group.kind === 'knowledge' ? '知识缺口' : '推理问题' }}</text> ·
                  {{ findingLabel(group.code, group.kind) }} · {{ group.studentCount }}名学生</text
                ><text class="finding__description">{{
                  expandedFinding === group.key ? '收起学生诊断摘要' : '查看学生诊断摘要与具体问题'
                }}</text></view
              >
            </button>
            <view
              v-if="expandedFinding === group.key"
              class="finding__details"
            >
              <text
                v-if="findingLoading"
                class="muted"
                >正在读取诊断摘要…</text
              >
              <MedState
                v-else-if="findingError"
                variant="error"
                icon="retry"
                title="诊断摘要读取失败"
                :description="findingError"
                action-label="重试"
                @action="loadFinding(group)"
              />
              <template v-else
                ><view
                  v-for="item in findingDetails(group)"
                  :key="`${item.participationId}`"
                  class="finding__student"
                  ><button @click="$emit('openStudent', { studentId: item.studentId, classId: item.classId })">
                    {{ item.studentName }} · {{ item.className }} <text>›</text></button
                  ><text>{{ item.summary }}</text></view
                ><text
                  v-if="!findingDetails(group).length"
                  class="muted"
                  >当前没有可读取的摘要。</text
                ></template
              >
            </view>
          </view>
        </template>
      </view>
      <view
        v-if="panel === 'overview' || panel === 'students' || panel === 'progress'"
        class="insights-card student-card"
        :class="{ 'student-card--list-only': studentListOnly }"
      >
        <view
          v-if="!studentListOnly"
          class="section-heading"
          ><text class="section-title">{{ panel === 'overview' ? '得分较低学生' : '学生学习记录' }}</text
          ><button
            v-if="panel === 'overview'"
            class="see-all"
            @click="$emit('selectPanel', 'students')"
          >
            查看全部 <text>›</text>
          </button></view
        >
        <MedState
          v-if="errors.students"
          variant="error"
          icon="retry"
          title="学生记录读取失败"
          :description="errors.students"
          action-label="重试"
          @action="refresh"
        />
        <template v-else
          ><TeacherInsightsStudentRow
            v-for="student in visibleStudents"
            :key="student.studentId"
            :student="student"
            :record-layout="studentListOnly"
            @open="openStudent" /><MedState
            v-if="!visibleStudents.length"
            variant="empty"
            icon="report"
            :title="panel === 'overview' ? '暂无可比较的成绩' : '当前范围没有学生记录'"
            :description="panel === 'overview' ? '学生完成测试后展示得分较低的学生。' : '可调整班级、课堂或统计日期。'"
        /></template>
        <template v-if="panel !== 'overview' && students && nextOffset < students.total"
          ><text
            v-if="moreError"
            class="load-error"
            >{{ moreError }}</text
          ><button
            class="load-more"
            :disabled="moreLoading"
            @click="loadMore"
          >
            {{ moreLoading ? '正在加载…' : moreError ? '重试加载更多' : '加载更多学生' }}
          </button></template
        >
      </view>
    </template>
    <view
      v-if="classChoice"
      class="class-choice-mask"
      @click="classChoice = undefined"
      ><view
        class="class-choice"
        @click.stop
        ><text class="section-title">选择学生所属班级</text><text class="muted">{{ classChoice.studentName }}</text
        ><button
          v-for="id in classChoice.classIds"
          :key="id"
          @click="chooseClass(id)"
        >
          {{ classes.find((item) => item.id === id)?.name || `班级 ${id}` }}</button
        ><button @click="classChoice = undefined">取消</button></view
      ></view
    >
  </view>
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import MedState from '@/components/ui/MedState.vue'
import TeacherInsightsStudentRow from './TeacherInsightsStudentRow.vue'
import TeacherInsightsKnowledgeTable from './TeacherInsightsKnowledgeTable.vue'
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
  type TeacherInsightsStudent,
  type TeacherInsightsKnowledgePage,
  type TeacherInsightsDiagnosisPage,
  type TeacherInsightsDiagnosis,
  type TeacherInsightsScope,
} from '@/features/analytics/public'
import type { TeacherInsightsPanel } from '@/platform/navigation/teacher'
const props = defineProps<{
  filters: TeacherInsightsFilters
  panel: TeacherInsightsPanel
  studentListOnly?: boolean
  classes: Array<{ id: number; name: string }>
}>()
const emit = defineEmits<{
  openStudent: [context: { studentId: number; classId: number }]
  selectPanel: [panel: TeacherInsightsPanel]
  scope: [scope: TeacherInsightsScope]
}>()
const overview = ref<TeacherInsightsOverview>()
const students = ref<TeacherInsightsStudentPage>()
const knowledge = ref<TeacherInsightsKnowledgePage>()
const diagnoses = ref<TeacherInsightsDiagnosisPage>()
const catalog = ref<KnowledgePoint[]>([])
const errors = ref<Partial<Record<'primary' | 'knowledge' | 'students' | 'diagnoses', string>>>({})
const loading = ref(false)
const moreLoading = ref(false)
const moreError = ref('')
const classChoice = ref<TeacherInsightsStudent>()
const expandedFinding = ref('')
const findingLoading = ref(false)
const findingError = ref('')
const allDiagnoses = ref<TeacherInsightsDiagnosis[]>()
let request = 0
let findingRequest = 0
let nextOffset = 0
const number = (value: number) => String(Math.round(value * 10) / 10)
const percent = (value: number | null) => (value === null ? '暂无样本' : `${number(value)}%`)
const pointLabel = (code: string) => learningGoalLabel(code, catalog.value)
const visibleStudents = computed(() => {
  const items = students.value?.items || []
  return props.panel === 'overview'
    ? items
        .filter((s) => s.periodResults.averageScore !== null)
        .slice()
        .sort((a, b) => a.periodResults.averageScore! - b.periodResults.averageScore! || a.studentId - b.studentId)
        .slice(0, 3)
    : items
})
const knowledgeRows = computed(() => {
  const weakest = (item: TeacherInsightsKnowledgePage['items'][number]) =>
    Math.min(item.accuracyRate ?? Infinity, item.shortAnswerScoreRate ?? Infinity)
  const items = (knowledge.value?.items || [])
    .slice()
    .sort((a, b) => weakest(a) - weakest(b) || a.pointCode.localeCompare(b.pointCode))
  return props.panel === 'overview' ? items.slice(0, 3) : items
})
const completionRingStyle = computed(() => {
  const rate = overview.value?.cohort.completionRate ?? 0
  return { background: `conic-gradient(#00dbe2 0 ${rate * 0.55}%, #00bce7 ${rate}%, #ededed ${rate}% 100%)` }
})

type Group = { key: string; kind: 'knowledge' | 'reasoning'; code: string; studentCount: number }
const findingGroups = computed<Group[]>(() => [
  ...(diagnoses.value?.knowledgeGaps || []).map((g) => ({
    ...g,
    key: `knowledge:${g.code}`,
    kind: 'knowledge' as const,
  })),
  ...(diagnoses.value?.reasoningIssues || []).map((g) => ({
    ...g,
    key: `reasoning:${g.code}`,
    kind: 'reasoning' as const,
  })),
])
const reasoningLabels: Record<string, string> = {
  information_gathering: '信息搜集',
  problem_representation: '问题表征',
  differential_diagnosis: '鉴别诊断',
  evidence_reasoning: '证据推理',
  test_selection: '检查选择',
  management_safety: '处置安全',
}
const findingLabel = (code: string, kind: 'knowledge' | 'reasoning') =>
  kind === 'knowledge' ? pointLabel(code) : reasoningLabels[code] || code
function findingDetails(group: Group) {
  return (allDiagnoses.value || []).flatMap((item) => {
    const findings = group.kind === 'knowledge' ? item.knowledgeGaps : item.reasoningIssues
    return findings.filter((f) => f.code === group.code).map((f) => ({ ...item, summary: f.summary }))
  })
}
function openStudent(student: TeacherInsightsStudent) {
  if (props.filters.classId !== undefined && student.classIds.includes(props.filters.classId))
    emit('openStudent', { studentId: student.studentId, classId: props.filters.classId })
  else if (student.classIds.length === 1)
    emit('openStudent', { studentId: student.studentId, classId: student.classIds[0]! })
  else if (student.classIds.length > 1) classChoice.value = student
}
function chooseClass(classId: number) {
  const student = classChoice.value
  if (!student?.classIds.includes(classId)) return
  emit('openStudent', { studentId: student.studentId, classId })
  classChoice.value = undefined
}
async function refresh() {
  const token = ++request
  findingRequest += 1
  const actor = getSession()
  overview.value = undefined
  students.value = undefined
  knowledge.value = undefined
  diagnoses.value = undefined
  errors.value = {}
  moreError.value = ''
  moreLoading.value = false
  nextOffset = 0
  classChoice.value = undefined
  expandedFinding.value = ''
  allDiagnoses.value = undefined
  findingLoading.value = false
  if (actor?.role !== 'teacher') {
    loading.value = false
    return
  }
  loading.value = true
  const current = () => token === request && getSession()?.openid === actor.openid && getSession()?.role === 'teacher'
  const filters = { ...props.filters }
  async function receive<T>(key: keyof typeof errors.value, promise: Promise<T>, apply: (value: T) => void) {
    try {
      const value = await promise
      if (current()) apply(value)
    } catch (reason) {
      if (current()) errors.value[key] = reason instanceof Error ? reason.message : '请稍后重试。'
    }
  }
  function reportScope(scope: TeacherInsightsScope) {
    emit('scope', scope)
  }
  async function readStudents() {
    const page = await getTeacherInsightsStudents(filters, 20, 0)
    if (props.panel !== 'overview') return page
    const items = [...page.items]
    let offset = page.offset + page.items.length
    while (offset < page.total && current()) {
      const next = await getTeacherInsightsStudents(filters, 100, offset)
      if (!next.items.length) throw new Error('学生列表未完整读取，请重试。')
      items.push(...next.items)
      offset += next.items.length
    }
    return { ...page, items: [...new Map(items.map((s) => [s.studentId, s])).values()] }
  }
  const queries: Promise<void>[] = []
  if (props.panel === 'overview')
    queries.push(
      receive('primary', getTeacherInsightsOverview(filters), (value) => {
        overview.value = value
        reportScope(value.scope)
      }),
    )
  if (props.panel === 'overview' || props.panel === 'students' || props.panel === 'progress')
    queries.push(
      receive('students', readStudents(), (value) => {
        students.value = value
        nextOffset = value.offset + value.items.length
        reportScope(value.scope)
      }),
    )
  if (props.panel === 'overview' || props.panel === 'knowledge')
    queries.push(
      receive('knowledge', getTeacherInsightsKnowledge(filters), (value) => {
        knowledge.value = value
        reportScope(value.scope)
      }),
    )
  if (props.panel === 'knowledge')
    queries.push(
      receive('diagnoses', getTeacherInsightsDiagnostics(filters, 20, 0), (value) => {
        diagnoses.value = value
        reportScope(value.scope)
      }),
    )
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
async function loadMore() {
  if (moreLoading.value || !students.value || nextOffset >= students.value.total) return
  const token = request
  const actor = getSession()
  const filters = { ...props.filters }
  moreLoading.value = true
  moreError.value = ''
  const current = () =>
    token === request &&
    actor?.role === 'teacher' &&
    getSession()?.openid === actor.openid &&
    getSession()?.role === 'teacher'
  try {
    const page = await getTeacherInsightsStudents(filters, 20, nextOffset)
    if (!current() || !students.value) return
    if (!page.items.length && nextOffset < page.total) throw new Error('暂未读取到后续学生，请重试。')
    nextOffset = page.offset + page.items.length
    students.value = {
      ...page,
      items: [...new Map([...students.value.items, ...page.items].map((s) => [s.studentId, s])).values()],
    }
  } catch (reason) {
    if (current()) moreError.value = reason instanceof Error ? reason.message : '加载失败，请重试。'
  } finally {
    if (current()) moreLoading.value = false
  }
}
async function toggleFinding(group: Group) {
  if (expandedFinding.value === group.key) {
    expandedFinding.value = ''
    return
  }
  expandedFinding.value = group.key
  if (!allDiagnoses.value) await loadFinding(group)
}
async function loadFinding(group: Group) {
  const token = ++findingRequest
  const scopeToken = request
  const actor = getSession()
  const filters = { ...props.filters }
  expandedFinding.value = group.key
  findingLoading.value = true
  findingError.value = ''
  const current = () =>
    token === findingRequest &&
    scopeToken === request &&
    actor?.role === 'teacher' &&
    getSession()?.openid === actor.openid &&
    getSession()?.role === 'teacher'
  try {
    const items = [...(diagnoses.value?.items || [])]
    let offset = items.length
    while (offset < (diagnoses.value?.total || 0) && current()) {
      const page = await getTeacherInsightsDiagnostics(filters, 100, offset)
      if (!page.items.length) throw new Error('诊断摘要未完整读取，请重试。')
      items.push(...page.items)
      offset += page.items.length
    }
    if (current()) allDiagnoses.value = [...new Map(items.map((item) => [item.participationId, item])).values()]
  } catch (reason) {
    if (current()) findingError.value = reason instanceof Error ? reason.message : '请稍后重试。'
  } finally {
    if (current()) findingLoading.value = false
  }
}
watch(
  () => [props.panel, props.filters.classId, props.filters.sessionId, props.filters.dateFrom, props.filters.dateTo],
  () => {
    void refresh()
  },
)
onMounted(refresh)
onBeforeUnmount(() => {
  request += 1
  findingRequest += 1
})
defineExpose({ refresh })
</script>
<style scoped>
.insights-read {
  display: flex;
  flex-direction: column;
  gap: 18rpx;
  color: var(--insights-ink, #0000b4);
  font-size: 24rpx;
  line-height: 1.5;
}
.insights-card {
  padding: 16rpx;
  background: #fff;
  border-radius: 16rpx;
}
.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12rpx;
  margin-bottom: 14rpx;
  min-height: 42rpx;
}
.section-title {
  display: flex;
  align-items: center;
  color: var(--insights-ink, #0000b4);
  font-size: 32rpx;
  line-height: 1.4;
  font-weight: 700;
}
.section-heading .section-title::before {
  content: '';
  width: 12rpx;
  height: 32rpx;
  margin-right: 12rpx;
  border-radius: 6rpx;
  background: linear-gradient(#04e7dc, #00b5e6);
  flex: none;
}
.see-all {
  flex: none;
  display: flex;
  align-items: center;
  gap: 6rpx;
  min-height: 44px;
  margin: -10rpx 0;
  padding: 0;
  background: transparent;
  color: #00bdc9;
  font-size: 22rpx;
  line-height: 1.4;
}
.see-all::after,
.load-more::after,
.finding__summary::after,
.finding__student button::after,
.class-choice button::after {
  border: 0;
}
.see-all > text {
  font-size: 36rpx;
}
.overview-metrics {
  display: flex;
  align-items: center;
  padding: 2rpx 8rpx 12rpx;
}
.overview-completion {
  position: relative;
  display: flex;
  align-items: center;
  gap: 14rpx;
  flex: 1.1;
  min-width: 0;
}
.completion-ring {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  flex: none;
  width: 148rpx;
  height: 148rpx;
}
.completion-ring__inner {
  width: 80%;
  height: 80%;
  border-radius: 50%;
  background: #fff;
}
.completion-ring__cap-track {
  position: absolute;
  inset: 0;
}
.completion-ring__cap {
  position: absolute;
  top: 0;
  left: 45%;
  width: 10%;
  height: 10%;
  border-radius: 50%;
  background: #00dbe2;
}
.completion-ring__cap--end {
  background: #00bce7;
}
.completion-value {
  position: absolute;
  width: 148rpx;
  text-align: center;
  font-size: 38rpx;
  font-weight: 750;
}
.completion-value--empty {
  font-size: 22rpx;
}
.completion-label {
  display: flex;
  flex-direction: column;
  font-size: 25rpx;
  font-weight: 650;
  white-space: pre-line;
}
.overview-average {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 18rpx;
  min-height: 140rpx;
  margin-left: 16rpx;
  padding-left: 18rpx;
  border-left: 2rpx solid #52bbff;
}
.average-icon {
  flex: none;
  width: 68rpx;
  height: 68rpx;
  padding: 16rpx;
  border-radius: 50%;
  background: #e8f7ff;
}
.average-value,
.average-label {
  display: block;
}
.average-value {
  font-size: 64rpx;
  font-weight: 700;
  white-space: nowrap;
  line-height: 1.1;
}
.average-value--empty {
  font-size: 28rpx;
}
.average-unit {
  font-size: 34rpx;
  margin-left: 6rpx;
}
.average-label {
  font-size: 24rpx;
  margin-top: 8rpx;
}
.overview-counts {
  display: flex;
  gap: 10rpx;
}
.count-pill {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  gap: 10rpx;
  min-width: 0;
  min-height: 66rpx;
  border: 1rpx solid #bee5ff;
  background: #eef8ff;
  border-radius: 14rpx;
  font-size: 21rpx;
}
.count-pill image {
  width: 38rpx;
  height: 38rpx;
  flex: none;
}
.count-pill--done {
  background: #edfcfc;
  border-color: #aff4ee;
}
.count-number {
  font-size: 48rpx;
  line-height: 1.2;
  font-weight: 700;
}
.count-pill--done .count-number {
  color: #009fae;
}
.student-card .section-heading {
  margin-bottom: 0;
}
.student-card--list-only {
  padding: 0 16rpx 8rpx;
  border-radius: 0;
}
.finding {
  margin-top: 14rpx;
  border: 1rpx solid #b7eff5;
  border-radius: 12rpx;
  background: #edfbfd;
}
.finding--reasoning {
  border-color: #ffe1ca;
  background: #fff5eb;
}
.finding__summary {
  display: flex;
  align-items: flex-start;
  gap: 20rpx;
  width: 100%;
  margin: 0;
  padding: 16rpx 14rpx;
  border-radius: 12rpx;
  background: transparent;
  text-align: left;
  line-height: 1.5;
}
.finding__icon {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 66rpx;
  height: 66rpx;
  border-radius: 50%;
  background: #dcfaff;
}
.finding__icon image {
  width: 42rpx;
  height: 42rpx;
}
.finding--reasoning .finding__icon {
  background: #ffebdc;
}
.finding__text {
  min-width: 0;
  padding-top: 8rpx;
}
.finding__title {
  display: block;
  font-size: 25rpx;
  font-weight: 650;
  color: var(--insights-ink, #0000b4);
}
.finding__kind {
  color: #00bdc9;
}
.finding--reasoning .finding__kind {
  color: #ff531d;
}
.finding__description {
  display: block;
  margin-top: 10rpx;
  font-size: 23rpx;
  color: var(--insights-ink, #0000b4);
}
.finding__details {
  padding: 0 16rpx 16rpx;
}
.finding__student {
  padding: 14rpx 0;
  border-top: 1rpx solid #d7ebf3;
}
.finding__student button {
  min-height: 44px;
  margin: 0;
  padding: 0;
  background: transparent;
  color: #148dff;
  text-align: left;
  font-size: 24rpx;
}
.finding__student > text {
  display: block;
  color: var(--insights-ink, #0000b4);
  font-size: 24rpx;
  line-height: 1.6;
}
.muted {
  color: #667ca8;
  font-size: 24rpx;
}
.load-more {
  min-height: 44px;
  margin: 12rpx 0 0;
  border: 1rpx solid #bee5ff;
  border-radius: 12rpx;
  background: #f1faff;
  color: #148dff;
  font-size: 24rpx;
}
.load-error {
  display: block;
  color: #a34d2a;
  margin-top: 12rpx;
}
.class-choice-mask {
  position: fixed;
  inset: 0;
  z-index: 40;
  display: flex;
  align-items: flex-end;
  background: rgba(10, 30, 70, 0.25);
}
.class-choice {
  width: 100%;
  max-height: 70vh;
  overflow-y: auto;
  padding: 28rpx 28rpx calc(28rpx + env(safe-area-inset-bottom));
  border-radius: 24rpx 24rpx 0 0;
  background: #fff;
}
.class-choice button {
  width: 100%;
  margin: 16rpx 0 0;
  min-height: 44px;
  background: #eff9ff;
  color: #0000b4;
  font-size: 26rpx;
}
@media screen and (max-width: 390px) {
  .completion-ring,
  .completion-value {
    width: 128rpx;
  }
  .completion-ring {
    height: 128rpx;
  }
  .completion-label {
    font-size: 23rpx;
  }
  .overview-average {
    gap: 10rpx;
    padding-left: 12rpx;
    margin-left: 10rpx;
  }
  .average-icon {
    width: 44rpx;
    height: 44rpx;
    padding: 14rpx;
  }
  .count-pill {
    gap: 6rpx;
    font-size: 20rpx;
  }
}
</style>
