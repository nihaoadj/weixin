<template>
  <view class="overview">
    <view class="priority-panel">
      <text class="eyebrow-label">今日待办</text>
      <text class="priority-title">需要你反馈的学习记录</text>
      <text class="priority-description">先完成报告批阅，再跟进班级的学习进展。</text>
      <view
        class="quick-links"
        :aria-busy="loading"
      >
        <button
          hover-class="is-pressed"
          :hover-start-time="0"
          :hover-stay-time="80"
          tabindex="0"
          role="button"
          class="priority-row"
          @keydown="activateButtonOnKey"
          @click="reportError ? $emit('retry') : $emit('reports')"
        >
          <view class="priority-copy">
            <text class="row-title">学生报告</text>
            <text class="row-description">{{
              reportError
                ? '队列读取失败，点击重试'
                : !loading && pendingReports === 0
                  ? '暂无待批阅报告，可查看已有记录'
                  : '等待教师形成性反馈'
            }}</text>
          </view>
          <view class="row-action"
            ><text>{{ loading ? '…' : reportError ? '重试' : (pendingReports ?? '—') }}</text
            ><text aria-hidden="true">›</text></view
          >
        </button>
        <button
          hover-class="is-pressed"
          :hover-start-time="0"
          :hover-stay-time="80"
          tabindex="0"
          role="button"
          class="priority-row"
          @keydown="activateButtonOnKey"
          @click="pblError ? $emit('retry') : $emit('pbl')"
        >
          <view class="priority-copy"
            ><text class="row-title">PBL 待处理</text
            ><text class="row-description">{{
              pblError
                ? '队列读取失败，点击重试'
                : !loading && pendingPbl === 0
                  ? '暂无需要反馈的 PBL 提交'
                  : '学生主动提交与课堂诊断'
            }}</text></view
          >
          <view class="row-action"
            ><text>{{ loading ? '…' : pblError ? '重试' : (pendingPbl ?? '—') }}</text
            ><text aria-hidden="true">›</text></view
          >
        </button>
        <button
          v-if="isReviewer"
          hover-class="is-pressed"
          :hover-start-time="0"
          :hover-stay-time="80"
          tabindex="0"
          role="button"
          class="priority-row"
          @keydown="activateButtonOnKey"
          @click="reviewError ? $emit('retry') : $emit('review')"
        >
          <view class="priority-copy">
            <text class="row-title">医学审核</text>
            <text class="row-description">{{ reviewError ? '队列读取失败，点击重试' : '核对病例内容与教学边界' }}</text>
          </view>
          <view class="row-action"
            ><text>{{ loading ? '…' : reviewError ? '重试' : (pendingReview ?? '—') }}</text
            ><text aria-hidden="true">›</text></view
          >
        </button>
      </view>
      <text
        v-if="reportError || reviewError || pblError"
        class="queue-error"
        role="alert"
        >部分待办暂时无法读取，不代表没有待处理内容。</text
      >
    </view>
    <view class="management">
      <text class="section-title">教学管理</text>
      <button
        hover-class="is-pressed"
        :hover-start-time="0"
        :hover-stay-time="80"
        tabindex="0"
        role="button"
        class="management-row"
        @keydown="activateButtonOnKey"
        @click="$emit('classes')"
      >
        <view class="management-copy"
          ><text class="row-title">班级管理</text><text class="row-description">维护成员与内容范围</text></view
        ><text aria-hidden="true">›</text>
      </button>
      <button
        hover-class="is-pressed"
        :hover-start-time="0"
        :hover-stay-time="80"
        tabindex="0"
        role="button"
        class="management-row"
        @keydown="activateButtonOnKey"
        @click="$emit('analytics')"
      >
        <view class="management-copy"
          ><text class="row-title">学情分析</text><text class="row-description">查看能力变化与薄弱项</text></view
        ><text aria-hidden="true">›</text>
      </button>
      <button
        hover-class="is-pressed"
        :hover-start-time="0"
        :hover-stay-time="80"
        tabindex="0"
        role="button"
        class="management-row"
        @keydown="activateButtonOnKey"
        @click="$emit('knowledgeCards')"
      >
        <view class="management-copy"
          ><text class="row-title">知识补充卡</text
          ><text class="row-description">编写、提交和审核知识巩固卡</text></view
        ><text aria-hidden="true">›</text>
      </button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { activateButtonOnKey } from '@/components/ui/keyboard'
defineProps<{
  loading: boolean
  isReviewer: boolean
  pendingReports?: number
  pendingReview?: number
  pendingPbl?: number
  reportError: boolean
  reviewError: boolean
  pblError: boolean
}>()
defineEmits<{ reports: []; review: []; pbl: []; classes: []; analytics: []; knowledgeCards: []; retry: [] }>()
</script>

<style scoped>
.overview {
  display: flex;
  padding: 24rpx 0;
  flex-direction: column;
  gap: 24rpx;
}
.priority-panel,
.management {
  display: flex;
  flex-direction: column;
}
.priority-panel {
  padding: 18rpx 2rpx 38rpx;
}
.management {
  padding: 34rpx 2rpx 12rpx;
  border-top: 1rpx solid var(--med-border);
}
.priority-title {
  margin-top: 8rpx;
  color: var(--med-ink);
  font-size: 34rpx;
  font-weight: 800;
  line-height: 1.4;
}
.priority-description,
.row-description {
  margin-top: 8rpx;
  color: var(--med-muted);
  font-size: 24rpx;
  line-height: 1.5;
}
.quick-links {
  margin-top: 24rpx;
}
.priority-row,
.management-row {
  display: flex;
  width: 100%;
  min-height: 104rpx;
  margin: 0;
  padding: 22rpx 0;
  align-items: center;
  justify-content: space-between;
  gap: 20rpx;
  color: var(--med-text);
  background: transparent;
  border-top: 1rpx solid var(--med-divider);
  border-radius: 0;
  text-align: left;
}
.priority-copy,
.management-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
}
.row-title {
  font-size: 28rpx;
  font-weight: 700;
}
.row-action {
  display: flex;
  align-items: center;
  gap: 16rpx;
  color: var(--med-clinical);
  font-family: var(--med-font-utility);
  font-size: 32rpx;
}
.section-title {
  margin-bottom: 20rpx;
  color: var(--med-ink);
  font-size: 30rpx;
  font-weight: 700;
}
.queue-error {
  color: var(--med-danger);
  font-size: 24rpx;
  line-height: 1.5;
}
@media screen and (max-width: 360px) {
  .priority-description,
  .row-description,
  .queue-error {
    font-size: 12px;
  }
}
@media screen and (min-width: 600px) {
  .priority-panel,
  .management {
    padding-right: 4px;
    padding-left: 4px;
  }
  .priority-title {
    font-size: 26px;
  }
  .priority-description,
  .row-description,
  .queue-error {
    font-size: 14px;
  }
  .row-title,
  .section-title {
    font-size: 18px;
  }
  .priority-row,
  .management-row {
    min-height: 80px;
    padding: 16px 0;
  }
  .row-action {
    font-size: 24px;
  }
}
</style>
