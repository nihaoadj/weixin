<template>
  <view class="safe-page node-page">
    <view
      v-if="loading"
      class="state-copy"
    >
      正在加载知识节点…
    </view>
    <view
      v-else-if="error"
      class="state-copy error-state"
      role="alert"
    >
      <text>{{ error }}</text>
      <button
        class="text-action"
        @click="returnToTree"
      >
        返回知识树
      </button>
    </view>
    <template v-else-if="point">
      <view class="node-hero">
        <image
          class="hero-art"
          src="/static/knowledge-node-hero.svg"
          mode="scaleToFill"
          alt=""
          aria-hidden="true"
        />
        <view class="hero-inner">
          <view class="hero-module">
            <image
              src="/static/knowledge-node-layers.svg"
              class="hero-module-icon"
              alt=""
              aria-hidden="true"
            />
            <text>{{ point.systemLabel }}</text>
          </view>
          <view class="head-line">
            <text class="node-title">{{ point.title }}</text>
            <text :class="['status-pill', `status-${point.status}`]"
              >{{ statusMark(point.status) }} {{ statusLabel(point.status) }}</text
            >
          </view>
          <text class="hero-summary">{{ point.description || point.objective }}</text>
          <text
            v-if="preparationNote"
            class="preparation-note"
            >{{ preparationNote }}</text
          >
        </view>
      </view>

      <view class="node-sheet">
        <view class="content-section goals-section">
          <view class="section-heading">
            <image
              src="/static/knowledge-node-target.svg"
              class="section-icon"
              alt=""
              aria-hidden="true"
            />
            <text class="section-title">学习目标</text>
          </view>
          <view class="goals-panel">
            <view class="goals-copy">
              <view
                v-for="(objective, index) in study?.material?.learningObjectives || point.learningObjectives"
                :key="objective"
                class="goal-row"
              >
                <text class="goal-number">{{ index + 1 }}</text>
                <text class="description">{{ objective }}</text>
              </view>
            </view>
            <view
              class="goals-decoration"
              aria-hidden="true"
            >
              <image
                src="/static/knowledge-node-goals.svg"
                alt=""
              />
            </view>
          </view>
        </view>

        <view
          v-if="study?.material"
          class="content-section"
        >
          <view class="section-heading">
            <image
              src="/static/knowledge-node-book.svg"
              class="section-icon"
              alt=""
              aria-hidden="true"
            />
            <text class="section-title">研讨准备</text>
          </view>
          <view class="preparation-grid">
            <view
              v-for="section in study.material.background"
              :key="section.title"
              class="preparation-card"
            >
              <view class="prep-icon-shell">
                <image
                  src="/static/knowledge-node-eye.svg"
                  class="prep-icon"
                  alt=""
                  aria-hidden="true"
                />
              </view>
              <text class="item-title">{{ section.title }}</text>
              <text class="description">{{ section.text }}</text>
            </view>
            <view class="preparation-card">
              <view class="prep-icon-shell">
                <image
                  src="/static/knowledge-node-bulb.svg"
                  class="prep-icon"
                  alt=""
                  aria-hidden="true"
                />
              </view>
              <text class="item-title">{{ study.material.example.title }}</text>
              <text class="description">{{ study.material.example.text }}</text>
            </view>
          </view>
        </view>

        <view class="content-section relationship-section">
          <view class="section-heading">
            <image
              src="/static/knowledge-node-network.svg"
              class="section-icon"
              alt=""
              aria-hidden="true"
            />
            <text class="section-title">学习位置</text>
          </view>
          <view class="relationship-grid">
            <view class="relationship-card">
              <view class="relationship-card-head">
                <image
                  src="/static/knowledge-node-cap.svg"
                  class="relationship-card-icon"
                  alt=""
                  aria-hidden="true"
                />
                <text class="item-title">前置知识</text>
              </view>
              <text
                v-if="!prerequisites.length"
                class="relationship-empty"
                >可以从这里直接开始。</text
              >
              <button
                v-for="item in prerequisites"
                :key="item.code"
                class="relation-row"
                @click="openPoint(item.code)"
              >
                <image
                  src="/static/knowledge-node-document.svg"
                  class="relation-item-icon"
                  alt=""
                  aria-hidden="true"
                />
                <view class="relation-copy">
                  <text class="relation-title">{{ item.title }}</text>
                  <text class="relation-meta">{{ item.systemLabel }} · {{ statusLabel(item.status) }}</text>
                </view>
                <text
                  class="relation-chevron"
                  aria-hidden="true"
                  >›</text
                >
              </button>
            </view>
            <view class="relationship-card">
              <view class="relationship-card-head">
                <image
                  src="/static/knowledge-node-network.svg"
                  class="relationship-card-icon"
                  alt=""
                  aria-hidden="true"
                />
                <text class="item-title">关联知识</text>
              </view>
              <text
                v-if="!related.length"
                class="relationship-empty"
                >暂无额外关联节点。</text
              >
              <button
                v-for="item in related"
                :key="item.code"
                class="relation-row"
                @click="openPoint(item.code)"
              >
                <image
                  src="/static/knowledge-node-document.svg"
                  class="relation-item-icon"
                  alt=""
                  aria-hidden="true"
                />
                <view class="relation-copy">
                  <text class="relation-title">{{ item.title }}</text>
                  <text class="relation-meta">{{ item.systemLabel }} · {{ statusLabel(item.status) }}</text>
                </view>
                <text
                  class="relation-chevron"
                  aria-hidden="true"
                  >›</text
                >
              </button>
            </view>
          </view>
          <view
            v-if="point.dependencies.length"
            class="dependency-notes"
          >
            <text class="subsection-title">前置关系依据</text>
            <view
              v-for="dependency in point.dependencies"
              :key="dependency.id"
              class="dependency-detail"
            >
              <text class="dependency-path"
                >{{ byCode.get(dependency.prerequisiteCode)?.title || dependency.prerequisiteCode }} →
                {{ point.title }}</text
              >
              <text>{{ dependency.rationale }}</text>
              <text class="dependency-limitation">边界：{{ dependency.limitation }}</text>
            </view>
          </view>
        </view>

        <view class="content-section source-section">
          <view class="section-heading source-heading">
            <image
              src="/static/knowledge-node-book.svg"
              class="section-icon"
              alt=""
              aria-hidden="true"
            />
            <text class="section-title">权威学习资料推荐</text>
          </view>
          <text
            v-if="!point.sources.length"
            class="relationship-empty"
            >当前目录暂无可查看的学习资料。</text
          >
          <view
            v-for="source in point.sources"
            :key="source.sourceKey"
            class="source-card"
          >
            <view class="source-identity"
              ><text>{{ sourceIdentityLabel(source.publisher) }}</text></view
            >
            <view class="source-content">
              <text class="source-publisher">{{ source.publisher }} · {{ sourceTypeLabel(source.sourceType) }}</text>
              <text class="source-title">{{ source.title }}</text>
              <text class="source-description">{{ sourceCardSummary(point) }}</text>
              <view class="source-link-row">
                <image
                  src="/static/knowledge-node-link.svg"
                  class="source-link-icon"
                  alt=""
                  aria-hidden="true"
                />
                <text class="source-url">{{ source.url }}</text>
              </view>
            </view>
            <button
              class="source-open"
              :disabled="!source.url"
              @click="openSource(source.sourceKey)"
            >
              <text>查看原文</text>
              <image
                src="/static/knowledge-node-external.svg"
                class="source-open-icon"
                alt=""
                aria-hidden="true"
              />
            </button>
          </view>
        </view>

        <view class="content-section advice-section">
          <view class="section-heading">
            <image
              src="/static/knowledge-node-idea.svg"
              class="section-icon"
              alt=""
              aria-hidden="true"
            />
            <text class="section-title">学习建议</text>
          </view>
          <view class="advice-grid">
            <view class="advice-step">
              <view class="advice-icon-shell">
                <image
                  src="/static/knowledge-node-book.svg"
                  class="advice-icon"
                  alt=""
                  aria-hidden="true"
                />
              </view>
              <view class="advice-content">
                <text class="advice-number">1.</text>
                <text class="advice-title">先阅读资料</text>
                <text class="advice-copy">建立基础认知</text>
              </view>
            </view>
            <text
              class="advice-arrow"
              aria-hidden="true"
              >→</text
            >
            <view class="advice-step">
              <view class="advice-icon-shell">
                <image
                  src="/static/knowledge-node-eye.svg"
                  class="advice-icon"
                  alt=""
                  aria-hidden="true"
                />
              </view>
              <view class="advice-content">
                <text class="advice-number">2.</text>
                <text class="advice-title">再观察线索</text>
                <text class="advice-copy">结合题目情境</text>
              </view>
            </view>
            <text
              class="advice-arrow"
              aria-hidden="true"
              >→</text
            >
            <view class="advice-step">
              <view class="advice-icon-shell">
                <image
                  src="/static/knowledge-node-group.svg"
                  class="advice-icon"
                  alt=""
                  aria-hidden="true"
                />
              </view>
              <view class="advice-content">
                <text class="advice-number">3.</text>
                <text class="advice-title">最后开始研讨</text>
                <text class="advice-copy">形成完整判断</text>
              </view>
            </view>
          </view>
        </view>
      </view>

      <view class="node-actions">
        <view class="actions-inner">
          <text
            v-if="actionError"
            class="action-error"
            role="alert"
            >{{ actionError }}</text
          >
          <view class="action-buttons">
            <button
              class="primary-action"
              :disabled="discussionBusy"
              @click="startDiscussion"
            >
              <image
                src="/static/knowledge-node-chat.svg"
                class="action-icon"
                alt=""
                aria-hidden="true"
              />
              <text>{{
                discussionBusy
                  ? '正在进入…'
                  : study?.activeSession
                    ? study.activeSession.phase === 'completed'
                      ? study.learningRouteId
                        ? '查看学习计划'
                        : '查看已完成研讨'
                      : '继续研讨'
                    : '开始研讨'
              }}</text>
            </button>
            <button
              v-if="study?.learningRouteId"
              class="review-action"
              @click="openLearningRoute"
            >
              <image
                src="/static/knowledge-node-document.svg"
                class="action-icon"
                alt=""
                aria-hidden="true"
              />
              <view class="action-copy"
                ><text>查看研讨学习计划</text><text class="action-caption">资料、病例与最终测试</text></view
              >
            </button>
          </view>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onBackPress, onLoad, onShow } from '@dcloudio/uni-app'
import {
  getKnowledgeMap,
  getStudyPath,
  startStudyPath,
  type KnowledgeMapPoint,
  type StudyPathState,
} from '@/features/learning/public'
import { createPblMessageId } from '@/features/pbl/public'
import { requireRole } from '@/features/identity/public'
import { goDetail, goReplace, handleBackPress, ROUTES } from '@/platform/navigation'

const requestedCode = ref('')
const points = ref<KnowledgeMapPoint[]>([])
const point = ref<KnowledgeMapPoint>()
const study = ref<StudyPathState>()
const loading = ref(false)
const error = ref('')
const discussionBusy = ref(false)
const actionError = ref('')
const byCode = computed(() => new Map(points.value.map((item) => [item.code, item])))
const prerequisites = computed(() =>
  (point.value?.dependencies || [])
    .map((dependency) => dependency.prerequisiteCode)
    .map((code) => byCode.value.get(code))
    .filter((item): item is KnowledgeMapPoint => Boolean(item)),
)
const related = computed(() =>
  points.value.filter((candidate) =>
    candidate.dependencies.some((dependency) => dependency.prerequisiteCode === point.value?.code),
  ),
)
const preparationNote = computed(() => {
  const incomplete = prerequisites.value.filter((item) => item.status !== 'stable')
  if (!incomplete.length) return ''
  return `建议先回顾：${incomplete.map((item) => item.title).join('、')}。你仍可直接学习当前节点。`
})

function statusLabel(status: KnowledgeMapPoint['status']) {
  return {
    not_started: '未开始',
    weak: '薄弱',
    learning: '学习中',
    due: '待复习',
    stable: '相对稳定',
  }[status]
}

function statusMark(status: KnowledgeMapPoint['status']) {
  return {
    not_started: '○',
    weak: '!',
    learning: '·',
    due: '◷',
    stable: '✓',
  }[status]
}

function sourceCardSummary(current: KnowledgeMapPoint) {
  const firstClause = (value?: string) =>
    (value || '')
      .trim()
      .split(/[，,；;。！？!?]/, 1)[0]
      ?.trim() || ''
  const descriptionClause = firstClause(current.description)
  const objectiveClause = firstClause(current.objective)
  const summary =
    descriptionClause && descriptionClause.length <= 22 ? descriptionClause : objectiveClause || descriptionClause
  return summary ? `${summary}。` : ''
}

function sourceTypeLabel(value: string) {
  return (
    {
      peer_reviewed: '同行评议文献',
      academic_reference: '学术参考资料',
      clinical_reference: '临床参考资料',
      professional_manual: '专业手册',
    }[value] || value
  )
}

function sourceIdentityLabel(publisher: string) {
  if (publisher === 'NCBI/PMC') return 'PMC'
  if (publisher === 'NCBI Bookshelf') return 'NIH'
  if (publisher === 'Merck Manual Professional Edition') return 'MSD'
  if (publisher === 'National Cancer Institute') return 'NCI'
  if (publisher === 'U.S. National Library of Medicine') return 'NLM'
  return publisher
}

async function load() {
  if (!requestedCode.value || loading.value) return
  loading.value = true
  error.value = ''
  actionError.value = ''
  try {
    points.value = await getKnowledgeMap()
    point.value = byCode.value.get(requestedCode.value)
    if (!point.value) error.value = '未找到这个知识节点，可能已不在当前目录中。'
    else study.value = await getStudyPath(point.value.code)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '知识节点加载失败，请稍后重试。'
  } finally {
    loading.value = false
  }
}

function openPoint(code: string) {
  if (code === requestedCode.value) return
  goReplace(ROUTES.studentKnowledgeNode, { topicCode: code })
}

function returnToTree() {
  goReplace(ROUTES.studentCases, { view: 'knowledge' })
}

async function startDiscussion() {
  if (!point.value || loading.value || discussionBusy.value) return
  if (study.value?.learningRouteId) {
    goDetail(ROUTES.studentLearningPlanDetail, { routeId: study.value.learningRouteId })
    return
  }
  discussionBusy.value = true
  actionError.value = ''
  try {
    const state = study.value?.activeSession
      ? study.value
      : await startStudyPath({
          pointCode: point.value.code,
          clientId: createPblMessageId(),
          interactionStyle: 'guided',
        })
    study.value = state
    goDetail(ROUTES.studentPbl, { topicCode: point.value.code, dialogueId: state.activeSession?.sessionId || '' })
  } catch (reason) {
    actionError.value = reason instanceof Error ? reason.message : '无法开始研讨，请稍后重试。'
  } finally {
    discussionBusy.value = false
  }
}

function openSource(sourceKey: string) {
  if (!point.value || !sourceKey) return
  goDetail(ROUTES.studentSourceView, { pointCode: point.value.code, sourceKey })
}

function openLearningRoute() {
  if (study.value?.learningRouteId) goDetail(ROUTES.studentLearningPlanDetail, { routeId: study.value.learningRouteId })
}

onLoad((options) => {
  requestedCode.value = typeof options?.topicCode === 'string' ? options.topicCode : ''
  if (!requestedCode.value) error.value = '缺少知识节点参数。'
})
onShow(() => {
  if (requireRole('student')) void load()
})
onBackPress(({ from }) => handleBackPress(from, ROUTES.studentCases, { view: 'knowledge' }))
</script>

<style scoped>
.node-page {
  --node-ink: #0b1e65;
  --node-text: #3f609b;
  --node-muted: #6580ae;
  --node-blue: #087fd7;
  --node-line: #deedfb;
  --node-wash: #f5faff;
  min-height: 100vh;
  background: var(--node-wash);
  color: var(--node-text);
}
.state-copy {
  display: flex;
  min-height: 72vh;
  padding: 32rpx;
  align-items: center;
  justify-content: center;
  color: var(--node-muted);
  font-size: 26rpx;
}
.error-state {
  flex-direction: column;
  gap: 20rpx;
  color: #9b2d49;
  text-align: center;
}
.text-action {
  min-height: 88rpx;
  margin: 0;
  padding: 0 28rpx;
  color: var(--node-blue);
  background: #fff;
  border: 1rpx solid var(--node-line);
  border-radius: 20rpx;
  font-size: 25rpx;
}
.node-hero {
  position: relative;
  min-height: 258rpx;
  overflow: hidden;
  background: linear-gradient(115deg, #fbfeff 0%, #f1faff 65%, #e7f5ff 88%, #fff 100%);
}
.hero-art {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 100%;
  height: 100%;
  opacity: 1;
}
.hero-inner {
  position: relative;
  z-index: 1;
  display: flex;
  max-width: 920px;
  min-height: 258rpx;
  box-sizing: border-box;
  margin: 0 auto;
  padding: 22rpx 32rpx 42rpx;
  flex-direction: column;
  justify-content: center;
  gap: 11rpx;
}
.hero-module {
  display: flex;
  align-items: center;
  gap: 7rpx;
  color: var(--node-blue);
  font-size: 22rpx;
  font-weight: 750;
  line-height: 1.4;
}
.hero-module-icon {
  width: 22rpx;
  height: 22rpx;
}
.head-line {
  display: flex;
  align-items: center;
  gap: 18rpx;
}
.node-title {
  max-width: 72%;
  color: var(--node-ink);
  font-size: 48rpx;
  font-weight: 800;
  letter-spacing: -1rpx;
  line-height: 1.26;
  overflow-wrap: anywhere;
}
.status-pill {
  display: inline-flex;
  min-height: 40rpx;
  box-sizing: border-box;
  padding: 4rpx 15rpx;
  align-items: center;
  color: #086b80;
  background: #e4f9fb;
  border: 1rpx solid #c3eaf0;
  border-radius: 99rpx;
  font-size: 21rpx;
  white-space: nowrap;
}
.status-pill.status-weak {
  color: #a5294a;
  background: #fff0f4;
  border-color: #f4c8d5;
}
.status-pill.status-due {
  color: #885018;
  background: #fff4e7;
  border-color: #f1d8b6;
}
.status-pill.status-learning {
  color: #075e95;
  background: #e8f4ff;
  border-color: #c9e3f7;
}
.status-pill.status-stable {
  color: #086a5e;
  background: #e5f8f2;
  border-color: #bce9db;
}
.hero-summary {
  display: block;
  max-width: 72%;
  color: #4a659d;
  font-size: 24rpx;
  line-height: 1.55;
}
.preparation-note {
  display: block;
  max-width: 72%;
  color: #795123;
  font-size: 20rpx;
  line-height: 1.4;
}
.node-sheet {
  position: relative;
  z-index: 2;
  min-height: 65vh;
  box-sizing: border-box;
  margin-top: -28rpx;
  padding: 9rpx 30rpx 206rpx;
  background: #fff;
  border-radius: 34rpx 34rpx 0 0;
}
.content-section {
  display: flex;
  max-width: 920px;
  margin: 0 auto;
  padding: 24rpx 2rpx 25rpx;
  flex-direction: column;
  gap: 14rpx;
  border-bottom: 1rpx solid var(--node-line);
}
.section-heading {
  display: flex;
  min-height: 38rpx;
  align-items: center;
  gap: 12rpx;
}
.section-icon {
  width: 42rpx;
  height: 42rpx;
  flex: none;
}
.section-title {
  color: var(--node-ink);
  font-size: 30rpx;
  font-weight: 800;
  line-height: 1.35;
}
.description {
  color: var(--node-text);
  font-size: 23rpx;
  line-height: 1.58;
  overflow-wrap: anywhere;
}
.goals-panel {
  position: relative;
  display: grid;
  min-height: 106rpx;
  box-sizing: border-box;
  padding: 19rpx 20rpx;
  grid-template-columns: minmax(0, 1fr) 116rpx;
  align-items: center;
  gap: 8rpx;
  background: linear-gradient(106deg, #f4faff 0%, #eaf5ff 100%);
  border: 1rpx solid #e7f2fd;
  border-radius: 20rpx;
  overflow: hidden;
}
.goals-copy {
  position: relative;
  z-index: 1;
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 10rpx;
}
.goal-row {
  display: flex;
  align-items: flex-start;
  gap: 13rpx;
}
.goal-number {
  display: inline-flex;
  width: 38rpx;
  height: 38rpx;
  flex: 0 0 38rpx;
  align-items: center;
  justify-content: center;
  color: #0874ca;
  background: linear-gradient(150deg, #e7f6ff, #cce8ff);
  border-radius: 50%;
  font-size: 24rpx;
  font-weight: 800;
}
.goal-row .description {
  flex: 1;
}
.subsection-title {
  color: var(--node-ink);
  font-size: 23rpx;
  font-weight: 700;
  line-height: 1.4;
}
.goals-decoration {
  position: relative;
  height: 100rpx;
}
.goals-decoration image {
  position: absolute;
  right: -10rpx;
  bottom: -12rpx;
  width: 122rpx;
  height: 122rpx;
}
.preparation-grid,
.relationship-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14rpx;
}
.preparation-card,
.relationship-card {
  display: flex;
  min-width: 0;
  box-sizing: border-box;
  padding: 17rpx;
  flex-direction: column;
  gap: 6rpx;
  background: linear-gradient(145deg, #f5fbff, #eaf6ff);
  border: 1rpx solid #eaf4fd;
  border-radius: 18rpx;
}
.preparation-card:nth-child(even) {
  background: linear-gradient(145deg, #f5fdff, #eafaff);
}
.preparation-card {
  display: grid;
  grid-template-columns: 68rpx minmax(0, 1fr);
  grid-template-rows: auto 1fr;
  align-content: start;
  column-gap: 11rpx;
  row-gap: 5rpx;
}
.prep-icon-shell {
  display: flex;
  width: 68rpx;
  height: 68rpx;
  grid-column: 1;
  grid-row: 1 / 3;
  align-items: center;
  justify-content: center;
  background: #e1f6ff;
  border: 2rpx solid #fff;
  border-radius: 50%;
}
.prep-icon {
  width: 50rpx;
  height: 50rpx;
}
.preparation-card .item-title,
.preparation-card .description {
  grid-column: 2;
}
.item-title {
  color: var(--node-ink);
  font-size: 25rpx;
  font-weight: 800;
  line-height: 1.45;
  overflow-wrap: anywhere;
}
.source-note,
.relationship-empty {
  color: var(--node-muted);
  font-size: 21rpx;
  line-height: 1.45;
}
.relationship-card-head {
  display: flex;
  min-height: 50rpx;
  align-items: center;
  gap: 9rpx;
}
.relationship-card-icon {
  width: 50rpx;
  height: 50rpx;
  flex: none;
}
.relation-row {
  display: flex;
  width: 100%;
  min-height: 66rpx;
  box-sizing: border-box;
  margin: 0;
  padding: 7rpx 8rpx;
  align-items: center;
  gap: 7rpx;
  color: var(--node-ink);
  background: rgba(255, 255, 255, 0.86);
  border: 1rpx solid #e3eff9;
  border-radius: 12rpx;
  font-size: 23rpx;
  text-align: left;
}
.relation-row + .relation-row {
  margin-top: 6rpx;
}
.relation-item-icon {
  width: 38rpx;
  height: 38rpx;
  flex: none;
}
.relation-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 2rpx;
}
.relation-title {
  font-size: 23rpx;
  font-weight: 700;
  overflow-wrap: anywhere;
}
.relation-meta {
  color: var(--node-muted);
  font-size: 19rpx;
  line-height: 1.35;
  overflow-wrap: anywhere;
}
.relation-chevron {
  color: var(--node-ink);
  font-size: 30rpx;
}
.dependency-notes {
  display: flex;
  margin-top: 3rpx;
  flex-direction: column;
  gap: 4rpx;
}
.dependency-detail {
  display: flex;
  padding: 11rpx 0;
  flex-direction: column;
  gap: 4rpx;
  color: var(--node-text);
  border-bottom: 1rpx solid #e7f1f9;
  font-size: 21rpx;
  line-height: 1.48;
}
.dependency-path {
  color: var(--node-blue);
  font-weight: 700;
}
.dependency-limitation {
  color: #755e47;
}
.source-section {
  gap: 10rpx;
}
.source-heading {
  align-items: center;
}
.source-card {
  display: flex;
  min-width: 0;
  padding: 14rpx;
  align-items: flex-start;
  gap: 11rpx;
  background: #fff;
  border: 1rpx solid #d8eafe;
  border-radius: 18rpx;
  box-shadow: 0 6rpx 16rpx rgba(22, 97, 181, 0.075);
}
.source-identity {
  display: flex;
  width: 88rpx;
  min-height: 78rpx;
  padding: 4rpx;
  flex: 0 0 88rpx;
  align-items: center;
  justify-content: center;
  color: #0868bd;
  border-right: 1rpx solid #e2effb;
  font-size: 16rpx;
  font-weight: 800;
  line-height: 1.25;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.source-content {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 2rpx;
}
.source-publisher {
  width: fit-content;
  max-width: 100%;
  padding: 1rpx 7rpx;
  color: #176e8a;
  background: #e5f8fb;
  border-radius: 7rpx;
  font-size: 18rpx;
  overflow-wrap: anywhere;
}
.source-title {
  display: block;
  min-width: 0;
  overflow: hidden;
  color: var(--node-ink);
  font-size: 22rpx;
  font-weight: 700;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.source-description {
  display: block;
  min-width: 0;
  overflow: hidden;
  color: var(--node-text);
  font-size: 19rpx;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.source-link-row {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 5rpx;
}
.source-link-icon {
  width: 20rpx;
  height: 20rpx;
  flex: none;
}
.source-url {
  display: block;
  max-width: 100%;
  overflow: hidden;
  color: #075cb2;
  font-size: 19rpx;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.source-open {
  display: flex;
  min-width: 130rpx;
  min-height: 58rpx;
  box-sizing: border-box;
  margin: 0;
  padding: 5rpx 10rpx;
  flex: 0 0 130rpx;
  align-items: center;
  justify-content: center;
  gap: 4rpx;
  color: #075ab1;
  background: linear-gradient(180deg, #fff, #f0f8ff);
  border: 1rpx solid #bfddfb;
  border-radius: 99rpx;
  font-size: 19rpx;
  line-height: 1.3;
  white-space: nowrap;
}
.source-open-icon {
  width: 20rpx;
  height: 20rpx;
  flex: none;
}
.source-open[disabled] {
  opacity: 0.5;
}
.advice-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 24rpx minmax(0, 1fr) 24rpx minmax(0, 1fr);
  align-items: center;
  gap: 2rpx;
}
.advice-step {
  display: flex;
  min-width: 0;
  min-height: 100rpx;
  box-sizing: border-box;
  padding: 10rpx 6rpx;
  flex-direction: row;
  justify-content: flex-start;
  align-items: center;
  gap: 5rpx;
  background: linear-gradient(150deg, #f6fbff, #eaf6ff);
  border-radius: 16rpx;
  text-align: left;
}
.advice-icon-shell {
  display: flex;
  width: 44rpx;
  height: 44rpx;
  flex: none;
  align-items: center;
  justify-content: center;
  background: #fff;
  border-radius: 12rpx;
  box-shadow: 0 3rpx 9rpx rgba(20, 108, 197, 0.09);
}
.advice-icon {
  width: 36rpx;
  height: 36rpx;
  flex: none;
}
.advice-content {
  display: grid;
  min-width: 0;
  min-height: 56rpx;
  grid-template-columns: 18rpx minmax(0, 1fr);
  grid-template-rows: 28rpx 26rpx;
  align-items: start;
  column-gap: 2rpx;
}
.advice-number {
  grid-column: 1;
  grid-row: 1;
  align-self: end;
  color: var(--node-blue);
  font-size: 19rpx;
  font-weight: 800;
  line-height: 1.1;
}
.advice-title {
  display: block;
  grid-column: 2;
  grid-row: 1;
  align-self: end;
  color: var(--node-ink);
  font-size: 18rpx;
  font-weight: 700;
  line-height: 1.25;
  white-space: nowrap;
}
.advice-copy {
  display: block;
  grid-column: 2;
  grid-row: 2;
  align-self: start;
  color: var(--node-muted);
  font-size: 17rpx;
  line-height: 1.35;
  white-space: nowrap;
}
.advice-arrow {
  display: flex;
  width: 100%;
  min-height: 42rpx;
  align-items: center;
  justify-content: center;
  color: #0875d2;
  font-size: 38rpx;
  font-weight: 800;
  line-height: 1;
  text-align: center;
}
.practice-section {
  gap: 16rpx;
}
.study-section {
  display: flex;
  flex-direction: column;
  gap: 7rpx;
}
.practice-option {
  width: 100%;
  min-height: 88rpx;
  margin: 0;
  padding: 12rpx 16rpx;
  color: var(--node-text);
  background: #f7fbff;
  border: 1rpx solid var(--node-line);
  border-radius: 14rpx;
  font-size: 25rpx;
  line-height: 1.5;
  text-align: left;
}
.practice-feedback {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
  padding-top: 16rpx;
  color: var(--node-text);
  border-top: 1rpx solid var(--node-line);
  font-size: 24rpx;
  line-height: 1.55;
}
.secondary-action {
  min-height: 88rpx;
  margin: 0;
  color: #075cae;
  background: #eef8ff;
  border: 1rpx solid #c8e2f9;
  border-radius: 18rpx;
  font-size: 25rpx;
}
.node-actions {
  position: fixed;
  z-index: 20;
  right: 0;
  bottom: 0;
  left: 0;
  padding: 13rpx 30rpx calc(13rpx + env(safe-area-inset-bottom));
  background: #fff;
  border-top: 1rpx solid #d6eafb;
  box-shadow: 0 -8rpx 24rpx rgba(14, 83, 160, 0.055);
}
.actions-inner {
  display: flex;
  max-width: 920px;
  margin: 0 auto;
  flex-direction: column;
  gap: 5rpx;
}
.action-buttons {
  display: flex;
  gap: 16rpx;
}
.primary-action,
.review-action {
  display: flex;
  min-width: 0;
  min-height: 92rpx;
  box-sizing: border-box;
  margin: 0;
  padding: 5rpx 12rpx;
  flex: 1;
  align-items: center;
  justify-content: center;
  border-radius: 99rpx;
  gap: 10rpx;
  font-size: 26rpx;
  font-weight: 800;
  line-height: 1.3;
  text-align: center;
}
.action-icon {
  width: 36rpx;
  height: 36rpx;
  flex: none;
}
.action-copy {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0;
}
.action-caption {
  font-size: 17rpx;
  font-weight: 500;
  line-height: 1.25;
}
.primary-action {
  color: #fff;
  background: linear-gradient(105deg, #48b9e9, #0875de);
  box-shadow: 0 7rpx 15rpx rgba(16, 111, 208, 0.16);
}
.review-action {
  color: #075aba;
  background: linear-gradient(180deg, #fff, #f4fbff);
  border: 2rpx solid #529cf4;
}
.primary-action[disabled] {
  color: #7890b2;
  background: #eff4f8;
  border-color: #d8e2ec;
  box-shadow: none;
}
.review-action[disabled] {
  color: #6590c9;
  background: linear-gradient(180deg, #fff, #f6fbff);
  border-color: #b8d9fc;
  opacity: 1;
}
.review-action[disabled] .action-icon {
  opacity: 0.65;
}
.action-error {
  color: #a5294a;
  font-size: 23rpx;
  line-height: 1.4;
  text-align: center;
}
@media screen and (max-width: 350px) {
  .preparation-grid,
  .relationship-grid {
    grid-template-columns: 1fr;
  }
  .source-identity {
    display: none;
  }
  .source-open {
    min-width: 74px;
    flex-basis: 74px;
    font-size: 12px;
  }
  .relation-meta,
  .source-url,
  .advice-copy,
  .action-caption {
    font-size: 12px;
  }
  .advice-title,
  .primary-action,
  .review-action {
    font-size: 12px;
  }
}
@media screen and (min-width: 600px) {
  .hero-inner {
    padding: 24px 32px 40px;
  }
  .node-title {
    font-size: 34px;
  }
  .hero-summary {
    font-size: 17px;
  }
  .node-sheet {
    padding: 12px 32px 180px;
  }
  .content-section {
    padding: 24px 0;
  }
  .section-title {
    font-size: 21px;
  }
  .description {
    font-size: 16px;
  }
  .item-title {
    font-size: 17px;
  }
  .source-title {
    font-size: 16px;
  }
  .source-note,
  .source-description {
    font-size: 14px;
  }
  .node-actions {
    padding: 12px 32px calc(16px + env(safe-area-inset-bottom));
  }
  .primary-action,
  .review-action {
    min-height: 52px;
    font-size: 17px;
  }
}
</style>
