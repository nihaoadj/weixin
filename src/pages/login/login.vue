<template>
  <view class="safe-page login-page">
    <view class="login-shell">
      <view class="hero">
        <view class="brand-lockup">
          <view class="logo"
            ><MedIcon
              name="brand"
              size="md"
          /></view>
          <view class="brand-copy">
            <text class="brand-kicker">医学带教工具</text>
            <text class="brand-note">记录学习过程，连接学生与教师</text>
          </view>
        </view>
        <text class="title">临床思维学习助手</text>
        <text class="subtitle">从一个病例问题开始，完成推理、反馈与复盘。</text>
        <view
          class="loop-note"
          aria-label="学习闭环：提问、临床推理、教师反馈"
        >
          <text class="loop-label">学习闭环</text>
          <view class="loop-flow">
            <text>提问</text><text aria-hidden="true">→</text><text>临床推理</text><text aria-hidden="true">→</text
            ><text>教师反馈</text>
          </view>
          <text class="loop-description">每次练习都会留下可回看、可批阅的思维记录。</text>
        </view>
      </view>
      <view class="role-panel card">
        <view class="panel-heading">
          <text class="panel-title">选择身份</text>
          <text class="panel-description">进入对应的学习或教学工作区</text>
        </view>
        <button
          :tabindex="Boolean(loadingRole) ? -1 : 0"
          role="button"
          class="role-button student"
          :loading="loadingRole === 'student'"
          :disabled="Boolean(loadingRole)"
          @keydown="activateButtonOnKey"
          @click="login('student')"
        >
          <view class="role-icon"><MedIcon name="student" /></view>
          <view class="role-copy"
            ><text class="role-title">学生</text><text class="role-desc">医学问答、病例训练与学习报告</text></view
          >
          <text class="arrow">›</text>
        </button>
        <button
          :tabindex="Boolean(loadingRole) ? -1 : 0"
          role="button"
          class="role-button teacher"
          :loading="loadingRole === 'teacher'"
          :disabled="Boolean(loadingRole)"
          @keydown="activateButtonOnKey"
          @click="login('teacher')"
        >
          <view class="role-icon"><MedIcon name="teacher" /></view>
          <view class="role-copy"
            ><text class="role-title">教师</text><text class="role-desc">报告批阅、教学内容与学情分析</text></view
          >
          <text class="arrow">›</text>
        </button>
        <text class="notice">当前为试点身份入口。医学内容仅用于教学辅助，不构成诊断或治疗建议。</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { activateButtonOnKey } from '@/components/ui/keyboard'
import { ref } from 'vue'
import MedIcon from '@/components/ui/MedIcon.vue'
import {
  isApiRuntime,
  isWechatMiniProgram,
  saveSession,
  syncDemoLoginWithBackend,
  syncWechatLoginWithBackend,
} from '@/features/identity/public'
import { relaunchForRole } from '@/platform/navigation'
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
    if (isApiRuntime() && isWechatMiniProgram()) {
      // 教师身份校验在 remoteAuth 内、写入 token 之前完成，
      // 失败时既不落新 token 也不污染本地 session。
      sessionUser = await syncWechatLoginWithBackend({ requestedRole: role, nickName, avatarUrl })
    } else {
      permissions = (await syncDemoLoginWithBackend({ role, openid, nickName, avatarUrl })) || permissions
    }
  } catch (error) {
    console.error('同步后端登录失败', error)
    if (isApiRuntime()) {
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
  display: flex;
  padding: 48rpx 32rpx;
  align-items: flex-start;
  justify-content: center;
  background: var(--med-paper);
}
.login-shell {
  width: 100%;
  max-width: 960px;
}
.hero {
  display: flex;
  width: 100%;
  flex-direction: column;
  align-items: flex-start;
  margin: 24rpx 0 40rpx;
}
.logo {
  display: flex;
  width: 88rpx;
  height: 88rpx;
  align-items: center;
  justify-content: center;
  border-radius: var(--med-radius-md);
  background: var(--med-brand-soft);
  border: 1rpx solid var(--med-border);
}
.brand-lockup {
  display: flex;
  align-items: center;
}
.brand-copy {
  display: flex;
  margin-left: 20rpx;
  flex-direction: column;
}
.brand-kicker {
  color: var(--med-ink);
  font-size: 26rpx;
  font-weight: 700;
}
.brand-note {
  margin-top: 5rpx;
  color: var(--med-muted);
  font-size: 22rpx;
}
.title {
  margin-top: 48rpx;
  color: var(--med-navy);
  font-size: 50rpx;
  font-weight: 800;
  line-height: 1.28;
}
.subtitle {
  max-width: 600rpx;
  margin-top: 16rpx;
  color: var(--med-text-secondary);
  font-size: 28rpx;
  line-height: 1.6;
}
.loop-note {
  display: flex;
  width: 100%;
  max-width: 640rpx;
  margin-top: 40rpx;
  padding: 26rpx 28rpx;
  box-sizing: border-box;
  flex-direction: column;
  background: var(--med-surface);
  border-left: 2rpx solid var(--med-border);
}
.loop-label {
  color: var(--med-clinical);
  font-size: 22rpx;
  font-weight: 700;
}
.loop-flow {
  display: flex;
  margin-top: 12rpx;
  align-items: center;
  flex-wrap: wrap;
  gap: 12rpx;
  color: var(--med-ink);
  font-size: 28rpx;
  font-weight: 700;
}
.loop-flow text:nth-child(even) {
  color: var(--med-clinical);
}
.loop-description {
  margin-top: 12rpx;
  color: var(--med-muted);
  font-size: 24rpx;
  line-height: 1.55;
}
.role-panel {
  width: 100%;
  margin: 0 auto;
  padding: 34rpx 28rpx 28rpx;
  box-sizing: border-box;
}
.panel-heading {
  display: flex;
  margin-bottom: 26rpx;
  flex-direction: column;
}
.panel-title {
  font-size: 32rpx;
  font-weight: 750;
}
.panel-description {
  margin-top: 6rpx;
  color: var(--med-muted);
  font-size: 23rpx;
}
.role-button {
  display: flex;
  width: 100%;
  min-height: 128rpx;
  margin: 16rpx 0;
  padding: 18rpx 24rpx;
  align-items: center;
  text-align: left;
  border-radius: var(--med-radius-md);
  color: var(--med-ink);
  background: var(--med-surface);
  border: 1rpx solid var(--med-border);
  line-height: 1.2;
}
.role-button:active {
  background: var(--med-brand-soft);
}
.role-icon {
  display: flex;
  width: 76rpx;
  height: 76rpx;
  margin-right: 24rpx;
  align-items: center;
  justify-content: center;
  background: var(--med-brand-soft);
  border-radius: var(--med-radius-md);
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
  color: var(--med-text-secondary);
  font-size: 24rpx;
}
.arrow {
  color: var(--med-brand);
  font-size: 56rpx;
}
.notice {
  display: block;
  margin-top: 24rpx;
  color: var(--med-muted);
  font-size: 22rpx;
  line-height: 1.6;
}
@media screen and (max-width: 360px) {
  .brand-kicker {
    font-size: 14px;
  }

  .brand-note,
  .panel-description,
  .role-desc,
  .loop-description {
    font-size: 12px;
  }

  .subtitle {
    font-size: 14px;
  }

  .loop-label,
  .notice {
    font-size: 11px;
  }

  .loop-flow {
    font-size: 15px;
  }
}
@media screen and (min-width: 600px) and (max-width: 899px) {
  .login-page {
    padding: 36px;
  }

  .login-shell {
    max-width: 640px;
  }

  .hero {
    margin: 12px 0 28px;
  }

  .logo {
    width: 56px;
    height: 56px;
  }

  .brand-copy {
    margin-left: 16px;
  }

  .brand-kicker {
    font-size: 18px;
  }

  .brand-note,
  .panel-description,
  .role-desc,
  .loop-description {
    font-size: 14px;
  }

  .title {
    margin-top: 36px;
    font-size: 36px;
  }

  .subtitle {
    margin-top: 12px;
    font-size: 17px;
  }

  .loop-note {
    max-width: none;
    margin-top: 28px;
    padding: 20px 24px;
  }

  .loop-label {
    font-size: 13px;
  }

  .loop-flow {
    font-size: 18px;
  }

  .role-panel {
    padding: 28px;
  }

  .panel-title {
    font-size: 22px;
  }

  .role-button {
    min-height: 84px;
    margin: 12px 0;
    padding: 14px 18px;
  }

  .role-icon {
    width: 52px;
    height: 52px;
    margin-right: 16px;
  }

  .role-title {
    font-size: 19px;
  }

  .notice {
    font-size: 12px;
  }
}
@media screen and (min-width: 900px) {
  .login-page {
    padding: 72px 56px;
    align-items: center;
  }

  .login-shell {
    display: grid;
    max-width: 1040px;
    grid-template-columns: minmax(0, 1.05fr) minmax(440px, 0.95fr);
    align-items: center;
    gap: 88px;
  }

  .hero {
    margin: 0;
  }

  .logo {
    width: 56px;
    height: 56px;
    border-radius: 14px;
  }

  .brand-copy {
    margin-left: 16px;
  }

  .brand-kicker {
    font-size: 18px;
  }

  .brand-note {
    margin-top: 4px;
    font-size: 14px;
  }

  .title {
    max-width: 520px;
    margin-top: 44px;
    font-size: 42px;
    line-height: 1.18;
    text-wrap: balance;
  }

  .subtitle {
    max-width: 520px;
    margin-top: 16px;
    font-size: 18px;
  }

  .loop-note {
    max-width: 520px;
    margin-top: 34px;
    padding: 24px 28px;
    border-left-width: 4px;
  }

  .loop-label,
  .loop-description,
  .panel-description,
  .role-desc {
    font-size: 14px;
  }

  .loop-flow {
    margin-top: 10px;
    gap: 10px;
    font-size: 19px;
  }

  .loop-description {
    margin-top: 10px;
  }

  .role-panel {
    margin: 0;
    padding: 32px;
    border-radius: 18px;
  }

  .panel-heading {
    margin-bottom: 22px;
  }

  .panel-title {
    font-size: 24px;
  }

  .role-button {
    min-height: 92px;
    margin: 14px 0;
    padding: 16px 20px;
    border-radius: 14px;
  }

  .role-icon {
    width: 56px;
    height: 56px;
    margin-right: 18px;
    border-radius: 12px;
  }

  .role-title {
    font-size: 20px;
  }

  .role-desc {
    margin-top: 6px;
  }

  .arrow {
    font-size: 38px;
  }

  .notice {
    margin-top: 20px;
    font-size: 13px;
  }
}
</style>
