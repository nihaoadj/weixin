<template>
  <view class="safe-page history-page">
    <view class="page-heading"
      ><button
        class="back-link"
        @click="openChat"
      >
        返回答疑</button
      ><text class="eyebrow-label">LEARNING TIMELINE</text><text class="heading-title">学习记录</text></view
    >
    <view class="topic-filter card">
      <text class="filter-label">按学习主题筛选</text>
      <view class="filter-actions">
        <picker
          v-if="topicOptions.length"
          :range="topicOptions"
          range-key="label"
          @change="selectTopic"
        >
          <button class="filter-select">{{ activeTopicLabel || '全部主题' }}</button>
        </picker>
        <button
          v-if="activeTopicCode"
          class="filter-clear"
          @click="clearTopic"
        >
          清除筛选
        </button>
      </view>
    </view>
    <MedState
      v-if="isLoading"
      variant="loading"
      icon="retry"
      title="正在加载学习记录"
      description="正在整理你的问答和报告。"
    />
    <MedState
      v-else-if="loadError"
      variant="error"
      icon="retry"
      title="记录加载失败"
      :description="loadError"
      action-label="重新加载"
      @action="refresh"
    />
    <MedState
      v-else-if="!isLoading && items.length === 0"
      icon="history"
      title="暂无历史记录"
      description="完成一次医学问答后，学习轨迹会安全地保存在这里。"
      action-label="开始医学问答"
      secondary-action-label="重新加载"
      @action="openChat"
      @secondary-action="refresh"
    />
    <view
      v-for="(item, index) in !isLoading && !loadError ? items : []"
      :key="item.conversationId"
      class="history-card card"
      @click="openConversation(item.conversationId)"
    >
      <view class="row">
        <text class="title">对话 {{ total - index }}</text>
        <text class="time">{{ formatDateTime(item.updatedAt || item.createdAt) }}</text>
      </view>
      <text class="preview">{{ item.messagePreview || '无内容' }}</text>
      <view
        v-if="item.topicCodes?.length"
        class="topic-tags"
      >
        <text
          v-for="code in item.topicCodes"
          :key="code"
          class="topic-tag"
        >
          {{ topicName(code) }}
        </text>
      </view>
      <view class="row footer">
        <text>{{ item.messageCount }} 条消息</text>
        <text
          v-if="item.reportStatus"
          class="tag"
          @click.stop="openReport(item.conversationId)"
        >
          {{ item.reportStatus === '已批阅' ? '查看教师反馈' : '查看报告' }}
        </text>
      </view>
    </view>
    <button
      v-if="!isLoading && !loadError && nextOffset < total"
      class="load-more"
      :loading="isLoadingMore"
      @click="loadMore"
    >
      加载更多
    </button>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import MedState from '@/components/ui/MedState.vue'
import { requireRole } from '@/features/identity/public'
import { goDetail, goPrimary, ROUTES } from '@/platform/navigation'
import { getConversationSummariesAsync } from '@/features/qa/public'
import { getKnowledgeCatalog } from '@/features/learning/public'
import type { ConversationSummary } from '@/types/domain'
import type { KnowledgePoint } from '@/types/knowledge'
import { formatDateTime } from '@/utils/date'

const PAGE_SIZE = 20
const items = ref<ConversationSummary[]>([])
const total = ref(0)
const isLoading = ref(false)
const isLoadingMore = ref(false)
const loadError = ref('')
const points = ref<KnowledgePoint[]>([])
const activeTopicCode = ref('')
let revision = 0
const nextOffset = ref(0)
const topicOptions = computed(() => [
  { label: '全部主题', code: '' },
  ...points.value.map((point) => ({ label: `${point.systemLabel} · ${point.title}`, code: point.code })),
])
const activeTopicLabel = computed(() => points.value.find((point) => point.code === activeTopicCode.value)?.title || '')

onShow(() => {
  if (!requireRole('student')) return
  void loadTopics()
  void refresh()
})

async function loadTopics() {
  try {
    points.value = await getKnowledgeCatalog()
  } catch {
    points.value = []
  }
}

async function refresh() {
  if (isLoading.value) return
  isLoading.value = true
  const requestRevision = ++revision
  loadError.value = ''
  try {
    const page = await getConversationSummariesAsync(PAGE_SIZE, 0, activeTopicCode.value || undefined)
    if (requestRevision !== revision) return
    items.value = page.items
    nextOffset.value = page.items.length
    total.value = page.total
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '请检查网络后重试'
  } finally {
    isLoading.value = false
  }
}

async function loadMore() {
  if (isLoading.value || isLoadingMore.value || nextOffset.value >= total.value) return
  isLoadingMore.value = true
  const requestRevision = revision
  try {
    const page = await getConversationSummariesAsync(PAGE_SIZE, nextOffset.value, activeTopicCode.value || undefined)
    if (requestRevision !== revision) return
    nextOffset.value = page.items.length ? nextOffset.value + page.items.length : page.total
    const existing = new Set(items.value.map((item) => item.conversationId))
    items.value.push(...page.items.filter((item) => !existing.has(item.conversationId)))
    total.value = page.total
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : '加载失败', icon: 'none' })
  } finally {
    isLoadingMore.value = false
  }
}

function selectTopic(event: { detail: { value: string | number } }) {
  const topic = topicOptions.value[Number(event.detail.value)]
  activeTopicCode.value = topic?.code || ''
  void refresh()
}

function clearTopic() {
  activeTopicCode.value = ''
  void refresh()
}

function topicName(code: string) {
  return points.value.find((point) => point.code === code)?.title || code
}

function openConversation(conversationId: string) {
  goDetail(ROUTES.studentChat, { conversationId })
}

function openChat() {
  goPrimary(ROUTES.studentChat)
}

function openReport(conversationId: string) {
  goDetail(ROUTES.studentReport, { conversationId })
}
</script>

<style scoped>
.history-page {
  padding: 36rpx 28rpx 64rpx;
}
.page-heading {
  display: flex;
  margin-bottom: 28rpx;
  flex-direction: column;
}
.heading-title {
  margin-top: 8rpx;
  color: var(--med-navy);
  font-size: 42rpx;
  font-weight: 800;
}
.back-link {
  width: fit-content;
  min-height: 64rpx;
  margin: 0 0 14rpx;
  padding: 0 14rpx;
  color: var(--med-clinical);
  background: var(--med-wash);
  font-size: 23rpx;
}
.history-card {
  margin-bottom: 22rpx;
  padding: 28rpx;
}
.topic-filter {
  display: flex;
  margin-bottom: 22rpx;
  padding: 18rpx 22rpx;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
}
.filter-label {
  color: var(--med-muted);
  font-size: 23rpx;
}
.filter-actions,
.topic-tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10rpx;
}
.filter-select,
.filter-clear {
  min-height: 48rpx;
  margin: 0;
  padding: 0 14rpx;
  color: var(--med-clinical);
  background: var(--med-wash);
  border-radius: var(--med-radius-sm);
  font-size: 22rpx;
  line-height: 48rpx;
}
.filter-clear {
  color: var(--med-muted);
  background: transparent;
}
.topic-tags {
  margin: -4rpx 0 16rpx;
}
.topic-tag {
  padding: 5rpx 10rpx;
  color: var(--med-clinical);
  background: var(--med-wash);
  border-radius: 99rpx;
  font-size: 20rpx;
}
.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.title {
  font-size: 30rpx;
  font-weight: 700;
}
.time {
  color: #8492a6;
  font-size: 22rpx;
}
.preview {
  display: -webkit-box;
  margin: 20rpx 0;
  overflow: hidden;
  color: var(--med-text-secondary);
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.footer {
  color: var(--med-muted);
  font-size: 22rpx;
}
.tag {
  padding: 7rpx 14rpx;
  color: var(--med-brand);
  background: var(--med-brand-soft);
  border-radius: 99rpx;
}
.load-more {
  margin-top: 24rpx;
  color: var(--med-brand);
  background: transparent;
  font-size: 24rpx;
}
</style>
