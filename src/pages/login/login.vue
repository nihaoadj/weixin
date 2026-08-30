<template>
  <view class="safe-page login-page">
    <view class="hero">
      <view class="brand-lockup">
        <view class="logo"
          ><MedIcon
            name="brand"
            size="lg"
        /></view>
        <text class="brand-kicker">MEDICAL LEARNING COPILOT</text>
      </view>
      <text class="title">临床思维学习助手</text>
      <text class="subtitle">循证提问 · 形成性评价 · 教师协作</text>
      <view class="trust-row"><text>教学场景</text><text>隐私友好</text><text>非临床诊疗</text></view>
    </view>
    <view class="role-panel card">
      <text class="panel-title">请选择您的身份</text>
      <button
        class="role-button student"
        :loading="loadingRole === 'student'"
        :disabled="Boolean(loadingRole)"
        @click="login('student')"
      >
        <view class="role-icon"><MedIcon name="student" /></view>
        <view class="role-copy"
          ><text class="role-title">学生</text><text class="role-desc">医学问答、练习与报告</text></view
        >
        <text class="arrow">›</text>
      </button>
      <button
        class="role-button teacher"
        :loading="loadingRole === 'teacher'"
        :disabled="Boolean(loadingRole)"
        @click="login('teacher')"
      >
        <view class="role-icon"><MedIcon name="teacher" /></view>
        <view class="role-copy"
          ><text class="role-title">教师</text><text class="role-desc">批阅报告与发布问题</text></view
        >
        <text class="arrow">›</text>
      </button>
      <text class="notice">当前为试点身份入口。医学内容用于教学辅助，不构成诊断或治疗建议。</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import MedIcon from '@/components/ui/MedIcon.vue'
import { isApiMode } from '@/config/runtime'
import { relaunchForRole } from '@/services/navigation'
import { saveSession } from '@/services/repository'
import { isWechatMiniProgram, syncDemoLoginWithBackend, syncWechatLoginWithBackend } from '@/services/remoteAuth'
import type { SessionUser, UserRole } from '@/types/domain'

const loadingRole = ref<UserRole | null>(null)

async function login(role: UserRole) {
  if (loadingRole.value) return
  loadingRole.value = role
  let nickName = role === 'student' ? '学生体验账号' : '教师体验账号'
  let avatarUrl = ''

  // #ifdef MP-WEIXIN
  try {
    const profile = await uni.getUserProfile({ desc: '用于展示学习账号信息', lang: 'zh_CN' })
    nickName = profile.userInfo.nickName || nickName
    avatarUrl = profile.userInfo.avatarUrl || ''
  } catch {
    uni.showToast({ title: '已使用体验身份进入', icon: 'none' })
  }
  // #endif

  const openid = role === 'student' ? 'demo_student' : 'demo_teacher'
  let permissions: string[] = []
  let sessionUser: SessionUser | undefined
  try {
    if (isApiMode() && isWechatMiniProgram()) {
      sessionUser = await syncWechatLoginWithBackend({ requestedRole: role, nickName, avatarUrl })
      if (role === 'teacher' && sessionUser.role !== 'teacher') {
        throw new Error('当前微信账号尚未开通教师身份')
      }
    } else {
      permissions = (await syncDemoLoginWithBackend({ role, openid, nickName, avatarUrl })) || permissions
    }
  } catch (error) {
    console.error('同步后端登录失败', error)
    if (isApiMode()) {
      uni.showToast({ title: error instanceof Error ? error.message : '后端登录失败', icon: 'none' })
      loadingRole.value = null
      return
    }
  }

  saveSession({
    openid: sessionUser?.openid || openid,
    role: sessionUser?.role || role,
    nickName: sessionUser?.nickName || nickName,
    avatarUrl: sessionUser?.avatarUrl || avatarUrl,
    classIds: sessionUser?.classIds || (role === 'student' ? ['demo_class_1'] : undefined),
    permissions: sessionUser?.permissions || permissions,
    createdAt: sessionUser?.createdAt || new Date().toISOString(),
  })
  const finalRole = sessionUser?.role || role
  relaunchForRole(finalRole)
  loadingRole.value = null
}
</script>

<style scoped>
.login-page {
  padding: 72rpx 36rpx 48rpx;
  background:
    radial-gradient(circle at 88% 4%, rgba(53, 183, 168, 0.2) 0, transparent 34%),
    linear-gradient(180deg, #eef8f7 0, #f4f8fa 45%);
}
.hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin: 42rpx 0 58rpx;
}
.logo {
  display: flex;
  width: 120rpx;
  height: 120rpx;
  align-items: center;
  justify-content: center;
  border-radius: 36rpx;
  background: #fff;
  border: 1rpx solid #d4e9e5;
  box-shadow: 0 22rpx 58rpx rgba(11, 93, 97, 0.18);
}
.brand-lockup {
  display: flex;
  align-items: center;
  flex-direction: column;
}
.brand-kicker {
  margin-top: 18rpx;
  color: #0f777b;
  font-size: 18rpx;
  font-weight: 700;
  letter-spacing: 3rpx;
}
.title {
  margin-top: 30rpx;
  color: #0b2239;
  font-size: 48rpx;
  font-weight: 800;
  letter-spacing: 2rpx;
}
.subtitle {
  margin-top: 12rpx;
  color: #637985;
}
.trust-row {
  display: flex;
  margin-top: 24rpx;
  gap: 12rpx;
}
.trust-row text {
  padding: 8rpx 14rpx;
  color: #3f626c;
  background: rgba(255, 255, 255, 0.78);
  border: 1rpx solid #d8e8ea;
  border-radius: 99rpx;
  font-size: 19rpx;
}
.role-panel {
  padding: 38rpx 30rpx 30rpx;
  backdrop-filter: blur(18rpx);
}
.panel-title {
  display: block;
  margin-bottom: 28rpx;
  font-size: 32rpx;
  font-weight: 650;
}
.role-button {
  display: flex;
  height: 142rpx;
  margin: 22rpx 0;
  padding: 0 28rpx;
  align-items: center;
  text-align: left;
  border-radius: 24rpx;
  color: #193246;
  border: 1rpx solid transparent;
  line-height: 1.2;
}
.role-button.student {
  background: #e9f7f5;
  border-color: #cce9e4;
}
.role-button.teacher {
  background: #edf3f8;
  border-color: #d8e3ed;
}
.role-icon {
  display: flex;
  width: 76rpx;
  height: 76rpx;
  margin-right: 24rpx;
  align-items: center;
  justify-content: center;
  background: #fff;
  border-radius: 22rpx;
}
.role-copy {
  display: flex;
  flex: 1;
  flex-direction: column;
}
.role-title {
  font-size: 32rpx;
  font-weight: 700;
}
.role-desc {
  margin-top: 8rpx;
  color: #64748b;
  font-size: 24rpx;
}
.arrow {
  color: #0f8b8d;
  font-size: 56rpx;
}
.notice {
  display: block;
  margin-top: 28rpx;
  color: #8795a8;
  font-size: 22rpx;
  line-height: 1.6;
}
</style>
