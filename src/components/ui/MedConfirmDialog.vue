<template>
  <view
    class="confirm-backdrop"
    role="presentation"
  >
    <view
      class="confirm-card"
      role="dialog"
      aria-modal="true"
      :aria-label="title"
    >
      <text class="confirm-title">{{ title }}</text>
      <text class="confirm-message">{{ message }}</text>
      <view class="confirm-actions">
        <button
          class="confirm-cancel"
          @click="$emit('cancel')"
        >
          {{ cancelText }}
        </button>
        <button
          :id="confirmId"
          class="confirm-accept"
          @click="$emit('confirm')"
        >
          {{ confirmText }}
        </button>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  message: string
  confirmText: string
  cancelText: string
  confirmId: string
}>()
defineEmits<{ cancel: []; confirm: [] }>()
</script>

<style scoped>
.confirm-backdrop {
  position: fixed;
  z-index: 1000;
  display: flex;
  box-sizing: border-box;
  padding: 24rpx;
  justify-content: center;
  align-items: center;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  background: rgba(14, 30, 49, 0.58);
}
.confirm-card {
  box-sizing: border-box;
  width: 100%;
  max-width: 640rpx;
  padding: 36rpx 32rpx 28rpx;
  background: #fff;
  border-radius: 20rpx;
  box-shadow: 0 16rpx 48rpx rgba(16, 41, 68, 0.18);
}
.confirm-title,
.confirm-message {
  display: block;
}
.confirm-title {
  color: #173052;
  font-size: 32rpx;
  font-weight: 700;
}
.confirm-message {
  margin-top: 18rpx;
  color: #526980;
  font-size: 26rpx;
  line-height: 1.55;
}
.confirm-actions {
  display: flex;
  gap: 16rpx;
  margin-top: 32rpx;
}
.confirm-actions button {
  flex: 1;
  min-width: 0;
  min-height: 80rpx;
  margin: 0;
  border-radius: 12rpx;
  font-size: 25rpx;
  font-weight: 700;
}
.confirm-cancel {
  color: #526980;
  background: #edf2f5;
}
.confirm-accept {
  color: #fff;
  background: #078d9b;
}
</style>
