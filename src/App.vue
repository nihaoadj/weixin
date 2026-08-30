<script setup lang="ts">
import { onLaunch } from '@dcloudio/uni-app'
import { ensureDemoData } from '@/services/repository'
import { isDemoMode } from '@/config/runtime'

onLaunch(() => {
  const logs = uni.getStorageSync('logs')
  const nextLogs = Array.isArray(logs) ? logs : []
  nextLogs.unshift(Date.now())
  uni.setStorageSync('logs', nextLogs.slice(0, 50))
  if (isDemoMode()) ensureDemoData()
})
</script>

<style>
page {
  --med-navy: #0b2239;
  --med-text: #193246;
  --med-muted: #637985;
  --med-brand: #0f8b8d;
  --med-brand-deep: #0b5d61;
  --med-accent: #35b7a8;
  --med-page: #f4f8fa;
  --med-surface: #ffffff;
  --med-border: #dbe7eb;
  --med-warning: #b36528;
  --med-danger: #c64753;
  --med-radius-sm: 14rpx;
  --med-radius-md: 20rpx;
  --med-radius-lg: 28rpx;
  --med-shadow-card: 0 16rpx 42rpx rgba(11, 34, 57, 0.08);
  min-height: 100%;
  color: var(--med-text);
  background: var(--med-page);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  font-size: 28rpx;
}

button::after {
  border: 0;
}

.safe-page {
  min-height: 100vh;
  box-sizing: border-box;
}

.card {
  background: var(--med-surface);
  border: 1rpx solid var(--med-border);
  border-radius: var(--med-radius-lg);
  box-shadow: var(--med-shadow-card);
}

.primary-button {
  min-height: 88rpx;
  color: #fff;
  background: linear-gradient(135deg, var(--med-brand-deep), var(--med-brand));
  border-radius: 20rpx;
  font-size: 30rpx;
  font-weight: 600;
}

input,
textarea {
  box-sizing: border-box;
}

button[disabled] {
  opacity: 0.48;
}

.muted {
  color: var(--med-muted);
}

.page-container {
  width: 100%;
  max-width: 1080rpx;
  margin: 0 auto;
  box-sizing: border-box;
}

.eyebrow-label {
  color: var(--med-brand);
  font-size: 20rpx;
  font-weight: 700;
  letter-spacing: 3rpx;
}

.pressable {
  transition:
    opacity 0.18s ease,
    transform 0.18s ease;
}

.pressable:active {
  opacity: 0.76;
  transform: scale(0.985);
}

@media screen and (min-width: 900px) {
  page {
    background: #eaf1f4;
  }

  .safe-page {
    max-width: 1080px;
    min-height: 100vh;
    margin: 0 auto;
    background: var(--med-page);
    box-shadow: 0 0 60px rgba(11, 34, 57, 0.08);
  }
}
</style>
