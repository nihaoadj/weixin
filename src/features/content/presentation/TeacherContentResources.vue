<template>
  <view class="resources">
    <view
      class="resource-switch"
      role="tablist"
      aria-label="资源类型"
    >
      <button
        v-for="option in resourceOptions"
        :id="`content-tab-${option.value}`"
        :key="option.value"
        class="resource-tab"
        :class="{ 'resource-tab--active': resource === option.value }"
        role="tab"
        :aria-selected="resource === option.value"
        @tap="selectResource(option.value)"
      >
        {{ option.label }}
      </button>
    </view>
    <view
      class="filters"
      aria-label="资源搜索"
    >
      <view class="search-row">
        <image
          class="search-icon"
          src="/static/content-search.svg"
          mode="aspectFit"
          aria-hidden="true"
        />
        <input
          id="content-search-input"
          v-model="keywordDraft"
          class="search-input"
          placeholder-class="search-placeholder"
          placeholder-style="color: #7d8db7"
          maxlength="100"
          :placeholder="`搜索${resourceLabel}标题与内容`"
          aria-label="资源搜索关键词"
          confirm-type="search"
          @confirm="search"
        />
        <view
          class="search-divider"
          aria-hidden="true"
        />
        <button
          id="content-search"
          class="search-button"
          :disabled="loading"
          @tap="search"
        >
          搜索
        </button>
      </view>
    </view>
    <view class="section-heading">
      <view class="section-label">
        <view
          class="section-accent"
          aria-hidden="true"
        />
        <text class="section-title">{{ resourceLabel }}</text>
        <text
          v-if="resource === 'question-bank'"
          class="section-total"
          >{{ bankTotal }} 道</text
        >
      </view>
      <button
        id="content-create"
        class="create-action"
        @tap="createResource"
      >
        <text
          v-if="resource === 'cases'"
          class="create-plus"
          aria-hidden="true"
          >＋</text
        >
        <text>{{ resource === 'cases' ? '创建病例' : '打开个人题库' }}</text>
      </button>
    </view>
    <scroll-view
      :key="`${resource}:${keyword}`"
      class="resource-list-scroll"
      scroll-y
      :aria-label="`${resourceLabel}列表`"
    >
      <MedState
        v-if="loading && loadedResource !== resource"
        variant="loading"
        icon="history"
        :title="`正在读取${resourceLabel}`"
        description="请稍候。"
      />
      <MedState
        v-else-if="loadError && loadedResource !== resource && !rows.length"
        variant="error"
        icon="retry"
        :title="`${resourceLabel}暂不可用`"
        :description="loadError"
        action-label="重试"
        @action="refresh"
      />
      <view
        v-else
        class="record-section"
      >
        <text
          v-if="loadError"
          class="inline-error"
          role="alert"
          >{{ loadError }}</text
        >
        <MedState
          v-if="!rows.length"
          variant="empty"
          icon="book"
          :title="`暂无${resourceLabel}`"
          :description="
            resource === 'question-bank'
              ? '可在课堂最终测试审阅页将单选题保存到个人题库。'
              : '可创建病例，或调整搜索关键词。'
          "
        />
        <template v-else>
          <view
            v-for="(row, rowIndex) in visibleRows"
            :key="row.key"
            class="resource-row"
          >
            <button
              class="row-title"
              :aria-label="`打开${resourceLabel}：${row.title}`"
              @tap="openRow(row)"
            >
              <text class="row-title-text">{{ row.title }}</text>
              <text class="row-summary">{{ row.summary }}</text>
              <text class="row-meta">{{ row.displayMeta }}</text>
            </button>
            <view class="row-actions">
              <button
                :id="`content-view-${rowIndex}`"
                class="small-action view-resource"
                :aria-label="`查看：${row.title}`"
                @tap="openRow(row)"
              >
                <image
                  class="action-icon"
                  src="/static/content-view.svg"
                  mode="aspectFit"
                  aria-hidden="true"
                /><text>查看</text>
              </button>
              <button
                v-if="row.problem && canAct(row.problem, 'edit')"
                :id="`content-edit-${rowIndex}`"
                class="small-action edit-resource"
                :disabled="Boolean(savingKey || pendingDeleteKey)"
                :aria-label="`编辑：${row.title}`"
                @tap="editProblem(row.problem)"
              >
                <image
                  class="action-icon"
                  src="/static/content-edit.svg"
                  mode="aspectFit"
                  aria-hidden="true"
                /><text>编辑</text>
              </button>
              <button
                v-if="row.bank"
                :id="`content-edit-${rowIndex}`"
                class="small-action edit-resource"
                :aria-label="`编辑：${row.title}`"
                @tap="openBankItem(row.bank)"
              >
                <image
                  class="action-icon"
                  src="/static/content-edit.svg"
                  mode="aspectFit"
                  aria-hidden="true"
                /><text>编辑</text>
              </button>
              <button
                v-if="row.bank || (row.problem && canAct(row.problem, 'delete'))"
                :id="`content-delete-${rowIndex}`"
                class="small-action delete-resource"
                :disabled="Boolean(savingKey || pendingDeleteKey)"
                :aria-label="`删除：${row.title}`"
                @tap="deleteResource(row)"
              >
                <image
                  class="action-icon"
                  src="/static/content-delete.svg"
                  mode="aspectFit"
                  aria-hidden="true"
                />
                <text>{{ savingKey === row.key ? '删除中…' : '删除' }}</text>
              </button>
            </view>
          </view>
          <button
            v-if="canLoadMore"
            class="load-more"
            :disabled="loading"
            @tap="loadMore"
          >
            {{ loading ? '正在读取…' : '加载更多' }}
          </button>
        </template>
      </view>
    </scroll-view>
  </view>
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import MedState from '@/components/ui/MedState.vue'
import { getSession } from '@/features/identity/public'
import {
  getGuidedCasesAsync,
  listTeacherQuestionBank,
  deleteGuidedCaseAsync,
  deleteTeacherQuestionBankItem,
  type TeacherQuestionBankItem,
} from '@/features/content/public'
import { getKnowledgeCatalog } from '@/features/learning/public'
import { goDetail, ROUTES } from '@/platform/navigation'
import type { Problem } from '@/types/domain'
import type { TeacherContentResource } from '@/platform/navigation/teacher'

type ResourceRow = {
  key: string
  title: string
  summary: string
  meta: string
  displayMeta: string
  sortTime: string
  problem?: Problem
  bank?: TeacherQuestionBankItem
}
const props = withDefaults(defineProps<{ resource: TeacherContentResource; keyword?: string }>(), { keyword: '' })
const emit = defineEmits<{ filtersChange: [value: { resource: TeacherContentResource; keyword: string }] }>()
const resourceOptions: Array<{ value: TeacherContentResource; label: string }> = [
  { value: 'cases', label: '病例库' },
  { value: 'question-bank', label: '个人题库' },
]
const problems = ref<Problem[]>([])
const bankItems = ref<TeacherQuestionBankItem[]>([])
const bankTotal = ref(0)
const knowledgeTitles = ref<Record<string, string>>({})
const loading = ref(false)
const loadedResource = ref<TeacherContentResource>()
const loadError = ref('')
const savingKey = ref('')
const pendingDeleteKey = ref('')
const keywordDraft = ref(props.keyword)
const rowLimit = ref(20)
let requestToken = 0
let loadedActor: string | undefined
let disposed = false
const resource = computed(() => props.resource)
const resourceLabel = computed(() => resourceOptions.find((item) => item.value === props.resource)?.label || '教学资源')
const rows = computed<ResourceRow[]>(() => {
  const values =
    props.resource === 'cases'
      ? problems.value
          .filter((item) => item.contentType === 'guided_case')
          .map((problem) => ({
            key: `case-${problem.id}`,
            title: problem.title,
            summary: problem.description || '查看病例内容。',
            meta: [problem.specialty || '病理学', problem.time].filter(Boolean).join(' · '),
            displayMeta: knowledgeMeta(problem.knowledgePointCodes || [], `学科：${problem.specialty || '病理学'}`),
            sortTime: problem.time,
            problem,
          }))
      : bankItems.value.map((bank) => ({
          key: `bank-${bank.id}`,
          title: bank.title,
          summary: bank.prompt,
          meta: bank.pointCodes.join(' · '),
          displayMeta: knowledgeMeta(bank.pointCodes, '未绑定知识点'),
          sortTime: bank.updatedAt,
          bank,
        }))
  const query = props.keyword.trim().toLocaleLowerCase()
  return values
    .filter((row) => !query || `${row.title} ${row.summary} ${row.meta}`.toLocaleLowerCase().includes(query))
    .sort((a, b) => b.sortTime.localeCompare(a.sortTime))
})
const visibleRows = computed(() => rows.value.slice(0, rowLimit.value))
const canLoadMore = computed(() =>
  props.resource === 'question-bank'
    ? bankItems.value.length < bankTotal.value
    : rows.value.length > visibleRows.value.length,
)
watch(
  () => props.keyword,
  (value) => {
    keywordDraft.value = value
  },
)
watch(
  () => [props.resource, props.keyword],
  () => {
    void refresh()
  },
)
function selectResource(value: TeacherContentResource) {
  if (value !== props.resource) emit('filtersChange', { resource: value, keyword: props.keyword })
}
function search() {
  emit('filtersChange', { resource: props.resource, keyword: keywordDraft.value.trim().slice(0, 100) })
}
function actionContextCurrent(actor: string | undefined, token: number) {
  return !disposed && requestToken === token && getSession()?.role === 'teacher' && getSession()?.openid === actor
}
function knowledgeMeta(codes: string[], fallback: string) {
  if (!codes.length) return fallback
  const titles = codes.map((code) => knowledgeTitles.value[code])
  return `知识点：${titles.every(Boolean) ? `${titles[0]}${codes.length > 1 ? ` 等${codes.length}项` : ''}` : `${codes.length} 项`}`
}
async function refreshKnowledgeTitles(actor: string | undefined, token: number) {
  const codes =
    props.resource === 'cases'
      ? problems.value.flatMap((problem) => problem.knowledgePointCodes || [])
      : bankItems.value.flatMap((item) => item.pointCodes)
  if (!codes.length) return
  try {
    const catalog = await getKnowledgeCatalog()
    if (actionContextCurrent(actor, token))
      knowledgeTitles.value = Object.fromEntries(catalog.map((point) => [point.code, point.title]))
  } catch {
    // Labels are optional presentation data; the resource list remains usable.
  }
}
async function refresh() {
  const actor = getSession()?.openid
  const token = ++requestToken
  const current = () => actionContextCurrent(actor, token)
  loadedActor = actor
  savingKey.value = ''
  pendingDeleteKey.value = ''
  loading.value = true
  loadError.value = ''
  knowledgeTitles.value = {}
  rowLimit.value = 20
  try {
    if (props.resource === 'cases') {
      const result = await getGuidedCasesAsync()
      if (!current()) return
      problems.value = result
    } else {
      const page = await listTeacherQuestionBank({ query: props.keyword.trim() || undefined, limit: 20, offset: 0 })
      if (!current()) return
      bankItems.value = page.items
      bankTotal.value = page.total
    }
    if (current()) {
      loadedResource.value = props.resource
      void refreshKnowledgeTitles(actor, token)
    }
  } catch (error) {
    if (current()) loadError.value = error instanceof Error ? error.message : '请稍后重试。'
  } finally {
    if (current()) loading.value = false
  }
}
async function loadMore() {
  if (loading.value) return
  if (props.resource !== 'question-bank') {
    rowLimit.value += 20
    return
  }
  const actor = getSession()?.openid
  const token = ++requestToken
  const current = () => actionContextCurrent(actor, token)
  loading.value = true
  loadError.value = ''
  try {
    const page = await listTeacherQuestionBank({
      query: props.keyword.trim() || undefined,
      limit: 20,
      offset: bankItems.value.length,
    })
    if (!current()) return
    const existing = new Set(bankItems.value.map((item) => item.id))
    bankItems.value = [...bankItems.value, ...page.items.filter((item) => !existing.has(item.id))]
    bankTotal.value = page.total
    rowLimit.value = bankItems.value.length
    void refreshKnowledgeTitles(actor, token)
  } catch (error) {
    if (current()) loadError.value = error instanceof Error ? error.message : '读取更多资源失败。'
  } finally {
    if (current()) loading.value = false
  }
}
function actorCurrent() {
  return !disposed && getSession()?.role === 'teacher' && getSession()?.openid === loadedActor
}
function canAct(problem: Problem, action: 'edit' | 'delete') {
  return actorCurrent() && problem.allowedActions?.includes(action) === true
}
function contentReturnContext() {
  return {
    tab: 'content',
    returnTab: 'problems',
    returnSection: 'resources',
    resource: props.resource,
    keyword: props.keyword || undefined,
  }
}
function openRow(row: ResourceRow) {
  if (!actorCurrent()) return
  if (row.problem) goDetail(ROUTES.teacherProblemDetail, { id: row.problem.id, ...contentReturnContext() })
  else if (row.bank) openBankItem(row.bank)
}
function editProblem(problem: Problem) {
  if (canAct(problem, 'edit')) goDetail(ROUTES.teacherCaseEdit, { id: problem.id, ...contentReturnContext() })
}
function openBankItem(item: TeacherQuestionBankItem) {
  if (actorCurrent()) goDetail(ROUTES.teacherQuestionBankDetail, { id: item.id, ...contentReturnContext() })
}
function createResource() {
  if (!actorCurrent()) return
  goDetail(props.resource === 'cases' ? ROUTES.teacherCaseEdit : ROUTES.teacherQuestionBank, contentReturnContext())
}
function deleteResource(row: ResourceRow) {
  if (savingKey.value || pendingDeleteKey.value || !actorCurrent() || (row.problem && !canAct(row.problem, 'delete')))
    return
  const actor = getSession()?.openid
  const token = requestToken
  pendingDeleteKey.value = row.key
  uni.showModal({
    title: `删除${props.resource === 'cases' ? '病例' : '题目'}？`,
    content: '删除后将从资源列表移除，已有课堂和测试记录保留。',
    confirmText: '删除',
    confirmColor: '#a33636',
    success: async ({ confirm }) => {
      if (!actionContextCurrent(actor, token)) return
      pendingDeleteKey.value = ''
      if (!confirm) return
      savingKey.value = row.key
      try {
        if (row.problem) await deleteGuidedCaseAsync(row.problem.id)
        else if (row.bank)
          await deleteTeacherQuestionBankItem(
            row.bank.id,
            row.bank.version,
            `delete-${row.bank.id}-${row.bank.version}-${Date.now()}`,
          )
        if (!actionContextCurrent(actor, token)) return
        if (row.problem) problems.value = problems.value.filter((item) => item.id !== row.problem?.id)
        else if (row.bank) {
          bankItems.value = bankItems.value.filter((item) => item.id !== row.bank?.id)
          bankTotal.value = Math.max(0, bankTotal.value - 1)
        }
        uni.showToast({ title: '已删除', icon: 'success' })
      } catch (error) {
        if (actionContextCurrent(actor, token))
          uni.showToast({ title: error instanceof Error ? error.message : '删除失败，请重试', icon: 'none' })
      } finally {
        if (actionContextCurrent(actor, token)) savingKey.value = ''
      }
    },
    fail: () => {
      if (actionContextCurrent(actor, token)) pendingDeleteKey.value = ''
    },
  })
}
onBeforeUnmount(() => {
  disposed = true
  requestToken += 1
})
onMounted(() => {
  // Mini Program child refs may become available after the parent's first onShow.
  if (!loadedResource.value && !loading.value) void refresh()
})
defineExpose({ refresh })
</script>
<style scoped>
.resources {
  --content-ink: #101449;
  --content-muted: #7184b3;
  --content-border: #c5e8ff;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  padding: 0 32rpx;
  color: var(--content-ink);
}
.resource-switch,
.filters,
.section-heading {
  flex: none;
}
.resource-list-scroll {
  flex: 1;
  height: 0;
  min-height: 0;
}
.record-section {
  padding-bottom: 28rpx;
}
.resource-switch {
  display: flex;
  overflow: hidden;
  border: 1rpx solid #b9ddfc;
  border-radius: 22rpx;
  background: rgba(255, 255, 255, 0.62);
}
.resource-tab {
  display: flex;
  flex: 1;
  min-width: 0;
  min-height: 44px;
  margin: 0;
  padding: 10rpx 12rpx;
  align-items: center;
  justify-content: center;
  border-radius: 21rpx;
  background: transparent;
  color: #5d709e;
  font-size: 30rpx;
  font-weight: 650;
  line-height: 1.35;
}
.resource-tab--active {
  color: #fff;
  background: linear-gradient(110deg, #1bddd7, #00b4df);
}
.filters {
  margin-top: 16rpx;
}
.search-row {
  display: flex;
  min-height: 44px;
  padding: 5rpx 6rpx 5rpx 22rpx;
  align-items: center;
  gap: 14rpx;
  border: 1rpx solid var(--content-border);
  border-radius: 40rpx;
  background: rgba(255, 255, 255, 0.92);
}
.search-icon {
  width: 32rpx;
  height: 32rpx;
  flex: none;
}
.search-input {
  min-width: 0;
  min-height: 44px;
  flex: 1;
  padding: 0;
  color: var(--content-ink);
  font-size: 25rpx;
}
.search-placeholder {
  color: #7d8db7;
}
.search-divider {
  width: 1rpx;
  height: 28rpx;
  background: #c5dfff;
}
.search-button {
  display: flex;
  min-height: 44px;
  margin: 0;
  padding: 0 27rpx;
  align-items: center;
  justify-content: center;
  border-radius: 32rpx;
  color: #fff;
  background: linear-gradient(110deg, #11d8dc, #00ade7);
  font-size: 25rpx;
  line-height: 1.3;
}
.section-heading {
  display: flex;
  min-height: 44px;
  margin: 20rpx 0 14rpx;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
}
.section-label {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 14rpx;
}
.section-accent {
  width: 11rpx;
  height: 44rpx;
  flex: none;
  border-radius: 7rpx;
  background: linear-gradient(#00dfd5, #009aff);
}
.section-title {
  color: var(--content-ink);
  font-size: 34rpx;
  font-weight: 750;
  line-height: 1.3;
}
.section-total {
  color: var(--content-muted);
  font-size: 24rpx;
  white-space: nowrap;
}
.create-action {
  display: flex;
  min-height: 44px;
  flex: none;
  margin: 0;
  padding: 0 24rpx;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
  border-radius: 40rpx;
  color: #fff;
  background: linear-gradient(110deg, #00cddd, #007aff);
  font-size: 24rpx;
  line-height: 1.3;
}
.create-plus {
  font-size: 38rpx;
  font-weight: 300;
  line-height: 1;
}
.record-section {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}
.resource-row {
  overflow: hidden;
  border: 1rpx solid var(--content-border);
  border-radius: 19rpx;
  background: #fff;
  box-shadow: 0 6rpx 18rpx rgba(76, 159, 206, 0.05);
}
.row-title {
  display: block;
  box-sizing: border-box;
  width: 100%;
  min-height: 44px;
  margin: 0;
  padding: 16rpx 20rpx 7rpx;
  border-radius: 0;
  background: transparent;
  text-align: left;
  line-height: 1.35;
}
.row-title-text {
  display: block;
  color: var(--content-ink);
  font-size: 30rpx;
  font-weight: 750;
  line-height: 1.35;
}
.row-summary {
  display: block;
  margin-top: 7rpx;
  color: var(--content-muted);
  font-size: 25rpx;
  line-height: 1.45;
}
.row-meta {
  display: block;
  margin-top: 4rpx;
  color: #7d8db4;
  font-size: 24rpx;
  line-height: 1.4;
}
.row-title-text,
.row-summary,
.row-meta {
  overflow-wrap: anywhere;
  word-break: break-word;
}
.row-actions {
  display: flex;
  margin: 0 20rpx;
  padding: 2rpx 0;
  align-items: stretch;
  border-top: 1rpx solid #d7edff;
}
.small-action {
  position: relative;
  display: flex;
  flex: 1;
  min-width: 0;
  min-height: 44px;
  margin: 0;
  padding: 8rpx 4rpx;
  align-items: center;
  justify-content: center;
  gap: 12rpx;
  border-radius: 0;
  color: #007aff;
  background: transparent;
  font-size: 24rpx;
  line-height: 1.3;
}
.small-action + .small-action::before {
  position: absolute;
  top: 28%;
  bottom: 28%;
  left: 0;
  width: 1rpx;
  background: #c1e0ff;
  content: '';
}
.action-icon {
  width: 28rpx;
  height: 28rpx;
  flex: none;
}
.delete-resource {
  color: #ff6d64;
}
.load-more {
  display: flex;
  min-height: 44px;
  margin: 0;
  padding: 8rpx 20rpx;
  align-items: center;
  justify-content: center;
  color: #667faa;
  border: 1rpx solid var(--content-border);
  border-radius: 16rpx;
  background: rgba(255, 255, 255, 0.65);
  font-size: 24rpx;
}
.inline-error {
  display: block;
  padding: 12rpx 0;
  color: #a33636;
  font-size: 24rpx;
  line-height: 1.5;
}
button::after {
  border: 0;
}
button[disabled] {
  opacity: 0.55;
}
</style>
