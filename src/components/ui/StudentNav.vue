<template>
  <view class="student-nav">
    <view
      v-for="item in items"
      :key="item.key"
      class="student-nav__item"
      :class="{ active: active === item.key }"
      @click="open(item.key)"
    >
      <MedIcon
        :name="item.icon"
        size="sm"
      />
      <text>{{ item.label }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import MedIcon from '@/components/ui/MedIcon.vue'

import { goPrimary, ROUTES, type StudentPrimaryRoute } from '@/services/navigation'

export type StudentTab = 'chat' | 'question' | 'learning' | 'history'

defineProps<{ active: StudentTab }>()

const items = [
  { key: 'chat' as const, label: '助手', icon: 'chat' as const },
  { key: 'question' as const, label: '病例', icon: 'book' as const },
  { key: 'learning' as const, label: '学习', icon: 'report' as const },
  { key: 'history' as const, label: '记录', icon: 'history' as const },
]

function open(key: StudentTab) {
  const routes: Record<StudentTab, StudentPrimaryRoute> = {
    chat: ROUTES.studentChat,
    question: ROUTES.studentCases,
    learning: ROUTES.studentLearning,
    history: ROUTES.studentHistory,
  }
  goPrimary(routes[key])
}
</script>

<style scoped>
.student-nav {
  display: flex;
  padding: 8rpx 4rpx;
  align-items: center;
  justify-content: space-around;
  background: #fff;
  border-radius: 18rpx;
}
.student-nav__item {
  display: flex;
  min-width: 112rpx;
  min-height: 72rpx;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 4rpx;
  color: #7b8c98;
  font-size: 20rpx;
  border-radius: 16rpx;
}
.student-nav__item.active {
  color: #0f777b;
  background: #eaf7f5;
  font-weight: 700;
}
</style>
