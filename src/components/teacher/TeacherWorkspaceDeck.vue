<template>
  <view
    class="teacher-deck-shell"
    :data-workspace="workspace"
  >
    <view
      class="teacher-deck"
      @touchstart="touchStart"
      @touchmove="motion.swipe.touchmove"
      @touchend="motion.swipe.touchend"
      @touchcancel="motion.reset"
    >
      <view
        v-for="item in mounted"
        :key="`${generation}:${item}`"
        class="teacher-deck__pane"
        :class="{
          'teacher-deck__pane--inactive': item !== current,
          'teacher-deck__pane--hidden': item !== current && motion.phase.value === 'idle',
          'teacher-deck__pane--moving': motion.phase.value !== 'idle',
        }"
        :style="motion.paneStyle(item)"
        :aria-hidden="item !== current"
      >
        <TeacherWorkspacePane
          :id="`teacher-pane-${item}`"
          :index="item"
          :current="current"
          :context="context(item)"
        />
      </view>
    </view>
    <view
      class="teacher-deck-navigation"
      role="navigation"
      aria-label="教师主导航"
    >
      <button
        v-for="item in navigation"
        :id="`teacher-nav-${item.workspace}`"
        :key="item.workspace"
        class="teacher-deck-navigation__item"
        :class="{
          'teacher-deck-navigation__item--active': workspace === item.workspace,
          'teacher-deck-navigation__item--preview': preview === item.workspace,
        }"
        :data-workspace="item.workspace"
        :aria-current="workspace === item.workspace ? 'page' : undefined"
        @tap="tapNavigation"
      >
        <image
          class="teacher-deck-navigation__image"
          :src="workspace === item.workspace ? item.activeImage : item.image"
          mode="aspectFit"
        />
        <text>{{ item.label }}</text>
      </button>
    </view>
  </view>
</template>
<script setup lang="ts">
import { computed, onMounted, onUnmounted, provide, ref, watch } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import TeacherWorkspacePane from './TeacherWorkspacePane.vue'
import { useTeacherDeckMotion } from './useTeacherDeckMotion'
import type { HorizontalTouchEvent } from './useHorizontalSwipe'
import { teacherNavigationKey, type InsightsSelection, type TeacherScreenContext } from './teacherScreenContext'
import { getSession } from '@/features/identity/public'
import { readTeacherInsightsPreference } from '@/platform/navigation/teacherPreferences'
import type { TeacherInsightsPanel, TeacherWorkspace } from '@/platform/navigation/teacher'
import { parseTeacherWorkspaceTarget } from '@/platform/navigation/teacher'
const props = defineProps<{
  initialWorkspace: 'pbl' | 'insights' | 'content'
  query: Record<string, string | undefined>
}>()
const panels: TeacherInsightsPanel[] = ['overview', 'knowledge', 'students']
const navigation = [
  { workspace: 'pbl', label: 'PBL', image: '/static/insights-pbl.svg', activeImage: '/static/pbl-reference-cap.svg' },
  {
    workspace: 'insights',
    label: '学情',
    image: '/static/pbl-reference-insights.svg',
    activeImage: '/static/insights-active.svg',
  },
  {
    workspace: 'content',
    label: '内容',
    image: '/static/pbl-reference-content.svg',
    activeImage: '/static/teacher-content-active.svg',
  },
]
const entry = parseTeacherWorkspaceTarget({ ...props.query, tab: props.initialWorkspace })
const entryWorkspace = entry.workspace === 'overview' ? 'pbl' : entry.workspace
function initialIndex() {
  if (entryWorkspace === 'pbl') return 0
  if (entryWorkspace === 'content') return 4
  const actor = getSession()
  const panel =
    (entry.workspace === 'insights' ? entry.panel : undefined) ||
    (actor ? readTeacherInsightsPreference(actor.openid)?.panel : undefined)
  return panel === 'knowledge' ? 2 : panel === 'students' || panel === 'progress' ? 3 : 1
}
const current = ref(initialIndex())
const identity = ref(getSession()?.openid || '')
const generation = ref(0)
const mounted = ref<number[]>([])
const ready = ref<number[]>([])
const blocked = ref(false)
const show = ref(0)
const insights = ref<InsightsSelection>()
const width = ref(uni.getWindowInfo?.().windowWidth || uni.getSystemInfoSync?.().windowWidth || 375)
const workspace = computed(() => (current.value === 0 ? 'pbl' : current.value === 4 ? 'content' : 'insights'))
const motion = useTeacherDeckMotion({
  current: () => current.value,
  width: () => width.value,
  allowed: (index) => index >= 0 && index <= 4 && !blocked.value && ready.value.includes(index),
  commit: (index) => {
    current.value = index
  },
})
const preview = computed(() => {
  if (motion.phase.value === 'idle') return undefined
  const index = Math.max(0, Math.min(4, Math.round(motion.position.value)))
  return index === 0 ? 'pbl' : index === 4 ? 'content' : 'insights'
})
function activate(index: number) {
  if (blocked.value || index < 0 || index > 4) return
  motion.reset()
  if (!mounted.value.includes(index)) mounted.value = [...mounted.value, index].sort()
  current.value = index
}
function preload() {
  mounted.value = [...new Set([...mounted.value, current.value, current.value - 1, current.value + 1])]
    .filter((index) => index >= 0 && index <= 4)
    .sort()
}
function navigate(target: TeacherWorkspace) {
  if (blocked.value) return
  const index = target === 'pbl' || target === 'overview' ? 0 : target === 'content' ? 4 : 1
  activate(index)
}
provide(teacherNavigationKey, navigate)
function tapNavigation(event: { currentTarget?: { dataset?: { workspace?: string } } }) {
  const target = event.currentTarget?.dataset?.workspace
  if (target === 'pbl' || target === 'insights' || target === 'content') navigate(target)
}
function selectPanel(panel: TeacherInsightsPanel) {
  const index = panels.indexOf(panel) + 1
  if (index < 1) return
  activate(index)
}
function context(index: number): Omit<TeacherScreenContext, 'active'> {
  const epoch = generation.value
  const owner = index === 0 ? 'pbl' : index === 4 ? 'content' : 'insights'
  return {
    show,
    insights,
    position: motion.position,
    panel: panels[index - 1],
    query: {
      ...(owner === entryWorkspace ? props.query : {}),
      ...(owner === 'insights' ? { panel: panels[index - 1] } : {}),
    },
    selectPanel,
    block: (value) => {
      if (index === current.value) {
        blocked.value = value
        if (value) motion.reset()
      }
    },
    ready: () => {
      if (epoch !== generation.value) return
      if (!ready.value.includes(index)) ready.value = [...ready.value, index]
    },
  }
}
function touchStart(event: HorizontalTouchEvent) {
  if (!blocked.value && motion.phase.value !== 'settling') motion.swipe.touchstart(event)
}
function resize() {
  motion.reset()
  width.value = uni.getWindowInfo?.().windowWidth || 375
}
watch(current, () => {
  blocked.value = false
  preload()
  uni.setNavigationBarTitle({
    title: workspace.value === 'pbl' ? 'PBL' : workspace.value === 'insights' ? '学情' : '内容',
  })
})
onShow(() => {
  const actor = getSession()
  if ((actor?.openid || '') !== identity.value || actor?.role !== 'teacher') {
    motion.reset()
    generation.value += 1
    mounted.value = []
    ready.value = []
    insights.value = undefined
    identity.value = actor?.openid || ''
    current.value = initialIndex()
    preload()
  }
  show.value += 1
})
preload()
onMounted(() => uni.onWindowResize?.(resize))
onUnmounted(() => uni.offWindowResize?.(resize))
</script>
<style scoped>
.teacher-deck-shell {
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--window-top, 0px));
  min-height: 0;
  overflow: hidden;
  background: #eaf8ff;
}
.teacher-deck {
  position: relative;
  width: 100%;
  flex: 1;
  height: 0;
  min-height: 0;
  overflow: hidden;
  background: #eaf8ff;
}
.teacher-deck-navigation {
  position: relative;
  z-index: 2;
  display: flex;
  flex: none;
  gap: 8rpx;
  padding: 14rpx 28rpx calc(14rpx + env(safe-area-inset-bottom));
  border-top: 1rpx solid #d3effb;
  background: #fff;
}
.teacher-deck-navigation__item {
  display: flex;
  flex: 1;
  min-width: 0;
  min-height: 56px;
  margin: 0;
  padding: 8rpx;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 8rpx;
  background: transparent;
  color: #7888b2;
  font-size: 26rpx;
  line-height: 1.4;
  border-radius: 12rpx;
}
.teacher-deck-navigation__item::after {
  border: 0;
}
.teacher-deck-navigation__item--active,
.teacher-deck-navigation__item--preview {
  color: #00b9c2;
}
.teacher-deck-navigation__item--active {
  font-weight: 600;
}
.teacher-deck-navigation__image {
  width: 48rpx;
  height: 48rpx;
}
.teacher-deck__pane {
  position: absolute;
  inset: 0;
  height: 100%;
  width: 100%;
}
.teacher-deck__pane--inactive {
  pointer-events: none;
}
.teacher-deck__pane--hidden {
  visibility: hidden;
}
.teacher-deck__pane--moving {
  will-change: transform;
}
@media (prefers-reduced-motion: reduce) {
  .teacher-deck__pane {
    transition: none !important;
  }
}
</style>
