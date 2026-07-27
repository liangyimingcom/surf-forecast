import { defineStore } from 'pinia'

// 区域选择（首访引导，localStorage 记忆，可随时换）。
export const useRegionStore = defineStore('region', {
  state: () => ({ region: localStorage.getItem('sf_region_v1') || '' }),
  actions: {
    set(r) { this.region = r || ''; localStorage.setItem('sf_region_v1', this.region) },
  },
})
