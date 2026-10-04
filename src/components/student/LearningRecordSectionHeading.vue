<template>
  <view class="section-heading">
    <view class="section-title-wrap">
      <text class="title-accent" />
      <text class="section-title">{{ title }}</text>
    </view>
    <text class="section-note">{{ note }}</text>
  </view>
</template>

<script setup lang="ts">
defineProps<{ title: string; note: string }>()
</script>

<style scoped>
.section-heading {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
}
.section-title-wrap {
  display: flex;
  align-items: center;
  gap: 12rpx;
}
.title-accent {
  width: 7rpx;
  height: 34rpx;
  flex: 0 0 7rpx;
  background: linear-gradient(180deg, #0a86ee, #24c8d7);
  border-radius: 99rpx;
}
.section-title {
  color: var(--med-ink);
  font-size: 30rpx;
  font-weight: 850;
  line-height: 1.35;
}
.section-note {
  color: #7185aa;
  font-size: 22rpx;
  line-height: 1.6;
}
</style>
