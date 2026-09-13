<template>
  <view class="knowledge-tree">
    <view class="tree-heading">
      <view class="heading-copy">
        <text class="eyebrow-label">PATHOLOGY KNOWLEDGE TREE</text>
        <text class="title">从概念主干，走到病理机制</text>
        <text class="muted">节点关系组织学习路径；打开节点本身不会改变掌握状态。</text>
      </view>
      <button
        v-if="recommendedPoint"
        class="next-link"
        :aria-label="`查看推荐知识点：${recommendedPoint.title}`"
        @click="openPoint(recommendedPoint.code)"
      >
        <text>建议下一步</text><text>{{ recommendedPoint.title }} ›</text>
      </button>
    </view>

    <view
      v-if="error"
      class="tree-error"
      role="alert"
    >
      <text>{{ error }}</text>
      <button @click="refresh">重新加载</button>
    </view>
    <view
      v-else-if="loading"
      class="tree-loading"
    >
      <text>正在整理知识结构…</text>
    </view>
    <template v-else-if="graph">
      <view
        v-if="graph.issues.length"
        class="graph-notice"
        role="status"
      >
        部分知识关系暂无法展示，其他节点仍可正常学习。
      </view>

      <view
        class="module-rail"
        role="tablist"
        aria-label="选择知识模块"
      >
        <button
          v-for="module in graph.modules"
          :key="module.code"
          class="module-tab"
          :class="{ active: selectedModule === module.code && !showAll }"
          role="tab"
          :aria-selected="selectedModule === module.code && !showAll"
          @click="focusModule(module.code)"
        >
          <text>{{ module.title }}</text>
          <text class="module-count">{{ module.stableCount }}/{{ module.pointCodes.length }}</text>
        </button>
      </view>

      <view class="tree-toolbar">
        <view class="tree-mode">
          <button
            class="mode-button"
            :class="{ active: !showAll }"
            :aria-pressed="!showAll"
            @click="focusRecommended"
          >
            聚焦建议
          </button>
          <button
            class="mode-button"
            :class="{ active: showAll }"
            :aria-pressed="showAll"
            @click="showWholeTree"
          >
            查看全树
          </button>
        </view>
        <view
          class="zoom-controls"
          aria-label="知识树缩放"
        >
          <button
            aria-label="缩小知识树"
            @click="zoomBy(-0.15)"
          >
            −
          </button>
          <text>{{ Math.round(scale * 100) }}%</text>
          <button
            aria-label="放大知识树"
            @click="zoomBy(0.15)"
          >
            +
          </button>
          <button
            class="reset-button"
            @click="resetViewport"
          >
            复位
          </button>
        </view>
      </view>

      <view
        class="tree-viewport"
        aria-label="可拖拽和缩放的病理学知识树"
        @touchstart="beginGesture"
        @touchmove.stop.prevent="moveGesture"
        @touchend="endGesture"
        @touchcancel="endGesture"
        @wheel.prevent="wheelZoom"
      >
        <view
          class="tree-plane"
          :class="{ 'is-moving': moving }"
          :style="planeStyle"
        >
          <view
            v-for="edge in visibleEdges"
            :key="edge.id"
            class="tree-edge"
            :class="[`edge-${edge.kind}`, { cross: edge.crossModule }]"
            :style="edgeStyle(edge)"
          />
          <button
            v-for="node in visibleNodes"
            :key="node.id"
            class="tree-node"
            :class="[
              `node-${node.kind}`,
              node.point ? `status-${node.point.status}` : '',
              { 'is-focused-module': node.kind === 'module' && node.id === selectedModule && !showAll },
            ]"
            :style="nodeStyle(node.id)"
            :aria-label="nodeLabel(node.id)"
            @click="activateNode(node.id)"
          >
            <template v-if="node.kind === 'point' && node.point">
              <text class="node-state">{{ statusMark(node.point.status) }}</text>
              <view class="node-copy">
                <text class="node-title">{{ node.title }}</text>
                <text class="node-level">第 {{ node.depth + 1 }} 层</text>
              </view>
              <text class="node-status">{{ statusLabel(node.point.status) }}</text>
            </template>
            <template v-else>
              <text class="node-title">{{ node.title }}</text>
              <text
                v-if="node.kind === 'module'"
                class="node-status"
              >
                {{ moduleSummary(node.id) }}
              </text>
              <text
                v-else
                class="node-status"
              >
                5 个知识模块
              </text>
            </template>
          </button>
        </view>
        <text class="gesture-hint">单指拖动 · 双指缩放 · 点击节点学习</text>
      </view>

      <view
        class="state-legend"
        aria-label="知识状态说明"
      >
        <text class="legend-title">学习状态</text>
        <text
          v-for="item in statusItems"
          :key="item.status"
          class="legend-item"
        >
          <text :class="`legend-mark status-${item.status}`">{{ item.mark }}</text
          >{{ item.label }}
        </text>
      </view>
      <text class="tree-reference">{{ mapPoints[0]?.reference }}</text>
    </template>
    <view
      v-else
      class="tree-empty"
    >
      暂无可展示的知识结构。
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  buildKnowledgeGraph,
  getKnowledgeMap,
  type KnowledgeGraphEdge,
  type KnowledgeMapPoint,
} from '@/features/learning/public'
import { goDetail, ROUTES } from '@/platform/navigation'

interface Position {
  x: number
  y: number
}

interface TouchLike {
  clientX: number
  clientY: number
}

interface GestureEvent {
  touches: ArrayLike<TouchLike>
}

interface WheelLikeEvent {
  deltaY: number
}

const WORLD_WIDTH = 1230
const WORLD_HEIGHT = 1160
const NODE_WIDTH = 208
const NODE_HEIGHT = 72
const MIN_SCALE = 0.6
const MAX_SCALE = 1.8

const mapPoints = ref<KnowledgeMapPoint[]>([])
const loading = ref(false)
const error = ref('')
const selectedModule = ref('')
const showAll = ref(false)
const scale = ref(1)
const offsetX = ref(0)
const offsetY = ref(0)
const moving = ref(false)
const gesture = ref({ x: 0, y: 0, distance: 0, scale: 1 })

const graph = computed(() => (mapPoints.value.length ? buildKnowledgeGraph(mapPoints.value) : undefined))
const recommendedPoint = computed(() =>
  mapPoints.value.find((point) => point.code === graph.value?.recommendedPointCode),
)
const selectedPoints = computed(
  () => graph.value?.modules.find((module) => module.code === selectedModule.value)?.pointCodes || [],
)
const visibleIds = computed(() => {
  if (!graph.value) return new Set<string>()

  if (showAll.value) {
    return new Set([
      graph.value.rootId,
      ...graph.value.modules.map((module) => module.code),
      ...mapPoints.value.map((point) => point.code),
    ])
  }

  return new Set([graph.value.rootId, ...(selectedModule.value ? [selectedModule.value] : []), ...selectedPoints.value])
})
const visibleNodes = computed(() => graph.value?.nodes.filter((node) => visibleIds.value.has(node.id)) || [])
const visibleEdges = computed(
  () => graph.value?.edges.filter((edge) => visibleIds.value.has(edge.from) && visibleIds.value.has(edge.to)) || [],
)
const planeStyle = computed(() => ({
  width: `${WORLD_WIDTH}px`,
  height: `${WORLD_HEIGHT}px`,
  transform: `translate(${offsetX.value}px, ${offsetY.value}px) scale(${scale.value})`,
}))
const statusItems: Array<{ status: KnowledgeMapPoint['status']; mark: string; label: string }> = [
  { status: 'not_started', mark: '○', label: '未开始' },
  { status: 'weak', mark: '!', label: '薄弱' },
  { status: 'learning', mark: '·', label: '学习中' },
  { status: 'due', mark: '◷', label: '待复习' },
  { status: 'stable', mark: '✓', label: '相对稳定' },
]

function positionFor(id: string): Position {
  if (!graph.value) return { x: 0, y: 0 }
  if (id === graph.value.rootId) return { x: (WORLD_WIDTH - NODE_WIDTH) / 2, y: 40 }
  const moduleIndex = graph.value.modules.findIndex((module) => module.code === id)
  if (moduleIndex >= 0) {
    if (showAll.value) return { x: 30 + moduleIndex * 235, y: 185 }
    const activeIndex = graph.value.modules.findIndex((module) => module.code === selectedModule.value)
    return {
      x: (WORLD_WIDTH - NODE_WIDTH) / 2 + (moduleIndex - Math.max(activeIndex, 0)) * 238,
      y: 185,
    }
  }

  const node = graph.value.nodes.find((item) => item.id === id)
  if (!node?.point) return { x: 0, y: 0 }
  const module = graph.value.modules.find((item) => item.code === node.moduleCode)
  const inLevel = graph.value.nodes.filter(
    (item) => item.kind === 'point' && item.moduleCode === node.moduleCode && item.depth === node.depth,
  )
  const levelIndex = inLevel.findIndex((item) => item.id === node.id)
  if (!showAll.value) {
    return {
      x: (WORLD_WIDTH - NODE_WIDTH) / 2 + (levelIndex - (inLevel.length - 1) / 2) * 232,
      y: 332 + node.depth * 142,
    }
  }
  const moduleIndexForPoint = module?.order || 0
  return {
    x: 30 + moduleIndexForPoint * 235,
    y: 334 + node.depth * 176 + levelIndex * 78,
  }
}

function nodeStyle(id: string) {
  const position = positionFor(id)
  return { left: `${position.x}px`, top: `${position.y}px` }
}

function edgeStyle(edge: KnowledgeGraphEdge) {
  const from = positionFor(edge.from)
  const to = positionFor(edge.to)
  const startX = from.x + NODE_WIDTH / 2
  const startY = from.y + NODE_HEIGHT
  const endX = to.x + NODE_WIDTH / 2
  const endY = to.y
  const deltaX = endX - startX
  const deltaY = endY - startY
  const length = Math.sqrt(deltaX * deltaX + deltaY * deltaY)
  const angle = (Math.atan2(deltaY, deltaX) * 180) / Math.PI
  return {
    left: `${startX}px`,
    top: `${startY}px`,
    width: `${length}px`,
    transform: `rotate(${angle}deg)`,
  }
}

function focusModule(code: string) {
  selectedModule.value = code
  showAll.value = false
  setFocusedViewport()
}

function focusRecommended() {
  selectedModule.value = graph.value?.recommendedModuleCode || graph.value?.modules[0]?.code || ''
  showAll.value = false
  setFocusedViewport()
}

function showWholeTree() {
  showAll.value = true
  setWholeTreeViewport()
}

function resetViewport() {
  if (showAll.value) setWholeTreeViewport()
  else setFocusedViewport()
}

function setFocusedViewport() {
  scale.value = 0.92
  offsetX.value = 0
  offsetY.value = 0
}

function setWholeTreeViewport() {
  scale.value = 0.62
  offsetX.value = 0
  offsetY.value = 0
}

function zoomBy(amount: number) {
  scale.value = Math.min(MAX_SCALE, Math.max(MIN_SCALE, Number((scale.value + amount).toFixed(2))))
}

function touchDistance(touches: ArrayLike<TouchLike>): number {
  if (touches.length < 2) return 0
  const first = touches[0]
  const second = touches[1]
  return Math.hypot(second.clientX - first.clientX, second.clientY - first.clientY)
}

function beginGesture(event: GestureEvent) {
  const touches = event.touches
  moving.value = false
  gesture.value = {
    x: touches[0]?.clientX || 0,
    y: touches[0]?.clientY || 0,
    distance: touchDistance(touches),
    scale: scale.value,
  }
}

function moveGesture(event: GestureEvent) {
  const touches = event.touches
  if (!touches.length) return
  if (touches.length > 1 && gesture.value.distance) {
    const nextDistance = touchDistance(touches)
    scale.value = Math.min(
      MAX_SCALE,
      Math.max(MIN_SCALE, gesture.value.scale * (nextDistance / gesture.value.distance)),
    )
    moving.value = true
    return
  }
  offsetX.value = Math.min(
    100,
    Math.max(-WORLD_WIDTH * scale.value + 220, offsetX.value + touches[0].clientX - gesture.value.x),
  )
  offsetY.value = Math.min(
    80,
    Math.max(-WORLD_HEIGHT * scale.value + 240, offsetY.value + touches[0].clientY - gesture.value.y),
  )
  gesture.value.x = touches[0].clientX
  gesture.value.y = touches[0].clientY
  moving.value = true
}

function endGesture() {
  setTimeout(() => {
    moving.value = false
  }, 0)
}

function wheelZoom(event: WheelLikeEvent) {
  zoomBy(event.deltaY < 0 ? 0.1 : -0.1)
}

function activateNode(id: string) {
  const node = graph.value?.nodes.find((item) => item.id === id)
  if (!node || moving.value) return
  if (node.kind === 'module') focusModule(node.id)
  if (node.kind === 'point') openPoint(node.id)
}

function openPoint(code: string) {
  goDetail(ROUTES.studentKnowledgeNode, { topicCode: code })
}

function moduleSummary(code: string) {
  const module = graph.value?.modules.find((item) => item.code === code)
  return module ? `${module.stableCount}/${module.pointCodes.length} 相对稳定` : ''
}

function statusMark(status: KnowledgeMapPoint['status']) {
  return statusItems.find((item) => item.status === status)?.mark || '○'
}

function statusLabel(status: KnowledgeMapPoint['status']) {
  return statusItems.find((item) => item.status === status)?.label || '未开始'
}

function nodeLabel(id: string) {
  const node = graph.value?.nodes.find((item) => item.id === id)
  if (!node) return ''
  if (!node.point) return `${node.title}，${node.kind === 'module' ? '点击聚焦模块' : '知识树根节点'}`
  const prerequisites = (node.point.prerequisiteCodes || []).length
  return `${node.point.systemLabel}，${node.title}，${statusLabel(node.point.status)}，${
    prerequisites ? `有 ${prerequisites} 个前置知识` : '可直接开始'
  }，点击进入学习`
}

async function refresh() {
  if (loading.value) return
  loading.value = true
  error.value = ''
  try {
    mapPoints.value = await getKnowledgeMap()
    if (!selectedModule.value) focusRecommended()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '知识结构加载失败，请稍后重试。'
  } finally {
    loading.value = false
  }
}

defineExpose({ refresh })
onMounted(() => void refresh())
</script>

<style scoped>
.knowledge-tree {
  display: flex;
  max-width: 920px;
  margin: 0 auto 32rpx;
  flex-direction: column;
  gap: 18rpx;
}
.tree-heading {
  display: flex;
  padding: 16rpx 0 6rpx;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20rpx;
  border-bottom: 1rpx solid var(--med-border);
}
.heading-copy {
  display: flex;
  max-width: 600rpx;
  flex-direction: column;
  gap: 8rpx;
}
.title {
  color: var(--med-ink);
  font-size: 36rpx;
  font-weight: 800;
  letter-spacing: -1rpx;
}
.muted,
.tree-reference {
  color: var(--med-muted);
  font-size: 22rpx;
  line-height: 1.6;
}
.next-link {
  display: flex;
  min-width: 150rpx;
  min-height: 72rpx;
  margin: 0 0 10rpx;
  padding: 8rpx 0 8rpx 18rpx;
  flex-direction: column;
  align-items: flex-start;
  color: var(--med-clinical);
  background: transparent;
  border-left: 4rpx solid var(--med-clinical);
  border-radius: 0;
  font-size: 22rpx;
  text-align: left;
}
.next-link text:last-child {
  color: var(--med-ink);
  font-size: 25rpx;
  font-weight: 700;
}
.tree-error,
.tree-loading,
.tree-empty,
.graph-notice {
  padding: 18rpx 0;
  color: var(--med-muted);
  border-bottom: 1rpx solid var(--med-border);
  font-size: 24rpx;
}
.tree-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  color: var(--med-danger);
}
.tree-error button {
  min-height: 56rpx;
  margin: 0;
  padding: 0 18rpx;
  color: var(--med-clinical);
  background: var(--med-wash);
  font-size: 23rpx;
}
.graph-notice {
  padding: 12rpx 16rpx;
  color: var(--med-safety-text);
  background: var(--med-safety-soft);
  border-bottom: 0;
  border-left: 4rpx solid var(--med-safety);
  font-size: 22rpx;
}
.module-rail {
  display: flex;
  overflow-x: auto;
  gap: 8rpx;
  padding-bottom: 4rpx;
  scrollbar-width: none;
}
.module-tab {
  display: flex;
  min-width: 178rpx;
  min-height: 70rpx;
  margin: 0;
  padding: 10rpx 14rpx;
  align-items: center;
  justify-content: space-between;
  color: var(--med-text-secondary);
  background: transparent;
  border: 1rpx solid var(--med-divider);
  border-radius: 0;
  font-size: 23rpx;
  text-align: left;
}
.module-tab.active {
  color: var(--med-clinical);
  background: var(--med-wash);
  border-color: var(--med-clinical);
  font-weight: 700;
}
.module-count {
  color: var(--med-muted);
  font-family: var(--med-font-utility);
  font-size: 18rpx;
}
.tree-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12rpx;
}
.tree-mode,
.zoom-controls {
  display: flex;
  align-items: center;
  gap: 6rpx;
}
.mode-button,
.zoom-controls button {
  min-height: 56rpx;
  margin: 0;
  padding: 0 14rpx;
  color: var(--med-text-secondary);
  background: transparent;
  border: 1rpx solid var(--med-border);
  border-radius: 0;
  font-size: 21rpx;
}
.mode-button.active {
  color: var(--med-clinical);
  background: var(--med-wash);
  border-color: var(--med-clinical);
}
.zoom-controls text {
  min-width: 62rpx;
  color: var(--med-muted);
  font-family: var(--med-font-utility);
  font-size: 20rpx;
  text-align: center;
}
.zoom-controls .reset-button {
  color: var(--med-clinical);
  border-color: transparent;
}
.tree-viewport {
  position: relative;
  height: 1000rpx;
  overflow: hidden;
  background:
    linear-gradient(90deg, rgba(10, 107, 102, 0.04) 1rpx, transparent 1rpx),
    linear-gradient(rgba(10, 107, 102, 0.04) 1rpx, transparent 1rpx), var(--med-surface);
  background-size: 36rpx 36rpx;
  border-top: 1rpx solid var(--med-border);
  border-bottom: 1rpx solid var(--med-border);
}
.tree-plane {
  position: absolute;
  top: 0;
  left: 50%;
  width: 1230px;
  margin-left: -615px;
  transform-origin: 50% 0;
  transition: transform 180ms var(--med-ease-out);
}
.tree-plane.is-moving {
  transition: none;
}
.tree-edge {
  position: absolute;
  height: 2px;
  transform-origin: 0 0;
  background: rgba(10, 107, 102, 0.32);
  pointer-events: none;
}
.tree-edge.edge-contains {
  background: rgba(10, 107, 102, 0.2);
}
.tree-edge.edge-prerequisite::after {
  position: absolute;
  top: -4px;
  right: -1px;
  width: 8px;
  height: 8px;
  background: var(--med-clinical);
  border-radius: 50%;
  content: '';
}
.tree-edge.cross {
  height: 0;
  background: transparent;
  border-top: 2px dashed rgba(154, 86, 24, 0.72);
}
.tree-node {
  position: absolute;
  display: flex;
  width: 208px;
  min-height: 72px;
  margin: 0;
  padding: 10px 12px;
  align-items: center;
  gap: 8px;
  color: var(--med-text);
  background: var(--med-surface);
  border: 1px solid var(--med-border);
  border-radius: 10px;
  box-shadow: none;
  font-size: 13px;
  text-align: left;
}
.tree-node.node-root,
.tree-node.node-module {
  justify-content: center;
  color: var(--med-ink);
  text-align: center;
}
.tree-node.node-root {
  flex-direction: column;
  color: #fff;
  background: var(--med-clinical);
  border-color: var(--med-clinical);
}
.tree-node.node-module {
  flex-direction: column;
  background: #f0f7f5;
  border-top: 4px solid var(--med-clinical);
}
.tree-node.node-module.is-focused-module {
  color: #fff;
  background: var(--med-clinical);
  border-color: var(--med-clinical);
}
.tree-node.node-module.is-focused-module .node-status {
  color: rgba(255, 255, 255, 0.76);
}
.node-state {
  display: inline-flex;
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  align-items: center;
  justify-content: center;
  color: var(--med-clinical);
  background: var(--med-wash);
  border-radius: 50%;
  font-family: var(--med-font-utility);
  font-size: 15px;
  font-weight: 700;
}
.node-copy {
  overflow: hidden;
  flex: 1;
}
.node-title {
  display: block;
  color: inherit;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.node-level {
  display: block;
  margin-top: 3px;
  color: var(--med-muted);
  font-family: var(--med-font-utility);
  font-size: 10px;
}
.node-status {
  flex: none;
  color: var(--med-muted);
  font-size: 11px;
}
.node-root .node-status {
  color: rgba(255, 255, 255, 0.72);
}
.status-weak {
  border-color: var(--med-danger);
}
.status-weak .node-state {
  color: #fff;
  background: var(--med-danger);
}
.status-due {
  border-color: var(--med-warning);
}
.status-due .node-state {
  color: #fff;
  background: var(--med-warning);
}
.status-learning {
  border-color: var(--med-accent);
}
.status-learning .node-state {
  color: #fff;
  background: var(--med-accent);
}
.status-stable {
  border-color: var(--med-success);
}
.status-stable .node-state {
  color: #fff;
  background: var(--med-success);
}
.gesture-hint {
  position: absolute;
  right: 14rpx;
  bottom: 12rpx;
  padding: 6rpx 10rpx;
  color: var(--med-muted);
  background: rgba(251, 253, 253, 0.88);
  font-size: 19rpx;
}
.state-legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12rpx;
  padding-bottom: 8rpx;
  border-bottom: 1rpx solid var(--med-divider);
}
.legend-title {
  color: var(--med-ink);
  font-size: 22rpx;
  font-weight: 700;
}
.legend-item {
  color: var(--med-muted);
  font-size: 20rpx;
}
.legend-mark {
  display: inline-flex;
  width: 22rpx;
  height: 22rpx;
  margin-right: 4rpx;
  align-items: center;
  justify-content: center;
  color: var(--med-clinical);
  background: var(--med-wash);
  border-radius: 50%;
  font-size: 17rpx;
  font-weight: 700;
}
.legend-mark.status-weak,
.legend-mark.status-due,
.legend-mark.status-learning,
.legend-mark.status-stable {
  color: #fff;
}
.legend-mark.status-weak {
  background: var(--med-danger);
}
.legend-mark.status-due {
  background: var(--med-warning);
}
.legend-mark.status-learning {
  background: var(--med-accent);
}
.legend-mark.status-stable {
  background: var(--med-success);
}
@media screen and (min-width: 600px) {
  .knowledge-tree {
    margin-bottom: 24px;
    gap: 14px;
  }
  .tree-heading {
    padding-top: 8px;
  }
  .title {
    font-size: 24px;
  }
  .muted,
  .tree-reference {
    font-size: 14px;
  }
  .module-tab {
    min-width: 150px;
    min-height: 48px;
    font-size: 14px;
  }
  .tree-viewport {
    height: 620px;
    background-size: 20px 20px;
  }
  .state-legend {
    gap: 10px;
  }
  .legend-title,
  .legend-item {
    font-size: 13px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .tree-plane {
    transition: none;
  }
}
</style>
