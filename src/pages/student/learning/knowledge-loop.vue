<template>
  <view class="safe-page loop-page">
    <view class="flow-section flow-hero">
      <text class="eyebrow-label">本知识点巩固</text>
      <text class="title">{{ selectedTopics[0]?.title || '知识点巩固' }}</text>
      <text class="muted">完成本轮客观小测；提交前不会显示答案或解析。</text>
      <view class="topic-list">
        <text
          v-for="topic in selectedTopics"
          :key="topic.code"
          class="topic-chip"
          >{{ topic.title }}</text
        >
      </view>
      <button
        class="primary"
        :disabled="!topicCodes.length || loading"
        @click="startExitQuiz"
      >
        {{ cards.length ? '重新抽取小测' : '开始 3 题巩固' }}
      </button>
    </view>

    <view
      v-if="cards.length"
      class="card quiz"
    >
      <text class="section-title">第 {{ cardIndex + 1 }} / {{ cards.length }} 题</text>
      <text class="prompt">{{ currentCard?.prompt }}</text>
      <button
        v-for="(option, index) in currentCard?.options || []"
        :key="option"
        class="option"
        :class="{ selected: selectedOption === index }"
        @click="selectedOption = index"
      >
        {{ String.fromCharCode(65 + index) }}. {{ option }}
      </button>
      <view class="confidence-row">
        <text class="muted">把握程度</text>
        <button
          v-for="item in confidences"
          :key="item.value"
          class="confidence"
          :class="{ selected: confidence === item.value }"
          @click="confidence = item.value"
        >
          {{ item.label }}
        </button>
      </view>
      <button
        class="primary"
        :disabled="selectedOption === undefined || submitting"
        @click="submitAnswer"
      >
        提交本题
      </button>
      <view
        v-if="result"
        class="result"
        :class="result.correct ? 'correct' : 'incorrect'"
      >
        <text>{{ result.correct ? '回答正确' : '这题需要回顾' }}</text>
        <text>{{ result.explanation }}</text>
        <text class="muted">下次复习：{{ formatDue(result.dueAt) }}</text>
        <button
          v-if="cardIndex < cards.length - 1"
          class="secondary"
          @click="nextCard"
        >
          下一题
        </button>
      </view>
    </view>

    <view
      v-if="recallCards.length"
      class="flow-section recall-section"
    >
      <text class="section-title">教师补充 · 主动回忆</text>
      <text class="muted">先在心中作答，再揭晓教学要点并记录你的回忆质量。</text>
      <view
        v-for="card in recallCards"
        :key="card.id"
        class="recall-card"
      >
        <text class="prompt">{{ card.prompt }}</text>
        <button
          v-if="activeRecallId !== card.id"
          class="secondary"
          @click="beginRecall(card.id)"
        >
          开始回忆
        </button>
        <template v-else>
          <button
            v-if="!revealedRecall"
            class="primary"
            :loading="recallLoading"
            @click="revealRecall"
          >
            揭晓教学要点
          </button>
          <template v-else>
            <view class="recall-answer"
              ><text>{{ revealedRecall.explanation }}</text></view
            >
            <view class="confidence-row">
              <button
                v-for="item in recallRatings"
                :key="item.value"
                class="confidence"
                :class="{ selected: recallRating === item.value }"
                :disabled="recallLoading"
                @click="rateRecall(item.value)"
              >
                {{ item.label }}
              </button>
            </view>
            <text
              v-if="recallResult"
              class="muted"
              >已记录；下次复习：{{ formatDue(recallResult.dueAt) }}</text
            >
          </template>
        </template>
      </view>
    </view>

    <view class="flow-section section">
      <view class="section-head">
        <text class="section-title">待复习</text>
        <text class="badge">{{ dashboard.dueCount }} 张</text>
      </view>
      <text class="muted">错题会自动进入队列；主动保存的问答重点也会在这里显示。</text>
      <view
        v-for="item in dashboard.items"
        :key="item.id"
        class="review-item"
      >
        <text>{{ topicName(item.pointCode) }}</text>
        <text class="muted">{{ item.note || '来自问答或客观小测' }}</text>
        <button
          class="ask-link"
          @click="askAbout(item.pointCode, '答错后追问原因')"
        >
          带着薄弱点去问助手
        </button>
      </view>
      <button
        v-if="dashboard.dueCount"
        class="secondary"
        @click="loadDueQueue"
      >
        开始到期复习
      </button>
      <button
        v-else
        class="secondary"
        @click="askAbout(topicCodes[0], '复习前先解释核心机制')"
      >
        复习前先问助手
      </button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import {
  createExitQuiz,
  getDueReviewQueue,
  getKnowledgeCatalog,
  getReviewDashboard,
  gradeObjectiveCard,
  rateRecallCard,
  revealRecallCard,
} from '@/features/learning/public'
import { getKnowledgeCardContributions } from '@/features/content/public'
import type {
  KnowledgeCardContribution,
  KnowledgePoint,
  RecallReveal,
  ReviewCard,
  ReviewDashboard,
  ReviewGrade,
} from '@/types/knowledge'
import { goDetail, ROUTES } from '@/platform/navigation'

const points = ref<KnowledgePoint[]>([])
const topicCodes = ref<string[]>([])
const cards = ref<ReviewCard[]>([])
const cardIndex = ref(0)
const selectedOption = ref<number>()
const confidence = ref<'low' | 'medium' | 'high'>('medium')
const result = ref<ReviewGrade>()
const loading = ref(false)
const submitting = ref(false)
const dashboard = ref<ReviewDashboard>({ dueCount: 0, weakPointCodes: [], items: [] })
const recallCards = ref<KnowledgeCardContribution[]>([])
const activeRecallId = ref<number>()
const revealedRecall = ref<RecallReveal>()
const recallRating = ref<'again' | 'hard' | 'good' | 'easy'>('good')
const recallResult = ref<ReviewGrade>()
const recallLoading = ref(false)
const confidences = [
  { value: 'low' as const, label: '不确定' },
  { value: 'medium' as const, label: '一般' },
  { value: 'high' as const, label: '很确定' },
]
const recallRatings = [
  { value: 'again' as const, label: '没有想起' },
  { value: 'hard' as const, label: '想起很吃力' },
  { value: 'good' as const, label: '基本想起' },
  { value: 'easy' as const, label: '轻松想起' },
]
const selectedTopics = computed(() => points.value.filter((point) => topicCodes.value.includes(point.code)))
const currentCard = computed(() => cards.value[cardIndex.value])

onLoad((options) => {
  const topicParam =
    typeof options?.topicCodes === 'string'
      ? options.topicCodes
      : typeof options?.topicCode === 'string'
        ? options.topicCode
        : ''
  void load(topicParam.split(',').filter(Boolean))
})

async function load(requestedTopics: string[]) {
  loading.value = true
  try {
    const [catalog, reviewDashboard, supplementalCards] = await Promise.all([
      getKnowledgeCatalog(),
      getReviewDashboard(),
      getKnowledgeCardContributions(),
    ])
    points.value = catalog
    topicCodes.value = requestedTopics.filter((code) => points.value.some((point) => point.code === code)).slice(0, 1)
    dashboard.value = {
      ...reviewDashboard,
      items: reviewDashboard.items.filter((item) => topicCodes.value.includes(item.pointCode)),
      dueCount: reviewDashboard.items.filter((item) => topicCodes.value.includes(item.pointCode)).length,
    }
    recallCards.value = supplementalCards.filter(
      (card) => card.cardType === 'recall' && card.status === 'approved' && topicCodes.value.includes(card.pointCode),
    )
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : '学习数据加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

async function startExitQuiz() {
  if (!topicCodes.value.length) return
  loading.value = true
  result.value = undefined
  selectedOption.value = undefined
  cardIndex.value = 0
  try {
    cards.value = await createExitQuiz(topicCodes.value)
    if (!cards.value.length) uni.showToast({ title: '这些主题暂未配置客观卡', icon: 'none' })
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : '小测创建失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

async function submitAnswer() {
  if (!currentCard.value || selectedOption.value === undefined || submitting.value) return
  submitting.value = true
  try {
    result.value = await gradeObjectiveCard(currentCard.value.cardCode, selectedOption.value, confidence.value)
    dashboard.value = await getReviewDashboard()
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : '提交失败', icon: 'none' })
  } finally {
    submitting.value = false
  }
}

function nextCard() {
  if (cardIndex.value >= cards.value.length - 1) return
  cardIndex.value += 1
  selectedOption.value = undefined
  result.value = undefined
}

async function loadDueQueue() {
  try {
    const dueCards = await getDueReviewQueue()
    if (!dueCards.length) return
    cards.value = dueCards
    cardIndex.value = 0
    selectedOption.value = undefined
    result.value = undefined
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : '复习队列加载失败', icon: 'none' })
  }
}

function beginRecall(cardId: number) {
  activeRecallId.value = cardId
  revealedRecall.value = undefined
  recallResult.value = undefined
  recallRating.value = 'good'
}

async function revealRecall() {
  if (!activeRecallId.value || recallLoading.value) return
  recallLoading.value = true
  try {
    revealedRecall.value = await revealRecallCard(activeRecallId.value)
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : '回忆卡揭晓失败', icon: 'none' })
  } finally {
    recallLoading.value = false
  }
}

async function rateRecall(rating: 'again' | 'hard' | 'good' | 'easy') {
  if (!activeRecallId.value || recallLoading.value) return
  recallRating.value = rating
  recallLoading.value = true
  try {
    recallResult.value = await rateRecallCard(activeRecallId.value, rating)
    dashboard.value = await getReviewDashboard()
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : '回忆自评保存失败', icon: 'none' })
  } finally {
    recallLoading.value = false
  }
}

function topicName(code: string) {
  return points.value.find((point) => point.code === code)?.title || code
}

function formatDue(value: string) {
  return value.replace('T', ' ').slice(0, 16)
}

function askAbout(pointCode: string | undefined, prompt: string) {
  if (!pointCode) {
    uni.showToast({ title: '请先选择学习主题', icon: 'none' })
    return
  }
  goDetail(ROUTES.studentPbl, { topicCode: pointCode, starter: prompt })
}
</script>

<style scoped>
.loop-page {
  padding: 28rpx;
  background: var(--med-page);
}
.quiz {
  margin-bottom: 20rpx;
  padding: 28rpx;
}
.flow-section {
  max-width: 920px;
  margin: 0 auto;
  padding: 34rpx 2rpx;
  border-top: 1rpx solid var(--med-border);
}
.flow-hero {
  padding-top: 12rpx;
  border-top: 0;
}
.hero,
.quiz,
.section,
.recall-section,
.map-section {
  display: flex;
  flex-direction: column;
  gap: 18rpx;
}
.recall-card {
  display: flex;
  padding-top: 18rpx;
  flex-direction: column;
  gap: 14rpx;
  border-top: 1rpx solid var(--med-border);
}
.map-system {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
}
.map-system-title {
  color: var(--med-ink);
  font-size: 25rpx;
  font-weight: 700;
}
.map-topics {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
}
.map-topic {
  display: flex;
  min-height: 52rpx;
  margin: 0;
  padding: 6rpx 14rpx;
  align-items: center;
  gap: 8rpx;
  color: var(--med-text);
  background: var(--med-wash);
  border: 1rpx solid var(--med-border);
  border-radius: var(--med-radius-sm);
  font-size: 22rpx;
  line-height: 1.35;
  text-align: left;
}
.map-status {
  color: var(--med-muted);
  font-size: 20rpx;
}
.status-weak {
  border-color: var(--med-danger, #b64a4a);
}
.status-due {
  border-color: var(--med-warning, #9b6f20);
}
.status-stable {
  border-color: var(--med-success, #317a59);
}
.recall-card:first-of-type {
  border-top: 0;
}
.recall-answer {
  padding: 18rpx;
  color: var(--med-text);
  background: var(--med-brand-soft);
  border-left: 4rpx solid var(--med-brand);
  font-size: 25rpx;
  line-height: 1.65;
}
.title {
  color: var(--med-ink);
  font-size: 34rpx;
  font-weight: 800;
  line-height: 1.4;
}
.eyebrow-label,
.muted {
  color: var(--med-muted);
  font-size: 24rpx;
  line-height: 1.6;
}
.topic-list,
.confidence-row,
.section-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12rpx;
}
.section-head {
  justify-content: space-between;
}
.topic-chip,
.topic-add,
.confidence {
  min-height: 48rpx;
  margin: 0;
  padding: 0 16rpx;
  color: var(--med-clinical);
  background: var(--med-wash);
  border-radius: 99rpx;
  font-size: 24rpx;
  line-height: 48rpx;
}
.topic-add,
.confidence {
  color: var(--med-text-secondary);
  background: transparent;
  border: 1rpx solid var(--med-border);
}
.confidence.selected,
.option.selected {
  color: #fff;
  background: var(--med-clinical);
  border-color: var(--med-clinical);
}
.primary,
.secondary {
  width: 100%;
  min-height: 88rpx;
  margin: 0;
  border-radius: var(--med-radius-sm);
  font-size: 28rpx;
}
.primary {
  color: #fff;
  background: var(--med-clinical);
}
.secondary {
  color: var(--med-clinical);
  background: var(--med-wash);
}
.section-title,
.prompt {
  color: var(--med-ink);
  font-size: 29rpx;
  font-weight: 700;
  line-height: 1.6;
}
.option {
  width: 100%;
  min-height: 80rpx;
  margin: 0;
  padding: 18rpx;
  color: var(--med-text);
  text-align: left;
  background: var(--med-surface);
  border: 1rpx solid var(--med-border);
  border-radius: var(--med-radius-sm);
  font-size: 26rpx;
  line-height: 1.5;
}
.badge {
  padding: 4rpx 12rpx;
  color: var(--med-clinical);
  background: var(--med-wash);
  border-radius: 99rpx;
  font-size: 22rpx;
}
.result {
  display: flex;
  padding: 18rpx;
  flex-direction: column;
  gap: 8rpx;
  border-radius: var(--med-radius-sm);
  font-size: 25rpx;
  line-height: 1.6;
}
.result.correct {
  color: #166534;
  background: #eefbf3;
}
.result.incorrect {
  color: #9a3412;
  background: #fff7ed;
}
.review-item {
  display: flex;
  padding: 16rpx 0;
  flex-direction: column;
  gap: 6rpx;
  border-top: 1rpx solid var(--med-border);
  font-size: 26rpx;
}
.ask-link {
  width: fit-content;
  min-height: 48rpx;
  margin: 0;
  padding: 0;
  color: var(--med-clinical);
  background: transparent;
  font-size: 24rpx;
  line-height: 48rpx;
}
</style>
