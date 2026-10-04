<template>
  <view class="safe-page report-page">
    <text
      class="sr-only"
      role="heading"
      aria-level="1"
      >历史问答总结</text
    >
    <MedState
      v-if="isLoading"
      variant="loading"
      icon="retry"
      title="正在加载历史总结"
      description="正在获取已保存的问答总结。"
    />
    <MedState
      v-else-if="loadError"
      variant="error"
      icon="retry"
      title="报告加载失败"
      :description="loadError"
      :action-label="reportKey ? '重新加载' : '返回聊天'"
      :secondary-action-label="reportKey ? '返回聊天' : ''"
      @action="reportKey ? loadReport(reportKey) : backToChat()"
      @secondary-action="backToChat"
    />
    <MedState
      v-else-if="!report"
      icon="report"
      title="历史总结不存在"
      description="这条历史记录不存在，请返回答疑继续学习。"
      action-label="返回聊天"
      @action="backToChat"
    />
    <template v-if="report && !isLoading && !loadError">
      <view class="report-hero card">
        <view class="report-mark"
          ><MedIcon
            name="report"
            size="lg"
        /></view>
        <text class="eyebrow">HISTORICAL QA SUMMARY</text>
        <view class="score-row"
          ><text class="score">{{ report.analysis.score }}</text
          ><text class="score-total">/ 100</text></view
        >
        <text class="score-label">AI 形成性评分</text>
        <text class="summary">{{ report.analysis.summary }}</text>
      </view>

      <SafetyBanner class="report-safety">历史总结仅用于回顾学习过程，不应输入真实患者身份信息。</SafetyBanner>

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

      <view class="section card submission-facts">
        <text class="section-title">提交信息</text>
        <view
          v-if="report.classId"
          class="fact-row"
        >
          <text class="fact-label">接收班级</text>
          <text class="fact-value">{{ report.className || '已提交班级' }}</text>
        </view>
        <view
          v-else
          class="fact-row"
        >
          <text class="fact-label">班级归属</text>
          <text class="fact-value">历史记录未关联班级，仅本人可见</text>
        </view>
        <view class="fact-row">
          <text class="fact-label">当前状态</text>
          <text class="fact-value">{{
            report.status === '已批阅'
              ? '教师已完成批阅'
              : report.status === '草稿'
                ? '历史草稿，仅本人可见'
                : '历史提交记录，仅供本人回看'
          }}</text>
        </view>
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
import { onBackPress, onLoad } from '@dcloudio/uni-app'
import MedIcon from '@/components/ui/MedIcon.vue'
import MedState from '@/components/ui/MedState.vue'
import SafetyBanner from '@/components/ui/SafetyBanner.vue'
import { requireRole } from '@/features/identity/public'
import { backOrRoute, handleBackPress, ROUTES } from '@/platform/navigation'
import { findReportByConversationAsync } from '@/features/reports/public'
import type { Report } from '@/types/domain'

const report = ref<Report | null>(null)
const isLoading = ref(false)
const loadError = ref('')
let reportKey = ''
const previewMessages = computed(() => report.value?.messages.slice(0, 5) || [])

onLoad((options) => {
  if (!requireRole('student')) return
  const id = typeof options?.conversationId === 'string' ? options.conversationId : ''
  void loadReport(id)
})

async function loadReport(id: string) {
  if (isLoading.value) return
  reportKey = id
  isLoading.value = true
  loadError.value = ''
  try {
    report.value = (await findReportByConversationAsync(id)) || null
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '请稍后重试'
  } finally {
    isLoading.value = false
  }
}

function backToChat() {
  backOrRoute(ROUTES.studentChat)
}

onBackPress(({ from }) => handleBackPress(from, ROUTES.studentChat))
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
    radial-gradient(circle at 85% 10%, rgba(53, 183, 168, 0.2), transparent 32%),
    linear-gradient(160deg, #fff, var(--med-brand-soft));
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
  color: var(--med-brand);
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
  color: var(--med-muted);
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
  color: var(--med-text-secondary);
  font-size: 24rpx;
  line-height: 1.55;
}
.teacher-review {
  border-left: 8rpx solid var(--med-brand);
}
.teacher-score {
  display: block;
  color: var(--med-brand);
  font-size: 46rpx;
  font-weight: 800;
}
.teacher-feedback {
  display: block;
  margin-top: 16rpx;
  color: var(--med-text-secondary);
  line-height: 1.65;
  white-space: pre-wrap;
}
.fact-row {
  display: flex;
  margin-top: 14rpx;
  align-items: flex-start;
  gap: 16rpx;
}
.fact-label {
  flex: none;
  width: 150rpx;
  color: var(--med-muted);
  font-size: 25rpx;
}
.fact-value {
  flex: 1;
  color: var(--med-text);
  font-size: 25rpx;
  line-height: 1.55;
  overflow-wrap: anywhere;
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
  background: var(--med-brand);
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
  color: var(--med-text-secondary);
  background: var(--med-divider);
  border-radius: 18rpx;
}
@media screen and (min-width: 600px) {
  .fact-label,
  .fact-value {
    font-size: 13px;
  }
}
</style>
