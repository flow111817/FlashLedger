import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    // 允许局域网访问 (关键)
    host: '0.0.0.0', 
    // 指定端口
    port: 5173,      
    // 监听文件修改 (Docker 必须配置这个，否则修改代码不生效)
    watch: {
      usePolling: true
    }
  }
})