<template>
  <view class="safe-page pbl"
    ><text class="title">病理学 PBL 课堂</text><view v-if="loading">正在加载课堂…</view
    ><view
      v-else-if="error"
      role="alert"
      >{{ error }}</view
    ><view v-else-if="!session">当前没有活动课堂。</view
    ><template v-else
      ><text class="topic">{{ session.topicCode }}</text
      ><view
        v-for="item in messages"
        :key="item.content"
        class="message"
        >{{ item.content }}</view
      ><view
        v-if="diagnostic"
        class="analysis"
        ><text>{{ diagnostic.assistantReply }}</text
        ><text v-if="diagnostic.followUpQuestion">追问：{{ diagnostic.followUpQuestion }}</text
        ><text v-if="diagnostic.knowledgeGaps.length || diagnostic.reasoningIssues.length"
          >已形成的薄弱分析仅对你和任课教师可见。</text
        ></view
      ><textarea
        v-model="draft"
        aria-label="输入你的病理学问题"
        :maxlength="2000"
        placeholder="写下你的疑问和判断依据"
      /><button
        :disabled="sending || !draft.trim()"
        @click="send"
      >
        {{ sending ? '分析中…' : '提交讨论' }}
      </button></template
    ></view
  >
</template>
<script setup lang="ts">
import { onShow } from '@dcloudio/uni-app'
import { ref } from 'vue'
import {
  getActivePblSessions,
  getPblParticipation,
  sendPblMessage,
  type PblDiagnostic,
  type PblSession,
} from '@/features/pbl/public'
const loading = ref(true),
  sending = ref(false),
  error = ref(''),
  session = ref<PblSession>(),
  messages = ref<{ role: string; content: string }[]>([]),
  diagnostic = ref<PblDiagnostic>(),
  draft = ref('')
async function load() {
  loading.value = true
  error.value = ''
  try {
    session.value = (await getActivePblSessions())[0]
    if (session.value) {
      const value = await getPblParticipation(session.value.id)
      messages.value = value.messages
      diagnostic.value = value.diagnostic
    }
  } catch {
    error.value = '课堂加载失败，请稍后重试。'
  } finally {
    loading.value = false
  }
}
async function send() {
  if (!session.value || sending.value) return
  sending.value = true
  try {
    const content = draft.value.trim()
    messages.value.push({ role: 'student', content })
    draft.value = ''
    diagnostic.value = await sendPblMessage(session.value.id, content)
  } catch {
    error.value = '提交失败，未切换到演示数据。'
  } finally {
    sending.value = false
  }
}
onShow(load)
</script>
<style scoped>
.pbl {
  padding: 28rpx;
}
.title {
  display: block;
  font-size: 38rpx;
  font-weight: 800;
}
.topic,
.analysis,
.message {
  display: block;
  margin-top: 20rpx;
  padding: 20rpx;
  background: var(--med-surface);
  border-radius: var(--med-radius-sm);
}
textarea {
  width: 100%;
  min-height: 180rpx;
  margin-top: 20rpx;
  padding: 16rpx;
  box-sizing: border-box;
  background: var(--med-surface);
}
button {
  margin-top: 16rpx;
  color: #fff;
  background: var(--med-clinical);
}
</style>
