<script setup lang="ts">
import { onLaunch } from '@dcloudio/uni-app'
import { ensureDemoData } from '@/features/qa/public'
import { recordStartupLog } from '@/platform/logs'

onLaunch(() => {
  recordStartupLog()
  ensureDemoData()
})
</script>

<style>
page {
  --med-paper: #f4f7f6;
  --med-ink: #15324a;
  --med-clinical: #0b716b;
  --med-wash: #e7f2f0;
  --med-safety: #9a5618;
  --med-safety-soft: #fef3e8;
  --med-safety-border: #efd1aa;
  --med-safety-text: #71502f;
  --med-alert: #b8454f;
  --med-alert-soft: #fff0f2;
  --med-font-body: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'HarmonyOS Sans SC', 'Microsoft YaHei', sans-serif;
  --med-font-display: var(--med-font-body);
  --med-font-utility: 'DIN Alternate', 'SFMono-Regular', Consolas, monospace;
  --med-navy: var(--med-ink);
  --med-text: #29465a;
  --med-text-secondary: #526174;
  --med-muted: #5c7080;
  --med-brand: var(--med-clinical);
  --med-brand-deep: #075954;
  --med-brand-soft: var(--med-wash);
  --med-accent: #2f8f87;
  --med-page: var(--med-paper);
  --med-surface: #ffffff;
  --med-border: #d7e2de;
  --med-divider: #e6edeb;
  --med-warning: var(--med-safety);
  --med-danger: var(--med-alert);
  --med-radius-sm: 12rpx;
  --med-radius-md: 20rpx;
  --med-radius-lg: 20rpx;
  --med-space-0: 8rpx;
  --med-space-1: 16rpx;
  --med-space-2: 24rpx;
  --med-space-3: 32rpx;
  --med-space-4: 48rpx;
  --med-space-5: 64rpx;
  --med-shadow-card: none;
  --med-motion-press: 70ms;
  --med-motion-settle: 180ms;
  --med-motion-enter: 200ms;
  --med-ease-out: cubic-bezier(0.2, 0.8, 0.2, 1);
  min-height: 100%;
  color: var(--med-text);
  background: var(--med-page);
  font-family: var(--med-font-body);
  font-size: 28rpx;
}

button {
  box-sizing: border-box;
  font-family: inherit;
  touch-action: manipulation;
  -webkit-tap-highlight-color: rgba(11, 113, 107, 0.14);
}

button::after,
.safe-page button::after {
  border: 0;
}

.safe-page {
  min-height: 100vh;
  box-sizing: border-box;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
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
  background: var(--med-clinical);
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

button:focus-visible,
input:focus-visible,
textarea:focus-visible,
input:focus-within,
textarea:focus-within {
  outline: 4rpx solid var(--med-clinical);
  outline-offset: 4rpx;
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
  color: var(--med-clinical);
  font-family: var(--med-font-utility);
  font-size: 22rpx;
  font-weight: 700;
  letter-spacing: 3rpx;
}

button,
.pressable {
  transition:
    opacity var(--med-motion-settle) var(--med-ease-out),
    transform var(--med-motion-settle) var(--med-ease-out);
  transform-origin: center;
}

button:not([disabled]):active,
button.is-pressed,
.pressable:active,
.pressable.is-pressed {
  opacity: 0.86;
  transform: translateY(1px);
  transition-duration: var(--med-motion-press);
}

button.motion-card:not([disabled]):active,
button.motion-card.is-pressed {
  transform: scale(0.992);
}

.step-enter {
  animation: med-step-enter var(--med-motion-enter) var(--med-ease-out);
}

@keyframes med-page-enter {
  from {
    opacity: 0.72;
  }
  to {
    opacity: 1;
  }
}

@keyframes med-step-enter {
  from {
    opacity: 0.72;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  button,
  .pressable {
    transition: none;
  }

  button:not([disabled]):active,
  button.is-pressed,
  .pressable:active,
  .pressable.is-pressed,
  button.motion-card:not([disabled]):active,
  button.motion-card.is-pressed {
    transform: none;
    transition: none;
  }

  .page-enter,
  .step-enter {
    animation: none;
  }
}

@media (hover: hover) {
  button:not([disabled]):hover {
    opacity: 0.92;
  }
}

@media screen and (min-width: 600px) and (max-width: 899px) {
  .eyebrow-label {
    font-size: 14px;
    letter-spacing: 2px;
  }
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
