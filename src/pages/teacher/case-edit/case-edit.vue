<template>
  <view class="safe-page case-authoring-page page-enter">
    <view class="page-container case-authoring-shell">
      <view class="authoring-header">
        <view class="title-block">
          <text class="eyebrow-label">病例五步编排器</text>
          <text
            role="heading"
            aria-level="1"
            class="page-title"
            >{{ headerTitle }}</text
          >
          <text class="page-description">核对病例内容并保存，保存后即可选入课堂。</text>
          <button
            role="button"
            tabindex="0"
            class="secondary-button pressable authoring-return"
            hover-class="is-pressed"
            :hover-start-time="0"
            :hover-stay-time="80"
            @click="back"
            @keydown="activateButtonOnKey"
          >
            返回内容列表
          </button>
        </view>
      </view>

      <view
        v-if="hydrating"
        class="load-state"
        aria-busy="true"
        aria-label="正在加载病例"
      >
        <text class="section-title">正在载入病例</text>
        <text class="helper-text">正在读取病例内容。</text>
      </view>

      <view
        v-else-if="loadError"
        class="load-state load-error"
        role="alert"
      >
        <text class="section-title">病例未能载入</text>
        <text class="helper-text">{{ loadError }}</text>
        <button
          role="button"
          tabindex="0"
          class="secondary-button pressable authoring-action"
          hover-class="is-pressed"
          :hover-start-time="0"
          :hover-stay-time="80"
          @click="loadExisting"
          @keydown="activateButtonOnKey"
        >
          重新载入
        </button>
        <button
          role="button"
          tabindex="0"
          class="secondary-button pressable authoring-action"
          hover-class="is-pressed"
          :hover-start-time="0"
          :hover-stay-time="80"
          @click="back"
          @keydown="activateButtonOnKey"
        >
          返回内容列表
        </button>
      </view>

      <CaseSetupForm
        v-else-if="!draft"
        v-model:topic="topic"
        v-model:level="level"
        v-model:objectives="objectives"
        :busy="loading"
        :error="generationError"
        @generate="generate"
      />

      <template v-else>
        <view class="knowledge-binding">
          <text class="field-label">对应知识点</text>
          <text class="helper-text">用于课堂学习目标；请选择与病例对应的知识点。</text>
          <text
            v-if="catalogLoading"
            class="helper-text"
            >正在读取知识点目录…</text
          >
          <template v-else-if="catalogError || !knowledgeCatalog.length">
            <text
              class="binding-error"
              role="alert"
              >{{ catalogError || '知识点目录为空，暂时无法保存病例。' }}</text
            >
            <button
              class="secondary-button binding-retry"
              :disabled="saving"
              @click="loadKnowledgeCatalog"
            >
              重新读取知识点
            </button>
          </template>
          <picker
            v-else
            :range="knowledgeOptions"
            :value="knowledgeIndex"
            :disabled="editingBlocked"
            @change="selectKnowledgePoint"
          >
            <view class="knowledge-picker">{{ knowledgeSelectionLabel }}<text aria-hidden="true">⌄</text></view>
          </picker>
        </view>
        <view
          class="step-overview"
          aria-label="病例编辑进度"
        >
          <view class="step-title-row">
            <view>
              <text class="step-count">第 {{ step }} 步，共 {{ authoringSteps.length }} 步</text>
              <text
                role="heading"
                aria-level="2"
                tabindex="-1"
                class="section-title"
                >{{ activeStep.label }}</text
              >
            </view>
            <text class="step-description">{{ activeStep.description }}</text>
          </view>
          <view
            class="step-track"
            aria-hidden="true"
          >
            <view
              v-for="item in authoringSteps"
              :key="item.id"
              :class="['step-marker', { active: item.id === step, complete: item.id < step }]"
            >
              <text class="step-marker-number">{{ item.id }}</text>
              <text class="step-marker-label">{{ item.shortLabel }}</text>
            </view>
          </view>
        </view>

        <view
          :key="step"
          class="authoring-sheet step-enter"
        >
          <template v-if="step === 1">
            <view class="section-intro">
              <text
                role="heading"
                aria-level="2"
                class="section-title"
                >病例概况</text
              >
              <text class="helper-text">学生进入病例时会先看到这里的公开信息。</text>
            </view>
            <view class="field-layout">
              <view class="field-block">
                <text
                  id="case-title-label"
                  class="field-label"
                  >病例标题</text
                >
                <input
                  v-model="draft.title"
                  class="field-control"
                  name="case-title"
                  data-native-name="case-title"
                  aria-labelledby="case-title-label"
                  :disabled="editingBlocked"
                  placeholder="例如：细胞损伤与适应"
                />
              </view>
              <view class="field-block">
                <text
                  id="case-specialty-label"
                  class="field-label"
                  >所属专科</text
                >
                <input
                  v-model="draft.specialty"
                  class="field-control"
                  name="case-specialty"
                  data-native-name="case-specialty"
                  aria-labelledby="case-specialty-label"
                  :disabled="editingBlocked"
                  placeholder="例如：病理学"
                />
              </view>
              <view class="field-block">
                <text
                  id="case-duration-label"
                  class="field-label"
                  >预计完成时间（分钟）</text
                >
                <input
                  v-model.number="draft.estimatedMinutes"
                  class="field-control"
                  name="case-duration"
                  data-native-name="case-duration"
                  aria-labelledby="case-duration-label"
                  :disabled="editingBlocked"
                  type="number"
                  placeholder="例如：20"
                />
              </view>
            </view>
            <view class="field-block">
              <text
                id="case-description-label"
                class="field-label"
                >教学简介</text
              >
              <textarea
                v-model="draft.description"
                class="field-control compact-text-control"
                name="case-description"
                data-native-name="case-description"
                aria-labelledby="case-description-label"
                :disabled="editingBlocked"
                placeholder="说明本病例的教学重点与适用场景"
              />
            </view>
            <view class="content-divider"></view>
            <view class="visibility-heading">
              <text class="visibility-label public-label">学生可见</text>
              <text class="helper-text">这些文字会成为学生的起始病情信息。</text>
            </view>
            <view class="field-block">
              <text
                id="case-intro-label"
                class="field-label"
                >患者简介</text
              >
              <textarea
                v-model="draft.caseDefinition.opening.patientIntro"
                class="field-control text-control"
                name="case-patient-intro"
                data-native-name="case-patient-intro"
                aria-labelledby="case-intro-label"
                :disabled="editingBlocked"
                placeholder="描述就诊背景和基础情况"
              />
            </view>
            <view class="field-block">
              <text
                id="case-chief-complaint-label"
                class="field-label"
                >主诉</text
              >
              <textarea
                v-model="draft.caseDefinition.opening.chiefComplaint"
                class="field-control text-control"
                name="case-chief-complaint"
                data-native-name="case-chief-complaint"
                aria-labelledby="case-chief-complaint-label"
                :disabled="editingBlocked"
                placeholder="学生需要首先处理的临床问题"
              />
            </view>
          </template>

          <template v-else-if="step === 2">
            <view class="section-intro">
              <text
                role="heading"
                aria-level="2"
                class="section-title"
                >阶段与事实</text
              >
              <text class="helper-text">阶段说明引导学生推进；隐藏事实只在相应触发词出现后提供。</text>
            </view>
            <view class="visibility-heading">
              <text class="visibility-label teacher-label">仅教师可见</text>
              <text class="helper-text">学生不会直接看到阶段指令、隐藏事实和触发条件。</text>
            </view>
            <view class="stage-list">
              <view
                v-for="stage in stageItems"
                :key="stage.id"
                class="stage-row"
              >
                <text
                  :id="`${stage.id}-label`"
                  class="stage-label"
                  >{{ stage.label }}</text
                >
                <textarea
                  v-model="draft.caseDefinition.stageInstructions[stage.id]"
                  class="field-control stage-control"
                  :name="`${stage.id}-instruction`"
                  :data-native-name="`${stage.id}-instruction`"
                  :aria-labelledby="`${stage.id}-label`"
                  :disabled="editingBlocked"
                  :placeholder="`${stage.label}阶段的教学引导`"
                />
              </view>
            </view>
            <view class="content-divider"></view>
            <view class="subsection-heading">
              <view>
                <text class="subsection-title">隐藏事实</text>
                <text class="helper-text">每条事实应有明确触发词，避免无条件泄露答案。</text>
              </view>
              <button
                v-if="!editingBlocked"
                role="button"
                tabindex="0"
                class="inline-action pressable"
                hover-class="is-pressed"
                :hover-start-time="0"
                :hover-stay-time="80"
                @click="addFact"
                @keydown="activateButtonOnKey"
              >
                新增事实
              </button>
            </view>
            <view class="fact-list">
              <view
                v-for="(fact, index) in draft.caseDefinition.facts"
                :key="fact.id"
                class="fact-entry"
              >
                <text class="entry-index">事实 {{ index + 1 }}</text>
                <view class="field-layout fact-fields">
                  <view class="field-block">
                    <text
                      :id="`fact-${fact.id}-label`"
                      class="field-label"
                      >事实标签</text
                    >
                    <input
                      v-model="fact.label"
                      class="field-control"
                      :name="`fact-${fact.id}-label-input`"
                      :data-native-name="`fact-${fact.id}-label-input`"
                      :aria-labelledby="`fact-${fact.id}-label`"
                      :disabled="editingBlocked"
                      placeholder="例如：发热病程"
                    />
                  </view>
                  <view class="field-block">
                    <text
                      :id="`fact-${fact.id}-trigger`"
                      class="field-label"
                      >触发词</text
                    >
                    <input
                      :value="fact.triggers.join('、')"
                      class="field-control"
                      :name="`fact-${fact.id}-triggers`"
                      :data-native-name="`fact-${fact.id}-triggers`"
                      :aria-labelledby="`fact-${fact.id}-trigger`"
                      :disabled="editingBlocked"
                      placeholder="用顿号或逗号分隔"
                      @input="updateTriggers(fact, $event)"
                    />
                  </view>
                </view>
                <view class="field-block">
                  <text
                    :id="`fact-${fact.id}-value`"
                    class="field-label"
                    >事实内容</text
                  >
                  <textarea
                    v-model="fact.value"
                    class="field-control compact-text-control"
                    :name="`fact-${fact.id}-value-input`"
                    :data-native-name="`fact-${fact.id}-value-input`"
                    :aria-labelledby="`fact-${fact.id}-value`"
                    :disabled="editingBlocked"
                    placeholder="记录需要按触发条件揭示的临床事实"
                  />
                </view>
              </view>
            </view>
          </template>

          <template v-else-if="step === 3">
            <view class="section-intro">
              <text
                role="heading"
                aria-level="2"
                class="section-title"
                >参考推理</text
              >
              <text class="helper-text">用于教师校验，不会展示给学生。</text>
            </view>
            <view class="visibility-heading">
              <text class="visibility-label teacher-label">仅教师可见</text>
            </view>
            <view class="field-block">
              <text
                id="case-representation-label"
                class="field-label"
                >问题表征参考</text
              >
              <textarea
                v-model="referenceText"
                class="field-control text-control"
                name="case-reference-representation"
                data-native-name="case-reference-representation"
                aria-labelledby="case-representation-label"
                :disabled="editingBlocked"
                placeholder="总结支持判断的关键临床表征"
              />
            </view>
            <view class="content-divider"></view>
            <text class="subsection-title">鉴别诊断</text>
            <view
              v-for="(item, index) in differentials"
              :key="`differential-${index}`"
              class="reference-entry"
            >
              <text class="entry-index">鉴别 {{ index + 1 }}</text>
              <view class="field-layout">
                <view class="field-block"
                  ><text
                    :id="`differential-${index}-name`"
                    class="field-label"
                    >诊断名称</text
                  ><input
                    v-model="item.diagnosis"
                    class="field-control"
                    :name="`differential-${index}-name-input`"
                    :data-native-name="`differential-${index}-name-input`"
                    :aria-labelledby="`differential-${index}-name`"
                    :disabled="editingBlocked"
                    placeholder="鉴别诊断"
                /></view>
                <view class="field-block"
                  ><text
                    :id="`differential-${index}-support`"
                    class="field-label"
                    >支持事实 ID</text
                  ><input
                    :value="item.supportingFactIds?.join('、')"
                    class="field-control"
                    :name="`differential-${index}-support-input`"
                    :data-native-name="`differential-${index}-support-input`"
                    :aria-labelledby="`differential-${index}-support`"
                    :disabled="editingBlocked"
                    placeholder="用顿号或逗号分隔"
                    @input="updateIds(item, 'supportingFactIds', $event)"
                /></view>
              </view>
              <view class="field-block"
                ><text
                  :id="`differential-${index}-opposing`"
                  class="field-label"
                  >反对事实 ID</text
                ><input
                  :value="item.opposingFactIds?.join('、')"
                  class="field-control"
                  :name="`differential-${index}-opposing-input`"
                  :data-native-name="`differential-${index}-opposing-input`"
                  :aria-labelledby="`differential-${index}-opposing`"
                  :disabled="editingBlocked"
                  placeholder="用顿号或逗号分隔"
                  @input="updateIds(item, 'opposingFactIds', $event)"
              /></view>
            </view>
            <view class="content-divider"></view>
            <text class="subsection-title">检查与处置</text>
            <view
              v-for="(item, index) in referenceTests"
              :key="`test-${index}`"
              class="reference-entry"
            >
              <text class="entry-index">检查 {{ index + 1 }}</text>
              <view class="field-block"
                ><text
                  :id="`test-${index}-name`"
                  class="field-label"
                  >检查名称</text
                ><input
                  v-model="item.name"
                  class="field-control"
                  :name="`test-${index}-name-input`"
                  :data-native-name="`test-${index}-name-input`"
                  :aria-labelledby="`test-${index}-name`"
                  :disabled="editingBlocked"
                  placeholder="检查名称"
              /></view>
              <view class="field-block"
                ><text
                  :id="`test-${index}-purpose`"
                  class="field-label"
                  >检查目的</text
                ><textarea
                  v-model="item.purpose"
                  class="field-control compact-text-control"
                  :name="`test-${index}-purpose-input`"
                  :data-native-name="`test-${index}-purpose-input`"
                  :aria-labelledby="`test-${index}-purpose`"
                  :disabled="editingBlocked"
                  placeholder="说明该检查如何支持决策"
                />
              </view>
            </view>
            <view
              v-for="(item, index) in referenceManagement"
              :key="`management-${index}`"
              class="reference-entry"
            >
              <text class="entry-index">处置 {{ index + 1 }}</text>
              <view class="field-block"
                ><text
                  :id="`management-${index}-action`"
                  class="field-label"
                  >处置行动</text
                ><input
                  v-model="item.action"
                  class="field-control"
                  :name="`management-${index}-action-input`"
                  :data-native-name="`management-${index}-action-input`"
                  :aria-labelledby="`management-${index}-action`"
                  :disabled="editingBlocked"
                  placeholder="处置行动"
              /></view>
              <view class="field-block"
                ><text
                  :id="`management-${index}-rationale`"
                  class="field-label"
                  >处置依据</text
                ><textarea
                  v-model="item.rationale"
                  class="field-control compact-text-control"
                  :name="`management-${index}-rationale-input`"
                  :data-native-name="`management-${index}-rationale-input`"
                  :aria-labelledby="`management-${index}-rationale`"
                  :disabled="editingBlocked"
                  placeholder="说明为何采用该处置"
                />
              </view>
            </view>
          </template>

          <template v-else-if="step === 4">
            <view class="section-intro">
              <text
                role="heading"
                aria-level="2"
                class="section-title"
                >评价量表</text
              >
              <text class="helper-text">六维权重由病例结构固定；请核对每项评价语句与关键词。</text>
            </view>
            <view class="visibility-heading">
              <text class="visibility-label teacher-label">仅教师可见</text>
              <text class="helper-text">学生不会看到评分关键词或评价规则。</text>
            </view>
            <view
              v-for="dimension in draft.rubric.dimensions"
              :key="dimension.id"
              class="rubric-entry"
            >
              <view class="rubric-heading"
                ><text class="subsection-title">{{ dimension.label }}</text
                ><text class="rubric-weight">权重 {{ dimension.weight }}%</text></view
              >
              <view
                v-for="criterion in dimension.criteria"
                :key="criterion.id"
                class="field-block criterion-row"
              >
                <text
                  :id="`criterion-${criterion.id}`"
                  class="field-label"
                  >评价标准</text
                >
                <input
                  v-model="criterion.label"
                  class="field-control"
                  :name="`criterion-${criterion.id}-input`"
                  :data-native-name="`criterion-${criterion.id}-input`"
                  :aria-labelledby="`criterion-${criterion.id}`"
                  :disabled="editingBlocked"
                  placeholder="评价标准"
                />
              </view>
            </view>
          </template>

          <template v-else>
            <view class="section-intro">
              <text
                role="heading"
                aria-level="2"
                class="section-title"
                >预览核对</text
              >
              <text class="helper-text">最后确认学生会看到的开场，以及仅供教师核对的内容边界。</text>
            </view>
            <view class="preview-section">
              <view class="visibility-heading"><text class="visibility-label public-label">学生可见预览</text></view>
              <text class="preview-title">{{ draft.title }}</text>
              <text class="preview-copy">{{ draft.caseDefinition.opening.patientIntro }}</text>
              <text class="preview-copy">主诉：{{ draft.caseDefinition.opening.chiefComplaint }}</text>
            </view>
            <view class="content-divider"></view>
            <view class="preview-section">
              <view class="visibility-heading"><text class="visibility-label teacher-label">教师核对</text></view>
              <text class="helper-text">学生视图不显示隐藏事实、参考推理和评分关键词。</text>
              <view class="preview-facts">
                <text
                  v-for="fact in draft.caseDefinition.facts"
                  :key="`preview-${fact.id}`"
                  class="preview-fact"
                  >{{ fact.label }}：{{ fact.value }}</text
                >
              </view>
            </view>
            <view class="safety-note"
              ><text>{{ draft.safetyNotice }}</text></view
            >
          </template>
        </view>

        <view
          class="authoring-actions"
          aria-label="病例编排操作"
        >
          <button
            v-if="step > 1"
            role="button"
            tabindex="0"
            class="secondary-button pressable authoring-action"
            hover-class="is-pressed"
            :hover-start-time="0"
            :hover-stay-time="80"
            @click="previous"
            @keydown="activateButtonOnKey"
          >
            上一步
          </button>
          <button
            v-if="step < 5"
            role="button"
            tabindex="0"
            class="primary-button pressable authoring-action"
            hover-class="is-pressed"
            :hover-start-time="0"
            :hover-stay-time="80"
            @click="next"
            @keydown="activateButtonOnKey"
          >
            下一步
          </button>
          <button
            v-if="step === 5 && !editingBlocked"
            role="button"
            :tabindex="canSave ? 0 : -1"
            class="primary-button pressable authoring-action"
            hover-class="is-pressed"
            :hover-start-time="0"
            :hover-stay-time="80"
            :loading="saving"
            :disabled="!canSave"
            :aria-disabled="!canSave"
            @click="save"
            @keydown="activateButtonOnKey"
          >
            {{ saving ? '正在保存' : '保存病例' }}
          </button>
        </view>
      </template>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
import { onBackPress, onLoad, onShow } from '@dcloudio/uni-app'
import CaseSetupForm from '@/features/content/presentation/CaseSetupForm.vue'
import { activateButtonOnKey } from '@/components/ui/keyboard'
import { getSession, requireRole } from '@/features/identity/public'
import { backOrRoute, handleBackPress, ROUTES } from '@/platform/navigation'
import { teacherContentReturnParams } from '@/platform/navigation/teacher'
let contentReturn = teacherContentReturnParams({}, 'cases')
import {
  generateCaseDraftAsync,
  getCaseAuthoringAsync,
  getGuidedCasesAsync,
  saveGuidedCaseAsync,
} from '@/features/content/public'
import { getKnowledgeCatalog } from '@/features/learning/public'
import type { KnowledgePoint } from '@/types/knowledge'
import type { CaseDraftGenerateResult, CaseFact, CaseStageId } from '@/types/case'

const authoringSteps = [
  { id: 1, label: '病例概况', shortLabel: '概况', description: '设定学生进入病例时会看到的公开开场。' },
  { id: 2, label: '阶段与事实', shortLabel: '事实', description: '组织教学阶段，并为触发式信息补足边界。' },
  { id: 3, label: '参考推理', shortLabel: '推理', description: '核对教师使用的参考路径。' },
  { id: 4, label: '评价量表', shortLabel: '量表', description: '检查固定权重下的评价语句与关键词。' },
  { id: 5, label: '预览核对', shortLabel: '核对', description: '区分学生可见内容与教师参考内容。' },
] as const
const stageItems: Array<{ id: CaseStageId; label: string }> = [
  { id: 'history', label: '病史采集' },
  { id: 'problem_representation', label: '问题表征' },
  { id: 'differential', label: '鉴别诊断' },
  { id: 'tests', label: '检查决策' },
  { id: 'management', label: '初步处置' },
]

const step = ref(1)
const topic = ref('细胞损伤与适应')
const level = ref('临床医学本科生')
const objectives = ref('训练病史采集\n训练鉴别诊断\n训练检查选择')
const draft = ref<CaseDraftGenerateResult>()
const currentId = ref<string>()
const currentSlug = ref<string>()
const sourceId = ref<string>()
const loading = ref(false)
const hydrating = ref(false)
const saving = ref(false)
const generationError = ref('')
const loadError = ref('')
const referenceText = ref('')
const knowledgePointCodes = ref<string[]>([])
const knowledgeCatalog = ref<KnowledgePoint[]>([])
const catalogLoading = ref(false)
const catalogError = ref('')
const savedSnapshot = ref(caseSnapshot())
function back() {
  const actorAtRequest = teacherOpenid
  if (saving.value || loading.value || hydrating.value) {
    uni.showToast({ title: '正在处理病例，请稍候', icon: 'none' })
    return
  }
  if (hasUnsavedChanges.value) {
    uni.showModal({
      title: '离开病例编排？',
      content: '当前修改尚未保存，离开后不会保留。',
      confirmText: '离开',
      success: ({ confirm }) => {
        if (confirm && actorAtRequest === teacherOpenid && currentActor()) leaveEditor()
      },
    })
    return
  }
  leaveEditor()
}

function leaveEditor() {
  if (disposed) return
  backOrRoute(ROUTES.teacherContent, contentReturn)
}

function caseSnapshot() {
  return JSON.stringify({
    topic: topic.value,
    level: level.value,
    objectives: objectives.value,
    draft: draft.value ?? null,
    referenceText: referenceText.value,
    knowledgePointCodes: knowledgePointCodes.value,
  })
}

const hasUnsavedChanges = computed(() => caseSnapshot() !== savedSnapshot.value)

function markSaved() {
  savedSnapshot.value = caseSnapshot()
}

const reference = computed(() => draft.value?.caseDefinition.referenceReasoning)
type ReferenceItem = NonNullable<
  CaseDraftGenerateResult['caseDefinition']['referenceReasoning']['differentials']
>[number]
const differentials = computed(() => reference.value?.differentials || [])
const referenceTests = computed(() => reference.value?.tests || [])
const referenceManagement = computed(() => reference.value?.management || [])
const activeStep = computed(() => authoringSteps[step.value - 1])
const headerTitle = computed(() => (draft.value ? '编排教学病例' : '创建教学病例'))
let teacherOpenid = ''
let disposed = false
onBeforeUnmount(() => {
  disposed = true
})
function currentActor() {
  const session = getSession()
  return !disposed && session?.role === 'teacher' && session.openid === teacherOpenid
}
function verifyActor() {
  if (currentActor()) return true
  draft.value = undefined
  referenceText.value = ''
  knowledgePointCodes.value = []
  knowledgeCatalog.value = []
  currentId.value = undefined
  loadError.value = '教师账号已变更，请返回内容列表。'
  return false
}
const editingBlocked = computed(() => saving.value || hydrating.value)
const knowledgeOptions = computed(() => [
  '请选择知识点',
  ...knowledgeCatalog.value.map((point) => `${point.systemLabel} · ${point.title}`),
])
const knowledgeIndex = computed(() =>
  knowledgePointCodes.value.length === 1
    ? Math.max(0, knowledgeCatalog.value.findIndex((point) => point.code === knowledgePointCodes.value[0]) + 1)
    : 0,
)
const knowledgeSelectionLabel = computed(() =>
  knowledgePointCodes.value.length
    ? knowledgePointCodes.value
        .map((code) => knowledgeCatalog.value.find((point) => point.code === code)?.title || code)
        .join('、')
    : '请选择知识点',
)
const canSave = computed(
  () =>
    !saving.value &&
    !catalogLoading.value &&
    !catalogError.value &&
    knowledgeCatalog.value.length > 0 &&
    knowledgePointCodes.value.length > 0 &&
    knowledgePointCodes.value.every((code) => knowledgeCatalog.value.some((point) => point.code === code)),
)
function selectKnowledgePoint(event: { detail: { value: string | number } }) {
  if (!verifyActor() || editingBlocked.value) return
  const selected = knowledgeCatalog.value[Number(event.detail.value) - 1]
  knowledgePointCodes.value = selected ? [selected.code] : []
}
async function loadKnowledgeCatalog() {
  if (catalogLoading.value || !verifyActor()) return
  catalogLoading.value = true
  catalogError.value = ''
  try {
    const catalog = await getKnowledgeCatalog()
    if (!verifyActor()) return
    knowledgeCatalog.value = catalog
  } catch (reason) {
    if (verifyActor()) {
      knowledgeCatalog.value = []
      catalogError.value = reason instanceof Error ? reason.message : '知识点目录读取失败，请重试。'
    }
  } finally {
    catalogLoading.value = false
  }
}

async function generate() {
  if (loading.value || !verifyActor()) return
  generationError.value = ''
  if (!topic.value.trim() || !level.value.trim() || !objectives.value.trim()) {
    generationError.value = '请填写病例主题、学习层级和至少一个教学目标。'
    return
  }
  loading.value = true
  try {
    const generated = await generateCaseDraftAsync({
      topic: topic.value.trim(),
      learnerLevel: level.value.trim(),
      learningObjectives: objectives.value
        .split('\n')
        .map((item) => item.trim())
        .filter(Boolean),
    })
    if (!verifyActor()) return
    draft.value = generated
    referenceText.value = String(generated.caseDefinition.referenceReasoning.problemRepresentation || '')
    step.value = 1
  } catch (error) {
    if (verifyActor()) generationError.value = error instanceof Error ? error.message : '请检查网络后重试。'
  } finally {
    loading.value = false
  }
}

function previous() {
  if (step.value <= 1) return
  step.value -= 1
  void alignStepContext()
}

function next() {
  if (!draft.value || step.value >= authoringSteps.length) return
  if (editingBlocked.value || !verifyActor() || !validateStep()) return
  if (step.value === 3) draft.value.caseDefinition.referenceReasoning.problemRepresentation = referenceText.value
  step.value += 1
  void alignStepContext()
}

async function alignStepContext() {
  await nextTick()
  uni.pageScrollTo({ selector: '.step-overview', duration: 0 })
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

function inputValue(event: unknown): string {
  const payload = event as { detail?: { value?: unknown }; target?: { value?: unknown } }
  return String(payload?.detail?.value ?? payload?.target?.value ?? '')
}

function updateTriggers(fact: CaseFact, event: unknown) {
  fact.triggers = inputValue(event)
    .split(/[、,，]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function updateIds(item: ReferenceItem, key: 'supportingFactIds' | 'opposingFactIds', event: unknown) {
  item[key] = inputValue(event)
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
  if (step.value === 3 && (!referenceText.value.trim() || !differentials.value.length)) {
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

function validateAll() {
  if (knowledgePointCodes.value.length > 3) {
    uni.showToast({ title: '请选择最多3个知识点', icon: 'none' })
    return false
  }
  const originalStep = step.value
  for (let candidate = 1; candidate <= 4; candidate += 1) {
    step.value = candidate
    if (!validateStep()) {
      void alignStepContext()
      return false
    }
  }
  step.value = originalStep
  return true
}

async function save() {
  if (!draft.value || saving.value || !verifyActor() || !validateAll()) return
  if (catalogLoading.value || catalogError.value || !knowledgeCatalog.value.length) {
    uni.showToast({ title: '请先读取知识点目录', icon: 'none' })
    return
  }
  if (
    !knowledgePointCodes.value.length ||
    knowledgePointCodes.value.some((code) => !knowledgeCatalog.value.some((point) => point.code === code))
  ) {
    uni.showToast({ title: '请选择有效的知识点', icon: 'none' })
    return
  }
  saving.value = true
  try {
    if (step.value === 3) draft.value.caseDefinition.referenceReasoning.problemRepresentation = referenceText.value
    const result = await saveGuidedCaseAsync(draft.value, currentId.value, {
      slug: currentSlug.value,
      knowledgePointCodes: [...knowledgePointCodes.value],
    })
    if (!verifyActor()) return
    currentId.value = result.id
    currentSlug.value = result.slug || currentSlug.value
    markSaved()
    uni.showToast({ title: '病例已保存', icon: 'success' })
  } catch (error) {
    if (verifyActor()) uni.showToast({ title: error instanceof Error ? error.message : '保存失败', icon: 'none' })
  } finally {
    saving.value = false
  }
}

async function loadExisting() {
  if (!sourceId.value || hydrating.value || !verifyActor()) return
  hydrating.value = true
  loadError.value = ''
  try {
    const item = (await getGuidedCasesAsync()).find((problem) => problem.id === sourceId.value)
    if (!verifyActor()) return
    if (!item?.allowedActions?.includes('edit')) throw new Error('当前账号无权编辑此病例。')
    const loaded = await getCaseAuthoringAsync(sourceId.value)
    if (!verifyActor()) return
    currentId.value = sourceId.value
    currentSlug.value = item.slug
    knowledgePointCodes.value = [...new Set(item.knowledgePointCodes || [])]
    draft.value = loaded
    if (!draft.value) throw new Error('病例不存在或当前账号无权查看。')
    referenceText.value = String(draft.value.caseDefinition.referenceReasoning.problemRepresentation || '')
    step.value = 1
    markSaved()
  } catch (error) {
    if (verifyActor()) loadError.value = error instanceof Error ? error.message : '请稍后重试。'
  } finally {
    hydrating.value = false
  }
}

onLoad((query) => {
  contentReturn = teacherContentReturnParams(query, 'cases')
  if (!requireRole('teacher')) return
  teacherOpenid = getSession()?.openid || ''
  if (!verifyActor()) return
  void loadKnowledgeCatalog()
  const id = query?.id ? String(query.id) : ''
  if (!id) return
  sourceId.value = id
  void loadExisting()
})
onShow(() => {
  if (teacherOpenid) verifyActor()
})
onBackPress(({ from }) => {
  if (from === 'navigateBack') return false
  if (saving.value || loading.value || hydrating.value) {
    uni.showToast({ title: '正在处理病例，请稍候', icon: 'none' })
    return true
  }
  if (hasUnsavedChanges.value) {
    back()
    return true
  }
  return handleBackPress(from, ROUTES.teacherContent, contentReturn)
})
</script>

<style scoped>
.knowledge-binding {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
  padding: 20rpx;
  border: 1rpx solid var(--med-border);
  border-radius: 12rpx;
}
.knowledge-picker {
  display: flex;
  min-height: 76rpx;
  padding: 12rpx 18rpx;
  align-items: center;
  justify-content: space-between;
  gap: 12rpx;
  background: var(--med-wash);
  border-radius: 10rpx;
  font-size: 25rpx;
  line-height: 1.5;
}
.binding-error {
  color: var(--med-alert);
  font-size: 24rpx;
  line-height: 1.5;
}
.binding-retry {
  min-height: 72rpx;
  margin: 0;
  font-size: 24rpx;
}

.case-authoring-page {
  min-height: 100vh;
  padding: var(--med-space-3);
}
.case-authoring-shell {
  display: flex;
  flex-direction: column;
  gap: var(--med-space-4);
}
.authoring-header {
  display: flex;
  padding-bottom: var(--med-space-3);
  flex-direction: column;
  gap: var(--med-space-3);
  border-bottom: 1rpx solid var(--med-border);
}
.title-block,
.workflow-status,
.section-intro,
.visibility-heading,
.field-block,
.stage-row,
.subsection-heading,
.rubric-heading,
.preview-section {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
}
.page-title {
  color: var(--med-ink);
  font-family: var(--med-font-display);
  font-size: 40rpx;
  font-weight: 700;
  line-height: 1.25;
}
.page-description,
.helper-text,
.step-description {
  color: var(--med-muted);
  font-size: 24rpx;
  line-height: 1.6;
}
.authoring-return {
  width: fit-content;
  min-height: 64rpx;
  margin: 6rpx 0 0;
  padding: 0 18rpx;
  font-size: 22rpx;
  line-height: 64rpx;
}
.workflow-current {
  color: var(--med-clinical);
  font-size: 24rpx;
  font-weight: 700;
}
.workflow-track {
  display: grid;
  grid-template-columns: auto 1fr auto 1fr auto;
  align-items: center;
  gap: 10rpx;
}
.workflow-node {
  color: var(--med-muted);
  font-size: 24rpx;
  white-space: nowrap;
}
.workflow-node.complete {
  color: var(--med-clinical);
  font-weight: 700;
}
.workflow-line {
  height: 2rpx;
  background: var(--med-border);
}
.load-state {
  display: flex;
  min-height: 300rpx;
  padding: var(--med-space-4) 0;
  flex-direction: column;
  justify-content: center;
  gap: 12rpx;
  border-top: 6rpx solid var(--med-wash);
}
.load-error {
  border-color: var(--med-alert);
}
.step-overview {
  display: flex;
  flex-direction: column;
  gap: var(--med-space-3);
}
.step-title-row {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}
.step-count,
.entry-index,
.rubric-weight {
  display: block;
  color: var(--med-clinical);
  font-family: var(--med-font-utility);
  font-size: 24rpx;
  font-weight: 700;
  letter-spacing: 1rpx;
}
.section-title {
  display: block;
  color: var(--med-ink);
  font-size: 32rpx;
  font-weight: 700;
  line-height: 1.35;
}
.step-track {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  border-top: 2rpx solid var(--med-divider);
}
.step-marker {
  display: flex;
  min-width: 0;
  padding: 12rpx 6rpx 0;
  flex-direction: column;
  gap: 5rpx;
  border-top: 4rpx solid transparent;
  transform: translateY(-3rpx);
}
.step-marker.active {
  border-color: var(--med-clinical);
}
.step-marker.complete .step-marker-number,
.step-marker.active .step-marker-number {
  color: #fff;
  background: var(--med-clinical);
}
.step-marker-number {
  display: flex;
  width: 34rpx;
  height: 34rpx;
  align-items: center;
  justify-content: center;
  color: var(--med-muted);
  background: var(--med-wash);
  border-radius: 50%;
  font-family: var(--med-font-utility);
  font-size: 24rpx;
}
.step-marker-label {
  color: var(--med-muted);
  font-size: 19rpx;
  line-height: 1.25;
  word-break: break-all;
}
.step-marker.active .step-marker-label {
  color: var(--med-ink);
  font-weight: 700;
}
.authoring-sheet {
  display: flex;
  padding: var(--med-space-3);
  flex-direction: column;
  gap: var(--med-space-3);
  background: var(--med-surface);
  border-top: 4rpx solid var(--med-clinical);
}
.review-lock,
.safety-note {
  padding: var(--med-space-2);
  color: var(--med-safety-text);
  background: var(--med-safety-soft);
  border-left: 6rpx solid var(--med-safety);
  font-size: 24rpx;
  line-height: 1.6;
}
.field-layout {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--med-space-3);
}
.field-label,
.subsection-title {
  color: var(--med-ink);
  font-size: 26rpx;
  font-weight: 700;
}
.field-control {
  width: 100%;
  min-height: 84rpx;
  padding: 18rpx 20rpx;
  color: var(--med-text);
  background: var(--med-surface);
  border: 1rpx solid var(--med-border);
  border-radius: var(--med-radius-sm);
  font: inherit;
  line-height: 1.45;
}
.text-control {
  min-height: 180rpx;
}
.compact-text-control,
.stage-control {
  min-height: 126rpx;
}
.content-divider {
  height: 1rpx;
  margin: 4rpx 0;
  background: var(--med-divider);
}
.visibility-heading {
  padding-left: var(--med-space-2);
  border-left: 4rpx solid var(--med-clinical);
}
.visibility-label {
  width: fit-content;
  padding: 5rpx 10rpx;
  font-size: 24rpx;
  font-weight: 700;
  line-height: 1.3;
}
.public-label {
  color: var(--med-clinical);
  background: var(--med-wash);
}
.teacher-label {
  color: var(--med-safety-text);
  background: var(--med-safety-soft);
}
.stage-list,
.fact-list {
  display: flex;
  flex-direction: column;
  gap: var(--med-space-3);
}
.stage-row {
  padding-bottom: var(--med-space-3);
  border-bottom: 1rpx solid var(--med-divider);
}
.stage-label {
  color: var(--med-text-secondary);
  font-size: 25rpx;
  font-weight: 700;
}
.subsection-heading {
  justify-content: space-between;
}
.inline-action {
  min-width: 156rpx;
  min-height: 64rpx;
  margin: 0;
  padding: 0 18rpx;
  color: var(--med-clinical);
  background: var(--med-wash);
  border-radius: var(--med-radius-sm);
  font-size: 24rpx;
  line-height: 64rpx;
}
.fact-entry,
.reference-entry,
.rubric-entry {
  display: flex;
  padding: 0 0 var(--med-space-3);
  flex-direction: column;
  gap: var(--med-space-2);
  border-bottom: 1rpx solid var(--med-divider);
}
.fact-fields {
  gap: var(--med-space-2);
}
.rubric-heading {
  flex-direction: row;
  align-items: baseline;
  justify-content: space-between;
}
.criterion-row {
  padding-top: 4rpx;
}
.preview-section {
  gap: var(--med-space-2);
}
.preview-title {
  color: var(--med-ink);
  font-size: 30rpx;
  font-weight: 700;
  line-height: 1.4;
}
.preview-copy,
.preview-fact {
  color: var(--med-text);
  font-size: 26rpx;
  line-height: 1.65;
}
.preview-facts {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}
.authoring-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--med-space-2);
  padding: var(--med-space-3) 0 calc(var(--med-space-4) + env(safe-area-inset-bottom));
  border-top: 1rpx solid var(--med-border);
}
.primary-button,
.secondary-button {
  min-height: 84rpx;
  margin: 0;
  padding: 0 20rpx;
  border-radius: var(--med-radius-md);
  font-size: 28rpx;
  font-weight: 700;
  line-height: 84rpx;
}
.primary-button {
  color: #fff;
  background: var(--med-clinical);
}
.secondary-button {
  color: var(--med-clinical);
  background: var(--med-wash);
}
.is-pressed {
  opacity: 0.8;
}
@media screen and (min-width: 600px) {
  .case-authoring-page {
    padding: 24px;
  }
  .authoring-header {
    flex-direction: row;
    align-items: end;
    justify-content: space-between;
  }
  .workflow-status {
    min-width: 260px;
  }
  .field-layout {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .authoring-actions {
    display: flex;
    justify-content: flex-end;
  }
  .authoring-action {
    flex: 0 1 220px;
  }
}
@media screen and (min-width: 600px) and (max-width: 899px) {
  .page-title {
    font-size: 24px;
  }
  .page-description,
  .helper-text,
  .step-description,
  .review-lock,
  .safety-note {
    font-size: 14px;
  }
  .workflow-current,
  .field-label,
  .subsection-title,
  .preview-copy,
  .preview-fact {
    font-size: 15px;
  }
  .section-title {
    font-size: 22px;
  }
  .step-marker-label,
  .step-marker-number,
  .step-count,
  .entry-index,
  .rubric-weight,
  .visibility-label {
    font-size: 12px;
  }
  .field-control {
    min-height: 48px;
    padding: 12px;
    font-size: 15px;
  }
  .text-control {
    min-height: 112px;
  }
  .compact-text-control,
  .stage-control {
    min-height: 80px;
  }
  .primary-button,
  .secondary-button {
    min-height: 48px;
    font-size: 15px;
    line-height: 48px;
  }
  .inline-action {
    min-height: 36px;
    font-size: 13px;
    line-height: 36px;
  }
}
@media screen and (min-width: 900px) {
  .case-authoring-page {
    padding: 40px;
  }
  .case-authoring-shell {
    max-width: 860px;
    gap: 32px;
  }
  .authoring-sheet {
    padding: 24px;
    border-top-width: 2px;
  }
  .page-title {
    font-size: 28px;
  }
  .page-description,
  .helper-text,
  .step-description,
  .review-lock,
  .safety-note {
    font-size: 14px;
  }
  .workflow-current,
  .field-label,
  .subsection-title,
  .preview-copy,
  .preview-fact {
    font-size: 15px;
  }
  .section-title {
    font-size: 22px;
  }
  .step-marker-label,
  .step-marker-number,
  .step-count,
  .entry-index,
  .rubric-weight,
  .visibility-label {
    font-size: 12px;
  }
  .field-control {
    min-height: 44px;
    padding: 10px 12px;
  }
  .text-control {
    min-height: 90px;
  }
  .compact-text-control,
  .stage-control {
    min-height: 64px;
  }
  .primary-button,
  .secondary-button {
    min-height: 44px;
    font-size: 15px;
    line-height: 44px;
  }
  .inline-action {
    min-height: 34px;
    font-size: 13px;
    line-height: 34px;
  }
}
</style>
