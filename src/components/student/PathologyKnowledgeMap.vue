<template>
  <view class="knowledge"
    ><text class="title">病理学知识地图</text><text class="muted">围绕课堂目标巩固概念，再用病例核对理解。</text
    ><text
      v-if="error"
      role="alert"
      >{{ error }}</text
    >
    <view class="topics"
      ><button
        v-for="topic in topics"
        :key="topic.code"
        :class="{ selected: selected === topic.code }"
        @click="selected = topic.code"
      >
        {{ topic.title }}
      </button></view
    >
    <view class="points"
      ><view
        v-for="point in visible"
        :key="point.code"
        class="point"
        ><text class="subtitle">{{ point.title }}</text
        ><text class="muted">{{ point.objective }}</text
        ><text>{{ point.description }}</text
        ><text class="muted"
          >前置：{{ names(point.prerequisiteCodes) || '可直接开始' }}；相关：{{ names(point.relatedCodes) }}</text
        >
        <view class="links"
          ><button
            v-for="code in [...(point.prerequisiteCodes || []), ...(point.relatedCodes || [])]"
            :key="code"
            @click="selected = points.find((p) => p.code === code)?.systemCode || selected"
          >
            查看 {{ names([code]) }}
          </button></view
        >
        <button @click="goDetail(ROUTES.studentKnowledgeLoop, { topicCode: point.code })">巩固与自测</button>
      </view></view
    ><text class="muted">知识关系用于组织学习；浏览目录不改变掌握状态。{{ points[0]?.reference }}</text>
  </view>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getKnowledgeCatalog, type KnowledgePoint } from '@/features/learning/public'
import { goDetail, ROUTES } from '@/platform/navigation'
const points = ref<KnowledgePoint[]>([]),
  selected = ref('pathology.cell-injury'),
  error = ref('')
const topics = computed(() =>
    Array.from(new Map(points.value.map((p) => [p.systemCode, { code: p.systemCode, title: p.systemLabel }])).values()),
  ),
  visible = computed(() => points.value.filter((p) => p.systemCode === selected.value))
const names = (codes?: string[]) =>
  codes?.map((code) => points.value.find((p) => p.code === code)?.title ?? code).join('、')
onMounted(async () => {
  try {
    points.value = await getKnowledgeCatalog()
  } catch {
    error.value = '知识目录加载失败，请刷新页面。'
  }
})
</script>
<style scoped>
.knowledge {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
  margin-bottom: 30rpx;
}
.title {
  font-size: 36rpx;
  font-weight: 800;
}
.subtitle {
  font-size: 30rpx;
  font-weight: 700;
}
.muted {
  color: var(--med-muted);
  font-size: 25rpx;
  line-height: 1.6;
}
.topics,
.links {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
}
.points {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr));
  gap: 20rpx;
}
.point {
  padding: 24rpx;
  display: flex;
  flex-direction: column;
  gap: 16rpx;
  border-radius: 16rpx;
  background: var(--med-surface);
}
button {
  font-size: 25rpx;
  margin: 0;
  min-height: 44px;
}
.selected {
  color: white;
  background: var(--med-primary);
}
</style>
