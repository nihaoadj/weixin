<template>
  <image
    class="med-icon"
    :class="`med-icon--${size}`"
    :src="`/static/icons/${name}.svg`"
    alt=""
    aria-hidden="true"
    mode="aspectFit"
  />
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    name:
      'brand' | 'student' | 'teacher' | 'chat' | 'history' | 'book' | 'report' | 'send' | 'copy' | 'retry' | 'classroom'
    size?: 'sm' | 'md' | 'lg'
  }>(),
  { size: 'md' },
)
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
.med-icon--md {
  width: 40rpx;
  height: 40rpx;
}
.med-icon--lg {
  width: 58rpx;
  height: 58rpx;
}
@media screen and (min-width: 600px) and (max-width: 899px) {
  .med-icon--sm {
    width: 20px;
    height: 20px;
  }

  .med-icon--md {
    width: 26px;
    height: 26px;
  }

  .med-icon--lg {
    width: 36px;
    height: 36px;
  }
}
@media screen and (min-width: 900px) {
  .med-icon--sm {
    width: 18px;
    height: 18px;
  }

  .med-icon--md {
    width: 24px;
    height: 24px;
  }

  .med-icon--lg {
    width: 34px;
    height: 34px;
  }
}
</style>
