<template>
  <view class="safe-page page">
    <view class="card intro">
      <text class="eyebrow-label">知识巩固内容</text>
      <text class="title">系统知识点下的教师补充卡</text>
      <text class="muted">系统目录不可改写；学生只能看到医学审核通过的补充卡。</text>
    </view>
    <view class="card">
      <text class="section-title">新建单选补充卡</text>
      <picker
        :range="pointOptions"
        range-key="label"
        @change="choosePoint"
        ><view class="field">{{ selectedPoint?.label || '选择系统知识点' }}</view></picker
      >
      <textarea
        v-model="form.prompt"
        class="field textarea"
        maxlength="1000"
        placeholder="输入题干"
      />
      <input
        v-for="(_, index) in form.options"
        :key="index"
        v-model="form.options[index]"
        class="field"
        :placeholder="`选项 ${String.fromCharCode(65 + index)}`"
      />
      <picker
        :range="answerOptions"
        @change="chooseCorrectOption"
        ><view class="field">正确答案：{{ correctLabel }}</view></picker
      >
      <textarea
        v-model="form.explanation"
        class="field textarea"
        maxlength="2000"
        placeholder="提交后展示的教学解析"
      />
      <input
        v-model="form.reference"
        class="field"
        maxlength="500"
        placeholder="医学参考来源"
      />
      <button
        class="primary"
        :disabled="saving"
        @click="createCard"
      >
        保存为草稿
      </button>
    </view>
    <view class="card">
      <view class="section-head"
        ><text class="section-title">我的补充卡</text
        ><button
          class="text-action"
          @click="load"
        >
          刷新
        </button></view
      >
      <MedState
        v-if="loading"
        variant="loading"
        icon="retry"
        title="正在读取补充卡"
        description=""
      />
      <MedState
        v-else-if="error"
        variant="error"
        icon="retry"
        title="补充卡读取失败"
        :description="error"
        action-label="重试"
        @action="load"
      />
      <text
        v-else-if="!cards.length"
        class="muted"
        >暂无补充卡。先选择一个系统知识点创建教学卡片。</text
      >
      <view
        v-for="card in cards"
        :key="card.id"
        class="card-row"
      >
        <text class="card-title">{{ pointName(card.pointCode) }}</text
        ><text class="muted">{{ card.prompt }}</text
        ><text class="status">{{ statusLabel(card.status) }}</text>
        <text
          v-if="card.reviewComment"
          class="muted"
          >审核意见：{{ card.reviewComment }}</text
        >
        <button
          v-if="card.status === 'draft' || card.status === 'rejected'"
          class="secondary"
          @click="submitCard(card.id)"
        >
          提交医学审核
        </button>
      </view>
    </view>
    <view
      v-if="isReviewer"
      class="card"
    >
      <view class="section-head"
        ><text class="section-title">待审核补充卡</text
        ><button
          class="text-action"
          @click="loadQueue"
        >
          刷新
        </button></view
      >
      <text
        v-if="!queue.length"
        class="muted"
        >暂无待审核补充卡。</text
      >
      <view
        v-for="card in queue"
        :key="card.id"
        class="card-row"
      >
        <text class="card-title">{{ pointName(card.pointCode) }}</text
        ><text>{{ card.prompt }}</text
        ><text class="muted">参考：{{ card.reference || '未填写' }}</text>
        <view class="review-actions"
          ><button
            class="secondary"
            @click="reviewCard(card.id, 'rejected')"
          >
            退回</button
          ><button
            class="primary compact"
            @click="reviewCard(card.id, 'approved')"
          >
            通过
          </button></view
        >
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import MedState from '@/components/ui/MedState.vue'
import { getSession, requireRole } from '@/features/identity/public'
import {
  createKnowledgeCardContribution,
  getKnowledgeCardContributions,
  getKnowledgeCardReviewQueue,
  reviewKnowledgeCardContribution,
  submitKnowledgeCardContribution,
} from '@/features/content/public'
import { getKnowledgeCatalog } from '@/features/learning/public'
import type { KnowledgeCardContribution, KnowledgeCardContributionInput, KnowledgePoint } from '@/types/knowledge'

const points = ref<KnowledgePoint[]>([])
const cards = ref<KnowledgeCardContribution[]>([])
const queue = ref<KnowledgeCardContribution[]>([])
const selectedCode = ref('')
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const form = ref({ prompt: '', options: ['', '', '', ''], correctOption: 0, explanation: '', reference: '' })
const isReviewer = computed(() => getSession()?.permissions?.includes('medical_review') || false)
const pointOptions = computed(() =>
  points.value.map((point) => ({ code: point.code, label: `${point.systemLabel} · ${point.title}` })),
)
const selectedPoint = computed(() => pointOptions.value.find((point) => point.code === selectedCode.value))
const answerOptions = ['A', 'B', 'C', 'D']
const correctLabel = computed(() => answerOptions[form.value.correctOption] || '请选择')

onShow(() => {
  if (requireRole('teacher')) void load()
})
async function load() {
  loading.value = true
  error.value = ''
  try {
    const [catalog, owned] = await Promise.all([getKnowledgeCatalog(), getKnowledgeCardContributions()])
    points.value = catalog
    cards.value = owned
    if (isReviewer.value) await loadQueue()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '请检查网络后重试'
  } finally {
    loading.value = false
  }
}
function choosePoint(event: { detail: { value: string | number } }) {
  selectedCode.value = pointOptions.value[Number(event.detail.value)]?.code || ''
}
function chooseCorrectOption(event: { detail: { value: string | number } }) {
  form.value.correctOption = Number(event.detail.value)
}
function input(): KnowledgeCardContributionInput | undefined {
  const options = form.value.options.map((item) => item.trim())
  if (
    !selectedCode.value ||
    !form.value.prompt.trim() ||
    options.some((item) => !item) ||
    !form.value.explanation.trim()
  ) {
    uni.showToast({ title: '请补全知识点、题干、选项和解析', icon: 'none' })
    return undefined
  }
  return {
    pointCode: selectedCode.value,
    cardType: 'single_choice',
    prompt: form.value.prompt.trim(),
    options,
    correctOption: form.value.correctOption,
    explanation: form.value.explanation.trim(),
    reference: form.value.reference.trim(),
  }
}
async function createCard() {
  const payload = input()
  if (!payload || saving.value) return
  saving.value = true
  try {
    const card = await createKnowledgeCardContribution(payload)
    cards.value = [card, ...cards.value]
    form.value = { prompt: '', options: ['', '', '', ''], correctOption: 0, explanation: '', reference: '' }
    uni.showToast({ title: '草稿已保存', icon: 'success' })
  } catch (cause) {
    uni.showToast({ title: cause instanceof Error ? cause.message : '保存失败', icon: 'none' })
  } finally {
    saving.value = false
  }
}
async function submitCard(id: number) {
  try {
    const card = await submitKnowledgeCardContribution(id)
    cards.value = cards.value.map((item) => (item.id === id ? card : item))
    if (isReviewer.value) await loadQueue()
  } catch (cause) {
    uni.showToast({ title: cause instanceof Error ? cause.message : '提交失败', icon: 'none' })
  }
}
async function loadQueue() {
  try {
    queue.value = await getKnowledgeCardReviewQueue()
  } catch (cause) {
    uni.showToast({ title: cause instanceof Error ? cause.message : '审核队列读取失败', icon: 'none' })
  }
}
async function reviewCard(id: number, decision: 'approved' | 'rejected') {
  try {
    await reviewKnowledgeCardContribution(
      id,
      decision,
      decision === 'approved' ? '教学内容已通过审核' : '请补充医学依据后重新提交',
    )
    await load()
    uni.showToast({ title: decision === 'approved' ? '已通过' : '已退回', icon: 'success' })
  } catch (cause) {
    uni.showToast({ title: cause instanceof Error ? cause.message : '审核失败', icon: 'none' })
  }
}
function pointName(code: string) {
  return points.value.find((point) => point.code === code)?.title || code
}
function statusLabel(status: KnowledgeCardContribution['status']) {
  return { draft: '草稿', pending: '待审核', approved: '已通过', rejected: '已退回', disabled: '已停用' }[status]
}
</script>

<style scoped>
.page {
  padding: 28rpx;
  background: var(--med-page);
}
.card {
  display: flex;
  margin-bottom: 20rpx;
  padding: 28rpx;
  flex-direction: column;
  gap: 16rpx;
  background: var(--med-surface);
  border: 1rpx solid var(--med-border);
  border-radius: var(--med-radius-md);
}
.intro {
  border-top: 6rpx solid var(--med-clinical);
}
.title {
  color: var(--med-ink);
  font-size: 34rpx;
  font-weight: 800;
  line-height: 1.4;
}
.section-title,
.card-title {
  color: var(--med-ink);
  font-size: 29rpx;
  font-weight: 700;
}
.eyebrow-label,
.muted {
  color: var(--med-muted);
  font-size: 24rpx;
  line-height: 1.55;
}
.field {
  width: 100%;
  min-height: 78rpx;
  padding: 16rpx;
  box-sizing: border-box;
  color: var(--med-text);
  background: var(--med-page);
  border: 1rpx solid var(--med-border);
  border-radius: var(--med-radius-sm);
  font-size: 26rpx;
}
.textarea {
  min-height: 130rpx;
}
.primary,
.secondary {
  min-height: 80rpx;
  margin: 0;
  border-radius: var(--med-radius-sm);
  font-size: 27rpx;
}
.primary {
  color: #fff;
  background: var(--med-clinical);
}
.secondary {
  color: var(--med-clinical);
  background: var(--med-wash);
}
.section-head,
.review-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
}
.text-action {
  min-height: 48rpx;
  margin: 0;
  padding: 0;
  color: var(--med-clinical);
  background: transparent;
  font-size: 24rpx;
}
.card-row {
  display: flex;
  padding: 18rpx 0;
  flex-direction: column;
  gap: 8rpx;
  border-top: 1rpx solid var(--med-border);
  font-size: 26rpx;
  line-height: 1.5;
}
.status {
  width: fit-content;
  padding: 4rpx 12rpx;
  color: var(--med-clinical);
  background: var(--med-wash);
  border-radius: 99rpx;
  font-size: 22rpx;
}
.review-actions {
  justify-content: flex-start;
}
.review-actions button {
  flex: 1;
}
.compact {
  min-height: 70rpx;
}
</style>
