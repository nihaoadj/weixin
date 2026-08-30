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
      v-for="(item, index) in items"
      :key="item.conversationId"
      class="history-card card"
      @click="openConversation(item.conversationId)"
    >
      <view class="row">
        <text class="title">对话 {{ items.length - index }}</text>
        <text class="time">{{ formatDateTime(item.updatedAt || item.createdAt) }}</text>
      </view>
      <text class="preview">{{ item.messages[0]?.content || '无内容' }}</text>
      <view class="row footer">
        <text>{{ item.messages.length }} 条消息</text>
        <text
          v-if="reportStatus.has(item.conversationId)"
          class="tag"
          @click.stop="openReport(item.conversationId)"
        >
          {{ reportStatus.get(item.conversationId) === '已批阅' ? '查看教师反馈' : '查看报告' }}
        </text>
      </view>
    </view>
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
import { getConversationsAsync, getReportsAsync } from '@/services/repositoryAsync'
import type { Conversation } from '@/types/domain'
import { formatDateTime } from '@/utils/date'

const items = ref<Conversation[]>([])
const reportStatus = ref(new Map<string, string>())
const isLoading = ref(false)
const loadError = ref('')

onShow(() => {
  if (!requireRole('student')) return
  void refresh()
})

async function refresh() {
  isLoading.value = true
  loadError.value = ''
  try {
    items.value = await getConversationsAsync()
    reportStatus.value = new Map((await getReportsAsync()).map((report) => [report.conversationId, report.status]))
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '请检查网络后重试'
  } finally {
    isLoading.value = false
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
