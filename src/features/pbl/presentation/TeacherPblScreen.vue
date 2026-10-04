<template>
  <TeacherPageFrame
    active="pbl"
    reference-layout
    fixed-content
    title="课堂教学"
    description="关注研讨进展，从学生记录进入分析与测试。"
  >
    <view class="pbl-hero"
      ><image
        class="pbl-hero__art"
        src="/static/pbl-reference-hero.svg"
        mode="aspectFill"
      /><text class="pbl-hero__title">课堂教学</text
      ><text class="pbl-hero__description">关注研讨进展，从学生记录进入分析与测试。</text></view
    >
    <MedState
      v-if="accessDenied"
      variant="error"
      icon="history"
      title="教师身份已变化"
      description="请重新登录教师账号。"
    />
    <MedState
      v-else-if="!scopeAllowed"
      :variant="error ? 'error' : 'loading'"
      icon="retry"
      :title="error || '正在读取班级范围'"
      :description="error ? '请重试读取班级范围。' : '请稍候。'"
      :action-label="error ? '重试' : undefined"
      @action="refresh"
    />
    <view
      v-else
      :key="identityGeneration"
      class="pbl-root"
    >
      <TeacherPblClassrooms
        ref="workspace"
        reference-layout
        fixed-records
        :classes="classes"
        :class-id="classId ? String(classId) : undefined"
        :session-id="sessionId === undefined ? undefined : String(sessionId)"
        @session-change="sessionId = $event"
        @open-diagnostic="openDiagnostic"
        @open-final-test="openFinalTest"
        @open-insights="openInsights"
        @open-test-queue="goDetail(ROUTES.teacherTestQueue)"
      >
        <template #class-picker>
          <picker
            :range="classOptions"
            :value="
              Math.max(
                0,
                classOptions.findIndex((item) => item.id === classId),
              )
            "
            aria-label="授课班级"
            range-key="name"
            @change="changeClass"
          >
            <view class="pbl-filter"
              ><view class="pbl-filter__value"
                ><image
                  class="pbl-filter__icon"
                  src="/static/pbl-reference-class.svg"
                  mode="aspectFit"
                /><text>{{ classes.find((item) => item.id === classId)?.name || '全部负责班级' }}</text></view
              ><view
                class="pbl-filter__arrow"
                aria-hidden="true"
            /></view>
          </picker>
        </template>
      </TeacherPblClassrooms>
    </view>
  </TeacherPageFrame>
</template>
<script setup lang="ts">
import { useTeacherScreenNextTick } from '../../../components/teacher/teacherScreenContext'
import { computed, ref, watch } from 'vue'
import {
  useTeacherScreenLoad as onLoad,
  useTeacherScreenShow as onShow,
} from '../../../components/teacher/teacherScreenContext'
import TeacherPageFrame from '@/components/teacher/TeacherPageFrame.vue'
import TeacherPblClassrooms from '@/features/pbl/presentation/TeacherPblClassrooms.vue'
import MedState from '@/components/ui/MedState.vue'
import { useTeacherRootScope } from '@/components/teacher/useTeacherRootScope'
import { getSession } from '@/features/identity/public'
import { readTeacherPblPreference, saveTeacherPblPreference } from '@/platform/navigation/teacherPreferences'
import { goDetail, goReplace, ROUTES } from '@/platform/navigation'
import { parseTeacherWorkspaceTarget, relaunchToTeacherWorkspace } from '@/platform/navigation/teacher'

const nextTick = useTeacherScreenNextTick()
const {
  classes,
  classId,
  error,
  accessDenied,
  identityGeneration,
  scopeAllowed,
  setInitialClass,
  selectClass,
  refreshScope,
} = useTeacherRootScope('pbl')
const workspace = ref<{ refresh(): Promise<void> }>()
const sessionId = ref<number | string>()
let redirecting = false
let preferenceIdentity: string | undefined
let initialTarget: Extract<ReturnType<typeof parseTeacherWorkspaceTarget>, { workspace: 'pbl' }> | undefined
const classOptions = computed(() => [{ id: undefined, name: '全部负责班级' }, ...classes.value])
function changeClass(event: { detail: { value: string } }) {
  sessionId.value = undefined
  selectClass(classOptions.value[Number(event.detail.value)]?.id)
}
onLoad((query) => {
  const target = parseTeacherWorkspaceTarget({ ...query, tab: 'pbl' })
  if (target.workspace !== 'pbl') {
    relaunchToTeacherWorkspace(target)
    return
  }
  if (target.section === 'diagnostics') {
    redirecting = true
    goReplace(ROUTES.teacherTestQueue, {
      classId: target.classId,
      sessionId: target.sessionId,
      reviewKind: target.reviewKind,
    })
    return
  }
  setInitialClass(target.classId)
  sessionId.value = target.sessionId
  initialTarget = { ...target, section: query?.section ? target.section : undefined }
})
async function refresh() {
  if (redirecting) return
  const actor = getSession()
  if (actor?.role === 'teacher' && actor.openid !== preferenceIdentity) {
    preferenceIdentity = actor.openid
    const saved = readTeacherPblPreference(actor.openid)
    sessionId.value = initialTarget?.sessionId ?? (saved?.section === 'diagnostics' ? undefined : saved?.sessionId)
    initialTarget = undefined
  }
  if (!(await refreshScope())) return
  if (classId.value === undefined && classes.value.length === 1) selectClass(classes.value[0].id)
  await nextTick()
  await workspace.value?.refresh()
}
onShow(refresh)
watch(sessionId, () => {
  if (!preferenceIdentity || getSession()?.openid !== preferenceIdentity || getSession()?.role !== 'teacher') return
  saveTeacherPblPreference(preferenceIdentity, {
    section: 'classrooms',
    sessionId: sessionId.value,
  })
})
function openDiagnostic(snapshotId: string) {
  goDetail(ROUTES.teacherPblDiagnosticDetail, {
    snapshotId,
    classId: classId.value,
    sessionId: sessionId.value,
    returnTab: 'pbl',
    returnSection: 'classrooms',
  })
}
function openFinalTest(finalTestId: string) {
  goDetail(ROUTES.teacherLearningFinalTest, {
    finalTestId,
    classId: classId.value,
    sessionId: sessionId.value,
    returnTab: 'pbl',
    returnSection: 'classrooms',
  })
}
function openInsights(context: { classId: string; sessionId: string }) {
  const target = parseTeacherWorkspaceTarget({ tab: 'insights', panel: 'progress', ...context })
  if (target.workspace === 'insights') relaunchToTeacherWorkspace(target)
}
</script>
<style scoped>
.pbl-hero {
  flex-shrink: 0;
  position: relative;
  margin: 0 -24rpx 14rpx;
  min-height: 210rpx;
  padding: 32rpx 34rpx 24rpx;
  box-sizing: border-box;
  overflow: hidden;
}
.pbl-hero__art {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
.pbl-hero__title {
  position: relative;
  display: block;
  color: #080b63;
  font-size: 56rpx;
  font-weight: 750;
  line-height: 1.3;
}
.pbl-hero__description {
  position: relative;
  display: block;
  margin-top: 12rpx;
  width: 70%;
  color: #657da9;
  font-size: 22rpx;
  line-height: 1.55;
}
.pbl-root {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
.pbl-filter {
  min-height: 60rpx;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8rpx;
  padding: 8rpx 16rpx;
  border: 1rpx solid #cbe0ff;
  border-radius: 12rpx;
  background: #ffffffed;
  color: #080b63;
  font-size: 24rpx;
  font-weight: 600;
  line-height: 1.4;
}
.pbl-filter__value {
  display: flex;
  min-width: 0;
  gap: 10rpx;
  align-items: center;
}
.pbl-filter__icon {
  flex: none;
  width: 34rpx;
  height: 34rpx;
}
.pbl-filter__arrow {
  flex: none;
  width: 10rpx;
  height: 10rpx;
  margin-right: 4rpx;
  border-right: 3rpx solid #8494ba;
  border-bottom: 3rpx solid #8494ba;
  transform: translateY(-3rpx) rotate(45deg);
}
</style>
