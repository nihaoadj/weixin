<template>
  <view class="tasks"
    ><view class="head"
      ><text class="title">PBL 课后任务</text
      ><button
        class="action"
        :disabled="loading || busy"
        @click="load"
      >
        刷新任务
      </button></view
    >
    <text
      v-if="loading"
      role="status"
      >正在加载任务…</text
    ><text
      v-if="error"
      role="alert"
      >{{ error }}</text
    >
    <view
      v-if="!loading && !plans.length"
      class="muted"
      >教师采用讨论建议后，你会收到对应的学习任务。</view
    >
    <view
      v-for="plan in plans"
      :key="plan.id"
      class="plan"
      ><view class="plan-heading">
        <view class="heading-info"
          ><text class="subtitle"
            >{{ plan.source_context.class_name }} · 课堂 {{ plan.source_context.session_id }}</text
          >
          ><text class="muted">截止 {{ new Date(plan.due_at).toLocaleDateString() }}</text></view
        ><text
          class="plan-status"
          :class="plan.verification_status"
          >{{ labels[plan.verification_status] }}</text
        ></view
      ><view
        class="plan-progress"
        :aria-label="`已完成 ${completedCount(plan)} / ${relevantCount(plan)} 项任务`"
        ><view class="progress-track"
          ><view
            class="progress-fill"
            :style="{ width: `${progressPercent(plan)}%` }" /></view
        ><text class="muted">已完成 {{ completedCount(plan) }} / {{ relevantCount(plan) }}</text></view
      >
      <text class="muted"
        >当前第 {{ plan.current_cycle }}/{{ plan.max_cycles }} 轮 · {{ plan.decision_policy_version }}</text
      >
      <text
        v-if="plan.automation_exhausted"
        class="exhausted"
        >自动轮次已结束，仍有目标需线下支持。</text
      >
      <view
        v-if="nextTask(plan)"
        class="next-hint"
        ><text class="next-hint-label">下一步</text><text>{{ taskLabels[nextTask(plan)!.task_type] }}</text
        ><text class="muted">按顺序完成，系统会按逐项目标自动判定。</text></view
      >
      <view
        v-for="task in plan.tasks"
        :key="task.id"
        class="task"
        :class="{ 'task--next': nextTask(plan)?.id === task.id }"
        ><text class="subtitle">第 {{ task.cycle_number }} 轮 · {{ taskLabels[task.task_type] }}</text
        ><text>{{ task.public_definition.prompt }}</text
        ><text class="task-meta">学习目标：{{ taskTargetLabel(task) }}</text
        ><text class="muted">资料来源：{{ taskReference(task) }}</text>
        <template v-if="task.status === 'completed'"
          ><text class="done">已完成</text
          ><text v-if="task.result"
            >{{ task.result.feedback
            }}<template v-if="task.result.score != null"> · {{ task.result.score }} 分</template></text
          ></template
        >
        <text
          v-else-if="task.status === 'inactive'"
          class="muted"
          >首轮未达标且命中此目标时自动激活。</text
        >
        <text
          v-else-if="task.status === 'skipped'"
          class="muted"
          >本轮该目标已达标，无需重复训练。</text
        >
        <template v-else-if="unlocked(plan, task)">
          <button
            v-if="task.task_type === 'focused_retry'"
            class="action"
            :disabled="busy"
            @click="startCase(task)"
          >
            开始病例重练
          </button>
          <template v-else
            ><radio-group
              v-if="task.public_definition.options"
              class="options"
              @change="answers[task.id] = { selected_option: radioValue($event) }"
              ><label
                v-for="(option, index) in task.public_definition.options"
                :key="index"
                class="option"
                ><radio
                  :value="String(index)"
                  :checked="answers[task.id]?.selected_option === index"
                  :disabled="busy"
                />{{ option }}</label
              ></radio-group
            >
            <textarea
              v-else
              class="answer-input"
              :value="answers[task.id]?.text || ''"
              :disabled="busy"
              :maxlength="4000"
              aria-label="填写任务回答"
              placeholder="写下你的解释与依据"
              @input="answers[task.id] = { text: inputValue($event) }"
            />
            <button
              class="primary action"
              :disabled="busy || !hasAnswer(task)"
              @click="submit(task)"
            >
              {{ busy ? '正在提交…' : nextTask(plan)?.id === task.id ? '完成这一步' : '提交学习结果' }}
            </button>
          </template> </template
        ><text
          v-else
          class="muted"
          >完成前一项任务后继续。</text
        >
      </view>
    </view>
  </view>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  getPblLearningPlans,
  submitPblTask,
  createPblMessageId,
  type PblPlan,
  type PblTask,
} from '@/features/pbl/public'
import { startLearningTask } from '@/features/learning/public'
import { goDetail, ROUTES } from '@/platform/navigation'
const plans = ref<PblPlan[]>([]),
  loading = ref(true),
  busy = ref(false),
  error = ref(''),
  answers = ref<Record<number, { text?: string; selected_option?: number }>>({}),
  submissionIds = ref<Record<number, string>>({})
type NativeInputEvent = { detail: { value: string } }
const inputValue = (event: unknown) => (event as NativeInputEvent).detail.value
const radioValue = (event: unknown) => Number((event as NativeInputEvent).detail.value)
const labels = {
  not_ready: '学习进行中',
  pending_teacher: '历史待转换',
  improved: '系统判定已改善',
  needs_reinforcement: '需继续巩固',
}
const taskLabels = {
  discussion: '正式讨论题',
  knowledge_review: '知识巩固',
  retest: '客观再测',
  micro_drill: '病例推理微训练',
  focused_retry: '完整病例重练',
}
const taskTargetLabel = (task: PblTask) =>
  task.public_definition.target_label || task.public_definition.point_code || task.target_code
const taskReference = (task: PblTask) => task.public_definition.reference || '教师采用的 PBL 训练，未提供单独资料来源。'
const unlocked = (plan: PblPlan, task: PblTask) =>
  task.cycle_number === plan.current_cycle &&
  plan.tasks
    .filter((t) => t.cycle_number === task.cycle_number && t.position < task.position)
    .every((t) => ['completed', 'skipped'].includes(t.status))
const completedCount = (plan: PblPlan) => plan.tasks.filter((task) => task.status === 'completed').length
const relevantCount = (plan: PblPlan) =>
  plan.tasks.filter((task) => !['inactive', 'skipped'].includes(task.status)).length
const progressPercent = (plan: PblPlan) =>
  relevantCount(plan) ? (completedCount(plan) / relevantCount(plan)) * 100 : 0
const nextTask = (plan: PblPlan) => plan.tasks.find((task) => task.status === 'pending' && unlocked(plan, task))
const hasAnswer = (task: PblTask) =>
  task.public_definition.options
    ? answers.value[task.id]?.selected_option != null
    : Boolean(answers.value[task.id]?.text?.trim())
async function load() {
  loading.value = true
  error.value = ''
  try {
    plans.value = await getPblLearningPlans()
  } catch {
    error.value = '任务加载失败，请点击刷新任务重试。'
  } finally {
    loading.value = false
  }
}
async function submit(task: PblTask) {
  busy.value = true
  error.value = ''
  submissionIds.value[task.id] ??= createPblMessageId()
  try {
    const plan = await submitPblTask(task.id, submissionIds.value[task.id], answers.value[task.id])
    plans.value = plans.value.map((p) => (p.id === plan.id ? plan : p))
  } catch (e) {
    error.value = e instanceof Error ? e.message : '提交失败，回答已保留。'
  } finally {
    busy.value = false
  }
}
async function startCase(task: PblTask) {
  busy.value = true
  error.value = ''
  try {
    const result = await startLearningTask(task.id)
    goDetail(ROUTES.studentCaseTraining, { id: String(result.attempt.id) })
  } catch (e) {
    error.value = e instanceof Error ? e.message : '病例启动失败。'
  } finally {
    busy.value = false
  }
}
onMounted(load)
defineExpose({ refresh: load })
</script>
<style scoped>
.tasks,
.plan,
.task {
  display: flex;
  flex-direction: column;
  gap: 18rpx;
}
.tasks {
  margin-bottom: 24rpx;
}
.head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
}
.title {
  font-size: 30rpx;
  font-weight: 800;
}
.subtitle {
  font-size: 27rpx;
  font-weight: 700;
}
.task-meta {
  color: var(--med-text-secondary);
  font-size: 24rpx;
  font-weight: 700;
}
.muted {
  color: var(--med-muted);
  font-size: 26rpx;
}
.plan {
  padding-top: 24rpx;
  border-top: 1px solid var(--med-border, #ddd);
}
.plan-heading,
.plan-progress {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
}
.plan-heading > .heading-info {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 6rpx;
}
.plan-status,
.next-hint-label {
  padding: 7rpx 12rpx;
  color: var(--med-clinical);
  background: var(--med-wash);
  border-radius: 99rpx;
  font-size: 22rpx;
  white-space: nowrap;
}
.plan-status.pending_teacher {
  color: var(--med-warning, #8a5a00);
  background: var(--med-warning-soft, #fff5df);
}
.plan-status.improved {
  color: var(--med-primary);
  background: var(--med-primary-soft, #e7f3ee);
}
.plan-status.needs_reinforcement {
  color: var(--med-alert, #9f2f2f);
  background: var(--med-alert-soft, #fbe8e8);
}
.plan-progress {
  align-items: center;
}
.progress-track {
  height: 8rpx;
  overflow: hidden;
  flex: 1;
  background: var(--med-divider);
  border-radius: 99rpx;
}
.progress-track > .progress-fill {
  height: 100%;
  background: var(--med-clinical);
  border-radius: inherit;
  transition: width 180ms ease;
}
.next-hint {
  display: flex;
  padding: 18rpx;
  align-items: flex-start;
  flex-direction: column;
  gap: 6rpx;
  background: var(--med-wash);
  border-radius: var(--med-radius-sm);
}
.task {
  background: var(--med-bg, #f6f8f6);
  padding: 24rpx;
  border-radius: 16rpx;
}
.task--next {
  border: 1rpx solid var(--med-clinical);
  box-shadow: 0 8rpx 20rpx rgba(11, 79, 65, 0.08);
}
.options {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}
.option {
  min-height: 44px;
  display: flex;
  align-items: center;
}
.answer-input {
  width: 100%;
  box-sizing: border-box;
  min-height: 120px;
}
.primary {
  background: var(--med-primary);
  color: white;
}
.action {
  min-height: 44px;
  font-size: 27rpx;
}
.done {
  color: var(--med-primary);
}
</style>
