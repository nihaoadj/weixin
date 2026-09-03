<template>
  <view class="queue"
    ><text class="heading">PBL 诊断队列</text><view v-if="loading">加载中…</view
    ><view
      v-else-if="error"
      role="alert"
      >{{ error }}</view
    ><view v-else-if="!items.length">暂无可处理的诊断建议。</view
    ><view
      v-for="item in items"
      :key="item.assistantReply"
      class="card"
      ><text>{{ item.assistantReply }}</text
      ><text>薄弱项 {{ item.knowledgeGaps.length }}；推理问题 {{ item.reasoningIssues.length }}</text
      ><view
        v-for="suggestion in item.recommendedQuestions"
        :key="suggestion.id"
        ><input
          v-model="suggestion.title"
          aria-label="建议题标题"
        /><textarea
          v-model="suggestion.prompt"
          aria-label="建议题内容"
        /><button @click="save(suggestion)">保存</button><button @click="publish(suggestion)">采用并发布</button></view
      ></view
    ></view
  >
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  adoptPblSuggestion,
  editPblSuggestion,
  getTeacherPblDiagnostics,
  type PblDiagnostic,
  type PblSuggestion,
} from '@/features/pbl/public'
const items = ref<PblDiagnostic[]>([]),
  loading = ref(true),
  error = ref('')
async function refresh() {
  loading.value = true
  try {
    items.value = await getTeacherPblDiagnostics()
  } catch {
    error.value = '队列加载失败，请重试。'
  } finally {
    loading.value = false
  }
}
async function save(item: PblSuggestion) {
  await editPblSuggestion(item)
}
async function publish(item: PblSuggestion) {
  await adoptPblSuggestion(item.id)
  await refresh()
}
onMounted(refresh)
defineExpose({ refresh })
</script>
<style scoped>
.heading {
  display: block;
  margin: 24rpx 0;
  font-size: 34rpx;
  font-weight: 800;
}
.card {
  margin-bottom: 20rpx;
  padding: 20rpx;
  background: var(--med-surface);
  border-radius: var(--med-radius-sm);
}
input,
textarea {
  width: 100%;
  margin-top: 12rpx;
  padding: 12rpx;
  box-sizing: border-box;
  border: 1rpx solid var(--med-border);
}
button {
  margin: 12rpx 12rpx 0 0;
}
</style>
