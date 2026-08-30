<template>
  <view class="safe-page page">
    <view
      v-if="item"
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
import { onLoad } from '@dcloudio/uni-app'
import { requireRole } from '@/services/auth'
import { backOrHome } from '@/services/navigation'
import { getReviewView, submitMedicalReview } from '@/services/teacherInsights'
import type { MedicalReviewView } from '@/services/caseRepositoryAsync'

const item = ref<MedicalReviewView>()
const comment = ref('')
const deciding = ref(false)
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

onLoad((query) => {
  if (!requireRole('teacher')) return
  id = String(query?.id || '')
  void (async () => {
    try {
      item.value = await getReviewView(id)
    } catch (error) {
      uni.showToast({ title: error instanceof Error ? error.message : '加载失败', icon: 'none' })
    }
  })()
})
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
    backOrHome('teacher')
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
  background: #f4f8fa;
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
  color: #718096;
  font-size: 22rpx;
  line-height: 1.55;
}
.section {
  display: block;
  margin-top: 28rpx;
  color: #0b2239;
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
  color: #087f8c;
  background: #e8f7f5;
  word-break: break-all;
  font-size: 20rpx;
}
textarea {
  width: auto;
  min-height: 220rpx;
  margin-top: 22rpx;
  padding: 18rpx;
  border: 1rpx solid #dbe7eb;
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
  background: #087f8c;
}
.secondary {
  color: #087f8c;
  background: #e6f7f5;
}
</style>
