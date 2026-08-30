<template>
  <view class="safe-page report-page">
    <template v-if="report">
      <view class="report-hero card">
        <view class="report-mark"
          ><MedIcon
            name="report"
            size="lg"
        /></view>
        <text class="eyebrow">FORMATIVE ASSESSMENT</text>
        <view class="score-row"
          ><text class="score">{{ report.analysis.score }}</text
          ><text class="score-total">/ 100</text></view
        >
        <text class="score-label">AI 形成性评分</text>
        <text class="summary">{{ report.analysis.summary }}</text>
      </view>

      <SafetyBanner class="report-safety">报告用于回顾学习过程，不应输入真实患者身份信息。</SafetyBanner>

      <view class="section card">
        <text class="section-title">改进建议</text>
        <view
          v-if="report.analysis.errors.length === 0"
          class="strength"
        >
          <text>{{ report.analysis.strengths?.[0] || '本次回答未检测到明显的结构性问题。' }}</text>
        </view>
        <view
          v-for="(issue, index) in report.analysis.errors"
          :key="index"
          class="issue"
        >
          <text class="issue-title">{{ index + 1 }}. {{ issue.content }}</text>
          <text class="suggestion">{{ issue.suggestion }}</text>
        </view>
        <text
          v-for="suggestion in report.analysis.generalSuggestions || []"
          :key="suggestion"
          class="general-suggestion"
          >{{ suggestion }}</text
        >
      </view>

      <view
        v-if="report.status === '已批阅'"
        class="section card teacher-review"
      >
        <text class="section-title">教师反馈</text>
        <text class="teacher-score">{{ report.teacherScore }} 分</text>
        <text class="teacher-feedback">{{ report.teacherFeedback || '教师暂未填写文字反馈。' }}</text>
      </view>

      <view class="section card">
        <text class="section-title">对话预览</text>
        <view
          v-for="message in previewMessages"
          :key="message.id"
          class="preview-row"
        >
          <text class="preview-role">{{ message.role === 'user' ? '我' : 'AI' }}</text>
          <text class="preview-content">{{ message.content }}</text>
        </view>
        <text
          v-if="report.messages.length > 5"
          class="more muted"
          >还有 {{ report.messages.length - 5 }} 条消息</text
        >
      </view>

      <view class="safety-note">本报告用于教学反馈，不构成医学诊断或治疗建议。</view>
      <view class="actions">
        <button
          class="primary-button"
          :disabled="report.status !== '草稿'"
          @click="submitToTeacher"
        >
          {{ actionLabel }}
        </button>
        <button
          class="secondary"
          @click="backToChat"
        >
          返回聊天
        </button>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import MedIcon from '@/components/ui/MedIcon.vue'
import SafetyBanner from '@/components/ui/SafetyBanner.vue'
import { requireRole } from '@/services/auth'
import { backOrHome, relaunchForRole } from '@/services/navigation'
import { findReportAsync, submitReportForReviewAsync } from '@/services/repositoryAsync'
import type { Report } from '@/types/domain'

const report = ref<Report | null>(null)
const previewMessages = computed(() => report.value?.messages.slice(0, 5) || [])
const actionLabel = computed(() => {
  if (report.value?.status === '待批阅') return '已提交教师批阅'
  if (report.value?.status === '已批阅') return '教师已完成批阅'
  return '提交给教师批阅'
})

onLoad((options) => {
  if (!requireRole('student')) return
  const id = typeof options?.conversationId === 'string' ? options.conversationId : ''
  void loadReport(id)
})

async function loadReport(id: string) {
  report.value = (await findReportAsync(id)) || null
  if (!report.value) {
    uni.showToast({ title: '报告不存在', icon: 'none' })
    backOrHome('student')
  }
}

async function submitToTeacher() {
  if (!report.value || report.value.status !== '草稿') return
  const submitted = await submitReportForReviewAsync(report.value.conversationId)
  if (!submitted) {
    uni.showToast({ title: '报告状态已变化，请重新打开', icon: 'none' })
    return
  }
  report.value = submitted
  uni.showToast({ title: '报告已提交', icon: 'success' })
  relaunchForRole('student')
}

function backToChat() {
  backOrHome('student')
}
</script>

<style scoped>
.report-page {
  padding: 28rpx 28rpx 210rpx;
}
.report-hero {
  display: flex;
  padding: 42rpx 32rpx;
  align-items: center;
  flex-direction: column;
  background:
    radial-gradient(circle at 85% 10%, rgba(53, 183, 168, 0.2), transparent 32%), linear-gradient(160deg, #fff, #eaf7f5);
}
.report-mark {
  display: flex;
  width: 96rpx;
  height: 96rpx;
  margin-bottom: 18rpx;
  align-items: center;
  justify-content: center;
  background: #fff;
  border: 1rpx solid #d1e8e4;
  border-radius: 28rpx;
  box-shadow: 0 14rpx 34rpx rgba(15, 139, 141, 0.12);
}
.eyebrow {
  color: #087f8c;
  font-size: 22rpx;
  letter-spacing: 4rpx;
}
.score {
  margin-top: 8rpx;
  color: #0b5d61;
  font-size: 94rpx;
  font-weight: 800;
  line-height: 1.15;
}
.score-row {
  display: flex;
  align-items: baseline;
}
.score-total {
  margin-left: 8rpx;
  color: #637985;
  font-size: 25rpx;
  font-weight: 700;
}
.score-label {
  color: #718096;
  font-size: 22rpx;
}
.summary {
  margin-top: 24rpx;
  line-height: 1.65;
  text-align: center;
}
.report-safety {
  margin-top: 24rpx;
}
.section {
  margin-top: 24rpx;
  padding: 30rpx;
}
.section-title {
  display: block;
  margin-bottom: 22rpx;
  font-size: 31rpx;
  font-weight: 700;
}
.issue {
  margin-top: 18rpx;
  padding: 22rpx;
  background: #fff8ed;
  border-radius: 18rpx;
}
.strength {
  padding: 22rpx;
  color: #176b5b;
  background: #e9f8f3;
  border-radius: 18rpx;
  line-height: 1.55;
}
.issue-title {
  display: block;
  color: #7b4a12;
  line-height: 1.55;
}
.suggestion {
  display: block;
  margin-top: 12rpx;
  color: #645d54;
  font-size: 24rpx;
  line-height: 1.55;
}
.general-suggestion {
  display: block;
  margin-top: 16rpx;
  color: #526174;
  font-size: 24rpx;
  line-height: 1.55;
}
.teacher-review {
  border-left: 8rpx solid #087f8c;
}
.teacher-score {
  display: block;
  color: #087f8c;
  font-size: 46rpx;
  font-weight: 800;
}
.teacher-feedback {
  display: block;
  margin-top: 16rpx;
  color: #526174;
  line-height: 1.65;
  white-space: pre-wrap;
}
.preview-row {
  display: flex;
  margin-top: 18rpx;
  align-items: flex-start;
}
.preview-role {
  display: flex;
  width: 54rpx;
  height: 54rpx;
  flex: 0 0 54rpx;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: #087f8c;
  border-radius: 18rpx;
  font-size: 20rpx;
}
.preview-content {
  margin-left: 16rpx;
  padding: 16rpx 20rpx;
  flex: 1;
  background: #f5f8fb;
  border-radius: 16rpx;
  line-height: 1.55;
}
.more {
  display: block;
  margin-top: 20rpx;
  text-align: center;
  font-size: 22rpx;
}
.safety-note {
  margin: 24rpx 8rpx;
  color: #8795a8;
  font-size: 22rpx;
  text-align: center;
}
.actions {
  position: fixed;
  right: 0;
  bottom: 0;
  left: 0;
  display: flex;
  padding: 16rpx 24rpx calc(16rpx + env(safe-area-inset-bottom));
  gap: 16rpx;
  background: #fff;
  border-top: 1rpx solid #e4edf5;
}
.actions button {
  flex: 1;
  font-size: 27rpx;
}
.secondary {
  color: #526174;
  background: #edf2f7;
  border-radius: 18rpx;
}
.primary-button[disabled] {
  opacity: 0.58;
}
</style>
