<template>
  <view class="safe-page login-page">
    <view class="login-shell">
      <view class="hero">
        <view class="hero-stage">
          <image
            class="hero-scene"
            :src="'/static/login-pathology-illustration-spaced.svg'"
            mode="scaleToFill"
            aria-hidden="true"
          />
          <view class="brand-lockup">
            <view class="logo">
              <image
                :src="'/static/login-brand-mark.svg'"
                mode="aspectFit"
                aria-hidden="true"
              />
            </view>
            <view class="brand-copy">
              <text class="brand-kicker">病理学 PBL 学习助手</text>
              <text class="brand-note">支持学生研讨、学习与教师教学</text>
            </view>
          </view>
          <view
            class="hero-quote"
            aria-hidden="true"
          >
            <text>以问题为起点，</text>
            <text>在思考中成长</text>
          </view>
          <text class="hero-tagline">AI 助力医学教育，让学习更高效、更深入</text>
        </view>
        <text class="title">病理学 PBL 学习助手</text>
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
          <view
            class="loop-decoration"
            aria-hidden="true"
            ><MedIcon
              name="report"
              size="lg"
          /></view>
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
            ><text class="role-title">学生</text><text class="role-desc">医学问答、病例训练与学习记录</text></view
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
            ><text class="role-title">教师</text><text class="role-desc">诊断审阅、教学内容与学情分析</text></view
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
  --login-ink: #102960;
  --login-text: #445f90;
  --login-muted: #627aa6;
  --login-blue: #167fe1;
  --login-teal: #0a929d;
  --login-border: #bfdcf5;
  display: flex;
  min-height: 100vh;
  padding: 0 0 calc(48rpx + env(safe-area-inset-bottom));
  justify-content: center;
  background: linear-gradient(180deg, #f5fbff 0%, #f8fcff 72%, #eef8ff 100%);
  color: var(--login-ink);
}
.login-shell {
  width: 100%;
  max-width: 750px;
}
.hero {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}
.hero-stage {
  position: relative;
  width: 100%;
  height: 350rpx;
  overflow: hidden;
  background: #e7f5ff;
}
.hero-scene {
  position: absolute;
  width: 100%;
  height: 100%;
  inset: 0;
}
.brand-lockup {
  position: relative;
  z-index: 1;
  display: flex;
  margin: 42rpx 36rpx 0;
  align-items: center;
  gap: 18rpx;
}
.logo,
.logo image {
  display: block;
  width: 84rpx;
  height: 84rpx;
}
.brand-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
}
.brand-kicker {
  color: var(--login-ink);
  font-size: 26rpx;
  font-weight: 800;
  line-height: 1.35;
}
.brand-note {
  margin-top: 5rpx;
  color: var(--login-text);
  font-size: 21rpx;
  line-height: 1.4;
}
.hero-quote {
  position: relative;
  z-index: 1;
  display: flex;
  width: 69%;
  margin: 6rpx 0 0 38rpx;
  flex-direction: column;
  color: #1872d3;
  font-family: 'STKaiti', 'KaiTi', 'Kaiti SC', serif;
  font-size: 60rpx;
  font-style: italic;
  font-weight: 600;
  letter-spacing: 2rpx;
  line-height: 1.2;
  text-shadow: 0 2rpx 4rpx rgba(255, 255, 255, 0.68);
  transform: rotate(-3deg);
}
.hero-quote text + text {
  margin-left: 36rpx;
}
.hero-tagline {
  position: absolute;
  z-index: 1;
  right: 20rpx;
  bottom: 24rpx;
  left: 38rpx;
  color: #536c9f;
  font-size: 23rpx;
  letter-spacing: 1rpx;
  line-height: 1.4;
}
.title {
  display: block;
  margin: 34rpx 38rpx 0;
  color: var(--login-ink);
  font-size: 53rpx;
  font-weight: 800;
  letter-spacing: 1rpx;
  line-height: 1.25;
}
.subtitle {
  display: block;
  margin: 12rpx 38rpx 0;
  color: var(--login-text);
  font-size: 27rpx;
  line-height: 1.55;
}
.loop-note {
  position: relative;
  display: flex;
  width: calc(100% - 76rpx);
  min-height: 170rpx;
  margin: 34rpx 38rpx 0;
  padding: 26rpx 28rpx 25rpx 46rpx;
  box-sizing: border-box;
  overflow: hidden;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.86);
  border: 1rpx solid #b8d9fa;
  border-radius: 20rpx;
  box-shadow: 0 10rpx 30rpx rgba(61, 141, 220, 0.08);
}
.loop-note::before,
.panel-heading::before {
  position: absolute;
  width: 7rpx;
  background: linear-gradient(180deg, #20d0dc, #1783e5);
  border-radius: 8rpx;
  content: '';
}
.loop-note::before {
  top: 28rpx;
  bottom: 28rpx;
  left: 22rpx;
}
.loop-label {
  color: var(--login-ink);
  font-size: 27rpx;
  font-weight: 800;
}
.loop-flow {
  display: flex;
  margin-top: 12rpx;
  flex-wrap: wrap;
  align-items: center;
  gap: 9rpx;
  color: var(--login-ink);
  font-size: 27rpx;
  font-weight: 750;
}
.loop-flow text:nth-child(even) {
  color: #168dd1;
}
.loop-description {
  margin-top: 9rpx;
  color: var(--login-text);
  font-size: 22rpx;
  line-height: 1.5;
}
.loop-decoration {
  position: absolute;
  right: 18rpx;
  bottom: 14rpx;
  display: flex;
  width: 84rpx;
  height: 84rpx;
  align-items: center;
  justify-content: center;
  background: #e8f6ff;
  border-radius: 18rpx;
  opacity: 0.56;
  transform: rotate(-9deg);
}
.role-panel.card {
  width: calc(100% - 76rpx);
  margin: 27rpx 38rpx 0;
  padding: 30rpx 22rpx 28rpx;
  box-sizing: border-box;
  background: rgba(255, 255, 255, 0.95);
  border: 1rpx solid var(--login-border);
  border-radius: 22rpx;
  box-shadow: 0 12rpx 34rpx rgba(61, 141, 220, 0.07);
}
.panel-heading {
  position: relative;
  display: flex;
  margin-bottom: 21rpx;
  padding-left: 28rpx;
  flex-direction: column;
}
.panel-heading::before {
  top: 2rpx;
  bottom: 4rpx;
  left: 1rpx;
}
.panel-title {
  color: var(--login-ink);
  font-size: 32rpx;
  font-weight: 800;
  line-height: 1.3;
}
.panel-description {
  margin-top: 6rpx;
  color: var(--login-muted);
  font-size: 22rpx;
  line-height: 1.4;
}
.role-button {
  display: flex;
  width: 100%;
  min-height: 116rpx;
  margin: 14rpx 0 0;
  padding: 14rpx 18rpx;
  align-items: center;
  text-align: left;
  color: var(--login-ink);
  background: linear-gradient(105deg, #f7fcff 0%, #fff 80%);
  border: 1rpx solid #bcdbf8;
  border-radius: 19rpx;
  line-height: 1.2;
  box-shadow: 0 4rpx 16rpx rgba(35, 124, 210, 0.035);
}
.role-button:active {
  background: #e7f5ff;
}
.role-icon {
  display: flex;
  width: 76rpx;
  height: 76rpx;
  margin-right: 20rpx;
  flex: none;
  align-items: center;
  justify-content: center;
  background: #e8f8fa;
  border-radius: 19rpx;
}
.role-icon .med-icon {
  width: 45rpx;
  height: 45rpx;
}
.role-button.teacher .role-icon {
  background: #e7f2ff;
}
.role-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
}
.role-title {
  color: var(--login-ink);
  font-size: 32rpx;
  font-weight: 750;
}
.role-desc {
  margin-top: 7rpx;
  color: var(--login-text);
  font-size: 22rpx;
  line-height: 1.3;
}
.arrow {
  margin-left: 8rpx;
  color: var(--login-blue);
  font-size: 54rpx;
  font-weight: 300;
  line-height: 1;
}
.notice {
  display: block;
  margin: 24rpx 1rpx 0;
  padding-top: 18rpx;
  color: var(--login-muted);
  border-top: 1rpx solid #e4f0fc;
  font-size: 21rpx;
  line-height: 1.55;
}
@media screen and (max-width: 360px) {
  .hero-quote {
    font-size: 51rpx;
  }
  .brand-note,
  .role-desc,
  .panel-description,
  .loop-description {
    font-size: 20rpx;
  }
  .loop-decoration {
    display: none;
  }
}
@media screen and (min-width: 600px) {
  .login-page {
    padding: 24px 24px 48px;
  }
  .login-shell {
    overflow: hidden;
    border: 1px solid #d7eafc;
    border-radius: 28px;
    box-shadow: 0 20px 60px rgba(30, 95, 159, 0.1);
  }
  .hero-stage {
    height: 330px;
  }
  .brand-lockup {
    margin: 34px 38px 0;
  }
  .logo,
  .logo image {
    width: 65px;
    height: 65px;
  }
  .brand-kicker {
    font-size: 21px;
  }
  .brand-note {
    font-size: 14px;
  }
  .hero-quote {
    margin: 28px 0 0 38px;
    font-size: 43px;
  }
  .hero-tagline {
    bottom: 35px;
    left: 40px;
    font-size: 16px;
  }
  .title {
    margin: 30px 38px 0;
    font-size: 35px;
  }
  .subtitle {
    margin: 10px 38px 0;
    font-size: 17px;
  }
  .loop-note {
    width: calc(100% - 76px);
    min-height: 125px;
    margin: 25px 38px 0;
    padding: 20px 28px 20px 45px;
  }
  .loop-note::before {
    width: 5px;
    top: 20px;
    bottom: 20px;
    left: 22px;
  }
  .loop-label,
  .loop-flow {
    font-size: 18px;
  }
  .loop-description {
    font-size: 14px;
  }
  .role-panel.card {
    width: calc(100% - 76px);
    margin: 24px 38px 38px;
    padding: 28px;
  }
  .panel-heading {
    padding-left: 22px;
  }
  .panel-heading::before {
    width: 5px;
  }
  .panel-title {
    font-size: 22px;
  }
  .panel-description,
  .role-desc {
    font-size: 14px;
  }
  .role-button {
    min-height: 84px;
    padding: 12px 16px;
  }
  .role-icon {
    width: 55px;
    height: 55px;
    margin-right: 16px;
  }
  .role-title {
    font-size: 21px;
  }
  .arrow {
    font-size: 38px;
  }
  .notice {
    font-size: 13px;
  }
}
</style>
