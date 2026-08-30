<template>
  <view class="report-list">
    <MedState
      v-if="isLoading"
      variant="loading"
      icon="retry"
      title="正在加载学生报告"
      description="正在同步最新的提交与批阅状态。"
    />
    <MedState
      v-else-if="error"
      variant="error"
      icon="retry"
      title="报告加载失败"
      :description="error"
      action-label="重新加载"
      @action="refresh"
    />
    <MedState
      v-else-if="reports.length === 0"
      variant="first-use"
      icon="report"
      title="还没有学生报告"
      description="学生完成问答并提交后，报告会出现在这里。你也可以先发布练习或管理班级。"
      action-label="重新加载"
      secondary-action-label="管理教学内容"
      @action="refresh"
      @secondary-action="$emit('manage')"
    />
    <template v-if="!isLoading && !error">
      <view
        v-for="report in reports"
        :key="report.conversationId"
        class="report-card card"
        @click="$emit('select', report.conversationId)"
      >
        <view class="header">
          <text class="title">{{ report.studentName || '学生' }} · 报告 {{ report.originalIndex }}</text>
          <text
            class="status"
            :class="{ reviewed: report.status === '已批阅' }"
            >{{ report.status || '待批阅' }}</text
          >
        </view>
        <text class="preview">{{ report.messages[0]?.content || '无内容' }}</text>
        <view class="footer">
          <text>{{ formatDateTime(report.createdAt) }}</text>
          <text>{{ report.messages.length }} 条消息</text>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import MedState from '@/components/ui/MedState.vue'
import { getReportsAsync } from '@/services/repositoryAsync'
import type { Report } from '@/types/domain'
import { formatDateTime } from '@/utils/date'

interface IndexedReport extends Report {
  originalIndex: number
}
const emit = defineEmits<{
  select: [id: string]
  count: [value: number]
  reviewed: [value: number]
  manage: []
}>()
const reports = ref<IndexedReport[]>([])
const isLoading = ref(false)
const error = ref('')

async function refresh() {
  if (isLoading.value) return
  isLoading.value = true
  error.value = ''
  try {
    reports.value = (await getReportsAsync())
      .filter((report) => report.status === '待批阅' || report.status === '已批阅')
      .map((report, index) => ({ ...report, originalIndex: index + 1 }))
      .sort((a, b) => {
        const aPending = a.status !== '已批阅'
        const bPending = b.status !== '已批阅'
        if (aPending !== bPending) return aPending ? -1 : 1
        return b.createdAt.localeCompare(a.createdAt)
      })
  } catch (loadError) {
    reports.value = []
    error.value = loadError instanceof Error ? loadError.message : '请稍后重试'
  } finally {
    isLoading.value = false
  }
  emit('count', reports.value.filter((report) => report.status === '待批阅').length)
  emit('reviewed', reports.value.filter((report) => report.status === '已批阅').length)
}

defineExpose({ refresh })
</script>

<style scoped>
.report-list {
  padding: 24rpx 24rpx 170rpx;
}
.report-card {
  margin-bottom: 20rpx;
  padding: 28rpx;
}
.header,
.footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.title {
  font-size: 29rpx;
  font-weight: 700;
}
.status {
  padding: 7rpx 14rpx;
  color: #b7791f;
  background: #fff7df;
  border-radius: 99rpx;
  font-size: 21rpx;
}
.status.reviewed {
  color: #087f8c;
  background: #e6f7f5;
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
  color: #8795a8;
  font-size: 21rpx;
}
</style>
