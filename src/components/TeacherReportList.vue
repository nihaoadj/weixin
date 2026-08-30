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
        :key="report.id"
        class="report-card card"
        @click="$emit('select', report.id)"
      >
        <view class="header">
          <text class="title">{{ report.studentName || '学生' }} · 报告 {{ report.originalIndex }}</text>
          <text
            class="status"
            :class="{ reviewed: report.status === '已批阅' }"
            >{{ report.status || '待批阅' }}</text
          >
        </view>
        <text class="preview">{{ report.messagePreview || '无内容' }}</text>
        <view class="footer">
          <text>{{ formatDateTime(report.createdAt) }}</text>
          <text>{{ report.messageCount }} 条消息</text>
        </view>
      </view>
    </template>
    <button
      v-if="!isLoading && !error && nextOffset < total"
      class="load-more"
      :loading="isLoadingMore"
      @click="loadMore"
    >
      加载更多
    </button>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import MedState from '@/components/ui/MedState.vue'
import { getReportSummariesAsync } from '@/services/repositoryAsync'
import type { ReportSummary } from '@/types/domain'
import { formatDateTime } from '@/utils/date'

interface IndexedReport extends ReportSummary {
  originalIndex: number
}
const emit = defineEmits<{
  select: [id: string]
  count: [value: number]
  reviewed: [value: number]
  manage: []
}>()
const reports = ref<IndexedReport[]>([])
const total = ref(0)
const isLoading = ref(false)
const isLoadingMore = ref(false)
const error = ref('')
let revision = 0
const nextOffset = ref(0)

async function refresh() {
  if (isLoading.value) return
  isLoading.value = true
  const requestRevision = ++revision
  error.value = ''
  try {
    const page = await getReportSummariesAsync(20, 0)
    if (requestRevision !== revision) return
    total.value = page.total
    nextOffset.value = page.items.length
    reports.value = page.items.map((report, index) => ({ ...report, originalIndex: index + 1 }))
    emit('count', page.pendingCount)
    emit('reviewed', page.reviewedCount)
  } catch (loadError) {
    reports.value = []
    error.value = loadError instanceof Error ? loadError.message : '请稍后重试'
  } finally {
    isLoading.value = false
  }
}

async function loadMore() {
  if (isLoading.value || isLoadingMore.value || nextOffset.value >= total.value) return
  isLoadingMore.value = true
  const requestRevision = revision
  try {
    const page = await getReportSummariesAsync(20, nextOffset.value)
    if (requestRevision !== revision) return
    total.value = page.total
    nextOffset.value = page.items.length ? nextOffset.value + page.items.length : page.total
    const existing = new Set(reports.value.map((report) => report.id))
    reports.value.push(
      ...page.items
        .filter((report) => !existing.has(report.id))
        .map((report, index) => ({ ...report, originalIndex: reports.value.length + index + 1 })),
    )
  } catch (loadError) {
    uni.showToast({ title: loadError instanceof Error ? loadError.message : '加载失败', icon: 'none' })
  } finally {
    isLoadingMore.value = false
  }
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
.load-more {
  margin-top: 24rpx;
  color: #087f8c;
  background: transparent;
  font-size: 24rpx;
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
