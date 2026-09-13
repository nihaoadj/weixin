<template>
  <view class="welcome">
    <text class="eyebrow-label">开始一次推理</text>
    <text class="welcome-title">从一个医学问题开始</text>
    <text class="welcome-description">梳理知识、练习鉴别诊断，或分析病例；结束后可生成学习报告。</text>
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
    <SafetyBanner
      compact
      class="welcome-safety"
    />
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
  margin: 8rpx auto 20rpx;
  flex-direction: column;
}
.welcome-title {
  margin-top: 8rpx;
  color: var(--med-ink);
  font-size: 33rpx;
  font-weight: 800;
  line-height: 1.4;
}
.welcome-description {
  margin-top: 10rpx;
  color: var(--med-muted);
  font-size: 25rpx;
  line-height: 1.6;
}
.quick-list {
  margin-top: 12rpx;
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
  margin-top: 18rpx;
}
@media screen and (max-width: 360px) {
  .welcome-title {
    font-size: 19px;
  }
  .welcome-description,
  .quick-item {
    font-size: 14px;
  }
}
@media screen and (min-width: 600px) {
  .welcome-title {
    margin-top: 6px;
    font-size: 24px;
  }
  .welcome-description,
  .quick-item {
    font-size: 16px;
  }
  .quick-list {
    margin-top: 8px;
  }
  .quick-item {
    min-height: 60px;
    padding: 16px 0;
  }
}
</style>
