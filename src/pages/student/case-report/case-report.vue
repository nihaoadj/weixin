<template>
  <view class="safe-page page">
    <MedState
      v-if="error"
      icon="retry"
      title="报告加载失败"
      :description="error"
      action-label="重新加载"
      @action="load"
    />
    <view
      v-if="report"
      class="card hero"
      ><text class="eyebrow-label">{{ report.fallbackUsed ? '确定性兜底报告' : '模型报告' }}</text
      ><text class="score">{{ report.totalScore }}</text
      ><text>总分 / 100</text><text class="muted">{{ report.summary }}</text></view
    >
    <view
      v-if="report"
      class="card body"
      ><text class="section">六维评价</text
      ><view
        v-for="dimension in report.dimensions"
        :key="dimension.dimensionId"
        class="dimension"
        ><view
          ><text>{{ dimension.label }}</text
          ><text>{{ dimension.score }}</text></view
        ><view class="bar"><view :style="{ width: `${dimension.score}%` }" /></view
        ><text class="muted">{{ dimension.feedback }}</text
        ><text class="evidence">{{ dimension.evidence.join('；') }}</text
        ><text class="muted">下一步：{{ dimension.nextStep }}</text></view
      ></view
    >
    <view
      v-if="report"
      class="card body"
      ><text class="section">优势</text><text>{{ report.strengths.join('、') || '继续完成更多高质量推理。' }}</text
      ><text class="section">薄弱点</text><text>{{ report.weaknesses.join('、') || '暂无明显薄弱维度。' }}</text
      ><view
        v-if="report.comparison"
        class="comparison"
        ><text class="section">较上次</text><text>总分 {{ signed(report.comparison.totalDelta) }}</text
        ><text
          v-for="item in report.comparison.dimensions"
          :key="item.dimensionId"
          >{{ item.dimensionId }}：{{ signed(item.delta) }}</text
        ></view
      ><button
        class="primary"
        @click="retry"
      >
        强化薄弱阶段</button
      ><button
        class="secondary"
        @click="openLearning"
      >
        查看个性化训练计划</button
      ><button
        class="secondary"
        @click="back"
      >
        返回病例列表
      </button></view
    >
  </view>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import MedState from '@/components/ui/MedState.vue'
import { requireRole } from '@/services/auth'
import { getCaseAssessmentAsync, getCaseAttemptAsync, startCaseAttemptAsync } from '@/services/caseRepositoryAsync'
import type { CaseAssessment } from '@/types/case'
const report = ref<CaseAssessment>()
const error = ref('')
let id = ''
async function load() {
  try {
    report.value = await getCaseAssessmentAsync(id)
    if (!report.value) error.value = '报告尚未生成'
  } catch (e) {
    error.value = e instanceof Error ? e.message : '请重试'
  }
}
const signed = (value: number) => (value > 0 ? `+${value}` : String(value))
async function retry() {
  const attempt = await getCaseAttemptAsync(id)
  if (!attempt) return
  const next = await startCaseAttemptAsync(attempt.problemId, id)
  uni.redirectTo({ url: `/pages/student/case-training/case-training?id=${next.id}` })
}
function back() {
  uni.reLaunch({ url: '/pages/student/question/question' })
}
function openLearning() {
  uni.navigateTo({ url: '/pages/student/learning/index' })
}
onLoad((query) => {
  if (!requireRole('student')) return
  id = String(query?.attemptId || '')
  void load()
})
</script>
<style scoped>
.page {
  padding: 28rpx;
}
.hero,
.body {
  display: flex;
  margin-bottom: 20rpx;
  padding: 30rpx;
  flex-direction: column;
  gap: 14rpx;
}
.score {
  color: #087f8c;
  font-size: 80rpx;
  font-weight: 800;
}
.section {
  margin-top: 8rpx;
  color: #0b2239;
  font-size: 29rpx;
  font-weight: 700;
}
.muted {
  color: #718096;
  font-size: 22rpx;
  line-height: 1.5;
}
.dimension {
  display: flex;
  padding: 18rpx 0;
  flex-direction: column;
  gap: 8rpx;
  border-bottom: 1rpx solid #edf2f7;
}
.dimension > view:first-child {
  display: flex;
  justify-content: space-between;
}
.bar {
  height: 12rpx;
  background: #e6edf2;
  border-radius: 99rpx;
}
.bar view {
  height: 100%;
  background: #087f8c;
  border-radius: 99rpx;
}
.evidence {
  font-size: 22rpx;
  white-space: pre-wrap;
}
.comparison {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}
.primary,
.secondary {
  height: 78rpx;
  line-height: 78rpx;
  color: #fff;
  background: #087f8c;
}
.secondary {
  color: #087f8c;
  background: #e6f7f5;
}
</style>
