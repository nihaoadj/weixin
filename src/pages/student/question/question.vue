<template>
  <view
    class="safe-page page"
    :class="{ 'page--knowledge': activeView === 'knowledge' }"
  >
    <text
      class="sr-only"
      role="heading"
      aria-level="1"
      >{{ pageTitle }}</text
    >

    <template v-if="activeView === 'cases'">
      <view class="case-intro">
        <view class="case-hero">
          <view class="case-hero__copy">
            <text class="case-hero__title">病例列表</text>
            <text class="case-hero__subtitle">结合结构化教学病例，提升病理思维能力</text>
          </view>
          <image
            class="case-hero__decoration"
            :src="caseHeroSrc"
            mode="aspectFit"
            alt=""
            aria-hidden="true"
          />
        </view>

        <view class="case-toolbar">
          <view
            class="case-scope-tabs"
            role="group"
            aria-label="病例学习状态筛选"
          >
            <button
              v-for="item in caseScopeOptions"
              :key="item.key"
              class="case-scope-tab"
              :class="{ active: caseScope === item.key }"
              :aria-pressed="caseScope === item.key"
              @keydown="activateButtonOnKey"
              @click="caseScope = item.key"
            >
              {{ item.label }}
            </button>
          </view>
          <button
            class="case-filter"
            :aria-label="difficultyFilter === 'all' ? '筛选病例难度' : `当前难度：${difficultyLabel(difficultyFilter)}`"
            @keydown="activateButtonOnKey"
            @click="showDifficultyFilter"
          >
            <view
              class="case-filter__icon"
              aria-hidden="true"
            >
              <text />
              <text />
              <text />
            </view>
            <text>{{ difficultyFilter === 'all' ? '筛选' : difficultyLabel(difficultyFilter) }}</text>
          </button>
        </view>
      </view>
    </template>
    <MedState
      v-if="loading"
      variant="loading"
      icon="retry"
      title="正在加载训练内容"
      description="正在获取可用教学病例。"
    />
    <MedState
      v-else-if="error"
      variant="error"
      icon="retry"
      title="训练内容加载失败"
      :description="error"
      action-label="重新加载"
      @action="load"
    />
    <template v-else-if="activeView === 'cases'">
      <view class="resource-section">
        <view
          v-if="visibleCases.length"
          class="case-list"
          role="list"
        >
          <button
            v-for="(problem, index) in visibleCases"
            :key="problem.id"
            class="case-card"
            role="listitem"
            :aria-label="`${caseActionLabel(problem.id)}病例：${problem.title}`"
            @keydown="activateButtonOnKey"
            @click="activateCase(problem.id)"
          >
            <view
              class="case-card__visual"
              :class="`case-card__visual--${index % 5}`"
              aria-hidden="true"
            >
              <view class="case-card__glyph">
                <text
                  v-for="part in 5"
                  :key="part"
                />
              </view>
            </view>
            <view class="case-card__copy">
              <text class="case-title">{{ problem.title }}</text>
              <text class="case-level">{{ difficultyLabel(problem.difficulty) }}</text>
              <text class="case-meta">{{ caseMeta(problem) }}</text>
            </view>
            <view class="case-card__action">
              <text>{{ caseActionLabel(problem.id) }}</text>
              <text
                class="case-card__arrow"
                aria-hidden="true"
                >›</text
              >
            </view>
          </button>
        </view>
        <view
          v-else-if="cases.length"
          class="case-empty"
        >
          <text class="case-empty__title">当前筛选下没有病例</text>
          <text class="case-empty__copy">可以查看全部病例或清除难度筛选。</text>
          <button @click="clearCaseFilters">查看全部病例</button>
        </view>
        <view
          v-else
          class="case-empty"
        >
          <text class="case-empty__title">暂时没有已发布病例</text>
          <text class="case-empty__copy">教师发布新的结构化病例后会显示在这里。</text>
        </view>
        <view
          class="case-footer-note"
          role="note"
        >
          合成教学内容，仅用于病理学习，不构成诊疗建议。
        </view>
      </view>
    </template>

    <PathologyKnowledgeMap
      v-else-if="activeView === 'knowledge'"
      ref="knowledgeMap"
    />

    <StudentPrimaryNav active="learning" />
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onBackPress, onLoad, onShow } from '@dcloudio/uni-app'
import PathologyKnowledgeMap from '@/features/learning/presentation/PathologyKnowledgeMap.vue'
import { activateButtonOnKey } from '@/components/ui/keyboard'
import MedState from '@/components/ui/MedState.vue'
import StudentPrimaryNav from '@/components/ui/StudentPrimaryNav.vue'
import { getDemoCaseProblemsAsync, getProblemsAsync } from '@/features/content/public'
import { requireRole } from '@/features/identity/public'
import { getCaseAttemptsAsync, startCaseAttemptAsync } from '@/features/training/public'
import { goDetail, handleBackPress, ROUTES } from '@/platform/navigation'
import type { CaseAttempt } from '@/types/case'
import type { Problem } from '@/types/domain'

type ResourceView = 'cases' | 'knowledge'
type CaseScope = 'all' | 'studied'

const resourceViews = new Set<ResourceView>(['cases', 'knowledge'])
const caseHeroSrc = '/static/case-list-hero.svg'
const pageTitles: Record<ResourceView, string> = {
  cases: '病例学习',
  knowledge: '知识点树',
}
const caseScopeOptions: Array<{ key: CaseScope; label: string }> = [
  { key: 'all', label: '全部' },
  { key: 'studied', label: '已学' },
]
const activeView = ref<ResourceView>('cases')
const caseScope = ref<CaseScope>('all')
const difficultyFilter = ref('all')
const knowledgeMap = ref<{ refresh: () => Promise<void> }>()
const cases = ref<Problem[]>([])
const attempts = ref<CaseAttempt[]>([])
const error = ref('')
const loading = ref(false)
const pageTitle = computed(() => pageTitles[activeView.value])
const latestAttemptByProblem = computed(() => {
  const latest = new Map<string, CaseAttempt>()
  const sorted = [...attempts.value].sort(
    (left, right) => new Date(right.startedAt).getTime() - new Date(left.startedAt).getTime(),
  )
  for (const attempt of sorted) {
    if (!latest.has(attempt.problemId)) latest.set(attempt.problemId, attempt)
  }
  return latest
})
const difficultyOptions = computed(() => [
  ...new Set(cases.value.flatMap((item) => (item.difficulty ? [item.difficulty] : []))),
])
const visibleCases = computed(() =>
  cases.value.filter((problem) => {
    const matchesScope = caseScope.value === 'all' || latestAttemptByProblem.value.has(problem.id)
    const matchesDifficulty = difficultyFilter.value === 'all' || problem.difficulty === difficultyFilter.value
    return matchesScope && matchesDifficulty
  }),
)

onLoad((options) => {
  const requested = typeof options?.view === 'string' ? options.view : ''
  activeView.value = resourceViews.has(requested as ResourceView) ? (requested as ResourceView) : 'cases'
  caseScope.value = 'all'
  difficultyFilter.value = 'all'
  uni.setNavigationBarTitle({ title: pageTitle.value })
})

async function load() {
  if (loading.value) return
  loading.value = true
  error.value = ''
  try {
    const [all, mine, demoCases] = await Promise.all([
      getProblemsAsync(),
      getCaseAttemptsAsync(),
      getDemoCaseProblemsAsync(),
    ])
    const publishedCases = [
      ...all.filter((item) => item.contentType === 'guided_case' && item.status === '已发布'),
      ...demoCases,
    ]
    cases.value = [...new Map(publishedCases.map((item) => [item.id, item])).values()]
    attempts.value = mine
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '请稍后重试'
  } finally {
    loading.value = false
  }
}

async function start(id: string) {
  try {
    openAttempt((await startCaseAttemptAsync(id)).id)
  } catch (reason) {
    uni.showToast({ title: reason instanceof Error ? reason.message : '无法开始训练', icon: 'none' })
  }
}

function openAttempt(id: string) {
  goDetail(ROUTES.studentCaseTraining, { id })
}

function openReport(id: string) {
  goDetail(ROUTES.studentCaseReport, { attemptId: id })
}

function difficultyLabel(value?: string) {
  const labels: Record<string, string> = { basic: '基础', intermediate: '进阶', advanced: '挑战' }
  return value ? labels[value] || value : '未分级'
}

function caseMeta(problem: Problem) {
  const specialty = problem.specialty || '病理学'
  const duration = problem.estimatedMinutes ? `${problem.estimatedMinutes}分钟` : '时长待定'
  const version = problem.version ? `V${problem.version}` : '版本待定'
  return `${specialty} · ${duration} · ${version}`
}

function caseActionLabel(problemId: string) {
  const attempt = latestAttemptByProblem.value.get(problemId)
  if (!attempt) return '开始'
  return attempt.status === 'assessed' ? '复盘' : '继续'
}

async function activateCase(problemId: string) {
  const attempt = latestAttemptByProblem.value.get(problemId)
  if (!attempt) {
    await start(problemId)
    return
  }
  if (attempt.status === 'assessed') {
    openReport(attempt.id)
    return
  }
  openAttempt(attempt.id)
}

function showDifficultyFilter() {
  const options = ['all', ...difficultyOptions.value]
  uni.showActionSheet({
    itemList: options.map((item) => (item === 'all' ? '全部难度' : difficultyLabel(item))),
    success: ({ tapIndex }) => {
      difficultyFilter.value = options[tapIndex] || 'all'
    },
  })
}

function clearCaseFilters() {
  caseScope.value = 'all'
  difficultyFilter.value = 'all'
}

onShow(() => {
  if (requireRole('student')) {
    if (activeView.value === 'knowledge') void knowledgeMap.value?.refresh()
    else void load()
  }
})

onBackPress(({ from }) => handleBackPress(from, ROUTES.studentLearning))
</script>

<style scoped>
.page {
  --case-ink: #071a5a;
  --case-text: #35558d;
  --case-muted: #7183ad;
  --case-cyan: #079baa;
  --case-blue: #087ccf;
  --case-page: #f2fafe;
  --case-border: #d6eaf7;
  --case-divider: #e7f2f8;
  min-height: 100vh;
  overflow-x: hidden;
  padding: 20rpx 28rpx 170rpx;
  color: var(--case-text);
  background: linear-gradient(180deg, var(--case-page) 0, #f8fcfe 620rpx, #fff 1180rpx);
}
.page--knowledge {
  padding: 0 0 170rpx;
  background: linear-gradient(180deg, #eef9fe 0, #f8fcff 960rpx, #f3fafe 100%);
}
.case-intro {
  max-width: 920px;
  margin: -20rpx -28rpx 24rpx;
  background: linear-gradient(155deg, #f8fdff 0%, #eaf8fd 65%, #f7fcff 100%);
}
.case-hero {
  position: relative;
  min-height: 136rpx;
  overflow: hidden;
  padding: 22rpx 14rpx 12rpx;
  box-sizing: border-box;
}
.case-hero::after {
  position: absolute;
  right: -80rpx;
  bottom: -80rpx;
  width: 470rpx;
  height: 180rpx;
  content: '';
  background: rgba(255, 255, 255, 0.48);
  border-radius: 50%;
  transform: rotate(-8deg);
}
.case-hero__copy {
  position: absolute;
  z-index: 2;
  top: 22rpx;
  left: 14rpx;
  display: flex;
  max-width: 450rpx;
  flex-direction: column;
  gap: 12rpx;
}
.case-hero__title {
  color: var(--case-ink);
  font-size: 46rpx;
  font-weight: 850;
  letter-spacing: -2rpx;
  line-height: 1.2;
}
.case-hero__subtitle {
  color: #6278a7;
  font-size: 21rpx;
  font-weight: 650;
  line-height: 1.45;
  white-space: nowrap;
}
.case-hero__decoration {
  position: absolute;
  z-index: 1;
  top: -9rpx;
  right: -2rpx;
  width: 390rpx;
  height: 174rpx;
}
.case-toolbar,
.case-scope-tabs,
.case-filter {
  display: flex;
  align-items: center;
}
.case-toolbar {
  position: relative;
  z-index: 2;
  padding: 0 28rpx 14rpx;
  justify-content: space-between;
  gap: 18rpx;
}
.case-scope-tabs {
  gap: 12rpx;
}
.case-scope-tab {
  min-width: 98rpx;
  min-height: 52rpx;
  margin: 0;
  padding: 0 22rpx;
  color: #6376a3;
  background: #edf3f8;
  border-radius: 99rpx;
  font-size: 22rpx;
  font-weight: 650;
}
.case-scope-tab.active {
  color: #fff;
  background: linear-gradient(135deg, #13b9c7, #079baa);
  box-shadow: 0 9rpx 22rpx rgba(7, 155, 170, 0.17);
}
.case-filter {
  min-height: 52rpx;
  margin: 0;
  padding: 0 8rpx 0 18rpx;
  justify-content: flex-end;
  gap: 12rpx;
  color: #6278a7;
  background: transparent;
  font-size: 22rpx;
}
.case-filter__icon {
  position: relative;
  width: 34rpx;
  height: 34rpx;
}
.case-filter__icon text {
  position: absolute;
  left: 0;
  height: 3rpx;
  background: #637aa8;
  border-radius: 99rpx;
}
.case-filter__icon text:nth-child(1) {
  top: 5rpx;
  width: 27rpx;
}
.case-filter__icon text:nth-child(2) {
  top: 15rpx;
  left: 6rpx;
  width: 17rpx;
}
.case-filter__icon text:nth-child(3) {
  top: 25rpx;
  left: 13rpx;
  width: 7rpx;
}
.case-filter__icon::after {
  position: absolute;
  top: 7rpx;
  right: 6rpx;
  width: 3rpx;
  height: 22rpx;
  content: '';
  background: #637aa8;
  border-radius: 99rpx;
  transform: rotate(18deg);
  transform-origin: top center;
}
.case-footer-note {
  padding: 8rpx 4rpx 18rpx;
  color: var(--case-muted);
  font-size: 20rpx;
  line-height: 1.5;
  text-align: center;
}
.resource-section {
  max-width: 920px;
  margin: 0 auto 22rpx;
}
.resource-section {
  display: flex;
  flex-direction: column;
  gap: 18rpx;
}
.case-title {
  color: var(--case-ink);
  font-weight: 700;
}
.case-title {
  font-size: 28rpx;
}
.case-list {
  display: grid;
  grid-template-columns: 1fr;
  gap: 18rpx;
}
.case-card {
  display: grid;
  width: 100%;
  min-height: 172rpx;
  margin: 0;
  padding: 22rpx 22rpx 22rpx 20rpx;
  box-sizing: border-box;
  align-items: center;
  grid-template-columns: 104rpx minmax(0, 1fr) 138rpx;
  gap: 18rpx;
  color: var(--case-text);
  background: #fff;
  border: 1rpx solid rgba(190, 222, 240, 0.76);
  border-radius: 24rpx;
  box-shadow: 0 12rpx 30rpx rgba(8, 124, 207, 0.075);
  text-align: left;
}
.case-card__visual {
  position: relative;
  display: flex;
  width: 104rpx;
  height: 104rpx;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: linear-gradient(145deg, #f0f8ff, #dbeeff);
  border-radius: 22rpx;
}
.case-card__glyph {
  position: relative;
  width: 72rpx;
  height: 72rpx;
}
.case-card__glyph text {
  position: absolute;
  display: block;
}
.case-card__visual--0 .case-card__glyph text,
.case-card__visual--4 .case-card__glyph text {
  width: 27rpx;
  height: 27rpx;
  background: radial-gradient(circle at 42% 38%, #a9d3ff 0 25%, #4b85df 28% 47%, #d5e8ff 50% 63%, #5a7fd1 66%);
  border-radius: 50%;
  box-shadow: 0 4rpx 8rpx rgba(56, 105, 186, 0.13);
}
.case-card__visual--0 .case-card__glyph text:nth-child(1),
.case-card__visual--4 .case-card__glyph text:nth-child(1) {
  top: 2rpx;
  left: 23rpx;
}
.case-card__visual--0 .case-card__glyph text:nth-child(2),
.case-card__visual--4 .case-card__glyph text:nth-child(2) {
  top: 25rpx;
  left: 2rpx;
}
.case-card__visual--0 .case-card__glyph text:nth-child(3),
.case-card__visual--4 .case-card__glyph text:nth-child(3) {
  top: 25rpx;
  right: 2rpx;
}
.case-card__visual--0 .case-card__glyph text:nth-child(4),
.case-card__visual--4 .case-card__glyph text:nth-child(4) {
  bottom: 0;
  left: 23rpx;
}
.case-card__visual--0 .case-card__glyph text:nth-child(5),
.case-card__visual--4 .case-card__glyph text:nth-child(5) {
  top: 26rpx;
  left: 23rpx;
  width: 23rpx;
  height: 23rpx;
}
.case-card__visual--1 {
  background: linear-gradient(145deg, #fff4fb, #f8e1f1);
}
.case-card__visual--1 .case-card__glyph::before {
  position: absolute;
  top: 9rpx;
  left: 9rpx;
  width: 54rpx;
  height: 54rpx;
  content: '';
  background: #e89ad9;
  border: 4rpx solid #c86ac2;
  border-radius: 44% 56% 48% 52%;
  box-shadow:
    -9rpx 4rpx 0 -6rpx #c86ac2,
    8rpx -5rpx 0 -6rpx #c86ac2,
    8rpx 8rpx 0 -6rpx #c86ac2;
}
.case-card__visual--1 .case-card__glyph::after {
  position: absolute;
  top: 28rpx;
  left: 27rpx;
  width: 23rpx;
  height: 19rpx;
  content: '';
  background: #b84eaf;
  border-radius: 48% 52% 45% 55%;
}
.case-card__visual--1 .case-card__glyph text {
  width: 8rpx;
  height: 8rpx;
  background: #fff0fa;
  border-radius: 50%;
}
.case-card__visual--1 .case-card__glyph text:nth-child(1) {
  top: 20rpx;
  left: 24rpx;
}
.case-card__visual--1 .case-card__glyph text:nth-child(2) {
  top: 19rpx;
  right: 19rpx;
}
.case-card__visual--1 .case-card__glyph text:nth-child(3) {
  bottom: 16rpx;
  left: 19rpx;
}
.case-card__visual--2 {
  background: linear-gradient(145deg, #effffb, #d9f7ee);
}
.case-card__visual--2 .case-card__glyph text:nth-child(1),
.case-card__visual--2 .case-card__glyph text:nth-child(2) {
  top: 25rpx;
  left: 4rpx;
  width: 64rpx;
  height: 24rpx;
  background: linear-gradient(90deg, #63d7be, #a7ecdc);
  border-radius: 12rpx;
  transform: rotate(45deg);
}
.case-card__visual--2 .case-card__glyph text:nth-child(2) {
  transform: rotate(-45deg);
}
.case-card__visual--2 .case-card__glyph text:nth-child(3) {
  top: 29rpx;
  left: 29rpx;
  width: 14rpx;
  height: 14rpx;
  background: #eafffa;
  border-radius: 3rpx;
}
.case-card__visual--3 {
  background: linear-gradient(145deg, #fff6f6, #ffe5e8);
}
.case-card__visual--3 .case-card__glyph::before {
  position: absolute;
  top: 15rpx;
  left: -10rpx;
  width: 92rpx;
  height: 42rpx;
  content: '';
  background: linear-gradient(180deg, #ffb6bd, #ffd9dd 42%, #ff9ca8 46% 57%, #ffd7dc 60%, #ffb2ba);
  border: 2rpx solid #f07f8d;
  border-radius: 46% 54% 48% 52%;
  transform: rotate(-16deg);
}
.case-card__visual--3 .case-card__glyph text {
  z-index: 1;
  width: 13rpx;
  height: 8rpx;
  background: #ed566b;
  border-radius: 50%;
  transform: rotate(-16deg);
}
.case-card__visual--3 .case-card__glyph text:nth-child(1) {
  top: 27rpx;
  left: 5rpx;
}
.case-card__visual--3 .case-card__glyph text:nth-child(2) {
  top: 31rpx;
  left: 27rpx;
}
.case-card__visual--3 .case-card__glyph text:nth-child(3) {
  top: 24rpx;
  right: 8rpx;
}
.case-card__visual--4 {
  background: linear-gradient(145deg, #f8f2ff, #eadffc);
}
.case-card__visual--4 .case-card__glyph text {
  background: radial-gradient(circle at 42% 38%, #d4b5fb 0 25%, #8a55ca 28% 47%, #ebdcff 50% 63%, #8450be 66%);
}
.case-card__copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 8rpx;
}
.case-title {
  display: -webkit-box;
  overflow: hidden;
  font-size: 29rpx;
  font-weight: 800;
  line-height: 1.35;
  text-overflow: ellipsis;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.case-level {
  align-self: flex-start;
  padding: 5rpx 17rpx;
  color: var(--case-cyan);
  background: #e4f8f3;
  border-radius: 99rpx;
  font-size: 20rpx;
  font-weight: 700;
  line-height: 1.25;
}
.case-meta {
  overflow: hidden;
  color: var(--case-muted);
  font-size: 21rpx;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.case-card__action {
  display: flex;
  min-height: 74rpx;
  padding: 0 18rpx 0 24rpx;
  box-sizing: border-box;
  align-items: center;
  justify-content: space-between;
  gap: 8rpx;
  color: #078b9d;
  background: linear-gradient(135deg, #e0f8f4, #e8faf8);
  border-radius: 99rpx;
  font-size: 27rpx;
  font-weight: 750;
  white-space: nowrap;
}
.case-card__arrow {
  color: #0593aa;
  font-size: 42rpx;
  font-weight: 400;
  line-height: 1;
}
.case-empty {
  display: flex;
  min-height: 220rpx;
  padding: 42rpx 28rpx;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 12rpx;
  color: var(--case-muted);
  background: rgba(255, 255, 255, 0.76);
  border: 1rpx dashed #bfdfed;
  border-radius: 22rpx;
  text-align: center;
}
.case-empty__title {
  color: var(--case-ink);
  font-size: 27rpx;
  font-weight: 750;
}
.case-empty__copy {
  font-size: 22rpx;
  line-height: 1.55;
}
.case-empty button {
  min-height: 76rpx;
  margin: 8rpx 0 0;
  padding: 0 28rpx;
  color: var(--case-cyan);
  background: #e5f8f4;
  border-radius: 99rpx;
  font-size: 24rpx;
}
@media screen and (max-width: 360px) {
  .case-hero__subtitle,
  .case-filter,
  .case-level,
  .case-meta,
  .case-empty__copy {
    font-size: 12px;
  }
  .case-card {
    grid-template-columns: 92rpx minmax(0, 1fr) 128rpx;
    gap: 14rpx;
  }
  .case-card__visual {
    width: 92rpx;
    height: 92rpx;
  }
}
@media screen and (min-width: 600px) {
  .page {
    padding: 24px 32px 128px;
  }
  .page.page--knowledge {
    padding: 0 0 128px;
  }
  .case-intro {
    margin-top: -24px;
    margin-right: -32px;
    margin-bottom: 24px;
    margin-left: -32px;
  }
  .case-hero {
    min-height: 118px;
    padding: 22px 18px 12px;
  }
  .case-hero__copy {
    top: 22px;
    left: 18px;
    max-width: 460px;
    gap: 10px;
  }
  .case-hero__title {
    font-size: 36px;
  }
  .case-hero__subtitle {
    font-size: 17px;
  }
  .case-hero__decoration {
    top: -8px;
    width: 330px;
    height: 146px;
  }
  .case-toolbar {
    padding: 0 32px 14px;
  }
  .case-scope-tab,
  .case-filter {
    min-height: 48px;
    font-size: 15px;
  }
  .resource-section {
    margin-bottom: 20px;
  }
  .case-title {
    font-size: 17px;
  }
  .case-list {
    gap: 16px;
  }
  .case-card {
    min-height: 138px;
    padding: 18px 20px;
    grid-template-columns: 92px minmax(0, 1fr) 132px;
    gap: 20px;
  }
  .case-card__visual {
    width: 92px;
    height: 92px;
  }
  .case-card__action {
    min-height: 48px;
    font-size: 17px;
  }
  .case-level,
  .case-meta {
    font-size: 13px;
  }
}
</style>
