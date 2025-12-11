<!-- src/App.vue -->
<script setup>
import { RouterView } from 'vue-router'
import Sidebar from './components/Sidebar.vue'
</script>

<template>
  <div class="flex h-screen w-screen text-gray-800">
    <!-- 左侧：侧边导航栏 -->
    <Sidebar class="w-64 flex-shrink-0 bg-white border-r border-gray-200" />
    
    <!-- 右侧：主内容区域 -->
    <main class="flex-1 flex flex-col h-full overflow-hidden bg-gray-50">
      <RouterView />
    </main>
  </div>
</template>