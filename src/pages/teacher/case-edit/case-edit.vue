<template>
  <view class="safe-page page">
    <view class="card intro"
      ><text class="title">病例五步编排器</text
      ><text class="muted">{{ statusLabel }} · 合成教学病例，不构成诊疗建议</text></view
    >
    <view class="steps"
      ><text
        v-for="item in steps"
        :key="item"
        :class="{ active: step === item }"
        >{{ item }}</text
      ></view
    >
    <view
      v-if="!draft"
      class="card form"
      ><input
        v-model="topic"
        placeholder="主题，例如：社区获得性肺炎"
      /><input
        v-model="level"
        placeholder="学习层级"
      /><textarea
        v-model="objectives"
        placeholder="教学目标，每行一个"
      /><button
        class="primary"
        :loading="loading"
        @click="generate"
      >
        生成病例草稿
      </button></view
    >
    <view
      v-else
      class="card form"
    >
      <template v-if="step === 1"
        ><input
          v-model="draft.title"
          :disabled="isReadOnly"
          placeholder="标题"
        /><textarea
          v-model="draft.description"
          :disabled="isReadOnly"
          placeholder="描述"
        /><input
          v-model="draft.specialty"
          :disabled="isReadOnly"
          placeholder="专科"
        /><input
          v-model.number="draft.estimatedMinutes"
          :disabled="isReadOnly"
          type="number"
          placeholder="预计分钟"
        /><textarea
          v-model="draft.caseDefinition.opening.patientIntro"
          :disabled="isReadOnly"
          placeholder="学生可见的患者简介"
        /><textarea
          v-model="draft.caseDefinition.opening.chiefComplaint"
          :disabled="isReadOnly"
          placeholder="主诉"
        />
      </template>
      <template v-else-if="step === 2"
        ><text class="section">阶段说明与隐藏事实（教师可编辑）</text
        ><textarea
          v-for="stage in stageIds"
          :key="stage"
          v-model="draft.caseDefinition.stageInstructions[stage]"
          :disabled="isReadOnly"
          :placeholder="`${stage}阶段说明`"
        /><text class="section">隐藏事实</text
        ><view
          v-for="fact in draft.caseDefinition.facts"
          :key="fact.id"
          class="fact"
          ><input
            v-model="fact.label"
            :disabled="isReadOnly"
            placeholder="标签" /><input
            v-model="fact.value"
            :disabled="isReadOnly"
            placeholder="内容" /><input
            :value="fact.triggers.join('、')"
            :disabled="isReadOnly"
            placeholder="触发词"
            @input="updateTriggers(fact, $event)" /></view
        ><button
          v-if="!isReadOnly"
          class="secondary"
          @click="addFact"
        >
          新增事实
        </button></template
      >
      <template v-else-if="step === 3"
        ><text class="section">参考路径</text
        ><textarea
          v-model="referenceText"
          :disabled="isReadOnly"
          placeholder="问题表征参考文本" /><view
          v-for="item in differentials"
          :key="item.diagnosis"
          class="fact"
          ><input
            v-model="item.diagnosis"
            :disabled="isReadOnly"
            placeholder="鉴别诊断" /><input
            :value="item.supportingFactIds?.join('、')"
            :disabled="isReadOnly"
            placeholder="支持事实 ID"
            @input="updateIds(item, 'supportingFactIds', $event)" /><input
            :value="item.opposingFactIds?.join('、')"
            :disabled="isReadOnly"
            placeholder="反对事实 ID"
            @input="updateIds(item, 'opposingFactIds', $event)" /></view
        ><text class="section">检查与处置</text
        ><view
          v-for="item in referenceTests"
          :key="item.name"
          class="fact"
          ><input
            v-model="item.name"
            :disabled="isReadOnly"
            placeholder="检查名称"
          /><textarea
            v-model="item.purpose"
            :disabled="isReadOnly"
            placeholder="检查目的"
          /></view
        ><view
          v-for="item in referenceManagement"
          :key="item.action"
          class="fact"
          ><input
            v-model="item.action"
            :disabled="isReadOnly"
            placeholder="处置行动"
          /><textarea
            v-model="item.rationale"
            :disabled="isReadOnly"
            placeholder="处置依据"
          /></view
      ></template>
      <template v-else-if="step === 4"
        ><text class="section">六维量表（权重固定）</text
        ><view
          v-for="dimension in draft.rubric.dimensions"
          :key="dimension.id"
          class="rubric"
          ><text>{{ dimension.label }} · {{ dimension.weight }}%</text
          ><input
            v-for="criterion in dimension.criteria"
            :key="criterion.id"
            v-model="criterion.label"
            :disabled="isReadOnly"
            placeholder="评价标准" /></view
      ></template>
      <template v-else
        ><text class="section">学生预览</text><text>{{ draft.caseDefinition.opening.patientIntro }}</text
        ><text>{{ draft.caseDefinition.opening.chiefComplaint }}</text
        ><text class="muted">学生视图不显示隐藏事实、参考路径和评分关键词。</text><text class="section">教师校验</text
        ><text
          v-for="fact in draft.caseDefinition.facts"
          :key="`preview-${fact.id}`"
          class="fact"
          >{{ fact.label }}：{{ fact.value }}</text
        ></template
      >
    </view>
    <view
      v-if="draft"
      class="actions"
      ><button
        v-if="step > 1"
        class="secondary"
        @click="step--"
      >
        上一步</button
      ><button
        v-if="step < 5"
        class="primary"
        @click="next"
      >
        下一步</button
      ><button
        v-if="step === 5 && !isReadOnly"
        class="primary"
        :loading="saving"
        @click="save"
      >
        保存草稿</button
      ><button
        v-if="step === 5 && canSubmitReview"
        class="secondary"
        :loading="submittingReview"
        @click="submitReview"
      >
        提交医学审核</button
      ><button
        v-if="step === 5 && canPublish"
        class="primary"
        :loading="publishing"
        @click="publish"
      >
        发布
      </button></view
    >
  </view>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { requireRole } from '@/services/auth'
import { backOrHome } from '@/services/navigation'
import {
  cloneCaseVersionAsync,
  generateCaseDraftAsync,
  getCaseAuthoringAsync,
  getGuidedCasesAsync,
  publishGuidedCaseAsync,
  saveGuidedCaseAsync,
  submitGuidedCaseForReviewAsync,
} from '@/services/caseRepositoryAsync'
import type { CaseDraftGenerateResult, CaseFact } from '@/types/case'
import type { Problem } from '@/types/domain'
const steps = [1, 2, 3, 4, 5]
const stageIds = ['history', 'problem_representation', 'differential', 'tests', 'management'] as const
const step = ref(1)
const topic = ref('社区获得性肺炎')
const level = ref('临床医学本科生')
const objectives = ref('训练病史采集\n训练鉴别诊断\n训练检查选择')
const draft = ref<CaseDraftGenerateResult>()
const currentId = ref<string>()
const currentSlug = ref<string>()
const loading = ref(false)
const saving = ref(false)
const publishing = ref(false)
const submittingReview = ref(false)
const referenceText = ref('')
const currentStatus = ref<Problem['status']>('待审核')
const reviewStatus = ref<NonNullable<Problem['medicalReviewStatus']>>('not_submitted')
const reference = computed(() => draft.value?.caseDefinition.referenceReasoning)
type ReferenceItem = NonNullable<
  CaseDraftGenerateResult['caseDefinition']['referenceReasoning']['differentials']
>[number]
const differentials = computed(() => reference.value?.differentials || [])
const referenceTests = computed(() => reference.value?.tests || [])
const referenceManagement = computed(() => reference.value?.management || [])
const isReadOnly = computed(() => reviewStatus.value === 'pending' || reviewStatus.value === 'approved')
const canSubmitReview = computed(
  () => Boolean(currentId.value) && (reviewStatus.value === 'not_submitted' || reviewStatus.value === 'rejected'),
)
const canPublish = computed(() => Boolean(currentId.value) && reviewStatus.value === 'approved')
const statusLabel = computed(() => {
  if (currentStatus.value === '已发布') return '已发布'
  if (reviewStatus.value === 'pending') return '医学审核中'
  if (reviewStatus.value === 'approved') return '审核通过，待发布'
  if (reviewStatus.value === 'rejected') return '已退回，可修改后重新提交'
  return '草稿，尚未提交审核'
})
async function generate() {
  loading.value = true
  try {
    draft.value = await generateCaseDraftAsync({
      topic: topic.value,
      learnerLevel: level.value,
      learningObjectives: objectives.value
        .split('\n')
        .map((item) => item.trim())
        .filter(Boolean),
    })
    referenceText.value = String(draft.value.caseDefinition.referenceReasoning.problemRepresentation || '')
    step.value = 1
  } finally {
    loading.value = false
  }
}
function next() {
  if (!draft.value) return
  if (isReadOnly.value) {
    step.value++
    return
  }
  if (!validateStep()) return
  if (step.value === 3) draft.value.caseDefinition.referenceReasoning.problemRepresentation = referenceText.value
  step.value++
}
function addFact() {
  draft.value?.caseDefinition.facts.push({
    id: `fact_${Date.now()}`,
    category: 'history',
    label: '新事实',
    value: '',
    triggers: [],
    revealStage: 'history',
  })
}
function updateTriggers(fact: CaseFact, event: unknown) {
  const target = (event as { target?: { value?: unknown } })?.target
  fact.triggers = String(target?.value || '')
    .split(/[、,，]/)
    .map((item) => item.trim())
    .filter(Boolean)
}
function updateIds(item: ReferenceItem, key: 'supportingFactIds' | 'opposingFactIds', event: unknown) {
  const target = (event as { target?: { value?: unknown } })?.target
  item[key] = String(target?.value || '')
    .split(/[、,，]/)
    .map((value) => value.trim())
    .filter(Boolean)
}
function validateStep() {
  if (!draft.value) return false
  if (step.value === 1 && (!draft.value.title.trim() || !draft.value.caseDefinition.opening.chiefComplaint.trim())) {
    uni.showToast({ title: '请补充标题和主诉', icon: 'none' })
    return false
  }
  if (
    step.value === 2 &&
    draft.value.caseDefinition.facts.some((fact) => !fact.label.trim() || !fact.value.trim() || !fact.triggers.length)
  ) {
    uni.showToast({ title: '事实的标签、内容和触发词不能为空', icon: 'none' })
    return false
  }
  if (step.value === 3 && (!reference.value?.problemRepresentation?.trim() || !differentials.value.length)) {
    uni.showToast({ title: '请补充参考表征和至少一项鉴别诊断', icon: 'none' })
    return false
  }
  if (
    step.value === 4 &&
    draft.value.rubric.dimensions.some((item) =>
      item.criteria.some((criterion) => !criterion.label.trim() || !criterion.keywords.length),
    )
  ) {
    uni.showToast({ title: '量表标签和关键词不能为空', icon: 'none' })
    return false
  }
  return true
}
async function save() {
  if (!draft.value) return
  if (!validateStep()) return
  saving.value = true
  try {
    if (step.value === 3) draft.value.caseDefinition.referenceReasoning.problemRepresentation = referenceText.value
    const result = await saveGuidedCaseAsync(draft.value, currentId.value, { slug: currentSlug.value })
    currentId.value = result.id
    currentSlug.value = result.slug || currentSlug.value
    currentStatus.value = result.status || '待审核'
    reviewStatus.value = result.medicalReviewStatus || 'not_submitted'
    uni.showToast({ title: '病例草稿已保存', icon: 'success' })
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : '保存失败', icon: 'none' })
  } finally {
    saving.value = false
  }
}
async function publish() {
  if (!currentId.value || !canPublish.value) return
  publishing.value = true
  try {
    await publishGuidedCaseAsync(currentId.value)
    uni.showToast({ title: '病例已发布', icon: 'success' })
    backOrHome('teacher')
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : '发布失败', icon: 'none' })
  } finally {
    publishing.value = false
  }
}
async function submitReview() {
  if (submittingReview.value) return
  if (!currentId.value) {
    await save()
  }
  if (!currentId.value || !canSubmitReview.value) return
  submittingReview.value = true
  try {
    const result = await submitGuidedCaseForReviewAsync(currentId.value)
    if (result) {
      currentStatus.value = result.status || '待审核'
      reviewStatus.value = result.medicalReviewStatus || 'pending'
    }
    uni.showToast({ title: '已提交医学审核', icon: 'success' })
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : '提交审核失败', icon: 'none' })
  } finally {
    submittingReview.value = false
  }
}
onLoad((query) => {
  if (!requireRole('teacher')) return
  const id = query?.id ? String(query.id) : ''
  if (!id) return
  void (async () => {
    const item = (await getGuidedCasesAsync()).find((problem) => problem.id === id)
    currentId.value = id
    currentSlug.value = item?.slug
    if (item?.status === '已发布') {
      const clone = await cloneCaseVersionAsync(id)
      currentId.value = clone.id
      currentSlug.value = clone.slug || currentSlug.value
      currentStatus.value = '待审核'
      reviewStatus.value = 'not_submitted'
    } else if (item) {
      currentStatus.value = item.status
      reviewStatus.value = item.medicalReviewStatus || 'not_submitted'
    }
    draft.value = await getCaseAuthoringAsync(currentId.value)
    if (draft.value) {
      referenceText.value = String(draft.value.caseDefinition.referenceReasoning.problemRepresentation || '')
      step.value = 1
    }
  })()
})
</script>
<style scoped>
.page {
  padding: 28rpx;
}
.intro,
.form {
  display: flex;
  margin-bottom: 20rpx;
  padding: 28rpx;
  flex-direction: column;
  gap: 14rpx;
}
.title {
  font-size: 34rpx;
  font-weight: 700;
}
.muted,
.fact {
  color: #718096;
  font-size: 22rpx;
  line-height: 1.5;
}
.steps {
  display: flex;
  margin-bottom: 18rpx;
  justify-content: space-between;
}
.steps text {
  padding: 8rpx 12rpx;
  color: #718096;
  background: #edf2f7;
  border-radius: 99rpx;
  font-size: 19rpx;
}
.steps .active {
  color: #fff;
  background: #087f8c;
}
.form input,
.form textarea {
  width: auto;
  min-height: 76rpx;
  padding: 14rpx;
  border: 1rpx solid #cbd5e1;
  border-radius: 12rpx;
}
.form textarea {
  min-height: 150rpx;
}
.section {
  font-size: 28rpx;
  font-weight: 700;
}
.fact {
  display: flex;
  padding: 12rpx 0;
  flex-direction: column;
  gap: 8rpx;
}
.rubric {
  display: flex;
  padding: 10rpx 0;
  flex-direction: column;
  gap: 6rpx;
}
.actions {
  display: flex;
  gap: 12rpx;
}
.primary,
.secondary {
  flex: 1;
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
