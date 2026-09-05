<template>
  <view class="safe-page page">
    <text
      class="sr-only"
      role="heading"
      aria-level="1"
      >病例与练习</text
    >

    <view
      class="resource-tabs"
      role="group"
      aria-label="选择训练资源"
    >
      <button
        v-for="item in viewOptions"
        :key="item.key"
        class="resource-tab"
        :class="{ active: activeView === item.key }"
        :aria-pressed="activeView === item.key"
        @keydown="activateButtonOnKey"
        @click="switchView(item.key)"
      >
        {{ item.label }}
      </button>
    </view>

    <view
      class="safety-note"
      role="note"
    >
      合成教学内容，用于病理学习，不构成诊疗建议。
    </view>

    <MedState
      v-if="loading"
      variant="loading"
      icon="retry"
      title="正在加载训练内容"
      description="正在获取可用病例与练习。"
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
      <view
        v-if="continuing"
        class="card section priority-section"
      >
        <text class="section-label">下一步</text>
        <text class="section-title">继续病例训练</text>
        <text>{{ continuing.opening.chiefComplaint }} · {{ stageLabel(continuing.currentStage) }}</text>
        <button
          class="primary"
          @click="openAttempt(continuing.id)"
        >
          继续训练
        </button>
      </view>

      <view class="resource-section">
        <text class="section-title">推荐病例</text>
        <view
          v-if="cases.length"
          class="case-list"
          role="list"
        >
          <button
            v-for="problem in cases"
            :key="problem.id"
            class="card case"
            role="listitem"
            :aria-label="'开始病例：' + problem.title"
            @click="start(problem.id)"
          >
            <view>
              <text class="case-title">{{ problem.title }}</text>
              <text class="muted">
                {{ problem.specialty }} · {{ problem.difficulty }} · {{ problem.estimatedMinutes }}分钟 · V{{
                  problem.version
                }}
              </text>
            </view>
            <text class="go">开始 ›</text>
          </button>
        </view>
        <text
          v-else
          class="empty-note"
          >暂时没有已发布病例。</text
        >
      </view>

      <view
        v-if="recent"
        class="card section"
      >
        <text class="section-title">最近训练结果</text>
        <text>总分 {{ recent.totalScore }} · 薄弱阶段 {{ stageLabel(recent.focusStage) }}</text>
        <button
          class="secondary"
          @click="openReport(recent.attemptId)"
        >
          查看训练报告
        </button>
      </view>
    </template>

    <PathologyKnowledgeMap v-else-if="activeView === 'knowledge'" />

    <template v-else>
      <view class="resource-section">
        <text class="section-title">PBL 讨论题</text>
        <view
          v-if="pblQuestions.length"
          class="question-list card"
        >
          <view
            v-for="item in pblQuestions"
            :key="item.id"
            class="question pbl-question"
          >
            <view>
              <text class="question-title">{{ item.title }}</text>
              <text class="muted">{{ item.description }}</text>
            </view>
            <text class="muted">开放讨论</text>
          </view>
        </view>
        <text
          v-else
          class="empty-note"
          >暂时没有 PBL 讨论题。</text
        >
      </view>

      <view class="resource-section">
        <text class="section-title">其他练习</text>
        <view
          v-if="questions.length"
          class="question-list card"
        >
          <button
            v-for="item in questions"
            :key="item.id"
            class="question"
            :aria-label="'查看练习：' + item.title"
            @click="openQuestion(item.id)"
          >
            <text class="question-title">{{ item.title }}</text>
            <text class="muted">{{ item.status }}</text>
          </button>
        </view>
        <text
          v-else
          class="empty-note"
          >暂时没有其他练习。</text
        >
      </view>
    </template>

    <StudentPrimaryNav active="learning" />
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onBackPress, onLoad, onShow } from '@dcloudio/uni-app'
import PathologyKnowledgeMap from '@/components/student/PathologyKnowledgeMap.vue'
import { activateButtonOnKey } from '@/components/ui/keyboard'
import MedState from '@/components/ui/MedState.vue'
import StudentPrimaryNav from '@/components/ui/StudentPrimaryNav.vue'
import { getDemoCaseProblemsAsync, getProblemsAsync } from '@/features/content/public'
import { requireRole } from '@/features/identity/public'
import { getStudentQuestionsAsync } from '@/features/qa/public'
import { getCaseAssessmentAsync, getCaseAttemptsAsync, startCaseAttemptAsync } from '@/features/training/public'
import { goDetail, handleBackPress, ROUTES } from '@/platform/navigation'
import { caseStages, type CaseAssessment, type CaseAttempt } from '@/types/case'
import type { Problem, StudentQuestion } from '@/types/domain'

type ResourceView = 'cases' | 'knowledge' | 'questions'

const viewOptions: Array<{ key: ResourceView; label: string }> = [
  { key: 'cases', label: '病例' },
  { key: 'knowledge', label: '知识' },
  { key: 'questions', label: '练习' },
]
const activeView = ref<ResourceView>('cases')
const cases = ref<Problem[]>([])
const pblQuestions = ref<Problem[]>([])
const questions = ref<StudentQuestion[]>([])
const attempts = ref<CaseAttempt[]>([])
const recent = ref<CaseAssessment>()
const error = ref('')
const loading = ref(false)
const continuing = computed(() => attempts.value.find((item) => item.status === 'in_progress'))
const stageLabel = (id?: string) => caseStages.find((item) => item.id === id)?.label || '训练完成'

onLoad((options) => {
  const requested = typeof options?.view === 'string' ? options.view : ''
  activeView.value = viewOptions.some((item) => item.key === requested) ? (requested as ResourceView) : 'cases'
})

async function load() {
  if (loading.value) return
  loading.value = true
  error.value = ''
  try {
    const [all, old, mine, demoCases] = await Promise.all([
      getProblemsAsync(),
      getStudentQuestionsAsync(),
      getCaseAttemptsAsync(),
      getDemoCaseProblemsAsync(),
    ])
    cases.value = [
      ...all.filter((item) => item.contentType === 'guided_case' && item.status === '已发布'),
      ...demoCases,
    ]
    pblQuestions.value = all.filter(
      (item) => item.contentType === 'question' && item.type === 'open_discussion' && item.status === '已发布',
    )
    questions.value = old.filter(
      (item) => !all.find((problem) => problem.id === item.id && problem.contentType === 'guided_case'),
    )
    attempts.value = mine
    const assessed = mine.find((item) => item.status === 'assessed')
    recent.value = assessed ? await getCaseAssessmentAsync(assessed.id) : undefined
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '请稍后重试'
  } finally {
    loading.value = false
  }
}

function switchView(view: ResourceView) {
  activeView.value = view
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

function openQuestion(id: string) {
  goDetail(ROUTES.studentQuestionDetail, { id, returnView: 'questions' })
}

onShow(() => {
  if (requireRole('student')) void load()
})

onBackPress(({ from }) => handleBackPress(from, ROUTES.studentLearning))
</script>

<style scoped>
.page {
  padding: 20rpx 28rpx 170rpx;
  background: var(--med-page);
}
.resource-tabs {
  display: grid;
  max-width: 920px;
  margin: 0 auto 18rpx;
  padding: 6rpx;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6rpx;
  background: var(--med-surface);
  border: 1rpx solid var(--med-border);
  border-radius: var(--med-radius-md);
}
.resource-tab {
  min-height: 76rpx;
  margin: 0;
  color: var(--med-muted);
  background: transparent;
  border-radius: var(--med-radius-sm);
  font-size: 25rpx;
}
.resource-tab.active {
  color: var(--med-clinical);
  background: var(--med-wash);
  font-weight: 700;
}
.safety-note,
.empty-note {
  display: block;
  max-width: 920px;
  margin: 0 auto 20rpx;
  color: var(--med-muted);
  font-size: 22rpx;
  line-height: 1.5;
}
.safety-note {
  padding: 12rpx 18rpx;
  box-sizing: border-box;
  border-left: 4rpx solid var(--med-safety);
  background: var(--med-safety-soft);
}
.resource-section,
.section {
  max-width: 920px;
  margin: 0 auto 22rpx;
}
.resource-section {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}
.section {
  display: flex;
  padding: 26rpx;
  flex-direction: column;
  gap: 12rpx;
}
.priority-section {
  border-top: 6rpx solid var(--med-clinical);
}
.section-label {
  color: var(--med-clinical);
  font-family: var(--med-font-utility);
  font-size: 21rpx;
  font-weight: 700;
}
.section-title,
.case-title,
.question-title {
  color: var(--med-navy);
  font-weight: 700;
}
.section-title {
  font-size: 30rpx;
}
.case-title,
.question-title {
  font-size: 28rpx;
}
.case-list {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16rpx;
}
.case {
  display: flex;
  width: 100%;
  min-height: 104rpx;
  margin: 0;
  padding: 24rpx;
  align-items: center;
  justify-content: space-between;
  gap: 20rpx;
  color: var(--med-text);
  text-align: left;
}
.case > view,
.pbl-question > view {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 8rpx;
}
.muted {
  color: var(--med-muted);
  font-size: 22rpx;
  line-height: 1.5;
}
.go {
  flex: none;
  color: var(--med-clinical);
}
.question-list {
  padding: 0 24rpx;
}
.question {
  display: flex;
  width: 100%;
  min-height: 88rpx;
  margin: 0;
  padding: 22rpx 0;
  align-items: center;
  justify-content: space-between;
  gap: 20rpx;
  color: var(--med-text);
  background: transparent;
  border-bottom: 1rpx solid var(--med-divider);
  border-radius: 0;
  text-align: left;
}
.question:last-child {
  border-bottom: 0;
}
.primary,
.secondary {
  min-height: 76rpx;
  margin: 6rpx 0 0;
  font-size: 25rpx;
}
.primary {
  color: #fff;
  background: var(--med-clinical);
}
.secondary {
  color: var(--med-clinical);
  background: var(--med-wash);
}
@media screen and (max-width: 360px) {
  .resource-tab,
  .primary,
  .secondary {
    font-size: 13px;
  }
  .muted,
  .safety-note,
  .empty-note {
    font-size: 12px;
  }
}
@media screen and (min-width: 600px) {
  .page {
    padding: 24px 32px 128px;
  }
  .resource-tabs {
    margin-bottom: 16px;
    padding: 4px;
    gap: 4px;
  }
  .resource-tab {
    min-height: 48px;
    font-size: 15px;
  }
  .safety-note,
  .empty-note {
    margin-bottom: 20px;
    padding: 10px 14px;
    font-size: 14px;
  }
  .resource-section,
  .section {
    margin-bottom: 20px;
  }
  .section {
    padding: 24px;
  }
  .section-title {
    font-size: 20px;
  }
  .case-title,
  .question-title {
    font-size: 17px;
  }
  .muted {
    font-size: 14px;
  }
  .case-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
  }
  .case {
    min-height: 96px;
    padding: 20px;
  }
}
</style>
