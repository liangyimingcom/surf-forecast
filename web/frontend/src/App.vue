<script setup>
// 根壳：加载功能开关(会员锁一期=false)。微信扫码登录二期开放，一期占位入口。
import { onMounted, ref } from 'vue'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const showWechat = ref(false)
onMounted(() => auth.loadFlags())
</script>

<template>
  <router-view />
  <button class="wxlogin" @click="showWechat = true" aria-label="登录">👤</button>
  <div v-if="showWechat" class="wxmask" @click.self="showWechat = false">
    <div class="wxbox">
      <h3>微信扫码登录</h3>
      <p>会员登录二期开放（微信小程序扫码）。一期全部内容公开，无需登录。</p>
      <button @click="showWechat = false">知道了</button>
    </div>
  </div>
</template>

<style scoped>
.wxlogin { position: fixed; top: 10px; right: 10px; z-index: 50; width: 38px; height: 38px; border-radius: 50%; border: none; background: #fff; box-shadow: 0 1px 4px rgba(0,0,0,.15); font-size: 18px; }
.wxmask { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.wxbox { background: #fff; border-radius: 16px; padding: 20px; max-width: 300px; text-align: center; }
.wxbox h3 { color: var(--sea1); margin: 0 0 8px; }
.wxbox p { font-size: 13px; color: var(--ink2); }
.wxbox button { margin-top: 12px; padding: 8px 20px; border: none; border-radius: 10px; background: var(--sea2); color: #fff; }
</style>
