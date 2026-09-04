<template>
  <view class="safe-page pbl">
    <view class="header"
      ><text class="eyebrow">PATHOLOGY · PBL</text><text class="title">我的 PBL 课堂</text
      ><text class="muted">从问题出发，用证据解释病理变化。</text>
      <button
        class="header-action"
        @click="goPrimary(ROUTES.studentLearning)"
      >
        查看课后任务
      </button></view
    >
    <MedState
      v-if="error"
      variant="error"
      icon="retry"
      title="课堂加载失败"
      :description="error"
      action-label="重新加载"
      @action="load"
    />
    <MedState
      v-else-if="loading"
      variant="loading"
      icon="retry"
      title="正在加载课堂"
      description="正在同步课堂阶段、讨论记录和学习线索。"
    />
    <view
      v-else-if="!sessions.length"
      class="panel"
      ><text>还没有加入 PBL 课堂</text><text class="muted">教师创建课堂后，会在这里显示。</text></view
    >
    <template v-else-if="session">
      <picker
        :range="sessionOptions"
        :value="sessionIndex"
        aria-label="选择 PBL 课堂"
        :disabled="sending"
        @change="selectSession"
        ><view class="selector">{{ sessionOptions[sessionIndex] }} ▾</view></picker
      >
      <view
        class="panel classroom-context"
        aria-label="当前课堂上下文"
        ><text class="section-title">{{ session.caseContext?.title || topicTitle(session.topicCode) }}</text
        ><text v-if="session.caseContext?.opening">{{ session.caseContext.opening.patient_intro }}</text>
        ><view class="classroom-meta">
          <text class="phase-chip">阶段：{{ phaseLabels[session.phase] }}</text>
          <text
            class="status-chip"
            :class="{ closed: session.status !== 'active' }"
          >{{ session.status === 'active' ? '课堂进行中' : '已结束，可回看' }}</text>
        </view
        >
        <text
          v-if="!session.caseId"
          class="muted"
          >历史课堂保留原有讨论上下文。</text
        >
        <view
          v-if="session.goalPointCodes.length"
          class="goal-list"
        >
          <text
            v-for="code in session.goalPointCodes"
            :key="code"
            class="goal-chip"
            >{{ pointTitle(code) }}</text
          >
        </view>
        >
      </view>
      <view
        class="conversation"
        aria-live="polite"
        aria-label="课堂讨论记录"
      >
        <view
          v-if="!messages.length"
          class="muted"
          >写下你不理解的问题，并说明目前的想法。助手会继续追问你的判断依据。</view
        >
        <view
          v-for="item in messages"
          :key="item.id"
          class="message"
          :class="{ own: item.role === 'student' }"
          ><text class="message-label">{{ item.role === 'student' ? '我的讨论' : '教学助手' }}</text
          ><text>{{ item.content }}</text></view
        >
      </view>
      <view
        v-if="diagnostic"
        class="panel diagnosis"
        ><text class="section-title">{{
          diagnostic.diagnosticStatus === 'ready' ? '待教师确认的学习线索' : '继续梳理思路'
        }}</text>
        <text v-if="diagnostic.followUpQuestion">追问：{{ diagnostic.followUpQuestion }}</text>
        <text v-if="diagnostic.diagnosticStatus === 'unavailable'">本次没有形成有效诊断，请重试或请教师帮助。</text>
        <view
          v-for="gap in diagnostic.knowledgeGaps"
          :key="gap.id"
          ><text>{{ pointTitle(gap.point_code) }}：{{ gap.summary }}</text
          ><text class="muted">依据：{{ gap.evidence_summary }}</text></view
        >
        <view
          v-for="issue in diagnostic.reasoningIssues"
          :key="issue.id"
          ><text>{{ issue.summary }}</text
          ><text class="muted">下一步：{{ issue.improvement }}</text></view
        >
        <text class="muted">{{ diagnostic.safetyNotice }}</text>
      </view>
      <view
        v-if="session.status === 'active'"
        class="panel composer"
      >
        <textarea
          v-model="draft"
          :disabled="sending"
          aria-label="输入你的病理学问题"
          :maxlength="2000"
          placeholder="我的疑问是……我目前的判断依据是……"
        /><button
          class="primary"
          :disabled="sending || !draft.trim()"
          @click="send"
        >
          {{ sending ? '正在分析，请稍候…' : retry ? '重试提交讨论' : '提交讨论' }}</button
        ><text class="muted">只填写合成教学内容，请勿提供身份或患者信息。</text></view
      >
      <view
        v-else
        class="notice"
        >课堂已结束，讨论记录可回看，课后任务仍可继续完成。</view
      >
    </template>
    <StudentPrimaryNav active="pbl" />
  </view>
</template>
<script setup lang="ts">
import { onShow } from '@dcloudio/uni-app'
import { computed, ref } from 'vue'
import MedState from '@/components/ui/MedState.vue'
import StudentPrimaryNav from '@/components/ui/StudentPrimaryNav.vue'
import {
  getActivePblSessions,
  getPblParticipation,
  sendPblMessage,
  createPblMessageId,
  type PblDiagnostic,
  type PblSession,
  type PblMessage,
} from '@/features/pbl/public'
import { getKnowledgeCatalog, type KnowledgePoint } from '@/features/learning/public'
import { goPrimary, ROUTES } from '@/platform/navigation'
const loading = ref(true),
  sending = ref(false),
  error = ref(''),
  sessions = ref<PblSession[]>([]),
  sessionIndex = ref(0),
  messages = ref<PblMessage[]>([]),
  diagnostic = ref<PblDiagnostic>(),
  draft = ref(''),
  points = ref<KnowledgePoint[]>([])
const retry = ref<{ id: string; content: string; sessionId: string }>()
const session = computed(() => sessions.value[sessionIndex.value])
const phaseLabels = { problem_framing: '明确问题', hypothesis: '提出假设', evidence: '讨论证据', synthesis: '总结解释' }
const topicTitle = (code: string) => points.value.find((p) => p.systemCode === code)?.systemLabel ?? code
const pointTitle = (code: string) => points.value.find((p) => p.code === code)?.title ?? code
const sessionOptions = computed(() =>
  sessions.value.map((s) => `${topicTitle(s.topicCode)} · ${s.status === 'active' ? '进行中' : '已结束'}`),
)
async function participation() {
  if (!session.value) return
  const result = await getPblParticipation(session.value.id)
  messages.value = result.messages
  diagnostic.value = result.diagnostic
}
async function load() {
  loading.value = true
  error.value = ''
  try {
    ;[sessions.value, points.value] = await Promise.all([getActivePblSessions(), getKnowledgeCatalog()])
    if (sessionIndex.value >= sessions.value.length) sessionIndex.value = 0
    await participation()
  } catch {
    error.value = '课堂加载失败，请检查网络后重新加载。'
  } finally {
    loading.value = false
  }
}
async function selectSession(event: { detail: { value: string } }) {
  sessionIndex.value = Number(event.detail.value)
  messages.value = []
  diagnostic.value = undefined
  draft.value = ''
  retry.value = undefined
  try {
    await participation()
  } catch {
    error.value = '讨论记录加载失败，请重试。'
  }
}
async function send() {
  if (!session.value || sending.value || !draft.value.trim()) return
  sending.value = true
  error.value = ''
  const content = draft.value.trim()
  if (retry.value?.content !== content || retry.value.sessionId !== session.value.id)
    retry.value = { id: createPblMessageId(), content, sessionId: session.value.id }
  try {
    const result = await sendPblMessage(session.value.id, content, retry.value.id)
    messages.value = result.messages
    diagnostic.value = result.diagnostic
    draft.value = ''
    retry.value = undefined
  } catch {
    error.value = '提交未确认，内容已保留。点击重试将使用同一消息标识。'
  } finally {
    sending.value = false
  }
}
onShow(load)
</script>
<style scoped>
.pbl {
  max-width: 1080px;
  margin: auto;
  padding: 24rpx 24rpx 180rpx;
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}
.header,
.panel {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}
.header {
  padding: 28rpx 8rpx 12rpx;
}
.eyebrow {
  font-size: 22rpx;
  letter-spacing: 3rpx;
  color: var(--med-primary);
}
.title {
  font-size: 44rpx;
  font-weight: 800;
}
.section-title {
  font-size: 32rpx;
  font-weight: 700;
}
.header-action {
  width: fit-content;
  min-height: 80rpx;
  margin: 4rpx 0 0;
  padding: 0 24rpx;
  color: var(--med-clinical);
  background: var(--med-wash);
  font-size: 25rpx;
}
.muted {
  font-size: 26rpx;
  color: var(--med-muted);
  line-height: 1.6;
}
.panel,
.selector,
.notice {
  padding: 24rpx;
  background: var(--med-surface);
  border-radius: var(--med-radius-md);
}
.classroom-context {
  gap: 18rpx;
  border-top: 6rpx solid var(--med-clinical);
}
.classroom-meta,
.goal-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
}
.phase-chip,
.status-chip,
.goal-chip {
  padding: 8rpx 14rpx;
  color: var(--med-clinical);
  background: var(--med-wash);
  border-radius: 99rpx;
  font-size: 23rpx;
  line-height: 1.4;
}
.status-chip {
  color: var(--med-primary);
  background: var(--med-primary-soft, #e7f3ee);
}
.status-chip.closed {
  color: var(--med-muted);
  background: var(--med-bg, #f6f8f6);
}
.goal-chip {
  color: var(--med-text-secondary);
  background: var(--med-bg, #f6f8f6);
}
.conversation {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}
.message {
  max-width: 90%;
  padding: 24rpx;
  background: var(--med-surface);
  border-radius: 20rpx;
  display: flex;
  flex-direction: column;
  gap: 12rpx;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.message.own {
  align-self: flex-end;
  background: var(--med-primary-soft, #e7f3ee);
}
.message-label {
  font-size: 23rpx;
  color: var(--med-muted);
}
textarea {
  width: 100%;
  min-height: 150rpx;
  box-sizing: border-box;
}
.primary {
  background: var(--med-primary);
  color: white;
}
button {
  min-height: 44px;
  font-size: 28rpx;
}
.notice {
  border: 1px solid var(--med-border, #ddd);
}
@media (min-width: 768px) {
  .pbl {
    padding: 32px;
  }
  .title {
    font-size: 34px;
  }
  .message {
    max-width: 75%;
  }
  .header-action {
    min-height: 44px;
    padding: 0 16px;
    font-size: 14px;
  }
}
</style>
