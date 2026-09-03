<template>
  <view class="safe-page page">
    <view
      v-if="task"
      class="card panel"
      ><text class="eyebrow-label">TASK {{ task.position }} / 3</text
      ><text class="title">{{ task.publicDefinition.title || task.taskType }}</text
      ><text class="muted">{{ task.publicDefinition.instruction }}</text
      ><text
        v-if="task.publicDefinition.reason"
        class="hint"
        >{{ task.publicDefinition.reason }}</text
      ></view
    >
    <MedState
      v-if="error"
      icon="retry"
      title="任务暂不可用"
      :description="error"
      action-label="返回学习首页"
      @action="back"
    />
    <view
      v-if="task"
      class="card panel"
      ><text class="section-title">任务状态</text><text>{{ statusLabel(task.status) }}</text
      ><button
        class="primary"
        :disabled="loading || task.status === 'completed'"
        @click="start"
      >
        {{ loading ? '准备中…' : task.taskType === 'micro_drill' ? '开始微训练' : '开始病例任务' }}
      </button></view
    >
  </view>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { onBackPress, onLoad } from '@dcloudio/uni-app'
import MedState from '@/components/ui/MedState.vue'
import { requireRole } from '@/features/identity/public'
import { backOrRoute, goDetail, goReplace, handleBackPress, ROUTES } from '@/platform/navigation'
import { getLearningPlan, startLearningTask } from '@/features/learning/public'
import type { LearningPlan, LearningTask } from '@/types/learning'
const task = ref<LearningTask>()
const error = ref('')
const loading = ref(false)
let taskId = 0
let planId = 0
const statusLabel = (status: LearningTask['status']) =>
  status === 'completed' ? '已完成' : status === 'in_progress' ? '进行中' : '待开始'
async function load(planId: number) {
  try {
    const plan: LearningPlan = await getLearningPlan(planId)
    task.value = plan.tasks.find((item) => item.id === taskId)
    if (!task.value) error.value = '任务不存在或已不可用'
  } catch (e) {
    error.value = e instanceof Error ? e.message : '请稍后重试'
  }
}
async function start() {
  if (!task.value) return
  loading.value = true
  try {
    const result = await startLearningTask(task.value.id)
    if (result.mode === 'case_attempt') goReplace(ROUTES.studentCaseTraining, { id: String(result.attempt.id) })
    else
      goDetail(ROUTES.studentLearningDrill, {
        attemptId: String(result.attempt.id),
        taskId: task.value.id,
        planId,
      })
  } catch (e) {
    uni.showToast({ title: e instanceof Error ? e.message : '无法开始任务', icon: 'none' })
  } finally {
    loading.value = false
  }
}
function back() {
  backOrRoute(ROUTES.studentLearning)
}
onLoad((query) => {
  if (!requireRole('student')) return
  taskId = Number(query?.taskId || 0)
  planId = Number(query?.planId || 0)
  void load(planId)
})

onBackPress(({ from }) => handleBackPress(from, ROUTES.studentLearning))
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
.section-title {
  color: var(--med-navy);
  font-size: 29rpx;
  font-weight: 750;
}
.muted {
  color: var(--med-muted);
  font-size: 23rpx;
  line-height: 1.55;
}
.hint {
  padding: 14rpx;
  color: #7b5e00;
  background: #fff8e1;
  border-radius: 14rpx;
  font-size: 22rpx;
}
.primary {
  color: #fff;
  background: var(--med-brand);
}
</style>
