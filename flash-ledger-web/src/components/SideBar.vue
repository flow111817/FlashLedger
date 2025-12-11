<script setup>
import { ref, onMounted } from 'vue'
import { pb } from '../lib/pb'

// 状态
const ledgers = ref([])
const currentLedgerId = ref(localStorage.getItem('currentLedgerId') || '')
const showCreateModal = ref(false)
const showDeleteModal = ref(false) // 删除确认弹窗
const ledgerToDelete = ref(null)   // 待删除的账本ID
const newLedgerName = ref('')

// 加载账本
const loadLedgers = async () => {
  try {
    const result = await pb.collection('ledgers').getFullList({ sort: '-created' })
    ledgers.value = result
    if (!currentLedgerId.value && result.length > 0) {
      selectLedger(result[0].id)
    }
  } catch (err) {
    console.error(err)
  }
}

// 切换
const selectLedger = (id) => {
  currentLedgerId.value = id
  localStorage.setItem('currentLedgerId', id)
  window.dispatchEvent(new CustomEvent('ledger-changed', { detail: id }))
}

// 创建
const createLedger = async () => {
  if (!newLedgerName.value) return
  await pb.collection('ledgers').create({ name: newLedgerName.value })
  newLedgerName.value = ''
  showCreateModal.value = false
  await loadLedgers()
}

// 触发删除确认
const confirmDelete = (id) => {
  ledgerToDelete.value = id
  showDeleteModal.value = true
}

// 执行删除
const executeDelete = async () => {
  if (!ledgerToDelete.value) return
  await pb.collection('ledgers').delete(ledgerToDelete.value)
  
  if (currentLedgerId.value === ledgerToDelete.value) {
    currentLedgerId.value = ''
    localStorage.setItem('currentLedgerId', '')
    window.dispatchEvent(new CustomEvent('ledger-changed', { detail: '' }))
  }
  
  showDeleteModal.value = false
  ledgerToDelete.value = null
  await loadLedgers()
}

onMounted(() => loadLedgers())
</script>

<template>
  <div class="flex flex-col h-full bg-[#FAFAF9] border-r border-stone-200">
    <!-- 标题 -->
    <div class="p-6">
      <div class="flex items-center gap-2 select-none">
        <img src="/logo.png" alt="Logo" class="w-8 h-8 object-contain block" />
        
        <!-- 修改点：
             1. 删除了 leading-none，改用 leading-tight (稍微松一点，容纳尾巴)
             2. 增加了 translate-y-[6px]
             3. 增加了 pb-1 (底部加一点点内边距，确保渐变色能覆盖到 g 的最底端) 
        -->
        <span class="font-bold text-lg bg-gradient-to-r from-amber-400 to-orange-500 bg-clip-text text-transparent leading-tight pb-1 translate-y-[6px]">
          FlashLedger
        </span>
      </div>
      
      <p class="text-xs text-stone-400 mt-1 pl-1">温暖你的每一笔开支</p>
    </div>
    
    <!-- 列表 -->
    <div class="flex-1 overflow-y-auto px-4 space-y-2">
      <div class="text-xs font-bold text-stone-400 mb-3 px-2">我的账本</div>
      <div 
        v-for="ledger in ledgers" 
        :key="ledger.id"
        @click="selectLedger(ledger.id)"
        class="group flex justify-between items-center p-3 rounded-2xl cursor-pointer transition-all duration-300"
        :class="currentLedgerId === ledger.id ? 'bg-white shadow-md shadow-stone-100 text-teal-600' : 'hover:bg-stone-100 text-stone-600'"
      >
        <div class="flex items-center gap-3">
          <div class="w-2 h-8 rounded-full transition-colors"
            :class="currentLedgerId === ledger.id ? 'bg-teal-400' : 'bg-stone-200 group-hover:bg-stone-300'">
          </div>
          <span class="font-medium">{{ ledger.name }}</span>
        </div>
        <!-- 删除按钮 -->
        <button @click.stop="confirmDelete(ledger.id)" class="opacity-0 group-hover:opacity-100 text-stone-300 hover:text-red-400 transition px-2">
          ×
        </button>
      </div>
    </div>

    <!-- 底部按钮 -->
    <div class="p-6">
      <button @click="showCreateModal = true" class="w-full bg-stone-800 text-[#FAFAF9] py-3 rounded-xl shadow-lg hover:shadow-xl hover:-translate-y-0.5 transition-all duration-300 font-medium flex items-center justify-center gap-2">
        <span>+</span> 新建账本
      </button>
    </div>

    <!-- 创建弹窗 (Modal) -->
    <div v-if="showCreateModal" class="fixed inset-0 bg-stone-900/30 backdrop-blur-sm flex items-center justify-center z-50">
      <div class="bg-white p-6 rounded-3xl shadow-2xl w-80">
        <h3 class="font-bold text-stone-700 text-lg mb-4">新建账本</h3>
        <input v-model="newLedgerName" class="w-full bg-stone-50 p-3 rounded-xl mb-6 outline-none focus:ring-2 focus:ring-teal-200" placeholder="账本名称..." autofocus @keyup.enter="createLedger">
        <div class="flex justify-end gap-3">
          <button @click="showCreateModal = false" class="px-4 py-2 text-stone-400 hover:text-stone-600">取消</button>
          <button @click="createLedger" class="px-6 py-2 bg-teal-400 text-white rounded-xl shadow-lg hover:bg-teal-500 font-bold">创建</button>
        </div>
      </div>
    </div>

    <!-- 删除确认弹窗 (Modal) -->
    <div v-if="showDeleteModal" class="fixed inset-0 bg-stone-900/30 backdrop-blur-sm flex items-center justify-center z-50">
      <div class="bg-white p-6 rounded-3xl shadow-2xl w-80">
        <h3 class="font-bold text-stone-800 text-lg mb-2">确认删除?</h3>
        <p class="text-sm text-stone-500 mb-6">该账本内的所有记录都将永久丢失。</p>
        <div class="flex justify-end gap-3">
          <button @click="showDeleteModal = false" class="px-4 py-2 text-stone-400 hover:text-stone-600">再想想</button>
          <button @click="executeDelete" class="px-6 py-2 bg-red-400 text-white rounded-xl shadow-lg hover:bg-red-500 font-bold">确认删除</button>
        </div>
      </div>
    </div>
  </div>
</template>