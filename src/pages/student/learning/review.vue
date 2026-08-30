<template>
  <view class="safe-page page"
    ><view class="card panel"
      ><text class="eyebrow-label">REFLECTION</text><text class="title">训练复盘</text
      ><text class="muted">正式能力变化与练习掌握度分开显示。</text
      ><view
        v-for="item in profile.formalDimensions"
        :key="String(item.dimension_id)"
        class="row"
        ><text>{{ item.label || item.dimension_id }}</text
        ><text>{{ item.score || 0 }}</text></view
      ></view
    ><view class="card panel"
      ><text class="section-title">微训练掌握度</text
      ><view
        v-for="(item, key) in profile.practiceMastery"
        :key="key"
        class="row"
        ><text>{{ key }}</text
        ><text>{{ item.averageScore }} 分 · {{ item.attemptCount }} 次</text></view
      ><text
        v-if="!Object.keys(profile.practiceMastery).length"
        class="muted"
        >完成微训练后显示掌握度。</text
      ><button
        class="secondary"
        @click="back"
      >
        返回学习首页
      </button></view
    ></view
  >
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { requireRole } from '@/services/auth'
import { backOrHome } from '@/services/navigation'
import { getLearningProfile } from '@/services/personalizedLearning'
import type { LearningProfile } from '@/types/learning'
const profile = ref<LearningProfile>({
  formalDimensions: [],
  recentAssessments: [],
  practiceMastery: {},
  unreadCount: 0,
})
function back() {
  backOrHome('student')
}
onLoad(async () => {
  if (!requireRole('student')) return
  profile.value = await getLearningProfile()
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
.section-title {
  font-size: 29rpx;
  font-weight: 750;
}
.muted {
  color: #718096;
  font-size: 23rpx;
}
.row {
  display: flex;
  padding: 16rpx 0;
  justify-content: space-between;
  border-bottom: 1rpx solid #e5edf0;
}
.secondary {
  color: #087f8c;
  background: #e6f7f5;
}
</style>
