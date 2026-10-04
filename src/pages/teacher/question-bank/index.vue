<template>
  <view class="safe-page bank-page">
    <view class="page-intro">
      <text class="eyebrow">教师个人资源</text>
      <text class="page-title">个人题库</text>
      <text class="intro-copy"
        >只保存由教师明确复制的去标识化题目。题库副本独立于课堂任务，不提供组卷或面向全班发布。</text
      >
    </view>

    <view class="filters">
      <view class="search-row">
        <input
          v-model="queryDraft"
          class="filter-input search-input"
          maxlength="100"
          placeholder="按题目标题搜索"
          confirm-type="search"
          @confirm="search"
        />
        <button
          class="primary-button search-button"
          :disabled="loading"
          @click="search"
        >
          搜索
        </button>
      </view>
      <input
        v-model="pointDraft"
        class="filter-input"
        maxlength="100"
        placeholder="知识点编码（可选，如 pathology.inflammation）"
        confirm-type="search"
        @confirm="search"
      />
      <picker
        :range="taskTypeOptions"
        range-key="label"
        :value="taskTypeIndex"
        @change="selectTaskType"
      >
        <view class="filter-input picker-input">{{ taskTypeOptions[taskTypeIndex]?.label }}<text>⌄</text></view>
      </picker>
      <text class="filter-note">筛选条件由服务端按当前教师身份执行。</text>
    </view>

    <MedState
      v-if="loading && !items.length"
      variant="loading"
      icon="history"
      title="正在读取个人题库"
      description="只查询当前教师拥有的题目。"
    />
    <MedState
      v-else-if="error && !items.length"
      variant="error"
      icon="retry"
      title="个人题库暂不可用"
      :description="error"
      action-label="重试"
      @action="load(true)"
    />
    <view
      v-else
      class="results"
    >
      <view class="results-heading">
        <text class="section-title">题库题目</text>
        <text class="count">{{ total }} 道</text>
      </view>
      <text
        v-if="!items.length"
        class="empty-copy"
      >
        个人题库还是空的。可在课堂最终测试审阅页，将已保存的单选题复制到这里。
      </text>
      <view
        v-for="item in items"
        :key="item.id"
        class="bank-record"
      >
        <button
          class="record-open"
          :aria-label="`查看题目：${item.title}`"
          @click="openItem(item)"
        >
          <view class="record-copy">
            <view class="record-title-row">
              <text class="record-title">{{ item.title }}</text>
            </view>
            <text class="record-prompt">{{ item.prompt }}</text>
            <text class="record-meta"
              >{{ taskTypeLabel(item.taskType) }} · {{ item.pointCodes.join('、') }} · v{{ item.version }}</text
            >
            <text class="record-meta">更新于 {{ item.updatedAt.slice(0, 10) }}</text>
          </view>
          <text
            class="arrow"
            aria-hidden="true"
            >›</text
          >
        </button>
        <button
          class="record-delete"
          :disabled="Boolean(deletingId)"
          @click="confirmDelete(item)"
        >
          删除
        </button>
      </view>
      <view
        v-if="error && items.length"
        class="inline-error"
        role="alert"
      >
        <text>{{ error }}</text
        ><button @click="load(true)">重试</button>
      </view>
      <button
        v-else-if="items.length < total"
        class="more-button"
        :disabled="loading"
        @click="load(false)"
      >
        {{ loading ? '正在读取…' : '加载更多' }}
      </button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { onBackPress, onLoad, onShow } from '@dcloudio/uni-app'
import MedState from '@/components/ui/MedState.vue'
import {
  deleteTeacherQuestionBankItem,
  listTeacherQuestionBank,
  type TeacherQuestionBankItem,
  type TeacherQuestionBankTaskType,
} from '@/features/content/public'
import { getSession, requireRole } from '@/features/identity/public'
import { goDetail, handleBackPress, ROUTES } from '@/platform/navigation'
import { teacherContentReturnParams } from '@/platform/navigation/teacher'

const taskTypeOptions: Array<{ value: '' | TeacherQuestionBankTaskType; label: string }> = [
  { value: '', label: '全部题型' },
  { value: 'retest', label: '目标验证再测' },
  { value: 'knowledge_review', label: '知识点巩固' },
  { value: 'discussion', label: '结构化讨论' },
  { value: 'micro_drill', label: '推理微训练' },
]
const taskType = ref<'' | TeacherQuestionBankTaskType>('')
const queryDraft = ref('')
const pointDraft = ref('')
const query = ref('')
const pointCode = ref('')
const items = ref<TeacherQuestionBankItem[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const loaded = ref(false)
const deletedIds = new Set<number>()
let requestToken = 0
let teacherOpenid = ''
let disposed = false
const deletingId = ref<number>()
onBeforeUnmount(() => {
  disposed = true
  requestToken += 1
})
function currentActor() {
  return !disposed && getSession()?.role === 'teacher' && getSession()?.openid === teacherOpenid
}
function verifyActor() {
  if (currentActor()) return true
  requestToken += 1
  items.value = []
  total.value = 0
  loaded.value = false
  loading.value = false
  deletingId.value = undefined
  error.value = '教师账号已变更，请返回内容页。'
  return false
}
const taskTypeIndex = computed(() =>
  Math.max(
    0,
    taskTypeOptions.findIndex((item) => item.value === taskType.value),
  ),
)

function taskTypeLabel(value: TeacherQuestionBankTaskType) {
  return taskTypeOptions.find((item) => item.value === value)?.label || '课堂练习'
}
function selectTaskType(event: { detail: { value: string | number } }) {
  taskType.value = taskTypeOptions[Number(event.detail.value)]?.value || ''
  void load(true)
}
function search() {
  query.value = queryDraft.value.trim()
  pointCode.value = pointDraft.value.trim()
  void load(true)
}
async function load(reset: boolean) {
  if (!verifyActor() || (loading.value && !reset)) return
  if (reset) {
    items.value = []
    total.value = 0
  }
  const token = ++requestToken
  loading.value = true
  error.value = ''
  try {
    const offset = reset ? 0 : items.value.length
    const page = await listTeacherQuestionBank({
      taskType: taskType.value || undefined,
      pointCode: pointCode.value || undefined,
      query: query.value || undefined,
      limit: 20,
      offset,
    })
    if (token !== requestToken || !verifyActor()) return
    const visibleItems = page.items.filter((item) => !deletedIds.has(item.id))
    items.value = reset ? visibleItems : [...items.value, ...visibleItems]
    total.value = Math.max(0, page.total - (page.items.length - visibleItems.length))
    loaded.value = true
  } catch (reason) {
    if (token === requestToken && verifyActor())
      error.value = reason instanceof Error ? reason.message : '读取失败，请重试。'
  } finally {
    if (token === requestToken) loading.value = false
  }
}
function openItem(item: TeacherQuestionBankItem) {
  if (!verifyActor()) return
  goDetail(ROUTES.teacherQuestionBankDetail, {
    id: item.id,
    resource: 'question-bank',
    keyword: query.value || undefined,
  })
}
function confirmDelete(item: TeacherQuestionBankItem) {
  if (deletingId.value || !verifyActor()) return
  deletingId.value = item.id
  uni.showModal({
    title: '删除这道题？',
    content: '删除后从个人题库移除，原测试及历史作答仍会保留。',
    confirmText: '删除',
    success: ({ confirm }) => {
      if (!verifyActor()) return
      if (confirm) void deleteItem(item)
      else deletingId.value = undefined
    },
    fail: () => {
      deletingId.value = undefined
    },
  })
}
async function deleteItem(item: TeacherQuestionBankItem) {
  if (!verifyActor()) return
  try {
    await deleteTeacherQuestionBankItem(item.id, item.version, `t64-bank-delete-${item.id}-v${item.version}`)
    if (!verifyActor()) return
    deletedIds.add(item.id)
    const wasVisible = items.value.some((entry) => entry.id === item.id)
    items.value = items.value.filter((entry) => entry.id !== item.id)
    if (wasVisible) total.value = Math.max(0, total.value - 1)
    uni.showToast({ title: '题目已删除', icon: 'success' })
  } catch (reason) {
    if (verifyActor()) error.value = reason instanceof Error ? reason.message : '删除失败，题目仍保留。'
  } finally {
    if (currentActor()) deletingId.value = undefined
  }
}
onLoad((queryValue) => {
  if (!requireRole('teacher')) return
  teacherOpenid = getSession()?.openid || ''
  const context = teacherContentReturnParams(queryValue, 'question-bank')
  query.value = context.keyword || ''
  queryDraft.value = query.value
  void load(true)
})
onShow(() => {
  if (teacherOpenid && verifyActor() && loaded.value) void load(true)
})
onBackPress(({ from }) =>
  handleBackPress(from, ROUTES.teacherContent, {
    resource: 'question-bank',
    keyword: query.value || undefined,
  }),
)
</script>

<style scoped>
.bank-page {
  display: flex;
  padding: 28rpx 24rpx calc(48rpx + env(safe-area-inset-bottom));
  flex-direction: column;
  gap: 24rpx;
  color: var(--med-ink);
}
.page-intro {
  display: flex;
  padding: 8rpx 4rpx 18rpx;
  flex-direction: column;
  gap: 10rpx;
  border-bottom: 1rpx solid var(--med-line);
}
.eyebrow {
  color: var(--med-primary);
  font-size: 22rpx;
  font-weight: 700;
}
.page-title {
  font-size: 38rpx;
  font-weight: 750;
}
.intro-copy,
.filter-note,
.record-meta,
.empty-copy,
.inline-error {
  color: var(--med-muted);
  font-size: 24rpx;
  line-height: 1.6;
}
.filters {
  display: flex;
  padding: 22rpx;
  flex-direction: column;
  gap: 14rpx;
  background: var(--med-surface);
  border: 1rpx solid var(--med-line);
  border-radius: 16rpx;
}
.search-row {
  display: flex;
  gap: 12rpx;
}
.filter-input {
  min-height: 78rpx;
  padding: 0 18rpx;
  box-sizing: border-box;
  color: var(--med-ink);
  background: #f7f9fc;
  border: 1rpx solid var(--med-line);
  border-radius: 12rpx;
  font-size: 23rpx;
}
.search-input {
  min-width: 0;
  flex: 1;
}
.search-button,
.primary-button {
  min-height: 78rpx;
  margin: 0;
  padding: 0 24rpx;
  color: #fff;
  background: var(--med-primary);
  border-radius: 12rpx;
  font-size: 23rpx;
}
.picker-input {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.results {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}
.results-heading {
  display: flex;
  min-height: 64rpx;
  align-items: center;
  justify-content: space-between;
}
.section-title {
  font-size: 29rpx;
  font-weight: 700;
}
.count {
  color: var(--med-muted);
  font-size: 23rpx;
}
.record-delete {
  margin: 0 0 16rpx;
  min-height: 72rpx;
  color: #9c3f3a;
  background: #fff;
  border: 1rpx solid #e6c6c3;
  font-size: 23rpx;
}
.bank-record {
  border-bottom: 1rpx solid var(--med-line);
}
.record-open {
  display: flex;
  width: 100%;
  min-height: 150rpx;
  margin: 0;
  padding: 20rpx 8rpx;
  align-items: center;
  gap: 18rpx;
  color: var(--med-ink);
  background: transparent;
  text-align: left;
}
.record-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 7rpx;
}
.record-title-row {
  display: flex;
  align-items: flex-start;
  gap: 12rpx;
}
.record-title {
  min-width: 0;
  flex: 1;
  font-size: 27rpx;
  font-weight: 700;
  line-height: 1.4;
}
.record-prompt {
  display: -webkit-box;
  overflow: hidden;
  color: #3f5269;
  font-size: 23rpx;
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.record-meta {
  overflow-wrap: anywhere;
  font-size: 20rpx;
}
.arrow {
  color: var(--med-primary);
  font-size: 42rpx;
}
.empty-copy {
  padding: 26rpx 4rpx;
}
.more-button {
  min-height: 78rpx;
  color: var(--med-primary);
  background: transparent;
  font-size: 24rpx;
}
.inline-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12rpx;
  color: #a23e39;
}
.inline-error button {
  flex: none;
  color: var(--med-primary);
  background: transparent;
  font-size: 23rpx;
}
</style>
