<script setup>
// 会员锁占位角标（Fable5 §8）：一期 member_lock=false → 隐藏(全公开)；二期 true → 显「会员专享」。
// 就位·开关控·不真拦截（真拦截在后端 member_gate）。
import { useAuthStore } from '../stores/auth'
const auth = useAuthStore()
</script>

<template>
  <span v-if="auth.memberLock" class="lock">🔒 会员专享 · 即将上线</span>
</template>

<style scoped>
.lock { display: inline-block; font-size: 11px; background: var(--warnbg); color: var(--warn); border-radius: 999px; padding: 2px 9px; margin-left: 6px; }
</style>
