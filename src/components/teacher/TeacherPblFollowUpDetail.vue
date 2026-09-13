<template>
  <view
    v-if="selectedPlanId"
    class="detail"
  >
    <button
      class="back"
      role="button"
      tabindex="0"
      @keydown="activateButtonOnKey"
      @click="$emit('back')"
    >
      返回列表
    </button>
    <view
      v-if="error"
      role="alert"
      >{{ error }}
      <button
        role="button"
        tabindex="0"
        @keydown="activateButtonOnKey"
        @click="$emit('retry')"
      >
        重试
      </button></view
    >
    <text v-else-if="loading">正在加载跟进详情…</text>
    <template v-else-if="detail">
      <text class="detail-heading">{{ detail.plan.source_context.topic_code }} · 正式任务跟进</text>
      <view class="decision-summary">
        <text>当前轮次：第 {{ detail.plan.current_cycle }} / {{ detail.plan.max_cycles }} 轮</text>
        <text>任务状态：{{ displayPlanStatus(detail.plan.status) }}</text>
        <text>系统判定：{{ decisionLabel }}</text>
        <text v-if="detail.plan.verification_note">判定说明：{{ detail.plan.verification_note }}</text>
      </view>

      <view class="record-group">
        <text class="group-heading">正式任务</text>
        <view
          v-for="task in detail.plan.tasks"
          :key="task.id"
          class="task"
        >
          <text>第 {{ task.cycle_number }} 轮 · {{ task.public_definition.target_label || task.target_code }}</text>
          <text>{{ task.public_definition.prompt }}</text>
          <text class="muted"
            >{{ displayTaskStatus(task.status)
            }}<template v-if="task.result?.score !== null && task.result">
              · 得分 {{ task.result.score }}</template
            ></text
          >
        </view>
      </view>

      <view
        v-if="failedTargets.length"
        class="record-group"
      >
        <text class="group-heading">失败目标</text>
        <text
          v-for="target in failedTargets"
          :key="target.target_type + '-' + target.target_code"
          >{{ target.label || target.target_code }}</text
        >
      </view>

      <view class="record-group">
        <text class="group-heading">两轮评价历史</text>
        <text
          v-if="!detail.plan.evaluations?.length"
          class="muted"
          >任务尚未形成系统评价。</text
        >
        <view
          v-for="evaluation in detail.plan.evaluations || []"
          :key="evaluation.cycle_number"
          class="evaluation"
        >
          <text>第 {{ evaluation.cycle_number }} 轮：{{ displayDecision(evaluation.result) }}</text>
          <text
            v-for="check in evaluation.checks"
            :key="check.target_type + '-' + check.target_code"
            class="check"
            >{{ check.label || check.target_code }}：{{ check.passed ? '已达标' : '未达标' }} ·
            {{ check.evidence_present ? '得分 ' + String(check.score ?? '未记录') : '证据缺失'
            }}<template v-if="check.threshold !== null"> / 阈值 {{ check.threshold }}</template></text
          >
        </view>
      </view>

      <view
        v-if="canSendSupport"
        class="support-form"
      >
        <text class="group-heading">补充支持反馈</text>
        <textarea
          :value="body"
          maxlength="1000"
          aria-label="补充支持反馈"
          :aria-invalid="Boolean(actionError)"
          placeholder="填写 1–1000 字后续支持建议"
          @input="updateBody"
        />
        <text
          v-if="actionError"
          class="action-error"
          role="alert"
          >{{ actionError }}</text
        >
        <button
          :disabled="busy || !valid"
          :tabindex="busy || !valid ? -1 : 0"
          role="button"
          @keydown="activateButtonOnKey"
          @click="$emit('sendFeedback')"
        >
          发送补充反馈
        </button>
      </view>
      <text
        v-else-if="detail.plan.verification_status === 'needs_reinforcement'"
        class="muted"
        >自动巩固尚未耗尽，当前不能发送补充支持反馈。</text
      >

      <view
        v-if="detail.feedbacks.length"
        class="record-group"
      >
        <text class="group-heading">教师反馈记录</text>
        <text
          v-for="feedback in detail.feedbacks"
          :key="feedback.id"
          >{{ feedback.body }}</text
        >
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { activateButtonOnKey } from '@/components/ui/keyboard'
import type { PblPlan, PblTeacherFeedback } from '@/features/pbl/public'

type FollowUpDetail = { plan: PblPlan; feedbacks: PblTeacherFeedback[] }

const props = defineProps<{
  selectedPlanId?: number
  detail?: FollowUpDetail
  body: string
  loading: boolean
  busy: boolean
  error: string
  actionError: string
}>()
const emit = defineEmits<{
  back: []
  retry: []
  'update:body': [value: string]
  sendFeedback: []
}>()

const failedTargets = computed(() => props.detail?.plan.decision_basis.failed_targets || [])
const canSendSupport = computed(
  () => props.detail?.plan.verification_status === 'needs_reinforcement' && props.detail.plan.automation_exhausted,
)
const valid = computed(() => props.body.trim().length >= 1 && props.body.trim().length <= 1000)
const decisionLabel = computed(() => {
  const plan = props.detail?.plan
  if (!plan) return '尚未判定'
  if (plan.decision_basis.result) return displayDecision(plan.decision_basis.result)
  return {
    not_ready: '任务尚未完成',
    pending_teacher: '等待系统判定',
    improved: '已达标',
    needs_reinforcement: '需要继续支持',
  }[plan.verification_status]
})

function updateBody(event: unknown) {
  const value =
    (event as { detail?: { value?: unknown }; target?: { value?: unknown } })?.detail?.value ??
    (event as { target?: { value?: unknown } })?.target?.value
  emit('update:body', String(value ?? ''))
}
function displayDecision(value: string) {
  return (
    {
      improved: '已达标',
      next_cycle_activated: '第一轮未达标，已激活第二轮',
      needs_reinforcement: '两轮后仍需支持',
    }[value] || value
  )
}
function displayPlanStatus(value: string) {
  return (
    {
      pending: '待开始',
      active: '进行中',
      completed: '已完成',
      needs_reinforcement: '需要支持',
    }[value] || value
  )
}
function displayTaskStatus(value: string) {
  return (
    {
      locked: '未激活',
      pending: '待完成',
      active: '待完成',
      completed: '已完成',
      passed: '已达标',
      failed: '未达标',
    }[value] || value
  )
}
</script>

<style scoped>
.detail,
.decision-summary,
.record-group,
.task,
.evaluation,
.support-form {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
}
.detail {
  min-width: 0;
  padding: 18rpx 0;
  border-top: 1rpx solid var(--med-border);
}
.detail-heading,
.group-heading {
  color: var(--med-ink);
  font-weight: 700;
}
.decision-summary {
  padding: 14rpx 0;
  color: var(--med-text);
  border-top: 2rpx solid var(--med-clinical);
}
.record-group,
.task,
.evaluation,
.support-form {
  padding-top: 14rpx;
  border-top: 1rpx solid var(--med-divider);
}
.task,
.evaluation {
  border-top-style: dashed;
}
.muted {
  color: var(--med-muted);
}
textarea {
  width: 100%;
  min-height: 180rpx;
  box-sizing: border-box;
  border: 1rpx solid var(--med-border);
}
.support-form button,
.back,
.detail [role='alert'] button {
  min-height: 44px;
}
.action-error {
  color: var(--med-danger);
}
@media screen and (min-width: 600px) {
  .detail {
    font-size: 14px;
  }
}
@media screen and (min-width: 768px) {
  .detail {
    padding: 16px;
    border: 1px solid var(--med-border);
  }
  .back {
    display: none;
  }
}
</style>
