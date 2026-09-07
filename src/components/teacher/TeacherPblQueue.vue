<template>
  <view class="pbl-workspace">
    <view
      v-if="error"
      class="notice"
      role="alert"
      >{{ error
      }}<button
        :disabled="busy"
        @click="refresh"
      >
        重新加载
      </button></view
    >
    <view
      v-if="loading"
      role="status"
      >正在加载课堂与诊断…</view
    >
    <view class="panel"
      ><text class="section-title">准备课堂</text
      ><view class="controls">
        <picker
          :range="classes"
          range-key="name"
          :value="classIndex"
          aria-label="选择班级"
          @change="changeClass"
          ><view class="select">{{ selectedClass?.name || '暂无班级' }} ▾</view></picker
        >
        <picker
          :range="topics"
          range-key="title"
          :value="topicIndex"
          aria-label="选择病理学主题"
          @change="changeTopic"
          ><view class="select">{{ topics[topicIndex]?.title || '选择主题' }} ▾</view></picker
        >
        <picker
          :range="availableCases"
          range-key="title"
          :value="caseIndex"
          aria-label="选择已审核病例"
          @change="caseIndex = Number($event.detail.value)"
          ><view class="select">{{ selectedCase?.title || '暂无已审核发布的本主题病例' }} ▾</view></picker
        > </view
      ><text class="muted">目标知识点（最多 3 项）</text>
      <checkbox-group
        class="goals"
        @change="goals = $event.detail.value"
        ><label
          v-for="point in topicPoints"
          :key="point.code"
          ><checkbox
            :value="point.code"
            :checked="goals.includes(point.code)"
            :disabled="goals.length >= 3 && !goals.includes(point.code)"
          />{{ point.title }}</label
        ></checkbox-group
      >
      <button
        class="primary"
        :disabled="busy || !selectedClass || !selectedCase || !goals.length || goals.length > 3"
        @click="create"
      >
        创建课堂
      </button></view
    >
    <view class="panel"
      ><text class="section-title">本班课堂</text
      ><text
        v-if="!sessions.length"
        class="muted"
        >还没有课堂，选择病例和学习目标后即可创建。</text
      >
      <view
        v-for="item in sessions"
        :key="item.id"
        class="session-row"
        ><view
          ><text>{{ item.caseContext?.title || topicName(item.topicCode) }}</text
          ><text class="muted"
            >{{ item.status === 'active' ? '进行中' : '已结束' }} · 学生阶段由系统自动推进</text
          ></view
        >
        <view class="phase-distribution">
          <text
            v-for="(label, phase) in phaseLabels"
            :key="phase"
            >{{ label }} {{ item.phaseCounts?.[phase] || 0 }}</text
          >
        </view>
        <button
          :disabled="busy"
          @click="showSummary(item)"
        >
          教学汇总</button
        ><button
          :disabled="busy || item.status === 'closed'"
          @click="close(item)"
        >
          {{ item.status === 'closed' ? '已关闭' : '关闭课堂' }}
        </button>
      </view>
    </view>
    <view
      v-if="summary"
      class="panel"
      ><text class="section-title">课堂学习汇总</text
      ><view class="stats"
        ><text>参与 {{ summary.participants }} 人</text><text>AI 诊断 {{ summary.diagnoses }} 次</text
        ><text>教师发布 {{ summary.published_suggestions }} 项</text
        ><text>任务完成 {{ summary.completed_tasks }}/{{ summary.tasks }}</text
        ><text>系统判定改善 {{ summary.improved }} 项</text
        ><text>自动轮次耗尽 {{ summary.automation_exhausted }} 项</text
        ><text
          >客观再测 {{ summary.objective_retest_count }} 次 ·
          {{
            summary.objective_retest_average == null ? '暂无成绩' : `${summary.objective_retest_average.toFixed(0)} 分`
          }}</text
        ></view
      ><text class="muted">教师查看阶段与逐项成绩；系统按固定阈值决定后续轮次。</text></view
    >
    <view class="panel"
      ><text class="section-title">诊断待办</text
      ><view class="controls">
        <picker
          :range="['全部课堂', ...sessions.map((s) => s.caseContext?.title || topicName(s.topicCode))]"
          :value="filterSession"
          aria-label="筛选课堂"
          @change="changeSessionFilter"
          ><view class="select"
            >{{ filterSession ? sessions[filterSession - 1]?.caseContext?.title || '已选择课堂' : '全部课堂' }} ▾</view
          ></picker
        >
        <picker
          :range="statusTitles"
          :value="filterStatus"
          aria-label="筛选处理状态"
          @change="changeStatusFilter"
          ><view class="select">{{ statusTitles[filterStatus] }} ▾</view></picker
        >
        <picker
          :range="['全部学生', ...students.map((s) => s.nickname)]"
          :value="filterStudent"
          aria-label="筛选学生"
          @change="changeStudentFilter"
          ><view class="select"
            >{{ filterStudent ? students[filterStudent - 1]?.nickname : '全部学生' }} ▾</view
          ></picker
        > </view
      ><text
        v-if="!items.length"
        class="muted"
        >暂无符合筛选条件的有效诊断。学生完成多轮讨论后，诊断会进入此队列。</text
      >
      <view
        v-for="item in items"
        :key="item.id"
        class="diagnostic"
        ><text class="section-title">{{ item.studentName }} · {{ item.className }}</text
        ><text class="muted"
          >{{ topicName(item.topicCode || '') }} · {{ item.sessionKind === 'student_initiated' ? '学生主动' : '教师课堂' }} · {{ item.interactionStyle === 'direct' ? '先直接解释' : '引导思考' }} · 会话 {{ item.sessionId }} · {{ formatTime(item.createdAt) }}</text
        >
        <text
          v-if="![3, 4].includes(item.schemaVersion || 0)"
          class="notice"
          >历史诊断只读，不纳入新版掌握统计。</text
        >
        <view
          v-for="gap in item.knowledgeGaps"
          :key="gap.id"
          class="finding"
          ><text>{{ pointName(gap.point_code) }}：{{ gap.summary }}</text
          ><text class="muted"
            >依据：{{ gap.evidence_summary }}（消息 {{ gap.evidence_message_ids.join('、') }}）</text
          ></view
        >
        <view
          v-for="issue in item.reasoningIssues"
          :key="issue.id"
          class="finding"
          ><text>推理问题：{{ issue.summary }}</text
          ><text class="muted">依据：{{ issue.evidence_summary }}</text
          ><text>建议：{{ issue.improvement }}</text></view
        >
        <button
          :disabled="busy"
          @click="history(item)"
        >
          查看诊断修订历史
        </button>
        <view
          v-if="histories[item.id || '']"
          class="muted"
          ><text
            v-for="revision in histories[item.id || '']"
            :key="revision.id"
            >修订 {{ revision.revision }}：{{
              revision.knowledgeGaps.map((g) => g.summary).join('；') || '历史分析'
            }}</text
          ></view
        >
        <view
          v-for="suggestion in item.recommendedQuestions"
          :key="suggestion.id"
          class="suggestion"
          ><text class="muted">{{ statusLabel(suggestion.status) }}</text
          ><input
            v-model="suggestion.title"
            aria-label="建议题标题"
            :disabled="!editable(suggestion, item)"
            :maxlength="200"
          /><textarea
            v-model="suggestion.prompt"
            aria-label="建议题内容"
            :disabled="!editable(suggestion, item)"
            :maxlength="2000"
          />
          <text class="muted">默认发布给 {{ item.studentName }}；可改为同班学生或全班。</text
          ><checkbox-group @change="targets[suggestion.id] = $event.detail.value.map(Number)"
            ><label
              v-for="student in students"
              :key="student.id"
              ><checkbox
                :value="String(student.id)"
                :checked="(targets[suggestion.id] || [Number(item.studentId)]).includes(student.id)"
                :disabled="!editable(suggestion, item) || wholeClass[suggestion.id]"
              />{{ student.nickname }}</label
            ></checkbox-group
          >
          <view class="controls"
            ><label
              ><switch
                :checked="wholeClass[suggestion.id] || false"
                :disabled="!editable(suggestion, item)"
                @change="wholeClass[suggestion.id] = switchValue($event)"
              />全班</label
            ><label
              v-if="item.sessionKind !== 'student_initiated'"
              ><switch
                :checked="caseRetry[suggestion.id] || false"
                :disabled="!editable(suggestion, item)"
                @change="caseRetry[suggestion.id] = switchValue($event)"
              />增加完整病例重练</label
            ></view
          >
          <view class="controls"
            ><button
              :disabled="busy || !editable(suggestion, item)"
              @click="save(suggestion)"
            >
              保存编辑</button
            ><button
              class="primary"
              :disabled="busy || !editable(suggestion, item)"
              @click="publish(suggestion)"
            >
              {{ suggestion.status === 'published' ? '已发布' : '采用并发布' }}</button
            ><button
              :disabled="busy || !editable(suggestion, item)"
              @click="reject(suggestion)"
            >
              拒绝
            </button></view
          >
        </view> </view
      ><view class="controls pagination"
        ><button
          :disabled="busy || offset === 0"
          @click="page(-1)"
        >
          上一页</button
        ><text>第 {{ Math.floor(offset / 20) + 1 }} 页 · 共 {{ total }} 条</text
        ><button
          :disabled="busy || offset + 20 >= total"
          @click="page(1)"
        >
          下一页
        </button></view
      ></view
    >
    <view class="panel"
      ><text class="section-title">学习结果数据</text
      ><text
        v-if="!results.length"
        class="muted"
        >采用建议并发布后，这里会显示学生的任务与结果。</text
      >
      <view
        v-for="plan in results"
        :key="plan.id"
        class="diagnostic"
        ><text
          >{{ students.find((s) => s.id === plan.student_id)?.nickname || `学生 ${plan.student_id}` }} · 课堂
          {{ plan.source_context.session_id }} · {{ verificationLabel(plan.verification_status) }}</text
        >
        <text class="muted"
          >第 {{ plan.current_cycle }}/{{ plan.max_cycles }} 轮 · 判定策略 {{ plan.decision_policy_version
          }}<template v-if="plan.automation_exhausted"> · 自动轮次已结束，需线下支持</template></text
        >
        <view
          v-for="task in plan.tasks"
          :key="task.id"
          class="finding"
          ><text
            >第 {{ task.cycle_number }} 轮 · {{ task.public_definition.prompt }} ·
            {{
              task.status === 'completed'
                ? '已完成'
                : task.status === 'inactive'
                  ? '未激活'
                  : task.status === 'skipped'
                    ? '已跳过'
                    : '待完成'
            }}</text
          ><text
            v-if="task.result"
            class="muted"
            >作答：{{
              task.result.answer.text ||
              (task.result.answer.selected_option == null
                ? '已记录'
                : `选项 ${task.result.answer.selected_option + 1}`)
            }}<template v-if="task.result.score != null"> · {{ task.result.score }} 分</template>；{{
              task.result.feedback
            }}</text
          ></view
        >
        <view
          v-if="plan.decision_basis.checks?.length"
          class="decision-grid"
        >
          <text
            v-for="check in plan.decision_basis.checks"
            :key="`${check.target_type}:${check.target_code}`"
            >{{ check.target_code }}：{{ check.passed ? '达标' : '未达标'
            }}<template v-if="check.threshold != null">
              · {{ check.score ?? '缺少成绩' }}/{{ check.threshold }}</template
            ></text
          >
        </view>
      </view>
    </view>
  </view>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  getTeacherClasses,
  getClassStudents,
  type TeacherClass,
  type TeacherStudent,
} from '@/features/classroom/public'
import { getGuidedCasesAsync } from '@/features/content/public'
import { getKnowledgeCatalog, type KnowledgePoint } from '@/features/learning/public'
import {
  adoptPblSuggestion,
  closePblSession,
  createPblSession,
  editPblSuggestion,
  getTeacherPblDiagnostics,
  getTeacherPblSessions,
  getPblSummary,
  getPblDiagnosticRevisions,
  getPblLearningResults,
  type PblDiagnostic,
  type PblSession,
  type PblSuggestion,
  type PblSummary,
  type PblPlan,
} from '@/features/pbl/public'
import type { Problem } from '@/types/domain'
const classes = ref<TeacherClass[]>([]),
  students = ref<TeacherStudent[]>([]),
  points = ref<KnowledgePoint[]>([]),
  cases = ref<Problem[]>([]),
  sessions = ref<PblSession[]>([]),
  items = ref<PblDiagnostic[]>([]),
  results = ref<PblPlan[]>([])
const classIndex = ref(0),
  topicIndex = ref(0),
  caseIndex = ref(0),
  goals = ref<string[]>([]),
  loading = ref(true),
  busy = ref(false),
  error = ref(''),
  total = ref(0),
  offset = ref(0),
  filterSession = ref(0),
  filterStatus = ref(0),
  filterStudent = ref(0),
  summary = ref<PblSummary>()
const targets = ref<Record<string, number[]>>({}),
  wholeClass = ref<Record<string, boolean>>({}),
  caseRetry = ref<Record<string, boolean>>({}),
  histories = ref<Record<string, PblDiagnostic[]>>({})
const selectedClass = computed(() => classes.value[classIndex.value]),
  topics = computed(() =>
    Array.from(new Map(points.value.map((p) => [p.systemCode, { code: p.systemCode, title: p.systemLabel }])).values()),
  ),
  topicPoints = computed(() => points.value.filter((p) => p.systemCode === topics.value[topicIndex.value]?.code)),
  availableCases = computed(() =>
    cases.value.filter(
      (c) =>
        c.medicalReviewStatus === 'approved' &&
        c.status === '已发布' &&
        c.knowledgePointCodes?.some((code) => code.startsWith(`${topics.value[topicIndex.value]?.code}.`)),
    ),
  ),
  selectedCase = computed(() => availableCases.value[caseIndex.value])
const phaseLabels = {
  problem_framing: '明确问题',
  hypothesis: '提出假设',
  evidence: '讨论证据',
  synthesis: '总结解释',
  completed: '已完成',
} as const
const statuses = ['', 'proposed', 'edited', 'published', 'rejected', 'superseded'],
  statusTitles = ['全部状态', '待审阅', '已编辑', '已发布', '已拒绝', '已更新']
const switchValue = (event: unknown) => Boolean((event as { detail: { value: boolean } }).detail.value)
const statusLabel = (s: string) => statusTitles[statuses.indexOf(s)] ?? s,
  topicName = (code: string) => topics.value.find((t) => t.code === code)?.title ?? code,
  pointName = (code: string) => points.value.find((p) => p.code === code)?.title ?? code
const verificationLabel = (s: string) =>
  ({
    not_ready: '学习进行中',
    pending_teacher: '历史待转换',
    improved: '系统判定已改善',
    needs_reinforcement: '需继续巩固',
  })[s] ?? s
const formatTime = (value?: string) => (value ? new Date(value).toLocaleString() : '')
const editable = (s: PblSuggestion, d: PblDiagnostic) =>
  [3, 4].includes(d.schemaVersion || 0) && ['proposed', 'edited'].includes(s.status)
async function run(action: () => Promise<void>) {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    await action()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败，请重试。'
  } finally {
    busy.value = false
  }
}
async function queue() {
  const data = await getTeacherPblDiagnostics({
    classId: selectedClass.value ? String(selectedClass.value.id) : undefined,
    sessionId: filterSession.value ? sessions.value[filterSession.value - 1]?.id : undefined,
    studentId: filterStudent.value ? String(students.value[filterStudent.value - 1]?.id) : undefined,
    status: statuses[filterStatus.value] || undefined,
    offset: offset.value,
  })
  items.value = data.items
  total.value = data.total
}
async function scope() {
  if (!selectedClass.value) return
  ;[sessions.value, students.value] = await Promise.all([
    getTeacherPblSessions(String(selectedClass.value.id)),
    getClassStudents(selectedClass.value.id),
  ])
  await queue()
  results.value = (await getPblLearningResults()).filter((p) => p.source_context.class_id === selectedClass.value?.id)
}
async function refresh() {
  loading.value = true
  await run(async () => {
    ;[classes.value, points.value, cases.value] = await Promise.all([
      getTeacherClasses(),
      getKnowledgeCatalog(),
      getGuidedCasesAsync(),
    ])
    classes.value = classes.value.filter((c) => c.status === 'active')
    await scope()
  })
  loading.value = false
}
function changeClass(e: { detail: { value: string } }) {
  classIndex.value = Number(e.detail.value)
  offset.value = 0
  filterSession.value = 0
  filterStudent.value = 0
  summary.value = undefined
  void run(scope)
}
function changeTopic(e: { detail: { value: string } }) {
  topicIndex.value = Number(e.detail.value)
  caseIndex.value = 0
  goals.value = []
}
function reloadQueue() {
  offset.value = 0
  void run(queue)
}
function changeSessionFilter(event: { detail: { value: string } }) {
  filterSession.value = Number(event.detail.value)
  reloadQueue()
}
function changeStatusFilter(event: { detail: { value: string } }) {
  filterStatus.value = Number(event.detail.value)
  reloadQueue()
}
function changeStudentFilter(event: { detail: { value: string } }) {
  filterStudent.value = Number(event.detail.value)
  reloadQueue()
}
function page(direction: number) {
  offset.value += direction * 20
  void run(queue)
}
function create() {
  void run(async () => {
    if (!selectedClass.value || !selectedCase.value) return
    await createPblSession(
      String(selectedClass.value.id),
      topics.value[topicIndex.value].code,
      selectedCase.value.id,
      goals.value,
    )
    await scope()
  })
}
function close(item: PblSession) {
  void run(async () => {
    await closePblSession(item.classId, item.id)
    await scope()
  })
}
function showSummary(item: PblSession) {
  void run(async () => {
    summary.value = await getPblSummary(item)
  })
}
function history(item: PblDiagnostic) {
  void run(async () => {
    if (item.id) histories.value[item.id] = await getPblDiagnosticRevisions(item.id)
  })
}
function save(item: PblSuggestion) {
  void run(async () => {
    Object.assign(item, await editPblSuggestion(item))
  })
}
function reject(item: PblSuggestion) {
  void run(async () => {
    Object.assign(item, await editPblSuggestion(item, true))
  })
}
function publish(item: PblSuggestion) {
  void run(async () => {
    Object.assign(
      item,
      await adoptPblSuggestion(item, {
        studentIds: wholeClass.value[item.id] ? [] : targets.value[item.id],
        wholeClass: wholeClass.value[item.id],
        includeCaseRetry: caseRetry.value[item.id],
      }),
    )
    await scope()
  })
}
onMounted(refresh)
defineExpose({ refresh })
</script>
<style scoped>
.pbl-workspace {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
  min-width: 0;
}
.panel {
  display: flex;
  flex-direction: column;
  gap: 18rpx;
}
.section-title {
  font-size: 31rpx;
  font-weight: 700;
}
.muted {
  display: block;
  color: var(--med-muted);
  font-size: 26rpx;
  line-height: 1.6;
}
.panel {
  padding: 24rpx;
  border-radius: var(--med-radius-md);
  background: var(--med-surface);
}
.controls,
.session-row,
.goals {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16rpx;
}
.session-row {
  padding: 18rpx 0;
  border-bottom: 1px solid var(--med-border, #ddd);
}
.session-row > view {
  flex: 1;
  min-width: 180px;
}
.select {
  padding: 18rpx;
  border: 1px solid var(--med-border, #ddd);
  border-radius: 12rpx;
  min-height: 44px;
  box-sizing: border-box;
}
.diagnostic {
  border-top: 1px solid var(--med-border, #ddd);
  padding: 24rpx 0;
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}
.finding {
  padding: 18rpx;
  background: var(--med-bg, #f4f6f4);
  border-radius: 12rpx;
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}
.suggestion {
  padding: 20rpx;
  border: 1px solid var(--med-border, #ddd);
  border-radius: 16rpx;
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}
input,
textarea {
  width: 100%;
  box-sizing: border-box;
  padding: 16rpx;
  background: var(--med-bg, #f4f6f4);
  border-radius: 10rpx;
}
input {
  min-height: 48px;
}
textarea {
  min-height: 110px;
}
.primary {
  background: var(--med-primary);
  color: white;
}
button {
  margin: 0;
  min-height: 44px;
  font-size: 26rpx;
}
.notice {
  padding: 20rpx;
  background: #fff3df;
}
.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 18rpx;
}
.goals label {
  font-size: 27rpx;
}
checkbox-group {
  display: flex;
  gap: 16rpx;
  flex-wrap: wrap;
}
.pagination {
  justify-content: space-between;
}
@media (max-width: 400px) {
  .panel {
    padding: 18rpx;
  }
  .controls > picker {
    width: 100%;
  }
}
</style>
