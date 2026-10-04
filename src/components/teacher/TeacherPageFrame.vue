<template>
  <view
    class="teacher-frame safe-page"
    :class="{
      'teacher-frame--embedded': embedded,
      'teacher-frame--deck': managed,
      'teacher-frame--pbl': referenceLayout && !managed,
      'teacher-frame--insights': referenceLayout && !managed && active === 'insights',
      'teacher-frame--overview': referenceLayout && !managed && active === 'insights' && overviewContent,
      'teacher-frame--content': referenceLayout && active === 'content',
    }"
    @touchstart="touchStart"
    @touchmove="touchMove"
    @touchend="touchEnd"
    @touchcancel="cancelTouch"
  >
    <view class="teacher-frame__stage">
      <view
        class="teacher-frame__body"
        :class="{ 'teacher-frame__body--moving': motion.phase.value !== 'idle' }"
        :style="swipeStyle"
      >
        <view
          v-if="!referenceLayout && !managed"
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
          v-if="!fixedContent"
          class="teacher-frame__scroll"
          scroll-y
          :aria-label="title"
        >
          <view
            class="teacher-frame__content"
            :class="{ 'teacher-frame__content--deck': managed }"
            ><slot
          /></view>
        </scroll-view>
        <view
          v-else
          class="teacher-frame__fixed"
        >
          <view
            class="teacher-frame__content"
            :class="{ 'teacher-frame__content--deck': managed }"
            ><slot
          /></view>
        </view>
      </view>
    </view>
    <view
      v-if="!embedded"
      class="teacher-frame__navigation"
      role="navigation"
      aria-label="教师主导航"
      @touchstart.stop
    >
      <button
        v-for="item in navigation"
        :id="`teacher-nav-${item.workspace}`"
        :key="item.workspace"
        class="teacher-frame__nav-item"
        :class="{
          'teacher-frame__nav-item--active': active === item.workspace,
          'teacher-frame__nav-item--preview': previewWorkspace === item.workspace,
        }"
        :aria-current="active === item.workspace ? 'page' : undefined"
        @click="navigate(item.workspace)"
      >
        <image
          v-if="referenceLayout || managed"
          class="teacher-frame__nav-image"
          :src="
            active === 'insights'
              ? item.workspace === 'insights'
                ? '/static/insights-active.svg'
                : item.workspace === 'pbl'
                  ? '/static/insights-pbl.svg'
                  : item.image
              : item.image
          "
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
import { computed, getCurrentInstance, inject, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import MedIcon from '@/components/ui/MedIcon.vue'
import { logout } from '@/features/identity/public'
import { switchTeacherWorkspace, type TeacherWorkspace } from '@/platform/navigation/teacher'
import {
  clearTeacherSwipeEntry,
  prepareTeacherSwipeEntry,
  takeTeacherSwipeEntry,
} from '@/platform/navigation/teacherSwipeMotion'
import { useHorizontalSwipe, type HorizontalTouchEvent, type SwipeDirection } from './useHorizontalSwipe'
import { useTeacherSwipeMotion, type TeacherSwipeProgress } from './useTeacherSwipeMotion'
import { teacherNavigationKey, useTeacherScreenContext } from './teacherScreenContext'

const props = defineProps<{
  active: TeacherWorkspace
  title: string
  description?: string
  referenceLayout?: boolean
  fixedContent?: boolean
  overviewContent?: boolean
  panelSwipes?: boolean
  swipeContext?: string
  swipeDisabled?: boolean
  managed?: boolean
  preview?: TeacherWorkspace
}>()
const emit = defineEmits<{
  horizontalSwipe: [direction: SwipeDirection]
  swipeProgress: [value: TeacherSwipeProgress]
  navigate: [workspace: TeacherWorkspace]
}>()
const embedded = Boolean(useTeacherScreenContext())
const navigateInDeck = inject(teacherNavigationKey, undefined)
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
  if (props.managed) {
    if (navigateInDeck) navigateInDeck(workspace)
    else emit('navigate', workspace)
    return
  }
  if (workspace === props.active || motion.busy.value) return
  clearTeacherSwipeEntry()
  cancelTouch()
  switchTeacherWorkspace(workspace)
}
function nextWorkspace(direction: SwipeDirection) {
  const index = navigation.findIndex((item) => item.workspace === props.active)
  return navigation[index + (direction === 'left' ? 1 : -1)]?.workspace
}
function readViewportWidth() {
  const info = uni.getWindowInfo?.() ?? uni.getSystemInfoSync?.()
  return info?.windowWidth && info.windowWidth > 0 ? info.windowWidth : 375
}
const width = ref(readViewportWidth())
const viewportWidth = () => width.value
const instance = getCurrentInstance()
const motion = useTeacherSwipeMotion({
  width: viewportWidth,
  canSwipe: (direction) => !props.swipeDisabled && Boolean(props.panelSwipes || nextWorkspace(direction)),
  progress: (value) => emit('swipeProgress', value),
  commit: (direction) => {
    if (props.panelSwipes) {
      emit('swipeProgress', undefined)
      emit('horizontalSwipe', direction)
      return
    }
    const next = nextWorkspace(direction)
    if (next) {
      prepareTeacherSwipeEntry(next, direction)
      switchTeacherWorkspace(next)
    }
  },
})
const swipeStyle = motion.style
const previewWorkspace = computed(() =>
  props.managed
    ? props.preview
    : !props.panelSwipes && motion.phase.value !== 'entering' && motion.direction.value && motion.progress.value > 0.08
      ? nextWorkspace(motion.direction.value)
      : undefined,
)
const swipe = useHorizontalSwipe(motion.release, { onDrag: motion.drag, onCancel: motion.cancel, viewportWidth })
function touchStart(event: HorizontalTouchEvent) {
  if (embedded || props.managed) return
  if (!motion.busy.value && !props.swipeDisabled) swipe.touchstart(event)
}
function touchMove(event: HorizontalTouchEvent) {
  swipe.touchmove(event)
}
function touchEnd(event: HorizontalTouchEvent) {
  swipe.touchend(event)
}
function cancelTouch() {
  if (embedded || props.managed) return
  swipe.cancel()
  motion.cancel()
}
function afterRender(callback: () => void) {
  if (instance?.proxy) instance.proxy.$nextTick(callback)
  else nextTick(callback)
}
const incoming = takeTeacherSwipeEntry(props.active)
const startEntry = incoming ? motion.enter(incoming) : undefined
onMounted(() => {
  if (startEntry) afterRender(startEntry)
  uni.onWindowResize?.(resize)
})
function resize() {
  swipe.cancel()
  motion.reset()
  width.value = readViewportWidth()
}
onUnmounted(() => uni.offWindowResize?.(resize))
watch(
  () => props.swipeContext,
  () => {
    if (motion.phase.value === 'waiting' && motion.direction.value) afterRender(motion.enter(motion.direction.value))
  },
  { flush: 'post' },
)
watch(
  () => props.swipeDisabled,
  (disabled) => {
    if (disabled) {
      swipe.cancel()
      motion.reset()
    }
  },
)
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
.teacher-frame__stage {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
.teacher-frame--embedded {
  height: 100%;
}
.teacher-frame__body {
  display: flex;
  flex: 1;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
}
.teacher-frame__body--moving {
  will-change: transform;
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
.teacher-frame__fixed {
  flex: 1;
  height: 0;
  min-height: 0;
  overflow: hidden;
}
.teacher-frame__fixed .teacher-frame__content {
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
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
  transition:
    color 160ms ease,
    transform 160ms ease;
}
.teacher-frame__nav-item--preview {
  color: var(--med-brand);
  transform: scale(1.06);
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
.teacher-frame--pbl .teacher-frame__fixed .teacher-frame__content {
  display: flex;
  flex-direction: column;
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
.teacher-frame--insights {
  --med-text: #0000b4;
  --med-ink: #0000b4;
  --med-muted: #7b88c2;
  --med-page: #eaf8ff;
  --insights-ink: #0000b4;
  background: linear-gradient(115deg, #edfaff, #e6f6ff 55%, #eefaff);
}
.teacher-frame--insights .teacher-frame__content {
  padding: 0 22rpx 28rpx;
}
.teacher-frame--insights .teacher-frame__fixed .teacher-frame__content {
  padding-bottom: 64rpx;
}
.teacher-frame--overview .teacher-frame__fixed .teacher-frame__content {
  padding-bottom: 18rpx;
}
.teacher-frame--insights .teacher-frame__navigation {
  border-color: #b6e6ff;
}
.teacher-frame--insights .teacher-frame__nav-item--active {
  color: #00c6d1;
}
.teacher-frame--content {
  --med-text: #101449;
  --med-muted: #7184b3;
  --med-page: #eaf9ff;
  --med-border: #c5e8ff;
  background: #eaf9ff;
}
.teacher-frame--content .teacher-frame__content {
  box-sizing: border-box;
  width: 100%;
  max-width: none;
  padding: 0;
}
.teacher-frame--pbl .teacher-frame__nav-item--preview {
  color: #00b9c2;
}
@media (prefers-reduced-motion: reduce) {
  .teacher-frame__body,
  .teacher-frame__nav-item {
    transition: none !important;
  }
}
.teacher-frame--embedded {
  min-height: 0;
}
.teacher-frame .teacher-frame__content.teacher-frame__content--deck {
  height: 100%;
  padding: 0;
  max-width: none;
}
.teacher-frame--deck .teacher-frame__navigation {
  padding: 14rpx 28rpx calc(14rpx + env(safe-area-inset-bottom));
  border-color: #d3effb;
  background: #fff;
}
.teacher-frame--deck .teacher-frame__nav-item {
  color: #7888b2;
  font-size: 26rpx;
  gap: 8rpx;
}
.teacher-frame--deck .teacher-frame__nav-item--active,
.teacher-frame--deck .teacher-frame__nav-item--preview {
  color: #00b9c2;
  background: transparent;
}
</style>
