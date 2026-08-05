import { defineStore } from 'pinia'
import { api } from '../api'

// 会员态 + 功能开关（一期 member_lock_enabled=false 全公开）。
// 测试期：账号密码登录解锁直播（/api/cams 后端要求登录）；二期换微信扫码，本登录 UI 届时下线。
export const useAuthStore = defineStore('auth', {
  state: () => ({ memberLock: false, loaded: false, user: null }),
  getters: {
    authenticated: (s) => !!s.user,
  },
  actions: {
    async loadFlags() {
      try { this.memberLock = !!(await api.flags()).member_lock_enabled }
      catch { this.memberLock = false }
      try {
        const me = await api.me()
        this.user = me.authenticated ? me : null
      } catch { this.user = null }
      this.loaded = true
    },
    async login(email, password) {
      await api.login(email, password)   // 失败抛错由弹层展示
      const me = await api.me()
      this.user = me.authenticated ? me : null
    },
    async logout() {
      try { await api.logout() } catch { /* 会话已失效也视为登出 */ }
      this.user = null
    },
  },
})
