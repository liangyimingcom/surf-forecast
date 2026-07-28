<script setup>
// 根壳：加载功能开关(会员锁一期=false) + 测试期账号密码登录（解锁直播）。
// 微信扫码登录二期开放，届时本登录表单下线（弹层内已注明）。
import { onMounted, ref } from 'vue'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const show = ref(false)
const email = ref('')
const password = ref('')
const busy = ref(false)
const err = ref('')

onMounted(() => auth.loadFlags())

async function doLogin() {
  if (!email.value || !password.value) { err.value = '请输入账号与密码'; return }
  busy.value = true; err.value = ''
  try {
    await auth.login(email.value, password.value)
    show.value = false
    password.value = ''
  } catch (e) {
    err.value = e.message || '登录失败'
  } finally { busy.value = false }
}

async function doLogout() {
  busy.value = true
  try { await auth.logout() } finally { busy.value = false; show.value = false }
}
</script>

<template>
  <router-view />
  <button class="wxlogin" :class="{ authed: auth.authenticated }" @click="show = true"
          :aria-label="auth.authenticated ? '账号' : '登录'">
    {{ auth.authenticated ? '🟢' : '👤' }}
  </button>
  <div v-if="show" class="wxmask" @click.self="show = false">
    <div class="wxbox">
      <template v-if="auth.authenticated">
        <h3>已登录</h3>
        <p class="who">{{ auth.user.email }}</p>
        <p>测试账号可观看浪点实时直播（作校验预报的信任工具）。</p>
        <button class="primary" :disabled="busy" @click="doLogout">退出登录</button>
      </template>
      <template v-else>
        <h3>测试账号登录</h3>
        <p>登录后可看浪点实时直播。正式版将改用<b>微信扫码登录</b>（二期），本表单届时下线。</p>
        <input v-model="email" type="text" placeholder="账号(邮箱)" autocomplete="username" @keyup.enter="doLogin" />
        <input v-model="password" type="password" placeholder="密码" autocomplete="current-password" @keyup.enter="doLogin" />
        <p v-if="err" class="err">{{ err }}</p>
        <button class="primary" :disabled="busy" @click="doLogin">{{ busy ? '登录中…' : '登录' }}</button>
      </template>
      <button class="ghost" @click="show = false">关闭</button>
    </div>
  </div>
</template>

<style scoped>
.wxlogin { position: fixed; top: 10px; right: 10px; z-index: 50; width: 38px; height: 38px; border-radius: 50%; border: none; background: #fff; box-shadow: 0 1px 4px rgba(0,0,0,.15); font-size: 18px; }
.wxlogin.authed { font-size: 14px; }
.wxmask { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.wxbox { background: #fff; border-radius: 16px; padding: 20px; width: min(320px, 88vw); text-align: center; }
.wxbox h3 { color: var(--sea1); margin: 0 0 8px; }
.wxbox p { font-size: 13px; color: var(--ink2); }
.wxbox .who { font-weight: 600; color: var(--ink); }
.wxbox input { display: block; width: 100%; box-sizing: border-box; margin: 8px 0; padding: 9px 12px; border: 1px solid #cbd5e1; border-radius: 10px; font-size: 14px; }
.wxbox .err { color: #b91c1c; font-size: 12.5px; }
.wxbox .primary { margin-top: 8px; width: 100%; padding: 9px 20px; border: none; border-radius: 10px; background: var(--sea2); color: #fff; font-size: 14px; }
.wxbox .primary:disabled { opacity: .6; }
.wxbox .ghost { margin-top: 8px; width: 100%; padding: 8px 20px; border: 1px solid #cbd5e1; border-radius: 10px; background: #fff; color: var(--ink2); font-size: 13px; }
</style>
