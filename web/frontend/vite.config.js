import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 甲-1：build 产物由后端 StaticFiles 直服（不改 CloudFront）。
// dev 时 /api 代理到本地 FastAPI（uvicorn 默认 8000）。
export default defineConfig({
  plugins: [vue()],
  build: { outDir: 'dist', emptyOutDir: true },
  server: {
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true }
    }
  }
})
