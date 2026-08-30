<template>
  <view class="safe-page history-page">
    <view class="page-heading"
      ><text class="eyebrow-label">LEARNING TIMELINE</text><text class="heading-title">学习记录</text></view
    >
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
    <view class="nav-shell"><StudentNav active="history" /></view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import MedState from '@/components/ui/MedState.vue'
import StudentNav from '@/components/ui/StudentNav.vue'
import { requireRole } from '@/services/auth'
import { goDetail, goPrimary, ROUTES } from '@/services/navigation'
import { getConversationSummariesAsync } from '@/services/repositoryAsync'
import type { ConversationSummary } from '@/types/domain'
import { formatDateTime } from '@/utils/date'

const PAGE_SIZE = 20
const items = ref<ConversationSummary[]>([])
const total = ref(0)
const isLoading = ref(false)
const isLoadingMore = ref(false)
const loadError = ref('')
let revision = 0
const nextOffset = ref(0)

onShow(() => {
  if (!requireRole('student')) return
  void refresh()
})

async function refresh() {
  if (isLoading.value) return
  isLoading.value = true
  const requestRevision = ++revision
  loadError.value = ''
  try {
    const page = await getConversationSummariesAsync(PAGE_SIZE, 0)
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
    const page = await getConversationSummariesAsync(PAGE_SIZE, nextOffset.value)
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

function openConversation(conversationId: string) {
  goDetail(ROUTES.studentChat, { conversationId })
}

function openChat() {
  goPrimary(ROUTES.studentChat)
}

function openReport(conversationId: string) {
  goDetail('/pages/report/report', { conversationId })
}
</script>

<style scoped>
.history-page {
  padding: 36rpx 28rpx 170rpx;
}
.page-heading {
  display: flex;
  margin-bottom: 28rpx;
  flex-direction: column;
}
.heading-title {
  margin-top: 8rpx;
  color: #0b2239;
  font-size: 42rpx;
  font-weight: 800;
}
.history-card {
  margin-bottom: 22rpx;
  padding: 28rpx;
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
  color: #526174;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.footer {
  color: #718096;
  font-size: 22rpx;
}
.tag {
  padding: 7rpx 14rpx;
  color: #087f8c;
  background: #e6f7f5;
  border-radius: 99rpx;
}
.load-more {
  margin-top: 24rpx;
  color: #087f8c;
  background: transparent;
  font-size: 24rpx;
}
.nav-shell {
  position: fixed;
  right: 24rpx;
  bottom: calc(18rpx + env(safe-area-inset-bottom));
  left: 24rpx;
  padding: 8rpx;
  background: #fff;
  border: 1rpx solid #dbe7eb;
  border-radius: 24rpx;
  box-shadow: 0 14rpx 40rpx rgba(11, 34, 57, 0.12);
}
</style>
