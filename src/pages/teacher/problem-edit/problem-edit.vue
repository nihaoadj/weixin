<template>
  <view class="safe-page edit-page">
    <view class="form card">
      <text class="page-title">{{ isEdit ? '编辑问题' : '新建问题' }}</text>
      <text class="label">问题类型</text>
      <picker
        :range="typeOptions"
        :value="typeIndex"
        @change="changeType"
      >
        <view class="picker">{{ typeOptions[typeIndex] }}<text>⌄</text></view>
      </picker>
      <text class="label">问题标题</text>
      <input
        v-model="title"
        class="input"
        placeholder="请输入问题标题"
      />
      <text class="label">问题描述</text>
      <textarea
        v-model="description"
        class="textarea"
        placeholder="请输入问题的详细描述"
        :maxlength="2000"
      />
      <text class="label">发布对象</text>
      <view class="targets">
        <view
          v-for="item in targetOptions"
          :key="item.value"
          class="target"
          :class="{ active: target === item.value }"
          @click="target = item.value"
          >{{ item.label }}</view
        >
      </view>
      <template v-if="target !== 'all'">
        <text class="label">{{ target === 'class' ? '班级名称' : '学生范围说明' }}</text>
        <input
          v-model="targetLabel"
          class="input"
          :placeholder="target === 'class' ? '例如：临床一班' : '例如：补修学生'"
        />
        <text class="label">{{ target === 'class' ? '班级 ID' : '学生 OpenID' }}</text>
        <input
          v-model="targetIdsInput"
          class="input"
          placeholder="多个 ID 使用英文逗号分隔"
        />
        <text class="hint">Demo 学生属于班级 demo_class_1，OpenID 为 demo_student。</text>
      </template>
      <button
        class="primary-button save"
        @click="save"
      >
        保存为待审核
      </button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { requireRole } from '@/services/auth'
import { backOrHome } from '@/services/navigation'
import { findProblemAsync, upsertProblemAsync } from '@/services/repositoryAsync'
import type { ProblemTarget, ProblemType } from '@/types/domain'

const typeOptions: ProblemType[] = ['医学常识', '模拟诊疗', '病例分析']
const targetOptions: Array<{ value: ProblemTarget; label: string }> = [
  { value: 'all', label: '全体学生' },
  { value: 'class', label: '指定班级' },
  { value: 'individual', label: '指定学生' },
]
const isEdit = ref(false)
const problemId = ref('')
const typeIndex = ref(0)
const title = ref('')
const description = ref('')
const target = ref<ProblemTarget>('all')
const targetLabel = ref('')
const targetIdsInput = ref('')

onLoad((options) => {
  if (!requireRole('teacher')) return
  const id = typeof options?.id === 'string' ? options.id : ''
  void loadProblem(id)
})

async function loadProblem(id: string) {
  const problem = id ? await findProblemAsync(id) : undefined
  if (!problem) return
  isEdit.value = true
  problemId.value = problem.id
  typeIndex.value = Math.max(0, typeOptions.indexOf(problem.type))
  title.value = problem.title
  description.value = problem.description
  target.value = problem.target
  targetLabel.value = problem.targetLabel || problem.className || ''
  targetIdsInput.value = (problem.targetIds || []).join(', ')
}

function changeType(event: { detail: { value: string } }) {
  typeIndex.value = Number(event.detail.value)
}

async function save() {
  if (!title.value.trim()) {
    uni.showToast({ title: '请输入问题标题', icon: 'none' })
    return
  }
  const targetIds = targetIdsInput.value
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean)
  if (target.value !== 'all' && (!targetLabel.value.trim() || targetIds.length === 0)) {
    uni.showToast({ title: '请填写发布对象名称和 ID', icon: 'none' })
    return
  }
  const existing = isEdit.value ? await findProblemAsync(problemId.value) : undefined
  await upsertProblemAsync({
    id: existing?.id || `prob_${Date.now()}`,
    type: typeOptions[typeIndex.value] || '医学常识',
    title: title.value.trim(),
    description: description.value.trim(),
    target: target.value,
    targetIds: target.value === 'all' ? [] : targetIds,
    targetLabel: target.value === 'all' ? '全体学生' : targetLabel.value.trim(),
    status: '待审核',
    time: new Date().toISOString().slice(0, 10),
  })
  uni.showToast({ title: '保存成功', icon: 'success' })
  backOrHome('teacher')
}
</script>

<style scoped>
.edit-page {
  padding: 28rpx;
}
.form {
  padding: 32rpx;
}
.page-title {
  display: block;
  margin-bottom: 30rpx;
  font-size: 36rpx;
  font-weight: 750;
}
.label {
  display: block;
  margin: 26rpx 0 12rpx;
  color: #526174;
  font-size: 24rpx;
}
.picker,
.input,
.textarea {
  box-sizing: border-box;
  width: 100%;
  padding: 20rpx 22rpx;
  background: #f5f8fb;
  border: 1rpx solid #e2eaf1;
  border-radius: 16rpx;
}
.picker {
  display: flex;
  height: 82rpx;
  align-items: center;
  justify-content: space-between;
}
.input {
  height: 82rpx;
}
.textarea {
  height: 240rpx;
}
.targets {
  display: flex;
  gap: 12rpx;
}
.target {
  padding: 18rpx 16rpx;
  flex: 1;
  color: #64748b;
  background: #edf2f7;
  border-radius: 14rpx;
  font-size: 22rpx;
  text-align: center;
}
.target.active {
  color: #fff;
  background: #087f8c;
}
.hint {
  display: block;
  margin-top: 10rpx;
  color: #8795a8;
  font-size: 21rpx;
  line-height: 1.5;
}
.save {
  margin-top: 42rpx;
}
</style>
