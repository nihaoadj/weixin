<template>
  <text
    class="tst"
    :class="`tst--${tone}`"
    >{{ label }}</text
  >
</template>

<script setup lang="ts">
// Compact rectangular status tag. The label is always visible and rendered
// verbatim — mapping a business state to copy and a tone stays with the
// caller, so this component can never invent or hide a state.
withDefaults(
  defineProps<{
    label: string
    tone?: 'neutral' | 'active' | 'success' | 'safety' | 'danger'
  }>(),
  { tone: 'neutral' },
)
</script>

<style scoped>
.tst {
  display: inline-flex;
  padding: 4rpx 14rpx;
  align-items: center;
  box-sizing: border-box;
  border: 1rpx solid var(--med-border);
  border-radius: 6rpx;
  font-size: 24rpx;
  font-weight: 600;
  line-height: 1.5;
  white-space: nowrap;
}
.tst--neutral {
  color: var(--med-muted);
  background: transparent;
}
.tst--active {
  color: var(--med-brand-deep);
  background: var(--med-wash);
  border-color: transparent;
}
.tst--success {
  color: var(--med-brand-deep);
  background: transparent;
  border-color: var(--med-clinical);
}
.tst--safety {
  color: var(--med-safety-text);
  background: var(--med-safety-soft);
  border-color: var(--med-safety-border);
}
.tst--danger {
  color: var(--med-alert);
  background: var(--med-alert-soft);
  border-color: transparent;
}
@media screen and (max-width: 359px) {
  .tst {
    font-size: 12px;
  }
}
</style>
