<template>
  <TeacherPageFrame
    id="teacher-content-frame"
    active="content"
    reference-layout
    fixed-content
    title="内容"
    description="维护课堂病例与个人题库。"
  >
    <view class="content-page">
      <view class="content-hero">
        <image
          class="content-hero__wave"
          src="/static/content-reference-wave.svg"
          mode="scaleToFill"
          aria-hidden="true"
        />
        <image
          class="content-hero__art"
          src="/static/content-reference-hero.png"
          mode="aspectFit"
          aria-hidden="true"
        />
        <view class="content-hero__copy">
          <text
            class="content-hero__title"
            role="heading"
            aria-level="1"
            >教学资源</text
          >
          <text class="content-hero__description">维护病例与个人题库</text>
        </view>
      </view>
      <MedState
        v-if="accessDenied"
        variant="error"
        icon="history"
        title="教师身份已变化"
        description="请重新登录教师账号。"
      />
      <TeacherContentResources
        v-else
        id="teacher-content-resources"
        :key="identity"
        ref="resources"
        class="content-page__resources"
        :resource="resource"
        :keyword="keyword"
        @filters-change="saveFilters"
      />
    </view>
  </TeacherPageFrame>
</template>
<script setup lang="ts">
import { useTeacherScreenNextTick } from '../../../components/teacher/teacherScreenContext'
import { ref } from 'vue'
import {
  useTeacherScreenLoad as onLoad,
  useTeacherScreenShow as onShow,
} from '../../../components/teacher/teacherScreenContext'
import TeacherPageFrame from '@/components/teacher/TeacherPageFrame.vue'
import TeacherContentResources from '@/features/content/presentation/TeacherContentResources.vue'
import MedState from '@/components/ui/MedState.vue'
import { getSession, requireRole } from '@/features/identity/public'
import { parseTeacherWorkspaceTarget, type TeacherContentResource } from '@/platform/navigation/teacher'
import { readTeacherContentPreference, saveTeacherContentPreference } from '@/platform/navigation/teacherPreferences'

const nextTick = useTeacherScreenNextTick()
const resources = ref<{ refresh(): Promise<void> }>()
const accessDenied = ref(true)
const identity = ref('')
const resource = ref<TeacherContentResource>('cases')
const keyword = ref('')
let initializedIdentity = ''

function validResource(value: unknown): value is TeacherContentResource {
  return value === 'cases' || value === 'question-bank'
}
function initializeFilters(openid: string, query?: Record<string, unknown>) {
  const preference = readTeacherContentPreference(openid)
  const hasQueryResource = Boolean(query && (query.resource !== undefined || query.section !== undefined))
  const hasQueryKeyword = Boolean(query && query.keyword !== undefined)
  const parsed = parseTeacherWorkspaceTarget({ ...(query as Record<string, string | undefined>), tab: 'content' })
  const selectedResource =
    hasQueryResource && parsed.workspace === 'content' && validResource(parsed.resource)
      ? parsed.resource
      : preference?.resource || 'cases'
  resource.value = selectedResource
  keyword.value = hasQueryKeyword && parsed.workspace === 'content' ? parsed.keyword || '' : preference?.keyword || ''
  initializedIdentity = openid
}

onLoad((query) => {
  const user = getSession()
  if (user?.role === 'teacher') initializeFilters(user.openid, query as Record<string, unknown>)
})

function saveFilters(value: { resource: TeacherContentResource; keyword: string }) {
  resource.value = value.resource
  keyword.value = value.keyword
  if (identity.value) saveTeacherContentPreference(identity.value, value)
}

onShow(async () => {
  const user = getSession()
  if (!user || user.role !== 'teacher') {
    identity.value = ''
    accessDenied.value = true
    requireRole('teacher')
    return
  }
  if (initializedIdentity !== user.openid) initializeFilters(user.openid)
  identity.value = user.openid
  accessDenied.value = false
  await nextTick()
  if (getSession()?.openid === user.openid && getSession()?.role === 'teacher') await resources.value?.refresh()
})
</script>
<style scoped>
.content-page {
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  color: #101449;
  background: linear-gradient(110deg, #edfaff, #e9f8ff 65%, #effbff);
}
.content-page__resources {
  display: flex;
  flex: 1;
  width: 100%;
  min-height: 0;
  overflow: hidden;
}
.content-hero {
  flex: none;
  position: relative;
  height: 198rpx;
  overflow: hidden;
}
.content-hero__wave {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
.content-hero__art {
  position: absolute;
  top: 8rpx;
  right: 20rpx;
  width: 248rpx;
  height: 180rpx;
}
.content-hero__copy {
  position: relative;
  z-index: 1;
  width: 440rpx;
  padding: 48rpx 0 0 40rpx;
}
.content-hero__title {
  display: block;
  color: #0c1244;
  font-size: 52rpx;
  font-weight: 750;
  line-height: 1.2;
}
.content-hero__description {
  display: block;
  margin-top: 10rpx;
  color: #647daa;
  font-size: 29rpx;
  font-weight: 500;
  line-height: 1.4;
}
</style>
