import { defineStore } from 'pinia'

// 当前浪点 REPORT/HISTORY（P4 详情页迁移时接入；沿用会话缓存秒切思路）。
export const useSpotStore = defineStore('spot', {
  state: () => ({ current: null, report: null, history: null }),
  actions: {
    setReport(r) { this.report = r },
    setHistory(h) { this.history = h },
  },
})
