<template>
  <view
    class="student-nav-icon"
    :class="`student-nav-icon--${name}`"
    aria-hidden="true"
  >
    <template v-if="name === 'chat'">
      <view class="chat-bubble"><text class="chat-line" /></view>
    </template>
    <template v-else-if="name === 'book'">
      <view class="book-page book-page--left" />
      <view class="book-page book-page--right" />
      <text class="book-spine" />
    </template>
    <template v-else>
      <view class="history-clock"><text class="history-hand" /></view>
      <text class="history-marker" />
    </template>
  </view>
</template>

<script setup lang="ts">
defineProps<{ name: 'chat' | 'book' | 'history' }>()
</script>

<style scoped>
.student-nav-icon {
  position: relative;
  display: block;
  width: 30rpx;
  height: 30rpx;
  color: inherit;
  font-size: 30rpx;
}
.chat-bubble {
  position: absolute;
  top: 0.067em;
  left: 0.067em;
  width: 0.867em;
  height: 0.7em;
  box-sizing: border-box;
  border: 0.1em solid currentColor;
  border-radius: 0.267em;
}
.chat-bubble::after {
  position: absolute;
  bottom: -0.2em;
  left: 0.167em;
  width: 0.233em;
  height: 0.233em;
  box-sizing: border-box;
  border-bottom: 0.1em solid currentColor;
  border-left: 0.1em solid currentColor;
  content: '';
  transform: skewY(-28deg);
}
.chat-line {
  position: absolute;
  top: 0.233em;
  left: 0.167em;
  width: 0.367em;
  height: 0.1em;
  background: currentColor;
  border-radius: 99rpx;
}
.book-page {
  position: absolute;
  top: 0.067em;
  width: 0.467em;
  height: 0.833em;
  box-sizing: border-box;
  border: 0.1em solid currentColor;
}
.book-page--left {
  left: 0.033em;
  border-right-width: 0.067em;
  border-radius: 0.233em 0.067em 0.067em 0.167em;
}
.book-page--right {
  right: 0.033em;
  border-left-width: 0.067em;
  border-radius: 0.067em 0.233em 0.167em 0.067em;
}
.book-spine {
  position: absolute;
  top: 0.167em;
  bottom: 0.067em;
  left: 0.467em;
  width: 0.067em;
  background: currentColor;
  border-radius: 99rpx;
}
.history-clock {
  position: absolute;
  top: 0.1em;
  left: 0.1em;
  width: 0.8em;
  height: 0.8em;
  box-sizing: border-box;
  border: 0.1em solid currentColor;
  border-radius: 50%;
}
.history-hand {
  position: absolute;
  top: 0.167em;
  left: 0.3em;
  width: 0.233em;
  height: 0.267em;
  box-sizing: border-box;
  border-bottom: 0.1em solid currentColor;
  border-left: 0.1em solid currentColor;
  border-radius: 0 0 0 0.067em;
}
.history-marker {
  position: absolute;
  top: 0;
  left: 0.033em;
  width: 0.233em;
  height: 0.233em;
  background: currentColor;
  border-radius: 0.067em 99px 0.067em 99px;
  transform: rotate(-18deg);
}

@media screen and (min-width: 600px) and (max-width: 899px) {
  .student-nav-icon {
    width: 20px;
    height: 20px;
    font-size: 20px;
  }
}

@media screen and (min-width: 900px) {
  .student-nav-icon {
    width: 18px;
    height: 18px;
    font-size: 18px;
  }
}
</style>
