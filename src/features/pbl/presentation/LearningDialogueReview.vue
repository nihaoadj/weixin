<template>
  <view
    class="dialogue-review"
    :class="{ 'has-turns': turns.length }"
  >
    <view class="dialogue-review__heading">
      <view class="dialogue-review__title-wrap">
        <view
          class="dialogue-review__icon"
          aria-hidden="true"
        >
          <text /><text /><text />
        </view>
        <view>
          <text class="dialogue-review__title">对话内容</text>
          <text class="dialogue-review__hint">左右切换轮次，单轮内上下滑动查看完整内容</text>
        </view>
      </view>
      <text
        v-if="turns.length"
        class="dialogue-review__count"
        >{{ currentIndex + 1 }}/{{ turns.length }}</text
      >
    </view>

    <view
      v-if="!turns.length"
      class="dialogue-review__empty"
    >
      <text>本次记录没有可回看的个人对话</text>
      <text>课堂共同任务仍会保留在下方学习证据中。</text>
    </view>

    <template v-else>
      <swiper
        class="dialogue-review__swiper"
        :current="currentIndex"
        :duration="220"
        :indicator-dots="false"
        aria-label="按轮回看研讨对话"
        @change="changeTurn"
      >
        <swiper-item
          v-for="(turn, index) in turns"
          :key="turn.id"
          class="dialogue-review__item"
        >
          <scroll-view
            class="dialogue-review__scroll"
            scroll-y
            enhanced
            :show-scrollbar="false"
            :aria-label="`第 ${index + 1} 轮对话完整内容`"
          >
            <view class="dialogue-turn">
              <view class="dialogue-turn__meta">
                <text>第 {{ index + 1 }} 轮</text>
                <text
                  class="dialogue-turn__scope"
                  :class="{ 'is-private': turn.scope === 'private_follow_up' }"
                  >{{ scopeLabel(turn.scope) }}</text
                >
              </view>

              <view class="dialogue-turn__student">
                <text class="dialogue-turn__role">我的问题</text>
                <text class="dialogue-turn__student-bubble">{{ turn.student.content }}</text>
              </view>

              <view class="dialogue-turn__assistant">
                <view
                  class="dialogue-turn__assistant-mark"
                  aria-label="AI 助教"
                >
                  <text /><text /><text />
                </view>
                <view class="dialogue-turn__assistant-copy">
                  <text
                    v-if="turn.assistant"
                    selectable
                    >{{ turn.assistant.content }}</text
                  >
                  <text
                    v-else
                    class="dialogue-turn__unavailable"
                    >本轮 AI 回复尚未形成。</text
                  >
                </view>
              </view>
            </view>
          </scroll-view>
        </swiper-item>
      </swiper>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import type { PblMessage, PblTurnScope } from '@/features/pbl/public'
import { groupLearningDialogueTurns } from './learningDialogueTurns'

const props = withDefaults(defineProps<{ messages: PblMessage[]; current?: number }>(), { current: 0 })
const emit = defineEmits<{ 'update:current': [value: number] }>()
const currentIndex = computed({
  get: () => props.current,
  set: (value: number) => emit('update:current', value),
})
const turns = computed(() => groupLearningDialogueTurns(props.messages))

watch(
  () => props.messages,
  () => {
    currentIndex.value = 0
  },
)

function scopeLabel(scope: PblTurnScope) {
  return scope === 'private_follow_up' ? '私人续问 · 仅自己可见 · 不计入证据' : '正式研讨证据'
}
function changeTurn(event: { detail: { current: string | number } }) {
  currentIndex.value = Number(event.detail.current)
}
</script>

<style scoped>
.dialogue-review {
  overflow: hidden;
  background: #fff;
  border: 1rpx solid #cfeaf3;
  border-radius: 22rpx;
}
.dialogue-review.has-turns {
  border-bottom: 0;
  border-radius: 22rpx 22rpx 0 0;
}
.dialogue-review__heading,
.dialogue-review__title-wrap,
.dialogue-turn__meta,
.dialogue-turn__assistant {
  display: flex;
  align-items: center;
}
.dialogue-review__heading {
  min-height: 92rpx;
  padding: 16rpx 20rpx;
  box-sizing: border-box;
  justify-content: space-between;
  gap: 16rpx;
  background: linear-gradient(90deg, #f4fbfe 0%, #fff 72%);
  border-bottom: 1rpx solid #e3f1f7;
}
.dialogue-review__title-wrap {
  min-width: 0;
  flex: 1;
  gap: 14rpx;
}
.dialogue-review__title-wrap > view:last-child {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 3rpx;
}
.dialogue-review__icon {
  display: flex;
  width: 44rpx;
  height: 36rpx;
  flex: 0 0 44rpx;
  align-items: center;
  justify-content: center;
  gap: 4rpx;
  background: linear-gradient(135deg, #2ba9ed, #0c8fd6);
  border-radius: 12rpx 12rpx 12rpx 4rpx;
}
.dialogue-review__icon text {
  width: 5rpx;
  height: 5rpx;
  background: #fff;
  border-radius: 50%;
}
.dialogue-review__title {
  color: #071a5a;
  font-size: 28rpx;
  font-weight: 800;
}
.dialogue-review__hint,
.dialogue-review__count {
  color: #7287ae;
  font-size: 19rpx;
  line-height: 1.4;
}
.dialogue-review__count {
  flex: none;
  font-variant-numeric: tabular-nums;
}
.dialogue-review__swiper {
  height: 620rpx;
}
.dialogue-review__item {
  display: block;
  width: 100%;
  height: 100%;
}
.dialogue-review__scroll {
  display: block;
  width: 100%;
  height: 620rpx;
}
.dialogue-turn {
  min-height: 620rpx;
  padding: 24rpx 22rpx 42rpx;
  box-sizing: border-box;
}
.dialogue-turn__meta {
  margin-bottom: 20rpx;
  justify-content: space-between;
  gap: 14rpx;
  color: #5d75a5;
  font-size: 20rpx;
}
.dialogue-turn__scope {
  padding: 6rpx 12rpx;
  color: #087f91;
  background: #eaf9fb;
  border-radius: 99rpx;
  font-size: 18rpx;
}
.dialogue-turn__scope.is-private {
  color: #8e4e76;
  background: #fff1f7;
}
.dialogue-turn__student {
  display: flex;
  margin-left: 64rpx;
  align-items: flex-end;
  flex-direction: column;
  gap: 8rpx;
}
.dialogue-turn__role {
  color: #6880aa;
  font-size: 19rpx;
}
.dialogue-turn__student-bubble {
  display: block;
  padding: 18rpx 20rpx;
  color: #294f89;
  background: linear-gradient(135deg, #edf9fd, #e7f4fb);
  border: 1rpx solid #d5edf7;
  border-radius: 24rpx 24rpx 8rpx 24rpx;
  font-size: 25rpx;
  line-height: 1.65;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
.dialogue-turn__assistant {
  margin-top: 30rpx;
  align-items: flex-start;
  gap: 14rpx;
}
.dialogue-turn__assistant-mark {
  position: relative;
  width: 38rpx;
  height: 38rpx;
  flex: 0 0 38rpx;
  color: #20b6c1;
}
.dialogue-turn__assistant-mark text {
  position: absolute;
  top: 16rpx;
  left: 4rpx;
  width: 30rpx;
  height: 5rpx;
  background: currentColor;
  border-radius: 99rpx;
}
.dialogue-turn__assistant-mark text:nth-child(2) {
  transform: rotate(60deg);
}
.dialogue-turn__assistant-mark text:nth-child(3) {
  transform: rotate(120deg);
}
.dialogue-turn__assistant-copy {
  min-width: 0;
  flex: 1;
  color: #365b95;
  font-size: 25rpx;
  line-height: 1.78;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
.dialogue-turn__unavailable {
  color: #7287ae;
}
.dialogue-review__empty {
  display: flex;
  min-height: 210rpx;
  padding: 38rpx 28rpx;
  box-sizing: border-box;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 10rpx;
  color: #5d75a5;
  font-size: 23rpx;
  line-height: 1.6;
  text-align: center;
}
@media (min-width: 600px) {
  .dialogue-review__swiper,
  .dialogue-review__scroll {
    height: 420px;
  }
  .dialogue-turn {
    min-height: 420px;
    padding: 20px 22px 28px;
  }
  .dialogue-review__title {
    font-size: 17px;
  }
  .dialogue-turn__student-bubble,
  .dialogue-turn__assistant-copy {
    font-size: 15px;
  }
}
</style>
