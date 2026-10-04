<template>
  <view class="source-view-page">
    <view
      v-if="loading"
      class="source-view-state"
      >正在打开资料…</view
    >
    <view
      v-else-if="error"
      class="source-view-state source-view-error"
      role="alert"
    >
      <text>{{ error }}</text>
      <button
        class="source-view-back"
        @click="returnToNode"
      >
        返回学习节点
      </button>
    </view>
    <web-view
      v-else-if="sourceUrl"
      :src="sourceUrl"
      @error="handleSourceError"
    />
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onBackPress, onLoad, onShow } from '@dcloudio/uni-app'
import { getKnowledgeMap } from '@/features/learning/public'
import { requireRole } from '@/features/identity/public'
import { backOrRoute, handleBackPress, ROUTES } from '@/platform/navigation'

const pointCode = ref('')
const sourceKey = ref('')
const sourceUrl = ref('')
const loading = ref(false)
const error = ref('')

function isSafeHttpsUrl(value: string): boolean {
  return /^https:\/\/[a-z0-9.-]+(?::\d+)?(?:[/?#]|$)/i.test(value) && !/\s/.test(value)
}

async function loadSource() {
  if (!pointCode.value || !sourceKey.value || loading.value) return
  loading.value = true
  error.value = ''
  sourceUrl.value = ''
  try {
    const points = await getKnowledgeMap()
    const point = points.find((item) => item.code === pointCode.value)
    const source = point?.sources.find((item) => item.sourceKey === sourceKey.value)
    if (!source) {
      error.value = '未找到这份学习资料。'
      return
    }
    if (!isSafeHttpsUrl(source.url)) {
      error.value = '这份资料的链接暂时无法安全打开。'
      return
    }
    sourceUrl.value = source.url
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '资料打开失败，请稍后重试。'
  } finally {
    loading.value = false
  }
}

function handleSourceError() {
  const failedUrl = sourceUrl.value
  sourceUrl.value = ''
  error.value = '原文暂时无法在小程序内打开。'
  if (!failedUrl) return
  uni.setClipboardData({
    data: failedUrl,
    success: () => {
      error.value = '原文暂时无法在小程序内打开，链接已复制，可在浏览器中粘贴访问。'
    },
  })
}

function returnToNode() {
  backOrRoute(ROUTES.studentKnowledgeNode, { topicCode: pointCode.value })
}

onLoad((options) => {
  pointCode.value = typeof options?.pointCode === 'string' ? options.pointCode : ''
  sourceKey.value = typeof options?.sourceKey === 'string' ? options.sourceKey : ''
  if (!pointCode.value || !sourceKey.value) error.value = '缺少学习资料参数。'
})
onShow(() => {
  if (requireRole('student')) void loadSource()
})
onBackPress(({ from }) => handleBackPress(from, ROUTES.studentKnowledgeNode, { topicCode: pointCode.value }))
</script>

<style scoped>
.source-view-page {
  min-height: 100vh;
  background: #f2f9ff;
}
.source-view-state {
  display: flex;
  min-height: 72vh;
  box-sizing: border-box;
  padding: 40rpx 32rpx;
  align-items: center;
  justify-content: center;
  color: #5874a3;
  font-size: 26rpx;
  line-height: 1.55;
  text-align: center;
}
.source-view-error {
  flex-direction: column;
  gap: 24rpx;
  color: #9b2d49;
}
.source-view-back {
  min-height: 80rpx;
  margin: 0;
  padding: 0 28rpx;
  color: #087ccf;
  background: #fff;
  border: 1rpx solid #d8eaf8;
  border-radius: 18rpx;
  font-size: 24rpx;
}
</style>
