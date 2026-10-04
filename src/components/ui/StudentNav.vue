<template>
  <view
    class="student-nav"
    role="navigation"
    aria-label="学生主导航"
  >
    <button
      v-for="item in items"
      :key="item.key"
      hover-class="is-pressed"
      :hover-start-time="0"
      :hover-stay-time="80"
      tabindex="0"
      role="button"
      class="student-nav__item"
      :class="{ active: active === item.key }"
      :aria-current="active === item.key ? 'page' : undefined"
      @keydown="activateButtonOnKey"
      @click="open(item.key)"
    >
      <StudentNavIcon :name="item.icon" />
      <text>{{ item.label }}</text>
    </button>
  </view>
</template>

<script setup lang="ts">
import { activateButtonOnKey } from '@/components/ui/keyboard'
import StudentNavIcon from '@/components/ui/StudentNavIcon.vue'

import { goPrimary, ROUTES, type StudentPrimaryRoute } from '@/platform/navigation'

export type StudentTab = 'learning' | 'pbl' | 'insights'

defineProps<{ active: StudentTab }>()

const items = [
  { key: 'pbl' as const, label: '研讨', icon: 'chat' as const },
  { key: 'learning' as const, label: '学习', icon: 'book' as const },
  { key: 'insights' as const, label: '学情', icon: 'history' as const },
]

function open(key: StudentTab) {
  const routes: Record<StudentTab, StudentPrimaryRoute> = {
    learning: ROUTES.studentLearning,
    pbl: ROUTES.studentPbl,
    insights: ROUTES.studentInsights,
  }
  goPrimary(routes[key])
}
</script>

<style scoped>
.student-nav {
  display: flex;
  padding: 8rpx;
  align-items: center;
  justify-content: space-around;
  background: var(--med-surface);
  border-radius: var(--med-radius-md);
}
.student-nav__item {
  display: flex;
  min-width: 0;
  min-height: 88rpx;
  margin: 0;
  padding: 8rpx;
  align-items: center;
  justify-content: center;
  flex: 1;
  flex-direction: column;
  gap: 4rpx;
  color: var(--med-muted);
  background: transparent;
  border-radius: var(--med-radius-sm);
  font-size: 24rpx;
  line-height: 1.2;
  transition:
    color var(--med-motion-settle) var(--med-ease-out),
    opacity var(--med-motion-settle) var(--med-ease-out),
    transform var(--med-motion-settle) var(--med-ease-out);
}
.student-nav__item.active {
  color: var(--med-clinical);
  background: transparent;
  font-weight: 700;
}
@media screen and (min-width: 600px) and (max-width: 899px) {
  .student-nav {
    padding: 6px;
  }

  .student-nav__item {
    min-height: 64px;
    padding: 6px;
    gap: 3px;
    font-size: 15px;
  }
}
</style>
