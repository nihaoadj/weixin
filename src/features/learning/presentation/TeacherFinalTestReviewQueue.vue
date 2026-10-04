<template>
  <view class="review-queue">
    <picker
      :range="kinds"
      range-key="label"
      @change="changeKind"
    >
      <view class="queue-filter">{{ kinds.find((entry) => entry.value === kind)?.label || '全部待处理测试' }}</view>
    </picker>
    <MedState
      v-if="loading"
      variant="loading"
      icon="history"
      title="正在读取测试状态"
      description="请稍候。"
    />
    <MedState
      v-else-if="error"
      variant="error"
      icon="retry"
      title="测试队列加载失败"
      :description="error"
      action-label="重试"
      @action="load"
    />
    <template v-else-if="page">
      <text class="queue-counts"
        >待审 {{ page.counts.pendingReview }} · 退改 {{ page.counts.needsChanges }} · 生成失败
        {{ page.counts.generationFailed }}</text
      >
      <MedState
        v-if="!page.items.length"
        variant="empty"
        icon="history"
        title="当前范围没有待处理测试"
        description="已开放的测试不计入待审队列。"
      />
      <view
        v-for="item in page.items"
        :key="item.id"
        class="queue-row"
      >
        <text class="queue-title">{{ item.studentName }} · {{ item.title }}</text>
        <text class="queue-meta">{{ item.className }} · {{ statusLabel(item) }}</text>
        <button
          v-if="item.canReview || item.canRetry"
          class="queue-action"
          @click="$emit('openFinalTest', item.id)"
        >
          {{ item.canRetry ? '查看生成异常' : '审阅最终测试' }}
        </button>
        <text
          v-else
          class="queue-meta"
          >暂不可操作，请稍后刷新状态。</text
        >
      </view>
      <TeacherPager
        :total="page.total"
        :offset="offset"
        @previous="paginate(-20)"
        @next="paginate(20)"
      />
    </template>
  </view>
</template>
<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import MedState from '@/components/ui/MedState.vue'
import TeacherPager from '@/components/teacher/TeacherPager.vue'
import {
  getTeacherFinalTestReviewQueue,
  type TeacherFinalTestReviewQueueKind,
  type TeacherFinalTestReviewQueueItem,
  type TeacherFinalTestReviewQueuePage,
} from '@/features/learning/public'

const props = defineProps<{
  classId?: number
  sessionId?: number | string
  initialKind?: TeacherFinalTestReviewQueueKind
}>()
const emit = defineEmits<{
  openFinalTest: [id: string]
  kindChange: [kind: TeacherFinalTestReviewQueueKind | undefined]
}>()
const kind = ref(props.initialKind)
const page = ref<TeacherFinalTestReviewQueuePage>()
const loading = ref(false)
const error = ref('')
const offset = ref(0)
let request = 0
const kinds: Array<{ label: string; value: TeacherFinalTestReviewQueueKind | undefined }> = [
  { label: '全部待处理测试', value: undefined },
  { label: '待审', value: 'pending_review' },
  { label: '退改', value: 'needs_changes' },
  { label: '生成失败', value: 'generation_failed' },
]
async function load() {
  const token = ++request
  loading.value = true
  error.value = ''
  page.value = undefined
  try {
    const value = await getTeacherFinalTestReviewQueue({
      classId: props.classId,
      sessionId: props.sessionId,
      kind: kind.value,
      limit: 20,
      offset: offset.value,
    })
    if (token === request) page.value = value
  } catch (reason) {
    if (token === request) error.value = reason instanceof Error ? reason.message : '请稍后重试。'
  } finally {
    if (token === request) loading.value = false
  }
}
function changeKind(event: { detail: { value: string } }) {
  kind.value = kinds[Number(event.detail.value)]?.value
  offset.value = 0
  emit('kindChange', kind.value)
  void load()
}
function paginate(delta: number) {
  offset.value = Math.max(0, offset.value + delta)
  void load()
}
function statusLabel(item: TeacherFinalTestReviewQueueItem) {
  if (item.generationState === 'generation_failed') return '测试生成失败'
  return item.reviewState === 'needs_changes' ? '教师已退改，等待继续审阅' : '测试草稿待审阅'
}
watch(
  () => [props.classId, props.sessionId],
  () => {
    offset.value = 0
    void load()
  },
)
watch(
  () => props.initialKind,
  (value) => {
    kind.value = value
    offset.value = 0
    void load()
  },
)
onMounted(load)
onBeforeUnmount(() => {
  request += 1
})
defineExpose({ refresh: load })
</script>
<style scoped>
.review-queue {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}
.queue-filter {
  min-height: 88rpx;
  display: flex;
  align-items: center;
  color: var(--med-clinical);
  font-size: 28rpx;
  border-bottom: 1rpx solid var(--med-divider);
}
.queue-counts,
.queue-meta {
  color: var(--med-muted);
  font-size: 24rpx;
  line-height: 1.6;
}
.queue-row {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
  padding: 24rpx 0;
  border-bottom: 1rpx solid var(--med-divider);
}
.queue-title {
  color: var(--med-ink);
  font-size: 28rpx;
  line-height: 1.5;
  overflow-wrap: anywhere;
}
.queue-action {
  min-height: 44px;
  margin: 0;
  color: var(--med-clinical);
  background: var(--med-wash);
  font-size: 26rpx;
}
</style>
