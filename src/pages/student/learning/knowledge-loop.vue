<template>
  <view class="safe-page compatibility-page">
    <text role="status">正在进入知识点学习…</text>
  </view>
</template>

<script setup lang="ts">
import { onLoad } from '@dcloudio/uni-app'
import { getSession, requireRole } from '@/features/identity/public'
import { getKnowledgeCatalog } from '@/features/learning/public'
import { goPrimary, goReplace, ROUTES } from '@/platform/navigation'

onLoad((options) => {
  if (!requireRole('student')) return
  const session = getSession()
  if (session?.role !== 'student' || !session.openid) return
  const requested =
    typeof options?.topicCode === 'string'
      ? [options.topicCode.trim()]
      : typeof options?.topicCodes === 'string'
        ? options.topicCodes.split(',').map((code) => code.trim())
        : []
  void openLearning(requested.filter(Boolean), session.openid)
})

async function openLearning(requested: string[], identity: string) {
  const isCurrentStudent = () => {
    const session = getSession()
    return session?.role === 'student' && session.openid === identity
  }
  if (!requested.length) {
    goPrimary(ROUTES.studentLearning)
    return
  }
  try {
    const catalog = await getKnowledgeCatalog()
    if (!isCurrentStudent()) return
    const code = requested.find((candidate) => catalog.some((point) => point.code === candidate))
    if (code) goReplace(ROUTES.studentKnowledgeNode, { topicCode: code })
    else goPrimary(ROUTES.studentLearning)
  } catch (reason) {
    if (!isCurrentStudent()) return
    uni.showToast({ title: reason instanceof Error ? reason.message : '知识目录暂不可用', icon: 'none' })
    goPrimary(ROUTES.studentLearning)
  }
}
</script>

<style scoped>
.compatibility-page {
  padding: 32rpx;
  color: var(--med-muted);
  background: var(--med-page);
}
</style>
