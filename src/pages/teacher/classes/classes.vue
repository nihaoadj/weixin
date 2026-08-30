<template>
  <view class="safe-page page">
    <view class="card intro">
      <text class="title">班级管理</text>
      <text class="muted">只显示当前教师的班级；使用学生 external ID 精确加入，不展示全库学生名单。</text>
    </view>
    <view class="card form">
      <input
        v-model="newName"
        placeholder="新班级名称"
      />
      <input
        v-model="newCode"
        placeholder="班级 code（创建后不可修改）"
      />
      <button
        class="primary"
        :loading="saving"
        @click="create"
      >
        创建班级
      </button>
    </view>
    <MedState
      v-if="loading"
      variant="loading"
      icon="retry"
      title="正在加载班级"
      description="正在同步班级与成员信息。"
    />
    <MedState
      v-else-if="loadError"
      variant="error"
      icon="retry"
      title="班级加载失败"
      :description="loadError"
      action-label="重新加载"
      @action="load"
    />
    <MedState
      v-else-if="!classes.length"
      variant="first-use"
      icon="report"
      title="创建第一个教学班级"
      description="班级用于限定学生范围并生成准确的教学学情。请在上方填写名称和唯一 code。"
      action-label="填写创建信息"
      @action="focusCreate"
    />
    <view
      v-for="classroom in classes"
      :key="classroom.id"
      class="card class-card"
    >
      <view class="class-header">
        <view>
          <text class="class-name">{{ classroom.name }}</text>
          <text class="muted">{{ classroom.code }} · {{ classroom.status === 'active' ? '启用' : '已归档' }}</text>
        </view>
        <view class="class-actions">
          <button
            class="small"
            @click="rename(classroom)"
          >
            改名
          </button>
          <button
            v-if="classroom.status === 'active'"
            class="small danger"
            @click="archive(classroom)"
          >
            归档
          </button>
        </view>
      </view>
      <button
        class="secondary full"
        @click="selectClass(classroom)"
      >
        {{ selected?.id === classroom.id ? '收起成员' : '查看成员' }}
      </button>
      <view
        v-if="selected?.id === classroom.id"
        class="members"
      >
        <view class="member-add">
          <input
            v-model="memberExternalId"
            placeholder="学生 external ID"
          />
          <button
            class="primary small"
            :loading="saving"
            @click="addMember(classroom)"
          >
            加入
          </button>
        </view>
        <view
          v-if="!students.length"
          class="muted"
          >暂无成员</view
        >
        <view
          v-for="student in students"
          :key="student.id"
          class="member"
        >
          <text>{{ student.nickname }} · {{ student.externalId }}</text>
          <button
            class="small danger"
            @click="removeMember(classroom, student.id)"
          >
            移除
          </button>
        </view>
      </view>
    </view>
  </view>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import MedState from '@/components/ui/MedState.vue'
import { requireRole } from '@/services/auth'
import {
  addStudentToClass,
  createTeacherClass,
  getClassStudents,
  getTeacherClasses,
  removeStudentFromClass,
  updateTeacherClass,
  type TeacherClass,
  type TeacherStudent,
} from '@/services/teacherInsights'

const classes = ref<TeacherClass[]>([])
const selected = ref<TeacherClass>()
const students = ref<TeacherStudent[]>([])
const newName = ref('')
const newCode = ref('')
const memberExternalId = ref('')
const saving = ref(false)
const loading = ref(false)
const loadError = ref('')

async function load() {
  if (loading.value) return
  loading.value = true
  loadError.value = ''
  try {
    classes.value = await getTeacherClasses()
    if (selected.value) {
      selected.value = classes.value.find((item) => item.id === selected.value?.id)
      if (selected.value) students.value = await getClassStudents(selected.value.id)
    }
  } catch (error) {
    classes.value = []
    loadError.value = error instanceof Error ? error.message : '请稍后重试'
  } finally {
    loading.value = false
  }
}
function focusCreate() {
  uni.pageScrollTo({ scrollTop: 0, duration: 250 })
  uni.showToast({ title: '请填写班级名称和 code', icon: 'none' })
}
async function create() {
  if (!newName.value.trim() || !newCode.value.trim()) {
    uni.showToast({ title: '请填写班级名称和 code', icon: 'none' })
    return
  }
  saving.value = true
  try {
    await createTeacherClass(newName.value.trim(), newCode.value.trim())
    newName.value = ''
    newCode.value = ''
    await load()
    uni.showToast({ title: '班级已创建', icon: 'success' })
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : '创建失败', icon: 'none' })
  } finally {
    saving.value = false
  }
}
function selectClass(classroom: TeacherClass) {
  if (selected.value?.id === classroom.id) {
    selected.value = undefined
    students.value = []
    return
  }
  selected.value = classroom
  void loadMembers(classroom.id)
}
async function loadMembers(classId: number) {
  try {
    students.value = await getClassStudents(classId)
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : '加载成员失败', icon: 'none' })
  }
}
function rename(classroom: TeacherClass) {
  uni.showModal({
    title: '修改班级名称',
    editable: true,
    placeholderText: classroom.name,
    success: async ({ confirm, content }) => {
      if (!confirm || !content?.trim()) return
      try {
        await updateTeacherClass(classroom.id, { name: content.trim() })
        await load()
      } catch (error) {
        uni.showToast({ title: error instanceof Error ? error.message : '改名失败', icon: 'none' })
      }
    },
  })
}
function archive(classroom: TeacherClass) {
  uni.showModal({
    title: '归档班级',
    content: '归档后不再进入默认学情，也不能新增成员。确定继续吗？',
    success: async ({ confirm }) => {
      if (!confirm) return
      try {
        await updateTeacherClass(classroom.id, { status: 'archived' })
        await load()
      } catch (error) {
        uni.showToast({ title: error instanceof Error ? error.message : '归档失败', icon: 'none' })
      }
    },
  })
}
async function addMember(classroom: TeacherClass) {
  if (!memberExternalId.value.trim()) return
  saving.value = true
  try {
    await addStudentToClass(classroom.id, memberExternalId.value.trim())
    memberExternalId.value = ''
    await loadMembers(classroom.id)
  } catch (error) {
    uni.showToast({ title: error instanceof Error ? error.message : '加入失败', icon: 'none' })
  } finally {
    saving.value = false
  }
}
function removeMember(classroom: TeacherClass, studentId: number) {
  uni.showModal({
    title: '移除成员',
    content: '确定移除该学生吗？',
    success: async ({ confirm }) => {
      if (!confirm) return
      try {
        await removeStudentFromClass(classroom.id, studentId)
        await loadMembers(classroom.id)
      } catch (error) {
        uni.showToast({ title: error instanceof Error ? error.message : '移除失败', icon: 'none' })
      }
    },
  })
}
onShow(() => {
  if (requireRole('teacher')) void load()
})
</script>
<style scoped>
.page {
  min-height: 100vh;
  padding: 28rpx;
  background: #f4f8fa;
}
.card {
  margin-bottom: 18rpx;
  padding: 28rpx;
}
.title,
.class-name {
  display: block;
  font-size: 34rpx;
  font-weight: 750;
}
.class-name {
  font-size: 29rpx;
}
.muted {
  display: block;
  margin-top: 10rpx;
  color: #718096;
  font-size: 22rpx;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 14rpx;
}
input {
  min-height: 70rpx;
  padding: 0 16rpx;
  border: 1rpx solid #dbe7eb;
  border-radius: 12rpx;
}
.primary,
.secondary,
.small {
  color: #fff;
  background: #087f8c;
}
.secondary {
  color: #087f8c;
  background: #e6f7f5;
}
.full {
  width: 100%;
  margin-top: 18rpx;
}
.class-header,
.member,
.member-add,
.class-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12rpx;
}
.class-actions {
  justify-content: flex-end;
}
.small {
  min-width: 110rpx;
  height: 58rpx;
  margin: 0;
  padding: 0 15rpx;
  line-height: 58rpx;
  font-size: 21rpx;
}
.danger {
  color: #b8323d;
  background: #fff0f1;
}
.members {
  margin-top: 20rpx;
  padding-top: 18rpx;
  border-top: 1rpx solid #e8eef4;
}
.member-add {
  align-items: stretch;
}
.member-add input {
  flex: 1;
}
.member {
  padding: 16rpx 0;
  border-bottom: 1rpx solid #eef2f5;
  font-size: 23rpx;
}
.empty {
  color: #718096;
  text-align: center;
}
</style>
