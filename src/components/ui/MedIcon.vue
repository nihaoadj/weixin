<template>
  <image
    class="med-icon"
    :class="`med-icon--${size}`"
    :src="`/static/icons/${name}.svg`"
    mode="aspectFit"
  />
</template>

<script setup lang="ts">
defineProps<{
  name: 'brand' | 'student' | 'teacher' | 'chat' | 'history' | 'book' | 'report' | 'send' | 'copy' | 'retry'
  size?: 'sm' | 'md' | 'lg'
}>()
</script>

<style scoped>
.med-icon {
  display: block;
  width: 40rpx;
  height: 40rpx;
}
.med-icon--sm {
  width: 30rpx;
  height: 30rpx;
}
.med-icon--lg {
  width: 58rpx;
  height: 58rpx;
}
</style>
