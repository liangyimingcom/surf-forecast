import { defineStore } from 'pinia'
import { api } from '../api'

// 会员态 + 功能开关（一期 member_lock_enabled=false 全公开）。
export const useAuthStore = defineStore('auth', {
  state: () => ({ memberLock: false, loaded: false }),
  actions: {
    async loadFlags() {
      try { this.memberLock = !!(await api.flags()).member_lock_enabled }
      catch { this.memberLock = false }
      this.loaded = true
    },
  },
})
