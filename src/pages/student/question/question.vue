<template>
  <view class="safe-page page">
    <PathologyKnowledgeMap />
    <view class="card intro"
      ><text class="eyebrow-label">PATHOLOGY CASE TRAINING</text><text class="title">病理学病例练习</text
      ><text class="muted">合成教学病例，不构成诊疗建议</text></view
    >
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
      title="病例加载失败"
      :description="error"
      action-label="重新加载"
      @action="load"
    />
    <MedState
      v-else-if="!hasContent"
      variant="first-use"
      icon="book"
      title="暂时没有可用训练"
      description="教师发布病例或练习后会显示在这里。你可以稍后刷新，或先使用医学问答助手。"
      action-label="重新加载"
      secondary-action-label="进入医学问答"
      @action="load"
      @secondary-action="openChat"
    />
    <template v-else>
      <view
        v-if="continuing"
        class="card section"
        ><text class="section-title">继续训练</text
        ><text>{{ continuing.opening.chiefComplaint }} · {{ stageLabel(continuing.currentStage) }}</text
        ><button
          class="primary"
          @click="openAttempt(continuing.id)"
        >
          继续
        </button></view
      >
      <text class="section-title">推荐病例</text>
      <view
        v-for="problem in cases"
        :key="problem.id"
        class="card case"
        @click="start(problem.id)"
        ><view
          ><text class="case-title">{{ problem.title }}</text
          ><text class="muted"
            >{{ problem.specialty }} · {{ problem.difficulty }} · {{ problem.estimatedMinutes }}分钟 · V{{
              problem.version
            }}</text
          ></view
        ><text class="go">开始 ›</text></view
      >
      <view
        v-if="recent"
        class="card section"
        ><text class="section-title">最近报告</text
        ><text>总分 {{ recent.totalScore }} · 薄弱阶段 {{ stageLabel(recent.focusStage) }}</text
        ><button
          class="secondary"
          @click="openReport(recent.attemptId)"
        >
          查看报告
        </button></view
      >
      <view
        v-if="pblQuestions.length"
        class="card section"
      >
        <text class="section-title">PBL 讨论题</text>
        <view
          v-for="item in pblQuestions"
          :key="item.id"
          class="question pbl-question"
        >
          <view
            ><text>{{ item.title }}</text
            ><text class="muted">{{ item.description }}</text></view
          >
          <text class="muted">开放讨论</text>
        </view>
      </view>
      <view class="card section">
        <text class="section-title">其他练习</text>
        <view
          v-for="item in questions"
          :key="item.id"
          class="question"
          @click="openQuestion(item.id)"
        >
          <text>{{ item.title }}</text>
          <text class="muted">{{ item.status }}</text>
        </view>
      </view>
    </template>
    <StudentPrimaryNav active="question" />
  </view>
</template>
<script setup lang="ts">
import PathologyKnowledgeMap from '@/components/student/PathologyKnowledgeMap.vue'
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import MedState from '@/components/ui/MedState.vue'
import StudentPrimaryNav from '@/components/ui/StudentPrimaryNav.vue'
import { getCaseAssessmentAsync, getCaseAttemptsAsync, startCaseAttemptAsync } from '@/features/training/public'
import { requireRole } from '@/features/identity/public'
import { goDetail, goPrimary, ROUTES } from '@/platform/navigation'
import { getDemoCaseProblemsAsync, getProblemsAsync } from '@/features/content/public'
import { getStudentQuestionsAsync } from '@/features/qa/public'
import { caseStages, type CaseAttempt, type CaseAssessment } from '@/types/case'
import type { Problem, StudentQuestion } from '@/types/domain'
const cases = ref<Problem[]>([])
const pblQuestions = ref<Problem[]>([])
const questions = ref<StudentQuestion[]>([])
const attempts = ref<CaseAttempt[]>([])
const recent = ref<CaseAssessment>()
const error = ref('')
const loading = ref(false)
const continuing = computed(() => attempts.value.find((item) => item.status === 'in_progress'))
const hasContent = computed(() =>
  Boolean(
    cases.value.length || pblQuestions.value.length || questions.value.length || continuing.value || recent.value,
  ),
)
const stageLabel = (id?: string) => caseStages.find((item) => item.id === id)?.label || '训练完成'
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
    if (assessed) recent.value = await getCaseAssessmentAsync(assessed.id)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '请稍后重试'
  } finally {
    loading.value = false
  }
}
async function start(id: string) {
  try {
    openAttempt((await startCaseAttemptAsync(id)).id)
  } catch (e) {
    uni.showToast({ title: e instanceof Error ? e.message : '无法开始训练', icon: 'none' })
  }
}
function openAttempt(id: string) {
  goDetail(ROUTES.studentCaseTraining, { id })
}
function openReport(id: string) {
  goDetail(ROUTES.studentCaseReport, { attemptId: id })
}
function openQuestion(id: string) {
  goDetail(ROUTES.studentQuestionDetail, { id })
}
function openChat() {
  goPrimary(ROUTES.studentChat)
}
onShow(() => {
  if (requireRole('student')) void load()
})
</script>
<style scoped>
.page {
  padding: 28rpx 28rpx 170rpx;
}
.intro,
.section {
  display: flex;
  margin-bottom: 24rpx;
  padding: 30rpx;
  flex-direction: column;
  gap: 12rpx;
}
.title,
.section-title,
.case-title {
  color: var(--med-navy);
  font-size: 34rpx;
  font-weight: 700;
}
.section-title {
  display: block;
  margin: 18rpx 4rpx;
  font-size: 29rpx;
}
.case {
  display: flex;
  margin-bottom: 18rpx;
  padding: 28rpx;
  align-items: center;
  justify-content: space-between;
}
.case view {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}
.muted {
  color: var(--med-muted);
  font-size: 22rpx;
}
.go {
  color: var(--med-brand);
}
.primary,
.secondary {
  height: 76rpx;
  margin: 10rpx 0 0;
  line-height: 76rpx;
  color: #fff;
  background: var(--med-brand);
  font-size: 25rpx;
}
.secondary {
  color: var(--med-brand);
  background: var(--med-brand-soft);
}
.question {
  display: flex;
  padding: 22rpx 0;
  justify-content: space-between;
  border-bottom: 1rpx solid var(--med-divider);
}
.pbl-question view {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 8rpx;
}
</style>
