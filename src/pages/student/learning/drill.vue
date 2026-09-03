<template>
  <view class="safe-page page">
    <MedState
      v-if="error"
      icon="retry"
      title="微训练暂不可用"
      :description="error"
      action-label="返回学习任务"
      @action="back"
    />
    <template v-else>
      <view class="card panel"
        ><text class="eyebrow-label">MICRO DRILL</text><text class="title">{{ definition.title || '微训练' }}</text
        ><text class="muted">{{ definition.context }}</text
        ><text class="instruction">{{ definition.instruction }}</text></view
      >
      <view class="card panel">
        <textarea
          v-model="answer"
          :maxlength="1200"
          placeholder="写下你的证据、判断与安全边界"
          auto-height
        /><button
          class="primary"
          :disabled="saving || submitted"
          @click="submit"
        >
          {{ submitted ? '已提交' : saving ? '评分中…' : '提交答案' }}
        </button></view
      >
      <view
        v-if="result"
        class="card panel result"
        ><text class="score">{{ result.score }} 分</text><text>{{ result.feedback }}</text
        ><text class="muted">下一步：{{ result.nextStep }}</text
        ><text
          v-for="item in result.evidence"
          :key="item"
          class="evidence"
          >原文证据：{{ item }}</text
        ><button
          class="secondary"
          @click="back"
        >
          返回计划
        </button></view
      >
    </template>
  </view>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { onBackPress, onLoad } from '@dcloudio/uni-app'
import MedState from '@/components/ui/MedState.vue'
import { requireRole } from '@/features/identity/public'
import { backOrRoute, handleBackPress, ROUTES } from '@/platform/navigation'
import { getLearningTaskAttempt, submitLearningTaskAttempt } from '@/features/learning/public'
import type { LearningTaskAttempt } from '@/types/learning'
const answer = ref('')
const result = ref<LearningTaskAttempt>()
const saving = ref(false)
const submitted = ref(false)
const definition = ref({ title: '', context: '', instruction: '' })
const error = ref('')
let attemptId = 0
let taskId = 0
let planId = 0
async function submit() {
  if (!answer.value.trim()) {
    uni.showToast({ title: '请先填写答案', icon: 'none' })
    return
  }
  saving.value = true
  try {
    result.value = await submitLearningTaskAttempt(attemptId, { text: answer.value.trim() })
    submitted.value = true
  } catch (e) {
    uni.showToast({ title: e instanceof Error ? e.message : '提交失败', icon: 'none' })
  } finally {
    saving.value = false
  }
}
function back() {
  if (hasUnsavedInput()) {
    uni.showModal({
      title: '离开微训练？',
      content: '当前答案尚未提交，离开后不会保留。',
      confirmText: '离开',
      success: ({ confirm }) => {
        if (confirm) leaveDrill()
      },
    })
    return
  }
  leaveDrill()
}

function leaveDrill() {
  const target = backTarget()
  backOrRoute(target.path, target.params)
}

function hasUnsavedInput() {
  return !submitted.value && Boolean(answer.value.trim())
}

function backTarget() {
  if (planId > 0 && taskId > 0) {
    return { path: ROUTES.studentLearningPlan, params: { planId, taskId } }
  }
  return { path: ROUTES.studentLearning, params: {} }
}

onLoad(async (query) => {
  if (!requireRole('student')) return
  attemptId = Number(query?.attemptId || 0)
  taskId = Number(query?.taskId || 0)
  planId = Number(query?.planId || 0)
  if (!attemptId) {
    error.value = '缺少训练记录，无法继续。'
    return
  }
  try {
    const item = await getLearningTaskAttempt(attemptId)
    definition.value = item.publicDefinition as typeof definition.value
    if (item.status === 'assessed') {
      result.value = item
      submitted.value = true
      answer.value = String(item.answer.text || '')
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '训练记录暂不可用，请返回计划重试。'
  }
})

onBackPress(({ from }) => {
  if (from === 'navigateBack') return false
  if (saving.value) {
    uni.showToast({ title: '正在提交答案，请稍候', icon: 'none' })
    return true
  }
  if (hasUnsavedInput()) {
    back()
    return true
  }
  const target = backTarget()
  return handleBackPress(from, target.path, target.params)
})
</script>
<style scoped>
.page {
  padding: 28rpx;
  background: var(--med-page);
}
.panel {
  display: flex;
  margin-bottom: 22rpx;
  padding: 30rpx;
  flex-direction: column;
  gap: 16rpx;
}
.title {
  color: var(--med-navy);
  font-size: 38rpx;
  font-weight: 800;
}
.muted {
  color: var(--med-muted);
  font-size: 23rpx;
  line-height: 1.55;
}
.instruction {
  color: var(--med-navy);
  line-height: 1.6;
}
textarea {
  width: auto;
  min-height: 240rpx;
  padding: 20rpx;
  background: #f7fafc;
  border: 1rpx solid var(--med-border);
  border-radius: 14rpx;
}
.primary {
  color: #fff;
  background: var(--med-brand);
}
.secondary {
  color: var(--med-brand);
  background: var(--med-brand-soft);
}
.result {
  align-items: flex-start;
}
.score {
  color: var(--med-brand);
  font-size: 64rpx;
  font-weight: 800;
}
.evidence {
  padding: 12rpx;
  color: #31556a;
  background: #edf7f7;
  font-size: 22rpx;
}
</style>
