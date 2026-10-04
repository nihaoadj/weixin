<template>
  <view
    class="teacher-frame safe-page"
    :class="{ 'teacher-frame--pbl': referenceLayout }"
  >
    <view
      v-if="!referenceLayout"
      class="teacher-frame__header"
    >
      <view class="teacher-frame__heading">
        <text
          class="teacher-frame__title"
          role="heading"
          aria-level="1"
          >{{ title }}</text
        >
        <text
          v-if="description"
          class="teacher-frame__description"
          >{{ description }}</text
        >
      </view>
      <button
        class="teacher-frame__account"
        @click="logout"
      >
        退出
      </button>
    </view>
    <scroll-view
      class="teacher-frame__scroll"
      scroll-y
      :aria-label="title"
    >
      <view class="teacher-frame__content"><slot /></view>
    </scroll-view>
    <view
      class="teacher-frame__navigation"
      role="navigation"
      aria-label="教师主导航"
    >
      <button
        v-for="item in navigation"
        :key="item.workspace"
        class="teacher-frame__nav-item"
        :class="{ 'teacher-frame__nav-item--active': active === item.workspace }"
        :aria-current="active === item.workspace ? 'page' : undefined"
        @click="navigate(item.workspace)"
      >
        <image
          v-if="referenceLayout"
          class="teacher-frame__nav-image"
          :src="item.image"
          mode="aspectFit"
        />
        <MedIcon
          v-else
          :name="item.icon"
          size="md"
        />
        <text>{{ item.label }}</text>
      </button>
    </view>
  </view>
</template>

<script setup lang="ts">
import MedIcon from '@/components/ui/MedIcon.vue'
import { logout } from '@/features/identity/public'
import { switchTeacherWorkspace, type TeacherWorkspace } from '@/platform/navigation/teacher'

const props = defineProps<{
  active: TeacherWorkspace
  title: string
  description?: string
  referenceLayout?: boolean
}>()
const navigation = [
  { workspace: 'pbl' as const, label: 'PBL', icon: 'classroom' as const, image: '/static/pbl-reference-cap.svg' },
  {
    workspace: 'insights' as const,
    label: '学情',
    icon: 'report' as const,
    image: '/static/pbl-reference-insights.svg',
  },
  { workspace: 'content' as const, label: '内容', icon: 'book' as const, image: '/static/pbl-reference-content.svg' },
]
function navigate(workspace: TeacherWorkspace) {
  if (workspace === props.active) return
  switchTeacherWorkspace(workspace)
}
</script>

<style scoped>
.teacher-frame {
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--window-top, 0px));
  overflow: hidden;
  background: var(--med-page);
  color: var(--med-text);
}
.teacher-frame__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24rpx;
  padding: 28rpx 32rpx 20rpx;
  background: var(--med-surface);
  border-bottom: 1rpx solid var(--med-border);
}
.teacher-frame__heading {
  min-width: 0;
}
.teacher-frame__title {
  display: block;
  font-size: 38rpx;
  font-weight: 650;
  line-height: 1.4;
}
.teacher-frame__description {
  display: block;
  margin-top: 6rpx;
  color: var(--med-muted);
  font-size: 26rpx;
  line-height: 1.6;
}
.teacher-frame__account {
  flex: none;
  min-width: 44px;
  min-height: 44px;
  padding: 0 16rpx;
  background: transparent;
  color: var(--med-muted);
  font-size: 26rpx;
}
.teacher-frame__account::after,
.teacher-frame__nav-item::after {
  border: 0;
}
.teacher-frame__scroll {
  min-height: 0;
  flex: 1;
  height: 0;
}
.teacher-frame__content {
  max-width: 920px;
  margin: 0 auto;
  padding: 24rpx 32rpx 40rpx;
}
.teacher-frame__navigation {
  display: flex;
  flex: none;
  gap: 8rpx;
  padding: 8rpx 16rpx calc(8rpx + env(safe-area-inset-bottom));
  border-top: 1rpx solid var(--med-border);
  background: var(--med-surface);
}
.teacher-frame__nav-item {
  display: flex;
  flex: 1;
  min-width: 0;
  min-height: 56px;
  margin: 0;
  padding: 8rpx;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 6rpx;
  background: transparent;
  color: var(--med-muted);
  font-size: 24rpx;
  line-height: 1.4;
  border-radius: 12rpx;
}
.teacher-frame__nav-item--active {
  color: var(--med-brand);
  background: var(--med-brand-soft);
  font-weight: 600;
}
@media screen and (min-width: 600px) {
  .teacher-frame__header {
    padding-inline: 32px;
  }
  .teacher-frame__content {
    padding: 28px 32px 40px;
  }
}
.teacher-frame--pbl {
  min-height: 0;
  --med-text: #171a65;
  --med-ink: #080b63;
  --med-muted: #7488b5;
  --med-border: #cbe2ff;
  --med-page: #eaf9ff;
  --med-brand: #00b9c2;
  background: linear-gradient(110deg, #eafaff, #e5f6ff 55%, #eefaff);
}
.teacher-frame--pbl .teacher-frame__content {
  padding: 0 24rpx 28rpx;
}
.teacher-frame--pbl .teacher-frame__navigation {
  padding: 14rpx 28rpx calc(14rpx + env(safe-area-inset-bottom));
  border-color: #d3effb;
}
.teacher-frame--pbl .teacher-frame__nav-item {
  color: #7888b2;
  font-size: 26rpx;
  gap: 8rpx;
}
.teacher-frame--pbl .teacher-frame__nav-item--active {
  color: #00b9c2;
  background: transparent;
}
.teacher-frame__nav-image {
  width: 48rpx;
  height: 48rpx;
}
</style>
