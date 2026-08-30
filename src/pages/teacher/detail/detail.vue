<template>
  <view class="safe-page detail-page">
    <MedState
      v-if="isLoading"
      variant="loading"
      icon="retry"
      title="正在加载报告"
      description="正在获取最新报告内容。"
    />
    <MedState
      v-else-if="loadError"
      variant="error"
      icon="retry"
      title="报告加载失败"
      :description="loadError"
      action-label="重新加载"
      @action="loadReport(reportKey)"
    />
    <MedState
      v-else-if="!report"
      icon="report"
      title="报告不存在"
      description="报告不存在或尚未提交给教师。"
      action-label="返回工作台"
      @action="backOrHome('teacher')"
    />
    <template v-if="report && !isLoading && !loadError">
      <view class="report-meta card">
        <view
          ><text
            class="status"
            :class="{ reviewed: report.status === '已批阅' }"
            >{{ report.status }}</text
          ><text class="time">{{ formatDateTime(report.createdAt) }}</text></view
        >
        <text class="ai-score">AI 形成性评分 {{ report.analysis.score }} 分</text>
      </view>

      <view class="section card">
        <text class="section-title">对话内容</text>
        <view
          v-for="message in report.messages"
          :key="message.id"
          class="message-row"
        >
          <text class="role">{{ message.role === 'user' ? '学生' : 'AI' }}</text>
          <text
            class="message"
            :class="message.role"
            >{{ message.content }}</text
          >
        </view>
      </view>

      <view class="section card">
        <text class="section-title">AI 分析</text>
        <text class="summary">{{ report.analysis.summary }}</text>
        <view
          v-if="report.analysis.errors.length === 0"
          class="strength"
          >{{ report.analysis.strengths?.[0] || '未检测到明显的结构性问题。' }}</view
        >
        <view
          v-for="(issue, index) in report.analysis.errors"
          :key="index"
          class="issue"
        >
          <text>{{ issue.content }}</text
          ><text class="suggestion">建议：{{ issue.suggestion }}</text>
        </view>
      </view>

      <view class="section card">
        <text class="section-title">教师评分与反馈</text>
        <text class="label">评分（0–100）</text>
        <input
          v-model="teacherScore"
          class="score-input"
          type="number"
          placeholder="请输入评分"
        />
        <text class="label">反馈</text>
        <textarea
          v-model="teacherFeedback"
          class="feedback-input"
          placeholder="请输入对学生的反馈"
          :maxlength="1000"
        />
      </view>
      <view class="bottom-space" />
      <view class="submit-bar"
        ><button
          class="primary-button"
          :loading="submitting"
          @click="submitFeedback"
        >
          提交评分和反馈
        </button></view
      >
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import MedState from '@/components/ui/MedState.vue'
import { onLoad } from '@dcloudio/uni-app'
import { requireRole } from '@/services/auth'
import { backOrHome } from '@/services/navigation'
import { findReportAsync, reviewReportAsync } from '@/services/repositoryAsync'
import type { Report } from '@/types/domain'
import { formatDateTime } from '@/utils/date'

const report = ref<Report | null>(null)
const isLoading = ref(false)
const loadError = ref('')
const submitting = ref(false)
let reportKey = ''
const teacherScore = ref('')
const teacherFeedback = ref('')

onLoad((options) => {
  if (!requireRole('teacher')) return
  const id = typeof options?.reportId === 'string' ? options.reportId : ''
  void loadReport(id)
})

async function loadReport(id: string) {
  if (isLoading.value) return
  reportKey = id
  isLoading.value = true
  loadError.value = ''
  try {
    report.value = (await findReportAsync(id)) || null
    if (!report.value) {
      uni.showToast({ title: '报告不存在', icon: 'none' })
      backOrHome('teacher')
      return
    }
    if (report.value.status === '草稿') {
      uni.showToast({ title: '该报告尚未提交', icon: 'none' })
      backOrHome('teacher')
      return
    }
    teacherScore.value = report.value.teacherScore === undefined ? '' : String(report.value.teacherScore)
    teacherFeedback.value = report.value.teacherFeedback || ''
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '请稍后重试'
  } finally {
    isLoading.value = false
  }
}

async function submitFeedback() {
  if (submitting.value) return
  if (!report.value || teacherScore.value.trim() === '') {
    uni.showToast({ title: '请输入评分', icon: 'none' })
    return
  }
  const score = Number(teacherScore.value)
  if (!Number.isFinite(score) || score < 0 || score > 100) {
    uni.showToast({ title: '评分必须在 0–100 之间', icon: 'none' })
    return
  }
  submitting.value = true
  try {
    const reviewed = await reviewReportAsync(
      report.value.id || report.value.conversationId,
      score,
      teacherFeedback.value.trim(),
    )
    if (!reviewed) {
      uni.showToast({ title: '报告状态已变化，请刷新后重试', icon: 'none' })
      return
    }
    report.value = reviewed
    uni.showToast({ title: '批阅已保存', icon: 'success' })
    backOrHome('teacher')
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : '保存失败，请重试', icon: 'none' })
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.detail-page {
  padding: 26rpx;
}
.report-meta,
.section {
  margin-bottom: 22rpx;
  padding: 28rpx;
}
.report-meta > view {
  display: flex;
  align-items: center;
  justify-content: space-between;
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
.time {
  margin-left: 16rpx;
  color: #8795a8;
  font-size: 22rpx;
}
.ai-score {
  display: block;
  margin-top: 22rpx;
  color: #087f8c;
  font-size: 32rpx;
  font-weight: 700;
}
.section-title {
  display: block;
  margin-bottom: 22rpx;
  font-size: 31rpx;
  font-weight: 700;
}
.message-row {
  display: flex;
  margin-top: 18rpx;
  align-items: flex-start;
}
.role {
  display: flex;
  width: 58rpx;
  height: 58rpx;
  flex: 0 0 58rpx;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: #087f8c;
  border-radius: 18rpx;
  font-size: 20rpx;
}
.message {
  margin-left: 15rpx;
  padding: 18rpx 20rpx;
  flex: 1;
  background: #f3f7fb;
  border-radius: 16rpx;
  line-height: 1.6;
  white-space: pre-wrap;
}
.message.user {
  background: #eef2fa;
}
.summary {
  display: block;
  line-height: 1.65;
}
.issue {
  margin-top: 18rpx;
  padding: 20rpx;
  background: #fff8ed;
  border-radius: 16rpx;
  line-height: 1.55;
}
.strength {
  margin-top: 18rpx;
  padding: 20rpx;
  color: #176b5b;
  background: #e9f8f3;
  border-radius: 16rpx;
  line-height: 1.55;
}
.suggestion {
  display: block;
  margin-top: 10rpx;
  color: #64748b;
  font-size: 24rpx;
}
.label {
  display: block;
  margin: 22rpx 0 12rpx;
  color: #526174;
  font-size: 24rpx;
}
.score-input,
.feedback-input {
  box-sizing: border-box;
  width: 100%;
  padding: 20rpx;
  background: #f5f8fb;
  border: 1rpx solid #e2eaf1;
  border-radius: 16rpx;
}
.score-input {
  height: 80rpx;
}
.feedback-input {
  height: 220rpx;
}
.bottom-space {
  height: 130rpx;
}
.submit-bar {
  position: fixed;
  right: 0;
  bottom: 0;
  left: 0;
  padding: 16rpx 24rpx calc(16rpx + env(safe-area-inset-bottom));
  background: #fff;
  border-top: 1rpx solid #e4edf5;
}
.submit-bar button {
  width: 100%;
}
</style>
