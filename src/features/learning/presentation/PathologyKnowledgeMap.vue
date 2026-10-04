<template>
  <view class="knowledge-tree">
    <view class="tree-hero">
      <view class="tree-heading">
        <view class="heading-copy">
          <view class="title">
            <text>从概念主干，</text>
            <text>走到病理机制</text>
          </view>
          <text class="muted">节点关系组织学习路径；打开节点本身不会改变掌握状态。</text>
        </view>
        <button
          v-if="recommendedPoint"
          class="next-link"
          :aria-label="`查看推荐知识点：${recommendedPoint.title}`"
          @click="openPoint(recommendedPoint.code)"
        >
          <view
            class="next-book"
            aria-hidden="true"
          >
            <text /><text />
          </view>
          <view class="next-copy">
            <text>建议下一步：</text>
            <text>{{ recommendedPoint.title }} <text aria-hidden="true">›</text></text>
            <text>循序渐进，打牢基础</text>
          </view>
        </button>
      </view>
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

      <scroll-view
        class="module-rail"
        scroll-x
        enhanced
        :show-scrollbar="false"
        role="tablist"
        aria-label="选择知识模块"
      >
        <view class="module-track">
          <button
            v-for="(module, index) in graph.modules"
            :key="module.code"
            class="module-tab"
            :class="{ active: selectedModule === module.code && !showAll }"
            role="tab"
            :aria-selected="selectedModule === module.code && !showAll"
            @click="focusModule(module.code)"
          >
            <image
              class="module-tab-icon"
              :src="moduleIcon(index)"
              mode="aspectFit"
              alt=""
              aria-hidden="true"
            />
            <text class="module-title">{{ module.title }}</text>
            <text class="module-count">{{ module.stableCount }}/{{ module.pointCodes.length }}</text>
          </button>
        </view>
      </scroll-view>

      <view class="tree-toolbar">
        <view class="tree-mode">
          <button
            class="mode-button"
            :class="{ active: !showAll }"
            :aria-pressed="!showAll"
            @click="focusRecommended"
          >
            <view
              class="mode-icon mode-icon--focus"
              aria-hidden="true"
              ><text
            /></view>
            <text>聚焦建议</text>
          </button>
          <button
            class="mode-button"
            :class="{ active: showAll }"
            :aria-pressed="showAll"
            @click="showWholeTree"
          >
            <view
              class="mode-icon mode-icon--tree"
              aria-hidden="true"
              ><text /><text /><text
            /></view>
            <text>查看全树</text>
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
            <text
              class="reset-icon"
              aria-hidden="true"
              >↻</text
            >复位
          </button>
        </view>
      </view>

      <view
        v-if="!showAll && focusedCrossDependencies.length"
        class="cross-dependency-strip"
        aria-label="当前主题的跨主题前置关系"
      >
        <text class="cross-dependency-title">跨主题前置</text>
        <button
          v-for="relation in focusedCrossDependencies"
          :key="relation.dependency.id"
          class="cross-dependency-link"
          @click="openPoint(relation.prerequisite.code)"
        >
          <text>{{ relation.prerequisite.title }}</text>
          <text aria-hidden="true">→</text>
          <text>{{ relation.dependent.title }}</text>
        </button>
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
          :class="{ 'is-moving': moving, 'is-overview': showAll }"
          :style="planeStyle"
        >
          <view
            v-for="segment in visibleEdgeSegments"
            :key="segment.id"
            class="tree-edge"
            :data-edge-id="segment.id"
            :data-edge-from="segment.from"
            :data-edge-to="segment.to"
            :class="[
              `edge-${segment.kind}`,
              `edge-${segment.orientation}`,
              {
                cross: segment.crossModule,
                'is-terminal': segment.terminal,
              },
            ]"
            :style="segment.style"
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
              <view
                v-if="node.kind === 'root'"
                class="node-book"
                aria-hidden="true"
                ><text /><text
              /></view>
              <image
                v-else
                class="node-module-icon"
                :src="moduleIconForCode(node.id)"
                mode="aspectFit"
                alt=""
                aria-hidden="true"
              />
              <view class="node-branch-copy">
                <text class="node-title">{{ node.title }}</text>
                <text class="node-status">
                  {{ node.kind === 'module' ? moduleSummary(node.id) : `${graph.modules.length} 个知识模块` }}
                </text>
              </view>
            </template>
          </button>
        </view>
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
        <text class="legend-item dependency-legend">
          <text class="dependency-line" />跨主题学习前置（圆点指向后学）
        </text>
      </view>
      <text class="dependency-note"
        >依赖来自 {{ mapPoints[0]?.catalogVersion }} 持久化目录；公开来源支持，当前仍待医学专家审核。{{
          mapPoints[0]?.relationshipNote
        }}</text
      >
      <view class="tree-reference">
        <text
          class="reference-icon"
          aria-hidden="true"
          >i</text
        >
        <text>{{ mapPoints[0]?.reference }}</text>
      </view>
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
  crossModuleDependenciesForModule,
  getKnowledgeMap,
  type KnowledgeGraphEdge,
  type KnowledgeMapPoint,
} from '@/features/learning/public'
import { goDetail, ROUTES } from '@/platform/navigation'

interface Position {
  x: number
  y: number
}

interface RenderedEdgeSegment {
  id: string
  from: string
  to: string
  kind: KnowledgeGraphEdge['kind']
  crossModule: boolean
  orientation: 'direct'
  terminal: boolean
  style: Record<string, string>
}

interface OverviewModuleLayout {
  code: string
  start: number
  width: number
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
const MIN_SCALE = 0.2
const MAX_SCALE = 1.8
const FOCUSED_SCALE = 0.6
const WHOLE_TREE_SCALE = 0.2
const FOCUSED_FIRST_LEVEL_Y = 332
const FOCUSED_LEVEL_GAP = 142
const OVERVIEW_NODE_WIDTH = 140
const OVERVIEW_NODE_HEIGHT = 64
const OVERVIEW_SIBLING_STEP = 150
const OVERVIEW_MODULE_GAP = 24
const OVERVIEW_SIDE_PADDING = 16
const moduleIcons = [
  '/static/knowledge-module-cell.svg',
  '/static/knowledge-module-inflammation.svg',
  '/static/knowledge-module-repair.svg',
  '/static/knowledge-module-circulation.svg',
  '/static/knowledge-module-tumor.svg',
]

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
const viewportWidth = ref(372)
const viewportHeight = ref(540)

const graph = computed(() => (mapPoints.value.length ? buildKnowledgeGraph(mapPoints.value) : undefined))
const recommendedPoint = computed(() =>
  mapPoints.value.find((point) => point.code === graph.value?.recommendedPointCode),
)
const selectedPoints = computed(
  () => graph.value?.modules.find((module) => module.code === selectedModule.value)?.pointCodes || [],
)
const focusedCrossDependencies = computed(() => {
  return crossModuleDependenciesForModule(mapPoints.value, selectedModule.value)
})
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
const visibleEdgeSegments = computed(() => {
  return visibleEdges.value.map((edge) => directEdgeSegment(edge))
})
const overviewLayout = computed(() => {
  if (!graph.value) return { worldWidth: WORLD_WIDTH, modules: [] as OverviewModuleLayout[] }

  let cursor = OVERVIEW_SIDE_PADDING
  const modules = graph.value.modules.map((module) => {
    const points = graph.value?.nodes.filter((node) => node.kind === 'point' && node.moduleCode === module.code)
    const depthCounts = new Map<number, number>()
    for (const point of points || []) depthCounts.set(point.depth, (depthCounts.get(point.depth) || 0) + 1)
    const widestLevel = Math.max(1, ...depthCounts.values())
    const width = OVERVIEW_NODE_WIDTH + (widestLevel - 1) * OVERVIEW_SIBLING_STEP
    const layout = { code: module.code, start: cursor, width }
    cursor += width + OVERVIEW_MODULE_GAP
    return layout
  })
  const contentWidth = Math.max(OVERVIEW_NODE_WIDTH, cursor - OVERVIEW_MODULE_GAP + OVERVIEW_SIDE_PADDING)
  const worldWidth = Math.max(contentWidth, viewportWidth.value / MIN_SCALE)
  const centeringOffset = (worldWidth - contentWidth) / 2
  return {
    worldWidth,
    modules: modules.map((module) => ({ ...module, start: module.start + centeringOffset })),
  }
})
const activeWorldWidth = computed(() => (showAll.value ? overviewLayout.value.worldWidth : WORLD_WIDTH))
const planeStyle = computed(() => ({
  width: `${activeWorldWidth.value}px`,
  height: `${WORLD_HEIGHT}px`,
  marginLeft: `${-activeWorldWidth.value / 2}px`,
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
  const nodeWidth = showAll.value ? OVERVIEW_NODE_WIDTH : NODE_WIDTH
  if (id === graph.value.rootId) return { x: (activeWorldWidth.value - nodeWidth) / 2, y: 40 }
  const moduleIndex = graph.value.modules.findIndex((module) => module.code === id)
  if (moduleIndex >= 0) {
    if (showAll.value) {
      const layout = overviewLayout.value.modules[moduleIndex]
      return { x: layout.start + (layout.width - OVERVIEW_NODE_WIDTH) / 2, y: 185 }
    }
    const activeIndex = graph.value.modules.findIndex((module) => module.code === selectedModule.value)
    return {
      x: (WORLD_WIDTH - NODE_WIDTH) / 2 + (moduleIndex - Math.max(activeIndex, 0)) * 238,
      y: 185,
    }
  }

  const node = graph.value.nodes.find((item) => item.id === id)
  if (!node?.point) return { x: 0, y: 0 }
  const inLevel = graph.value.nodes.filter(
    (item) => item.kind === 'point' && item.moduleCode === node.moduleCode && item.depth === node.depth,
  )
  const levelIndex = inLevel.findIndex((item) => item.id === node.id)
  const moduleLevels = [
    ...new Set(
      graph.value.nodes
        .filter((item) => item.kind === 'point' && item.moduleCode === node.moduleCode)
        .map((item) => item.depth),
    ),
  ].sort((left, right) => left - right)
  const compactedDepth = Math.max(moduleLevels.indexOf(node.depth), 0)
  if (!showAll.value) {
    return {
      x: (WORLD_WIDTH - NODE_WIDTH) / 2 + (levelIndex - (inLevel.length - 1) / 2) * 232,
      y: FOCUSED_FIRST_LEVEL_Y + compactedDepth * FOCUSED_LEVEL_GAP,
    }
  }
  const moduleLayout = overviewLayout.value.modules.find((item) => item.code === node.moduleCode)
  if (!moduleLayout) return { x: 0, y: 0 }
  return {
    x:
      moduleLayout.start +
      (moduleLayout.width - OVERVIEW_NODE_WIDTH) / 2 +
      (levelIndex - (inLevel.length - 1) / 2) * OVERVIEW_SIBLING_STEP,
    y: FOCUSED_FIRST_LEVEL_Y + compactedDepth * FOCUSED_LEVEL_GAP,
  }
}

function nodeStyle(id: string) {
  const position = positionFor(id)
  const width = showAll.value ? OVERVIEW_NODE_WIDTH : NODE_WIDTH
  const minHeight = showAll.value ? OVERVIEW_NODE_HEIGHT : NODE_HEIGHT
  return { left: `${position.x}px`, top: `${position.y}px`, width: `${width}px`, minHeight: `${minHeight}px` }
}

function directEdgeSegment(edge: KnowledgeGraphEdge): RenderedEdgeSegment {
  const from = positionFor(edge.from)
  const to = positionFor(edge.to)
  const nodeWidth = showAll.value ? OVERVIEW_NODE_WIDTH : NODE_WIDTH
  const nodeHeight = showAll.value ? OVERVIEW_NODE_HEIGHT : NODE_HEIGHT
  const crossOverview = showAll.value && edge.crossModule
  const movingRight = to.x > from.x
  const startX = crossOverview ? (movingRight ? from.x + nodeWidth : from.x) : from.x + nodeWidth / 2
  const startY = crossOverview ? from.y + nodeHeight / 2 : from.y + nodeHeight
  const endX = crossOverview ? (movingRight ? to.x : to.x + nodeWidth) : to.x + nodeWidth / 2
  const endY = crossOverview ? to.y + nodeHeight / 2 : to.y
  const deltaX = endX - startX
  const deltaY = endY - startY
  const length = Math.sqrt(deltaX * deltaX + deltaY * deltaY)
  const angle = (Math.atan2(deltaY, deltaX) * 180) / Math.PI
  return {
    id: edge.id,
    from: edge.from,
    to: edge.to,
    kind: edge.kind,
    crossModule: edge.crossModule,
    orientation: 'direct',
    terminal: edge.kind === 'prerequisite',
    style: {
      left: `${startX}px`,
      top: `${startY}px`,
      width: `${length}px`,
      transform: `rotate(${angle}deg)`,
    },
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
  scale.value = FOCUSED_SCALE
  offsetX.value = 0
  offsetY.value = 0
}

function setWholeTreeViewport() {
  scale.value = WHOLE_TREE_SCALE
  offsetX.value = 0
  offsetY.value = 0
}

function zoomBy(amount: number) {
  scale.value = Math.min(MAX_SCALE, Math.max(MIN_SCALE, Number((scale.value + amount).toFixed(2))))
  constrainViewport()
}

function horizontalPanLimit(currentScale = scale.value) {
  return Math.max(0, (activeWorldWidth.value * currentScale - viewportWidth.value) / 2)
}

function minimumVerticalOffset(currentScale = scale.value) {
  return Math.min(0, viewportHeight.value - WORLD_HEIGHT * currentScale)
}

function constrainViewport() {
  const horizontalLimit = horizontalPanLimit()
  offsetX.value = Math.min(horizontalLimit, Math.max(-horizontalLimit, offsetX.value))
  offsetY.value = Math.min(0, Math.max(minimumVerticalOffset(), offsetY.value))
}

function updateViewportMetrics() {
  const windowInfo = typeof uni.getWindowInfo === 'function' ? uni.getWindowInfo() : uni.getSystemInfoSync?.()
  if (!windowInfo?.windowWidth) return
  const horizontalGutter = typeof uni.upx2px === 'function' ? uni.upx2px(56) : 28
  viewportWidth.value = Math.max(240, windowInfo.windowWidth - horizontalGutter)
  viewportHeight.value = typeof uni.upx2px === 'function' ? uni.upx2px(1080) : 540
  constrainViewport()
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
    constrainViewport()
    moving.value = true
    return
  }
  const horizontalLimit = horizontalPanLimit()
  offsetX.value = Math.min(
    horizontalLimit,
    Math.max(-horizontalLimit, offsetX.value + touches[0].clientX - gesture.value.x),
  )
  offsetY.value = Math.min(0, Math.max(minimumVerticalOffset(), offsetY.value + touches[0].clientY - gesture.value.y))
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

function moduleIcon(index: number) {
  return moduleIcons[index % moduleIcons.length]
}

function moduleIconForCode(code: string) {
  const index = graph.value?.modules.findIndex((module) => module.code === code) ?? 0
  return moduleIcon(Math.max(index, 0))
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
  const prerequisites = node.point.dependencies.length
  return `${node.point.systemLabel}，${node.title}，${statusLabel(node.point.status)}，${
    prerequisites ? `有 ${prerequisites} 个前置知识` : '可直接开始'
  }，点击进入学习`
}

async function refresh() {
  if (loading.value) return
  loading.value = true
  error.value = ''
  try {
    const nextPoints = await getKnowledgeMap()
    buildKnowledgeGraph(nextPoints)
    mapPoints.value = nextPoints
    if (!selectedModule.value) focusRecommended()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '知识结构加载失败，请稍后重试。'
  } finally {
    loading.value = false
  }
}

defineExpose({ refresh })
onMounted(() => {
  updateViewportMetrics()
  void refresh()
})
</script>

<style scoped>
.knowledge-tree {
  --tree-ink: #071a5a;
  --tree-text: #35558d;
  --tree-muted: #7183ad;
  --tree-primary: #079baa;
  --tree-blue: #087ccf;
  --tree-border: #d6eaf7;
  --tree-wash: #edf8fe;
  display: flex;
  max-width: 920px;
  margin: 0 auto 34rpx;
  flex-direction: column;
  gap: 20rpx;
  color: var(--tree-text);
}
.tree-hero {
  position: relative;
  overflow: hidden;
  padding: 28rpx 28rpx 30rpx;
  background:
    radial-gradient(circle at 68% 78%, rgba(82, 196, 235, 0.2) 0, rgba(82, 196, 235, 0) 25%),
    linear-gradient(158deg, #f8fdff 0%, #e7f6fd 58%, #f3faff 100%);
  border-bottom: 1rpx solid rgba(188, 224, 242, 0.7);
}
.tree-hero::before,
.tree-hero::after {
  display: none;
}
.tree-heading {
  position: relative;
  z-index: 1;
  display: flex;
  min-height: 176rpx;
  align-items: center;
  justify-content: space-between;
  gap: 22rpx;
}
.heading-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 12rpx;
}
.title {
  display: flex;
  flex-wrap: wrap;
  color: var(--tree-ink);
  font-size: 38rpx;
  font-weight: 850;
  letter-spacing: -1.5rpx;
  line-height: 1.25;
}
.title text {
  white-space: nowrap;
}
.muted {
  color: var(--tree-muted);
  font-size: 23rpx;
  line-height: 1.55;
}
.next-link {
  display: flex;
  width: 262rpx;
  min-height: 146rpx;
  margin: 0;
  padding: 18rpx 18rpx;
  align-items: center;
  gap: 15rpx;
  color: var(--tree-primary);
  background: rgba(255, 255, 255, 0.72);
  border: 1rpx solid rgba(255, 255, 255, 0.96);
  border-radius: 24rpx;
  box-shadow: 0 12rpx 28rpx rgba(49, 135, 181, 0.09);
  font-size: 20rpx;
  text-align: left;
}
.next-book,
.node-book {
  position: relative;
  display: flex;
  width: 60rpx;
  height: 52rpx;
  flex: 0 0 60rpx;
  align-items: flex-end;
  justify-content: center;
  gap: 4rpx;
}
.next-book text,
.node-book text {
  display: block;
  width: 27rpx;
  height: 45rpx;
  background: linear-gradient(155deg, #7ed9f3 0%, #c9f1fb 100%);
  border-radius: 5rpx 15rpx 5rpx 3rpx;
  transform: skewY(10deg);
}
.next-book text:last-child,
.node-book text:last-child {
  border-radius: 15rpx 5rpx 3rpx 5rpx;
  transform: skewY(-10deg);
}
.next-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 4rpx;
}
.next-copy > text:nth-child(2) {
  overflow: hidden;
  color: var(--tree-primary);
  font-size: 26rpx;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.next-copy > text:last-child {
  color: var(--tree-muted);
  font-size: 16rpx;
  white-space: nowrap;
}
.tree-error,
.tree-loading,
.tree-empty,
.graph-notice {
  margin: 0 28rpx;
  padding: 18rpx 20rpx;
  color: var(--tree-muted);
  background: rgba(255, 255, 255, 0.84);
  border: 1rpx solid var(--tree-border);
  border-radius: 16rpx;
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
  color: var(--tree-primary);
  background: var(--tree-wash);
  border-radius: 28rpx;
  font-size: 23rpx;
}
.graph-notice {
  color: var(--med-safety-text);
  background: var(--med-safety-soft);
  border-color: rgba(235, 175, 96, 0.38);
  font-size: 22rpx;
}
.module-rail {
  width: 100%;
  white-space: nowrap;
  scrollbar-width: none;
}
.module-track {
  display: inline-flex;
  padding: 0 28rpx 4rpx;
  gap: 10rpx;
}
.module-tab {
  display: flex;
  width: 132rpx;
  min-height: 122rpx;
  margin: 0;
  padding: 8rpx 10rpx;
  flex: 0 0 132rpx;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 5rpx;
  color: var(--tree-text);
  background: rgba(255, 255, 255, 0.78);
  border: 1rpx solid var(--tree-border);
  border-radius: 16rpx;
  font-size: 21rpx;
  text-align: center;
}
.module-tab.active {
  color: var(--tree-primary);
  background: linear-gradient(160deg, #ffffff 0%, #e7f8f8 100%);
  border-color: var(--tree-primary);
  box-shadow: inset 0 0 0 1rpx rgba(7, 155, 170, 0.08);
  font-weight: 700;
}
.module-tab-icon {
  width: 42rpx;
  height: 42rpx;
}
.module-title {
  display: -webkit-box;
  overflow: hidden;
  width: 100%;
  min-height: 48rpx;
  font-weight: 750;
  line-height: 1.15;
  text-overflow: ellipsis;
  white-space: normal;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.module-count {
  color: var(--tree-muted);
  font-family: var(--med-font-utility);
  font-size: 19rpx;
}
.tree-toolbar {
  display: flex;
  margin: 0 28rpx;
  padding: 12rpx;
  align-items: center;
  justify-content: space-between;
  gap: 12rpx;
  background: rgba(255, 255, 255, 0.9);
  border: 1rpx solid rgba(214, 234, 247, 0.9);
  border-radius: 20rpx;
  box-shadow: 0 8rpx 22rpx rgba(53, 117, 156, 0.07);
}
.tree-mode,
.zoom-controls {
  display: flex;
  align-items: center;
  gap: 6rpx;
}
.cross-dependency-strip {
  display: flex;
  margin: -2rpx 28rpx 0;
  padding: 14rpx 18rpx;
  align-items: center;
  gap: 10rpx;
  overflow-x: auto;
  color: #526d96;
  background: rgba(246, 251, 255, 0.94);
  border-right: 1rpx solid var(--tree-border);
  border-bottom: 1rpx solid var(--tree-border);
  border-left: 1rpx solid var(--tree-border);
  border-radius: 0 0 16rpx 16rpx;
}
.cross-dependency-title {
  flex: 0 0 auto;
  font-size: 20rpx;
  font-weight: 700;
}
.cross-dependency-link {
  display: flex;
  min-height: 44rpx;
  margin: 0;
  padding: 0 12rpx;
  align-items: center;
  flex: 0 0 auto;
  gap: 8rpx;
  color: #0a7e9a;
  background: #fff;
  border: 1rpx solid #cbe9f1;
  border-radius: 999rpx;
  font-size: 19rpx;
  line-height: 1.2;
}
.mode-button,
.zoom-controls button {
  min-height: 56rpx;
  margin: 0;
  padding: 0 14rpx;
  color: var(--tree-text);
  background: transparent;
  border: 1rpx solid var(--tree-border);
  border-radius: 12rpx;
  font-size: 21rpx;
}
.mode-button {
  display: flex;
  align-items: center;
  gap: 8rpx;
}
.mode-button.active {
  color: var(--tree-primary);
  background: #eefafa;
  border-color: var(--tree-primary);
  font-weight: 700;
}
.mode-icon {
  position: relative;
  display: block;
  width: 28rpx;
  height: 28rpx;
  flex: 0 0 28rpx;
}
.mode-icon--focus {
  border: 3rpx solid currentColor;
  border-radius: 50%;
}
.mode-icon--focus::before,
.mode-icon--focus::after,
.mode-icon--focus text {
  position: absolute;
  border-radius: 50%;
  content: '';
}
.mode-icon--focus::before {
  inset: 5rpx;
  border: 2rpx solid currentColor;
}
.mode-icon--focus::after {
  top: -5rpx;
  right: -5rpx;
  width: 8rpx;
  height: 8rpx;
  background: currentColor;
  border: 3rpx solid #fff;
}
.mode-icon--tree::before,
.mode-icon--tree::after {
  position: absolute;
  background: currentColor;
  content: '';
}
.mode-icon--tree::before {
  top: 7rpx;
  left: 13rpx;
  width: 2rpx;
  height: 13rpx;
}
.mode-icon--tree::after {
  top: 18rpx;
  left: 4rpx;
  width: 20rpx;
  height: 2rpx;
}
.mode-icon--tree text {
  position: absolute;
  bottom: 0;
  width: 7rpx;
  height: 7rpx;
  background: currentColor;
  border-radius: 50%;
}
.mode-icon--tree text:first-child {
  top: 0;
  left: 10rpx;
}
.mode-icon--tree text:nth-child(2) {
  left: 0;
}
.mode-icon--tree text:last-child {
  right: 0;
}
.zoom-controls text {
  min-width: 62rpx;
  color: var(--tree-text);
  font-family: var(--med-font-utility);
  font-size: 22rpx;
  text-align: center;
}
.zoom-controls .reset-button {
  display: flex;
  align-items: center;
  gap: 5rpx;
  color: var(--tree-primary);
}
.reset-icon {
  min-width: 0 !important;
  font-size: 28rpx !important;
}
.tree-viewport {
  position: relative;
  height: 1080rpx;
  margin: 0 28rpx;
  overflow: hidden;
  background:
    linear-gradient(90deg, rgba(64, 160, 208, 0.09) 1rpx, transparent 1rpx),
    linear-gradient(rgba(64, 160, 208, 0.09) 1rpx, transparent 1rpx), #fbfeff;
  background-size: 36rpx 36rpx;
  border: 1rpx solid var(--tree-border);
  border-radius: 24rpx;
  box-shadow: 0 12rpx 28rpx rgba(42, 125, 167, 0.07);
}
.tree-plane {
  position: absolute;
  top: 0;
  left: 50%;
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
  background: rgba(7, 155, 170, 0.55);
  pointer-events: none;
}
.tree-edge.edge-contains {
  background: rgba(7, 155, 170, 0.42);
}
.tree-edge.edge-prerequisite.is-terminal::after {
  position: absolute;
  top: -4px;
  right: -1px;
  width: 8px;
  height: 8px;
  background: var(--tree-primary);
  border-radius: 50%;
  content: '';
}
.tree-edge.cross {
  height: 0;
  background: transparent;
  border-top: 2px dashed rgba(154, 86, 24, 0.72);
}
.tree-edge.cross.edge-prerequisite.is-terminal::after {
  background: #9a5618;
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
  color: var(--tree-ink);
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid #d5e9f5;
  border-radius: 16px;
  box-shadow: 0 7px 18px rgba(44, 110, 151, 0.09);
  font-size: 13px;
  text-align: left;
}
.tree-plane.is-overview .tree-node {
  padding: 8px;
  gap: 6px;
  border-radius: 12px;
}
.tree-plane.is-overview .node-module-icon {
  width: 34px;
  height: 34px;
  flex-basis: 34px;
}
.tree-plane.is-overview .node-book {
  width: 34px;
  height: 31px;
  flex-basis: 34px;
}
.tree-plane.is-overview .node-book text {
  width: 15px;
  height: 27px;
}
.tree-plane.is-overview .node-state {
  width: 23px;
  height: 23px;
  flex-basis: 23px;
  font-size: 12px;
}
.tree-plane.is-overview .node-title {
  font-size: 14px;
}
.tree-plane.is-overview .node-level {
  font-size: 10px;
}
.tree-plane.is-overview .node-status {
  padding: 4px 6px;
  font-size: 10px;
}
.tree-node.node-root,
.tree-node.node-module {
  justify-content: flex-start;
  color: #fff;
  text-align: left;
}
.tree-node.node-root {
  background: linear-gradient(145deg, #30b5d6 0%, #087eb7 100%);
  border-color: rgba(8, 126, 183, 0.42);
}
.tree-node.node-module {
  background: linear-gradient(145deg, #35c3bd 0%, #079baa 100%);
  border-color: rgba(7, 155, 170, 0.42);
}
.tree-node.node-module.is-focused-module {
  box-shadow: 0 9px 24px rgba(7, 155, 170, 0.2);
}
.tree-node.node-module.is-focused-module .node-status {
  color: rgba(255, 255, 255, 0.82);
}
.node-book {
  width: 43px;
  height: 38px;
  flex-basis: 43px;
  gap: 3px;
}
.node-book text {
  width: 19px;
  height: 33px;
  background: #fff;
  border-radius: 3px 9px 3px 2px;
}
.node-book text:last-child {
  border-radius: 9px 3px 2px 3px;
}
.node-module-icon {
  width: 42px;
  height: 42px;
  padding: 5px;
  flex: 0 0 42px;
  background: rgba(255, 255, 255, 0.92);
  border-radius: 50%;
  box-sizing: border-box;
}
.node-branch-copy {
  min-width: 0;
  flex: 1;
}
.node-state {
  display: inline-flex;
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  align-items: center;
  justify-content: center;
  color: var(--tree-primary);
  background: #e7f8fa;
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
  font-size: 18px;
  font-weight: 700;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.node-level {
  display: block;
  margin-top: 3px;
  color: var(--tree-muted);
  font-family: var(--med-font-utility);
  font-size: 12px;
}
.node-status {
  padding: 5px 8px;
  flex: none;
  color: var(--tree-muted);
  background: #f1f6fb;
  border-radius: 12px;
  font-size: 13px;
}
.node-root .node-status {
  padding: 2px 0;
  color: rgba(255, 255, 255, 0.82);
  background: transparent;
}
.node-module .node-status {
  padding: 2px 0;
  color: rgba(255, 255, 255, 0.82);
  background: transparent;
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
.state-legend {
  display: flex;
  margin: 0 28rpx;
  flex-wrap: wrap;
  align-items: center;
  gap: 14rpx 18rpx;
  padding: 8rpx 2rpx 0;
}
.legend-title {
  color: var(--tree-ink);
  font-size: 24rpx;
  font-weight: 700;
}
.legend-item {
  color: var(--tree-muted);
  font-size: 21rpx;
}
.legend-mark {
  display: inline-flex;
  width: 22rpx;
  height: 22rpx;
  margin-right: 4rpx;
  align-items: center;
  justify-content: center;
  color: var(--tree-primary);
  background: #e8f8f9;
  border-radius: 50%;
  font-size: 17rpx;
  font-weight: 700;
}
.dependency-legend {
  display: inline-flex;
  align-items: center;
}
.dependency-line {
  display: inline-block;
  width: 34rpx;
  height: 0;
  margin-right: 6rpx;
  border-top: 2rpx dashed rgba(154, 86, 24, 0.78);
}
.dependency-note {
  display: block;
  margin: -2rpx 28rpx 0;
  color: #8a5b2d;
  font-size: 20rpx;
  line-height: 1.5;
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
.tree-reference {
  display: flex;
  margin: 0 28rpx;
  align-items: flex-start;
  gap: 10rpx;
  color: var(--tree-muted);
  font-size: 21rpx;
  line-height: 1.5;
}
.reference-icon {
  display: inline-flex;
  width: 26rpx;
  height: 26rpx;
  flex: 0 0 26rpx;
  align-items: center;
  justify-content: center;
  border: 2rpx solid currentColor;
  border-radius: 50%;
  font-size: 18rpx;
  font-weight: 800;
  line-height: 1;
}
@media screen and (min-width: 600px) {
  .knowledge-tree {
    margin-bottom: 24px;
    gap: 16px;
  }
  .tree-hero {
    padding: 22px 28px;
    border-radius: 0 0 24px 24px;
  }
  .tree-heading {
    min-height: 134px;
  }
  .title {
    font-size: 28px;
  }
  .muted {
    font-size: 15px;
  }
  .next-link {
    width: 240px;
    min-height: 112px;
    padding: 14px 16px;
  }
  .module-tab {
    width: 150px;
    min-height: 88px;
    flex-basis: 150px;
    font-size: 14px;
  }
  .module-tab-icon {
    width: 28px;
    height: 28px;
  }
  .tree-viewport {
    height: 680px;
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
