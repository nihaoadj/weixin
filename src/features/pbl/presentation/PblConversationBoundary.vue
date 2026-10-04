<template>
  <view
    class="boundary"
    role="note"
    aria-label="正式研讨与私人续问分界"
  >
    <view class="boundary__line" />
    <view class="boundary__content">
      <text class="boundary__title">四阶段证据已冻结</text>
      <text class="boundary__text">从这里开始是私人续问，仅你自己可见，不提交教师，也不进入诊断或学习统计。</text>
    </view>
  </view>
</template>

<style scoped>
.boundary {
  display: flex;
  width: 100%;
  max-width: 800px;
  margin: 32rpx auto 24rpx;
  box-sizing: border-box;
  align-items: center;
  gap: 18rpx;
}
.boundary__line {
  width: 5rpx;
  min-height: 88rpx;
  flex: 0 0 5rpx;
  background: var(--med-clinical);
  border-radius: 99rpx;
}
.boundary__content {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 5rpx;
}
.boundary__title {
  color: var(--med-ink);
  font-size: 25rpx;
  font-weight: 750;
}
.boundary__text {
  color: var(--med-muted);
  font-size: 22rpx;
  line-height: 1.55;
}
</style>
