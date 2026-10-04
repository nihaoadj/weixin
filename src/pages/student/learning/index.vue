<template>
  <view class="safe-page learning-page">
    <MedState
      v-if="accessDenied"
      variant="error"
      icon="history"
      title="学生身份已变化"
      description="学习任务与学情数据已清除。请使用当前学生账号重新进入学习页。"
    />
    <template v-else>
      <text
        class="sr-only"
        role="heading"
        aria-level="1"
        >学习</text
      >

      <view class="learning-hero">
        <image
          class="hero-decoration"
          src="/static/learning-hero-decoration.svg"
          mode="scaleToFill"
          alt=""
          aria-hidden="true"
        />
        <view class="hero-copy">
          <view
            class="hero-slogan"
            aria-label="医学之路 始于学习 成于坚持"
          >
            <text>医学之路</text>
            <text>始于学习</text>
            <text>成于坚持</text>
          </view>
          <text class="hero-subtitle">用 AI 点亮医学之路，每一次学习，都是更好的自己</text>
        </view>
      </view>

      <view class="page-content">
        <view
          class="routes-section"
          aria-labelledby="routes-title"
        >
          <view class="module-head">
            <view class="module-heading"
              ><text
                class="module-mark"
                aria-hidden="true"
              /><text
                id="routes-title"
                class="module-title"
                >研讨学习计划</text
              ></view
            >
            <button
              class="module-link"
              @click="goDetail(ROUTES.studentLearningPlans)"
            >
              全部计划 <text aria-hidden="true">›</text>
            </button>
          </view>
          <view
            v-if="routesLoading && !routeItems.length"
            class="inline-state"
            role="status"
            >正在读取你的学习计划…</view
          >
          <view
            v-else-if="routesError && !routeItems.length"
            class="inline-state inline-state--error"
            role="alert"
            ><text>{{ routesError }}</text
            ><button @click="reloadRoutes">重新加载</button></view
          >
          <view
            v-else-if="!routeItems.length"
            class="routes-empty"
          >
            <text class="route-empty-title">完成一次研讨后，学习计划会自动出现在这里</text>
            <text class="route-empty-copy">计划会根据研讨中的知识目标安排资料学习、合成病例和最终测试。</text>
            <button
              class="route-primary"
              @click="goDetail(ROUTES.studentPbl)"
            >
              开始研讨
            </button>
          </view>
          <view
            v-for="route in routeItems"
            :key="route.id"
            class="route-card"
            role="button"
            @click="openRoute(route.id)"
          >
            <view class="route-card-head"
              ><text class="route-kind">{{ route.sourceKind === 'classroom' ? '课堂研讨' : '自主研讨' }}</text
              ><text class="route-date">{{ formatRouteDate(route.updatedAt) }}</text></view
            >
            <text class="route-title">{{ route.title }}</text>
            <text class="route-target">目标知识点：{{ goalLabels(route.goalPointCodes) || '以学习计划为准' }}</text>
            <view class="route-card-foot"
              ><text>已完成 {{ route.progress.completedSteps }}/{{ route.progress.totalSteps }} 步</text
              ><text>{{ routeActionLabel(route) }} ›</text></view
            >
          </view>
          <view
            v-if="routesError && routeItems.length"
            class="inline-state inline-state--error"
            role="alert"
            ><text>{{ routesError }}</text
            ><button @click="reloadRoutes">刷新计划</button></view
          >
        </view>

        <view class="section-divider" />

        <view
          class="knowledge-section"
          aria-labelledby="knowledge-title"
        >
          <view class="module-head">
            <view class="module-heading">
              <text
                class="module-mark"
                aria-hidden="true"
              />
              <text
                id="knowledge-title"
                class="module-title"
                >知识点清单</text
              >
            </view>
            <button
              class="module-link"
              @keydown="activateButtonOnKey"
              @click="openKnowledgeMap"
            >
              全部知识点 <text aria-hidden="true">›</text>
            </button>
          </view>

          <scroll-view
            v-if="knowledgeCategories.length"
            class="category-scroll"
            scroll-x
            enhanced
            :show-scrollbar="false"
            aria-label="知识系统筛选"
          >
            <view class="category-track">
              <button
                v-for="category in knowledgeCategories"
                :key="category.key"
                class="category-tab"
                :class="{ active: selectedKnowledgeCategory === category.key }"
                :aria-pressed="selectedKnowledgeCategory === category.key"
                @keydown="activateButtonOnKey"
                @click="selectKnowledgeCategory(category.key)"
              >
                {{ category.label }}
              </button>
            </view>
          </scroll-view>

          <view
            v-if="knowledgeLoading"
            class="inline-state"
            role="status"
            >正在整理知识点…</view
          >
          <view
            v-else-if="knowledgeError"
            class="inline-state inline-state--error"
            role="alert"
          >
            <text>{{ knowledgeError }}</text>
            <button @click="() => loadKnowledge()">重新加载</button>
          </view>
          <scroll-view
            v-else-if="visibleKnowledgePoints.length"
            :key="selectedKnowledgeCategory"
            class="knowledge-list-scroll"
            scroll-y
            enhanced
            :show-scrollbar="false"
            aria-label="当前分类的知识点，可上下滑动"
          >
            <view
              class="knowledge-list"
              role="list"
            >
              <button
                v-for="(point, index) in visibleKnowledgePoints"
                :key="point.code"
                class="knowledge-row"
                role="listitem"
                :aria-label="`${point.title}，${point.systemLabel}，${point.cardCount} 张学习卡，${knowledgeStatusLabel(point.status)}`"
                @keydown="activateButtonOnKey"
                @click="openKnowledgePoint(point.code)"
              >
                <view
                  class="knowledge-icon"
                  :class="`knowledge-icon--${index % 3}`"
                  aria-hidden="true"
                >
                  <view class="knowledge-glyph" />
                </view>
                <view class="knowledge-copy">
                  <text class="knowledge-title">{{ point.title }}</text>
                  <text class="knowledge-meta">{{ point.systemLabel }} · {{ point.cardCount }} 张学习卡</text>
                </view>
                <view class="knowledge-progress">
                  <view
                    class="status-track"
                    aria-hidden="true"
                  >
                    <view
                      class="status-fill"
                      :class="`status-fill--${point.status}`"
                      :style="{ width: `${knowledgeStatusLevel(point.status) * 25}%` }"
                    />
                  </view>
                  <text class="status-label">{{ knowledgeStatusLabel(point.status) }}</text>
                </view>
                <text
                  class="row-arrow"
                  aria-hidden="true"
                  >›</text
                >
              </button>
            </view>
          </scroll-view>
          <view
            v-else
            class="inline-state"
          >
            <text>当前分类暂无可用知识点</text>
            <button @click="openKnowledgeMap">查看完整知识地图</button>
          </view>
        </view>

        <view class="section-divider" />

        <view
          class="practice-section"
          aria-labelledby="practice-title"
        >
          <view class="module-head">
            <view class="module-heading">
              <text
                class="module-mark"
                aria-hidden="true"
              />
              <text
                id="practice-title"
                class="module-title"
                >自主学习</text
              >
            </view>
          </view>
          <view
            class="practice-grid"
            role="list"
          >
            <button
              v-for="practice in practices"
              :key="practice.key"
              class="practice-card"
              :class="`practice-card--${practice.key}`"
              role="listitem"
              :aria-label="`${practice.title}，${practice.description}`"
              @keydown="activateButtonOnKey"
              @click="openPractice(practice.key)"
            >
              <view class="practice-icon"
                ><MedIcon
                  :name="practice.icon"
                  size="lg"
              /></view>
              <view class="practice-copy">
                <text class="practice-title">{{ practice.title }}</text>
                <text class="practice-description">{{ practice.description }}</text>
              </view>
              <text
                class="practice-arrow"
                aria-hidden="true"
                >›</text
              >
            </button>
          </view>
        </view>
      </view>

      <StudentPrimaryNav active="learning" />
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import MedIcon from '@/components/ui/MedIcon.vue'
import MedState from '@/components/ui/MedState.vue'
import StudentPrimaryNav from '@/components/ui/StudentPrimaryNav.vue'
import { activateButtonOnKey } from '@/components/ui/keyboard'
import { getSession, requireRole } from '@/features/identity/public'
import {
  getKnowledgeMap,
  getLearningRoutes,
  type KnowledgeMapPoint,
  type KnowledgeStatus,
  type LearningRouteSummary,
  learningGoalLabel,
} from '@/features/learning/public'
import { goDetail, ROUTES } from '@/platform/navigation'

type PracticeKey = 'cases' | 'knowledge'

const knowledgePoints = ref<KnowledgeMapPoint[]>([])
const routeItems = ref<LearningRouteSummary[]>([])
const routesLoading = ref(false)
const routesError = ref('')
let routesRequest = 0
const knowledgeLoading = ref(false)
const knowledgeError = ref('')
const accessDenied = ref(false)
let knowledgeRequest = 0
let studentContextVersion = 0
let studentIdentity: string | undefined
let identityInitialized = false
const selectedKnowledgeCategory = ref('focus')

function isCurrentStudent(contextVersion: number, identity: string): boolean {
  const session = getSession()
  return (
    contextVersion === studentContextVersion &&
    identityInitialized &&
    !accessDenied.value &&
    studentIdentity === identity &&
    session?.role === 'student' &&
    session.openid === identity
  )
}

function clearStudentLearningData() {
  studentContextVersion += 1
  routesRequest += 1
  knowledgeRequest += 1
  routeItems.value = []
  routesError.value = ''
  routesLoading.value = false
  knowledgePoints.value = []
  knowledgeError.value = ''
  knowledgeLoading.value = false
}

function denyStudentWorkspace() {
  clearStudentLearningData()
  identityInitialized = false
  accessDenied.value = true
}

const practices = [
  { key: 'cases' as const, title: '病例学习', description: '临床病例 · 实战提升', icon: 'brand' as const },
  { key: 'knowledge' as const, title: '知识点学习', description: '查看知识目标 · 开始研讨', icon: 'report' as const },
]
const statusOrder: Record<KnowledgeStatus, number> = {
  weak: 0,
  due: 1,
  learning: 2,
  not_started: 3,
  stable: 4,
}
const sortedKnowledgePoints = computed(() =>
  knowledgePoints.value
    .map((point, index) => ({ point, index }))
    .sort((left, right) => statusOrder[left.point.status] - statusOrder[right.point.status] || left.index - right.index)
    .map(({ point }) => point),
)
const knowledgeCategories = computed(() => {
  const systems = new Map<string, string>()
  for (const point of knowledgePoints.value) systems.set(point.systemCode, point.systemLabel)
  return [{ key: 'focus', label: '最近学习' }, ...[...systems].map(([key, label]) => ({ key, label }))]
})
const visibleKnowledgePoints = computed(() => {
  const source =
    selectedKnowledgeCategory.value === 'focus'
      ? sortedKnowledgePoints.value
      : sortedKnowledgePoints.value.filter((point) => point.systemCode === selectedKnowledgeCategory.value)
  return source
})
const learningTopicCode = computed(
  () =>
    sortedKnowledgePoints.value.find((point) => ['weak', 'due', 'learning'].includes(point.status))?.code ||
    sortedKnowledgePoints.value[0]?.code,
)

function knowledgeStatusLabel(status: KnowledgeStatus) {
  return {
    not_started: '未开始',
    weak: '需巩固',
    learning: '学习中',
    due: '待复习',
    stable: '相对稳定',
  }[status]
}

function knowledgeStatusLevel(status: KnowledgeStatus) {
  return { not_started: 0, weak: 1, learning: 2, due: 3, stable: 4 }[status]
}

function selectKnowledgeCategory(key: string) {
  selectedKnowledgeCategory.value = key
}

async function loadKnowledge(contextVersion = studentContextVersion, identity = studentIdentity) {
  if (!identity || accessDenied.value || knowledgeLoading.value) return
  const request = ++knowledgeRequest
  knowledgeLoading.value = true
  knowledgeError.value = ''
  try {
    const points = await getKnowledgeMap()
    if (!isCurrentStudent(contextVersion, identity) || request !== knowledgeRequest) return
    knowledgePoints.value = points
    const currentExists = knowledgeCategories.value.some((item) => item.key === selectedKnowledgeCategory.value)
    if (!currentExists) selectedKnowledgeCategory.value = 'focus'
  } catch (reason) {
    if (isCurrentStudent(contextVersion, identity) && request === knowledgeRequest)
      knowledgeError.value = reason instanceof Error ? reason.message : '知识点加载失败，请稍后重试。'
  } finally {
    if (isCurrentStudent(contextVersion, identity) && request === knowledgeRequest) knowledgeLoading.value = false
  }
}

function openRoute(id: string) {
  goDetail(ROUTES.studentLearningPlanDetail, { routeId: id })
}
function goalLabels(codes: string[]) {
  return codes.map((code) => learningGoalLabel(code, knowledgePoints.value)).join('、')
}
function reloadRoutes() {
  void loadRoutes()
}
function formatRouteDate(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleDateString('zh-CN')
}
function routeActionLabel(route: LearningRouteSummary) {
  if (route.nextAction === 'view_result') return '查看结果'
  if (route.nextAction === 'wait_teacher') return '等待教师开放'
  if (route.nextAction === 'wait_generation') return '计划生成中'
  if (route.nextAction === 'test') return '开始最终测试'
  if (route.nextAction === 'case') return '继续病例学习'
  if (route.nextAction === 'retry_route' || route.nextAction === 'retry_test') return '需要重试'
  return '继续资料学习'
}
async function loadRoutes(contextVersion = studentContextVersion, identity = studentIdentity) {
  if (!identity || accessDenied.value || routesLoading.value) return
  const token = ++routesRequest
  routesLoading.value = true
  routesError.value = ''
  try {
    const page = await getLearningRoutes('active', 4, 0)
    if (!isCurrentStudent(contextVersion, identity) || token !== routesRequest) return
    routeItems.value = page.items
  } catch (reason) {
    if (token === routesRequest && isCurrentStudent(contextVersion, identity))
      routesError.value = reason instanceof Error ? reason.message : '学习计划加载失败，请稍后重试。'
  } finally {
    if (token === routesRequest && isCurrentStudent(contextVersion, identity)) routesLoading.value = false
  }
}

function openCases() {
  goDetail(ROUTES.studentCases, { view: 'cases' })
}

function openKnowledgeMap() {
  goDetail(ROUTES.studentCases, { view: 'knowledge' })
}

function openKnowledgePoint(code: string) {
  goDetail(ROUTES.studentKnowledgeNode, { topicCode: code })
}

function openPractice(key: PracticeKey) {
  if (key === 'cases') {
    openCases()
    return
  }
  if (learningTopicCode.value) {
    goDetail(ROUTES.studentKnowledgeNode, { topicCode: learningTopicCode.value })
    return
  }
  openKnowledgeMap()
}

onShow(() => {
  const session = getSession()
  if (!requireRole('student') || session?.role !== 'student' || !session.openid) {
    denyStudentWorkspace()
    return
  }
  if (identityInitialized && studentIdentity !== session.openid) {
    clearStudentLearningData()
    studentIdentity = session.openid
  }
  if (!identityInitialized) {
    studentIdentity = session.openid
    identityInitialized = true
  }
  accessDenied.value = false
  const contextVersion = studentContextVersion
  void loadKnowledge(contextVersion, session.openid)
  void loadRoutes(contextVersion, session.openid)
})
</script>

<style scoped>
.learning-page {
  --learning-ink: #071a5a;
  --learning-text: #35558d;
  --learning-muted: #7183ad;
  --learning-blue: #087ccf;
  --learning-cyan: #18c7d6;
  --learning-wash: #eef8fd;
  --learning-border: #d6eaf7;
  --learning-divider: #e6f2f9;
  overflow-x: hidden;
  padding-bottom: calc(154rpx + env(safe-area-inset-bottom));
  color: var(--learning-text);
  background: #fff;
}
.routes-section {
  padding: 0 26rpx 18rpx;
}
.route-card {
  display: flex;
  max-width: 920px;
  box-sizing: border-box;
  margin: 0 auto 14rpx;
  padding: 20rpx 22rpx;
  flex-direction: column;
  gap: 9rpx;
  background: #fff;
  border: 1rpx solid #dce8ef;
  border-radius: 16rpx;
}
.route-card-head,
.route-card-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12rpx;
}
.route-kind {
  color: #07848f;
  font-size: 22rpx;
  font-weight: 700;
}
.route-date,
.route-target {
  color: #718198;
  font-size: 21rpx;
}
.route-title {
  color: #17325d;
  font-size: 28rpx;
  font-weight: 700;
}
.route-card-foot {
  margin-top: 4rpx;
  padding-top: 10rpx;
  color: #61748a;
  border-top: 1rpx solid #edf2f5;
  font-size: 22rpx;
}
.route-card-foot text:last-child {
  color: #07848f;
  font-weight: 700;
}
.routes-empty {
  display: flex;
  max-width: 920px;
  box-sizing: border-box;
  margin: 0 auto;
  padding: 22rpx;
  align-items: flex-start;
  flex-direction: column;
  gap: 10rpx;
  background: #f5fafc;
  border: 1rpx solid #e0ebf0;
  border-radius: 14rpx;
}
.route-empty-title {
  color: #264466;
  font-size: 24rpx;
  font-weight: 700;
}
.route-empty-copy {
  color: #718198;
  font-size: 22rpx;
  line-height: 1.6;
}
.route-primary {
  min-height: 68rpx;
  margin: 4rpx 0 0;
  padding: 0 22rpx;
  color: #fff;
  background: #078d9b;
  border-radius: 10rpx;
  font-size: 23rpx;
}
.learning-hero {
  position: relative;
  height: 198rpx;
  overflow: hidden;
  padding: 44rpx 38rpx 22rpx;
  box-sizing: border-box;
  background: #f5fbfe;
}
.hero-decoration {
  position: absolute;
  z-index: 0;
  top: 0;
  left: 0;
  display: block;
  width: 100%;
  height: 100%;
}
.hero-copy {
  position: relative;
  z-index: 2;
  display: flex;
  max-width: 540rpx;
  flex-direction: column;
  gap: 10rpx;
}
.hero-slogan {
  display: flex;
  align-items: center;
  gap: 32rpx;
  color: #087fe2;
  font-family: 'STKaiti', 'KaiTi', 'Kaiti SC', serif;
  font-size: 31rpx;
  font-weight: 500;
  letter-spacing: 1rpx;
  line-height: 1.35;
  transform: skew(-5deg);
}
.hero-slogan text {
  white-space: nowrap;
}
.hero-subtitle {
  max-width: 500rpx;
  color: #596fa7;
  font-size: 19.5rpx;
  font-weight: 650;
  line-height: 1.5;
  letter-spacing: 0;
}
.page-content {
  display: flex;
  max-width: 920px;
  margin: -18rpx auto 0;
  padding: 0 28rpx;
  box-sizing: border-box;
  flex-direction: column;
  background: linear-gradient(180deg, #f8fcfe 0, #fff 110rpx);
}
.section-divider {
  height: 4rpx;
  margin: 34rpx 0;
  background: #e3f1fa;
}
.knowledge-section,
.practice-section {
  display: flex;
  flex-direction: column;
  gap: 22rpx;
}
.module-head,
.module-heading {
  display: flex;
  align-items: center;
}
.module-head {
  justify-content: space-between;
}
.module-heading {
  gap: 14rpx;
}
.module-mark {
  width: 8rpx;
  height: 46rpx;
  background: linear-gradient(180deg, #18d8d5, #087ccf);
  border-radius: 99rpx;
  box-shadow: 0 4rpx 10rpx rgba(8, 124, 207, 0.12);
}
.module-title {
  color: var(--learning-ink);
  font-size: 36rpx;
  font-weight: 850;
  letter-spacing: -1rpx;
}
.module-link {
  min-height: 72rpx;
  margin: 0;
  padding: 0 4rpx 0 18rpx;
  color: #5b73a5;
  background: transparent;
  font-size: 25rpx;
  line-height: 72rpx;
}
.module-link text {
  margin-left: 10rpx;
  color: var(--learning-blue);
  font-size: 36rpx;
}
.category-scroll {
  width: 100%;
  white-space: nowrap;
}
.category-track {
  display: inline-flex;
  gap: 10rpx;
}
.category-tab {
  min-height: 64rpx;
  margin: 0;
  padding: 0 22rpx;
  color: #6277a5;
  background: #f3f7fd;
  border-radius: 15rpx;
  font-size: 23rpx;
  white-space: nowrap;
}
.category-tab.active {
  color: #087ccf;
  background: #e4f5fd;
  font-weight: 750;
}
.knowledge-list {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}
.knowledge-list-scroll {
  width: 100%;
  height: 492rpx;
}
.knowledge-row {
  display: flex;
  width: 100%;
  min-height: 112rpx;
  margin: 0;
  padding: 20rpx 18rpx;
  align-items: center;
  gap: 18rpx;
  color: var(--learning-text);
  background: #fff;
  border: 1rpx solid var(--learning-border);
  border-radius: 18rpx;
  text-align: left;
}
.knowledge-icon {
  position: relative;
  display: flex;
  width: 72rpx;
  height: 72rpx;
  align-items: center;
  justify-content: center;
  flex: 0 0 72rpx;
  background: linear-gradient(145deg, #edf8ff, #deeffc);
  border-radius: 50%;
}
.knowledge-glyph {
  position: relative;
  width: 34rpx;
  height: 40rpx;
}
.knowledge-glyph::before,
.knowledge-glyph::after {
  position: absolute;
  top: 7rpx;
  width: 15rpx;
  height: 28rpx;
  content: '';
  background: linear-gradient(180deg, #62c3ff, #0877e6);
  border-radius: 13rpx 13rpx 16rpx 16rpx;
}
.knowledge-glyph::before {
  left: 1rpx;
  transform: rotate(10deg);
}
.knowledge-glyph::after {
  right: 1rpx;
  transform: rotate(-10deg);
}
.knowledge-icon--1 {
  background: linear-gradient(145deg, #fff1f4, #ffe0e7);
}
.knowledge-icon--1 .knowledge-glyph::before,
.knowledge-icon--1 .knowledge-glyph::after {
  background: linear-gradient(180deg, #ff8195, #ee405e);
  transform: rotate(35deg);
  border-radius: 50% 50% 45% 45%;
}
.knowledge-icon--2 {
  background: linear-gradient(145deg, #fff8e8, #ffebc7);
}
.knowledge-icon--2 .knowledge-glyph::before,
.knowledge-icon--2 .knowledge-glyph::after {
  background: linear-gradient(180deg, #ffc05b, #f08b1e);
  transform: rotate(70deg);
  border-radius: 60% 35% 60% 35%;
}
.knowledge-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 6rpx;
}
.knowledge-title {
  display: -webkit-box;
  overflow: hidden;
  color: var(--learning-ink);
  font-size: 27rpx;
  font-weight: 800;
  line-height: 1.4;
  text-overflow: ellipsis;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.knowledge-meta {
  color: var(--learning-muted);
  font-size: 21rpx;
  line-height: 1.45;
}
.knowledge-progress {
  display: flex;
  width: 166rpx;
  flex: 0 0 166rpx;
  align-items: center;
  gap: 12rpx;
}
.status-track {
  height: 16rpx;
  overflow: hidden;
  flex: 1;
  background: #e4ebf3;
  border-radius: 99rpx;
}
.status-fill {
  height: 100%;
  min-width: 0;
  background: linear-gradient(90deg, #4eb5f5, #087ccf);
  border-radius: inherit;
}
.status-fill--weak {
  background: linear-gradient(90deg, #ff7890, #e94f68);
}
.status-fill--due {
  background: linear-gradient(90deg, #50d8c4, #14bfae);
}
.status-fill--stable {
  background: linear-gradient(90deg, #47d7c1, #1caf9e);
}
.status-label {
  min-width: 62rpx;
  color: #6376a3;
  font-size: 21rpx;
  text-align: right;
}
.row-arrow {
  flex: none;
  color: var(--learning-blue);
  font-size: 42rpx;
}
.inline-state {
  display: flex;
  min-height: 108rpx;
  padding: 20rpx 22rpx;
  box-sizing: border-box;
  justify-content: center;
  flex-direction: column;
  gap: 8rpx;
  color: var(--learning-muted);
  background: #f7fbfe;
  border: 1rpx dashed #cfe8f5;
  border-radius: 18rpx;
  font-size: 23rpx;
}
.inline-state--error {
  color: var(--med-danger);
}
.inline-state button {
  min-height: 64rpx;
  margin: 0;
  padding: 0;
  color: var(--learning-blue);
  background: transparent;
  font-size: 23rpx;
  text-align: left;
}
.practice-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14rpx;
}
.practice-card {
  display: flex;
  min-width: 0;
  min-height: 124rpx;
  margin: 0;
  padding: 20rpx 16rpx;
  align-items: center;
  gap: 12rpx;
  color: var(--learning-text);
  background: #fff;
  border: 1rpx solid var(--learning-border);
  border-radius: 18rpx;
  text-align: left;
}
.practice-icon {
  display: flex;
  width: 58rpx;
  height: 58rpx;
  align-items: center;
  justify-content: center;
  flex: 0 0 58rpx;
  background: linear-gradient(145deg, #eaf9ff, #dff0ff);
  border-radius: 15rpx;
}
.practice-card--knowledge .practice-icon {
  background: linear-gradient(145deg, #e6fffb, #c9f7ef);
}
.practice-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 5rpx;
}
.practice-title {
  color: var(--learning-ink);
  font-size: 25rpx;
  font-weight: 800;
  line-height: 1.35;
}
.practice-description {
  overflow: hidden;
  color: var(--learning-muted);
  font-size: 19rpx;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.practice-arrow {
  flex: none;
  color: var(--learning-blue);
  font-size: 38rpx;
}
.learning-page :deep(.student-primary-nav) {
  border-top-color: #dcecf5;
  box-shadow: 0 -8rpx 24rpx rgba(8, 83, 139, 0.045);
}
.learning-page :deep(.student-nav__item) {
  color: #7183ad;
}
.learning-page :deep(.student-nav__item.active) {
  color: #087ccf;
}
@media screen and (max-width: 360px) {
  .hero-subtitle,
  .module-link,
  .category-tab,
  .knowledge-meta,
  .status-label,
  .inline-state {
    font-size: 12px;
  }
  .practice-description {
    font-size: 12px;
  }
  .knowledge-progress {
    width: 138rpx;
    flex-basis: 138rpx;
  }
}
@media screen and (min-width: 600px) {
  .learning-hero {
    height: 172px;
    padding: 34px 40px;
  }
  .hero-copy {
    max-width: 640px;
    gap: 10px;
  }
  .hero-slogan {
    font-size: 25px;
  }
  .hero-subtitle {
    font-size: 15px;
  }
  .page-content {
    padding: 32px 32px 0;
  }
  .section-divider {
    height: 2px;
    margin: 32px 0;
  }
  .module-title {
    font-size: 24px;
  }
  .module-link {
    font-size: 15px;
  }
  .knowledge-row {
    min-height: 92px;
    padding: 16px;
  }
  .knowledge-list-scroll {
    height: 316px;
  }
  .knowledge-title {
    font-size: 17px;
  }
  .knowledge-meta,
  .status-label {
    font-size: 13px;
  }
  .practice-card {
    min-height: 104px;
    padding: 18px;
  }
  .practice-title {
    font-size: 16px;
  }
  .practice-description {
    font-size: 13px;
  }
}
</style>
