<template>
  <view
    class="detail-skeleton"
    role="status"
    aria-live="polite"
    aria-busy="true"
    :aria-label="label"
  >
    <text class="loading-label">{{ label }}</text>
    <view
      class="skeleton-header"
      aria-hidden="true"
    >
      <view class="skeleton-line skeleton-kicker" />
      <view class="skeleton-line skeleton-title" />
      <view class="skeleton-line skeleton-meta" />
    </view>
    <view
      v-for="section in 2"
      :key="section"
      class="skeleton-section"
      aria-hidden="true"
    >
      <view class="skeleton-line skeleton-heading" />
      <view class="skeleton-line" />
      <view class="skeleton-line" />
      <view class="skeleton-line skeleton-short" />
    </view>
  </view>
</template>

<script setup lang="ts">
defineProps<{ label: string }>()
</script>

<style scoped>
.detail-skeleton {
  padding: 8px 0;
}
.loading-label {
  color: var(--med-muted);
  font-size: 14px;
}
.skeleton-header {
  padding: 24px 0;
  border-bottom: 1px solid var(--med-border);
}
.skeleton-section {
  padding: 24px 0;
}
.skeleton-line {
  height: 12px;
  margin-bottom: 12px;
  background: var(--med-divider);
  border-radius: 2px;
}
.skeleton-kicker {
  width: 28%;
}
.skeleton-title {
  width: 72%;
  height: 28px;
  margin: 16px 0;
}
.skeleton-meta {
  width: 42%;
}
.skeleton-heading {
  width: 32%;
  height: 18px;
  margin-bottom: 20px;
}
.skeleton-short {
  width: 65%;
}
</style>
