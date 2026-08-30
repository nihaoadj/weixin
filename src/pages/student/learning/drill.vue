<template>
  <view class="safe-page page">
    <view class="card panel"
      ><text class="eyebrow-label">MICRO DRILL</text><text class="title">{{ definition.title || '微训练' }}</text
      ><text class="muted">{{ definition.context }}</text
      ><text class="instruction">{{ definition.instruction }}</text></view
    >
    <view class="card panel">
      <textarea
        v-model="answer"
        :maxlength="1200"
        placeholder="写下你的证据、判断与安全边界"
        auto-height
      /><button
        class="primary"
        :disabled="saving || submitted"
        @click="submit"
      >
        {{ submitted ? '已提交' : saving ? '评分中…' : '提交答案' }}
      </button></view
    >
    <view
      v-if="result"
      class="card panel result"
      ><text class="score">{{ result.score }} 分</text><text>{{ result.feedback }}</text
      ><text class="muted">下一步：{{ result.nextStep }}</text
      ><text
        v-for="item in result.evidence"
        :key="item"
        class="evidence"
        >原文证据：{{ item }}</text
      ><button
        class="secondary"
        @click="back"
      >
        返回计划
      </button></view
    >
  </view>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { requireRole } from '@/services/auth'
import { backOrHome } from '@/services/navigation'
import { getLearningTaskAttempt, submitLearningTaskAttempt } from '@/services/personalizedLearning'
import type { LearningTaskAttempt } from '@/types/learning'
const answer = ref('')
const result = ref<LearningTaskAttempt>()
const saving = ref(false)
const submitted = ref(false)
const definition = ref({ title: '', context: '', instruction: '' })
let attemptId = 0
async function submit() {
  if (!answer.value.trim()) {
    uni.showToast({ title: '请先填写答案', icon: 'none' })
    return
  }
  saving.value = true
  try {
    result.value = await submitLearningTaskAttempt(attemptId, { text: answer.value.trim() })
    submitted.value = true
  } catch (e) {
    uni.showToast({ title: e instanceof Error ? e.message : '提交失败', icon: 'none' })
  } finally {
    saving.value = false
  }
}
function back() {
  backOrHome('student', 2)
}
onLoad(async (query) => {
  if (!requireRole('student')) return
  attemptId = Number(query?.attemptId || 0)
  try {
    const item = await getLearningTaskAttempt(attemptId)
    definition.value = item.publicDefinition as typeof definition.value
    if (item.status === 'assessed') {
      result.value = item
      submitted.value = true
      answer.value = String(item.answer.text || '')
    }
  } catch {
    /* start page will surface unavailable state */
  }
})
</script>
<style scoped>
.page {
  padding: 28rpx;
  background: #f4f8fa;
}
.panel {
  display: flex;
  margin-bottom: 22rpx;
  padding: 30rpx;
  flex-direction: column;
  gap: 16rpx;
}
.title {
  color: #0b2239;
  font-size: 38rpx;
  font-weight: 800;
}
.muted {
  color: #718096;
  font-size: 23rpx;
  line-height: 1.55;
}
.instruction {
  color: #0b2239;
  line-height: 1.6;
}
textarea {
  width: auto;
  min-height: 240rpx;
  padding: 20rpx;
  background: #f7fafc;
  border: 1rpx solid #dbe7eb;
  border-radius: 14rpx;
}
.primary {
  color: #fff;
  background: #087f8c;
}
.secondary {
  color: #087f8c;
  background: #e6f7f5;
}
.result {
  align-items: flex-start;
}
.score {
  color: #087f8c;
  font-size: 64rpx;
  font-weight: 800;
}
.evidence {
  padding: 12rpx;
  color: #31556a;
  background: #edf7f7;
  font-size: 22rpx;
}
</style>
