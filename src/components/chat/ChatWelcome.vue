<template>
  <view class="welcome card">
    <text class="eyebrow-label">开始一次推理</text>
    <text class="welcome-title">从一个医学问题开始</text>
    <text class="welcome-description">梳理知识、练习鉴别诊断，或一起分析病例。对话结束后，可以生成学习报告。</text>
    <view class="quick-list">
      <button
        v-for="question in questions"
        :key="question"
        hover-class="is-pressed"
        :hover-start-time="0"
        :hover-stay-time="80"
        tabindex="0"
        role="button"
        class="quick-item"
        :aria-label="`提问：${question}`"
        @keydown="activateButtonOnKey"
        @click="$emit('ask', question)"
      >
        <text class="quick-question">{{ question }}</text>
        <text
          class="quick-arrow"
          aria-hidden="true"
          >›</text
        >
      </button>
    </view>
    <SafetyBanner class="welcome-safety" />
  </view>
</template>

<script setup lang="ts">
import { activateButtonOnKey } from '@/components/ui/keyboard'
import SafetyBanner from '@/components/ui/SafetyBanner.vue'

defineProps<{ questions: readonly string[] }>()
defineEmits<{ ask: [question: string] }>()
</script>

<style scoped>
.welcome {
  display: flex;
  max-width: 720px;
  margin: 4rpx auto 32rpx;
  padding: 32rpx;
  flex-direction: column;
}
.welcome-title {
  margin-top: 10rpx;
  color: var(--med-ink);
  font-size: 38rpx;
  font-weight: 800;
  line-height: 1.4;
}
.welcome-description {
  margin-top: 14rpx;
  color: var(--med-muted);
  font-size: 25rpx;
  line-height: 1.65;
}
.quick-list {
  margin-top: 28rpx;
}
.quick-item {
  display: flex;
  width: 100%;
  min-height: 88rpx;
  margin: 0;
  padding: 20rpx 0;
  align-items: center;
  justify-content: space-between;
  gap: 20rpx;
  color: var(--med-text);
  background: transparent;
  border-top: 1rpx solid var(--med-divider);
  border-radius: 0;
  font-size: 26rpx;
  line-height: 1.5;
  text-align: left;
}
.quick-question {
  min-width: 0;
  flex: 1;
}
.quick-arrow {
  color: var(--med-clinical);
  font-size: 36rpx;
}
.welcome-safety {
  margin-top: 24rpx;
}
@media screen and (max-width: 360px) {
  .welcome-title {
    font-size: 20px;
  }
  .welcome-description,
  .quick-item {
    font-size: 14px;
  }
}
@media screen and (min-width: 600px) {
  .welcome {
    padding: 32px;
  }
  .welcome-title {
    margin-top: 8px;
    font-size: 28px;
  }
  .welcome-description,
  .quick-item {
    font-size: 16px;
  }
  .quick-list {
    margin-top: 24px;
  }
  .quick-item {
    min-height: 60px;
    padding: 16px 0;
  }
}
</style>
