<template>
  <view class="safe-page page">
    <MedState
      v-if="loading"
      variant="loading"
      icon="retry"
      title="正在加载审核详情"
      description="正在读取病例版本与审核记录。"
    />
    <MedState
      v-else-if="loadError"
      variant="error"
      icon="retry"
      title="审核详情加载失败"
      :description="loadError"
      :action-label="id ? '重新加载' : '返回工作台'"
      :secondary-action-label="id ? '返回工作台' : ''"
      @action="id ? load : back"
      @secondary-action="back"
    />
    <view
      v-else-if="item"
      class="card"
    >
      <text class="title">{{ item.title }}</text>
      <text class="muted"
        >{{ item.specialty }} · {{ item.difficulty }} · 版本 {{ item.version }} · {{ statusLabel }}</text
      >
      <text class="section">元数据与学生开场</text>
      <text class="body">{{ item.description }}</text>
      <text class="body">场景：{{ item.caseDefinition.opening.setting }}</text>
      <text class="body">患者简介：{{ item.caseDefinition.opening.patientIntro }}</text>
      <text class="body">主诉：{{ item.caseDefinition.opening.chiefComplaint }}</text>

      <text class="section">隐藏事实（仅审核专家可见）</text>
      <view
        v-for="fact in item.caseDefinition.facts"
        :key="fact.id"
        class="row"
      >
        <text>{{ fact.label }} · {{ fact.id }}</text
        ><text class="body">{{ fact.value }}</text>
      </view>

      <text class="section">参考路径</text>
      <text class="body">{{ referenceProblem }}</text>
      <view
        v-for="entry in differentials"
        :key="entry.diagnosis"
        class="row"
      >
        <text>{{ entry.priority }}. {{ entry.diagnosis }}</text>
        <text class="body"
          >支持：{{ entry.supportingFactIds.join('、') || '无' }}；反对：{{
            entry.opposingFactIds.join('、') || '无'
          }}</text
        >
      </view>
      <view
        v-for="entry in referenceTests"
        :key="entry.name"
        class="row"
      >
        <text>检查：{{ entry.name }} · {{ entry.priority }}</text
        ><text class="body">{{ entry.purpose }}</text>
      </view>
      <view
        v-for="entry in referenceManagement"
        :key="entry.action"
        class="row"
      >
        <text>处置：{{ entry.action }}</text
        ><text class="body">{{ entry.rationale }}</text>
      </view>

      <text class="section">六维量表</text>
      <view
        v-for="dimension in item.rubric.dimensions"
        :key="dimension.id"
        class="row"
      >
        <text>{{ dimension.label }} · {{ dimension.weight }}%</text>
        <text
          v-for="criterion in dimension.criteria"
          :key="criterion.id"
          class="body"
          >{{ criterion.label }}：{{ criterion.keywords.join('、') }}</text
        >
      </view>

      <text
        v-if="item.caseDefinition.practiceBlueprints?.length"
        class="section"
        >练习蓝图</text
      >
      <view
        v-for="blueprint in item.caseDefinition.practiceBlueprints || []"
        :key="blueprint.id"
        class="row"
      >
        <text>{{ blueprint.id }} · {{ blueprint.dimensionId }} · {{ blueprint.stageId }}</text>
        <text class="body">{{ blueprint.publicInstruction }} · {{ blueprint.answerSchema }}</text>
      </view>
      <text class="section">审核摘要与版本</text>
      <text class="digest">当前 digest：{{ item.currentDigest }}</text>
      <text class="body">作者：{{ item.authorNickname || '未记录' }} · 父版本：{{ item.parentProblemId || '无' }}</text>
      <view
        v-for="review in item.reviews"
        :key="review.id"
        class="review"
      >
        <text>{{ review.decision === 'approved' ? '通过' : '退回' }} · {{ review.createdAt }}</text>
        <text class="body">{{ review.comment || '无意见' }} · digest {{ review.caseDigest }}</text>
      </view>

      <view
        v-if="item.medicalReviewStatus === 'pending'"
        class="decision"
      >
        <textarea
          v-model="comment"
          placeholder="退回意见至少 5 个字符；通过意见可留空"
        />
        <view class="actions">
          <button
            class="secondary"
            :loading="deciding"
            @click="decide('rejected')"
          >
            退回修改
          </button>
          <button
            class="primary"
            :loading="deciding"
            @click="decide('approved')"
          >
            审核通过
          </button>
        </view>
      </view>
      <text
        v-else
        class="muted"
        >该版本已完成审核，审核记录不可修改。</text
      >
    </view>
  </view>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { onBackPress, onLoad } from '@dcloudio/uni-app'
import MedState from '@/components/ui/MedState.vue'
import { requireRole } from '@/features/identity/public'
import { backOrRoute, handleBackPress, ROUTES } from '@/platform/navigation'
import { getReviewView, submitMedicalReview } from '@/features/content/public'
import type { MedicalReviewView } from '@/types/review'

const item = ref<MedicalReviewView>()
const comment = ref('')
const deciding = ref(false)
const loading = ref(false)
const loadError = ref('')
let id = ''
const reasoning = computed(() => item.value?.caseDefinition.referenceReasoning || {})
const referenceProblem = computed(() => String(reasoning.value.problemRepresentation || ''))
const differentials = computed(() => reasoning.value.differentials || [])
const referenceTests = computed(() => reasoning.value.tests || [])
const referenceManagement = computed(() => reasoning.value.management || [])
const statusLabel = computed(() =>
  item.value?.medicalReviewStatus === 'pending'
    ? '待审核'
    : item.value?.medicalReviewStatus === 'approved'
      ? '已通过'
      : '已退回',
)

function back() {
  backOrRoute(ROUTES.teacherReviewList)
}

async function load() {
  if (loading.value) return
  if (!id) {
    loadError.value = '缺少病例编号，无法打开审核详情。'
    return
  }
  loading.value = true
  loadError.value = ''
  try {
    item.value = await getReviewView(id)
    if (!item.value) loadError.value = '病例版本不存在，或当前身份无权查看。'
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '加载失败，请稍后重试。'
  } finally {
    loading.value = false
  }
}
onLoad((query) => {
  if (!requireRole('teacher')) return
  id = typeof query?.id === 'string' ? query.id : ''
  void load()
})
onBackPress(({ from }) => handleBackPress(from, ROUTES.teacherReviewList))
async function decide(decision: 'approved' | 'rejected') {
  if (deciding.value || !item.value) return
  if (decision === 'rejected' && comment.value.trim().length < 5) {
    uni.showToast({ title: '退回意见至少需要 5 个字符', icon: 'none' })
    return
  }
  if (decision === 'approved') {
    const result = await new Promise<boolean>((resolve) => {
      uni.showModal({
        title: '确认审核通过',
        content: '确认该版本的事实、参考路径和量表均可用于教学吗？',
        success: ({ confirm }) => resolve(confirm),
      })
    })
    if (!result) return
  }
  deciding.value = true
  try {
    await submitMedicalReview(id, decision, comment.value.trim())
    uni.showToast({ title: decision === 'approved' ? '已通过' : '已退回', icon: 'success' })
    back()
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : '提交失败', icon: 'none' })
  } finally {
    deciding.value = false
  }
}
</script>
<style scoped>
.page {
  min-height: 100vh;
  padding: 28rpx;
  background: var(--med-page);
}
.card {
  padding: 28rpx;
}
.title {
  display: block;
  font-size: 34rpx;
  font-weight: 750;
}
.muted,
.body {
  display: block;
  margin-top: 10rpx;
  color: var(--med-muted);
  font-size: 22rpx;
  line-height: 1.55;
}
.section {
  display: block;
  margin-top: 28rpx;
  color: var(--med-navy);
  font-size: 27rpx;
  font-weight: 700;
}
.row,
.review {
  display: flex;
  margin-top: 12rpx;
  padding: 14rpx;
  flex-direction: column;
  gap: 4rpx;
  background: #f8fbfc;
  border-radius: 12rpx;
  font-size: 23rpx;
}
.digest {
  display: block;
  margin-top: 12rpx;
  padding: 12rpx;
  color: var(--med-brand);
  background: var(--med-brand-soft);
  word-break: break-all;
  font-size: 20rpx;
}
textarea {
  width: auto;
  min-height: 220rpx;
  margin-top: 22rpx;
  padding: 18rpx;
  border: 1rpx solid var(--med-border);
  border-radius: 14rpx;
}
.actions {
  display: flex;
  gap: 16rpx;
  margin-top: 20rpx;
}
.actions button {
  flex: 1;
}
.primary,
.secondary {
  color: #fff;
  background: var(--med-brand);
}
.secondary {
  color: var(--med-brand);
  background: var(--med-brand-soft);
}
</style>
