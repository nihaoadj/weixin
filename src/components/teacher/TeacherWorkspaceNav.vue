<template>
  <view
    class="teacher-nav"
    role="navigation"
    aria-label="教师主导航"
  >
    <button
      v-for="item in items"
      :key="item.key"
      hover-class="is-pressed"
      :hover-start-time="0"
      :hover-stay-time="80"
      class="teacher-nav__item"
      :class="{ active: active === item.key }"
      :aria-current="active === item.key ? 'page' : undefined"
      role="button"
      tabindex="0"
      @click="$emit('change', item.key)"
      @keydown.enter.prevent="$emit('change', item.key)"
      @keydown.space.prevent="$emit('change', item.key)"
    >
      <MedIcon
        :name="item.icon"
        size="sm"
      />
      <text>{{ item.label }}</text>
    </button>
  </view>
</template>

<script setup lang="ts">
import MedIcon from '@/components/ui/MedIcon.vue'

export type TeacherWorkspace = 'overview' | 'reports' | 'problems' | 'pbl'
defineProps<{ active: TeacherWorkspace }>()
defineEmits<{ change: [workspace: TeacherWorkspace] }>()
const items = [
  { key: 'overview' as const, label: '待办', icon: 'teacher' as const },
  { key: 'reports' as const, label: '学情', icon: 'report' as const },
  { key: 'problems' as const, label: '内容', icon: 'book' as const },
  { key: 'pbl' as const, label: 'PBL', icon: 'report' as const },
]
</script>

<style scoped>
.teacher-nav {
  display: flex;
  padding: 8rpx 16rpx calc(8rpx + env(safe-area-inset-bottom));
  gap: 12rpx;
  background: var(--med-surface);
  border-top: 1rpx solid var(--med-border);
}
.teacher-nav__item {
  display: flex;
  min-width: 0;
  min-height: 56px;
  margin: 0;
  padding: 8rpx;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6rpx;
  color: var(--med-muted);
  background: transparent;
  border-radius: var(--med-radius-sm);
  font-size: 24rpx;
  line-height: 1.2;
}
.teacher-nav__item.active {
  color: var(--med-clinical);
  background: var(--med-wash);
  font-weight: 700;
}
@media screen and (max-width: 360px) {
  .teacher-nav__item {
    font-size: 12px;
  }
}
@media screen and (min-width: 600px) {
  .teacher-nav__item {
    font-size: 15px;
  }
}
@media screen and (min-width: 900px) {
  .teacher-nav {
    height: 100%;
    padding: 24px 12px;
    box-sizing: border-box;
    flex-direction: column;
    gap: 8px;
    border-top: 0;
    border-right: 1px solid var(--med-border);
  }
  .teacher-nav__item {
    min-height: 52px;
    padding: 12px 16px;
    flex: none;
    flex-direction: row;
    justify-content: flex-start;
    gap: 12px;
    border-radius: 8px;
  }
}
</style>
