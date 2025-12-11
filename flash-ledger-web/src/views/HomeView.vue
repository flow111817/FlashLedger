<script setup>
import { ref, onMounted, onUnmounted, computed, reactive, watch } from 'vue'
import { pb } from '../lib/pb'
import { 
  format, startOfMonth, endOfMonth, eachDayOfInterval, 
  isSameDay, addMonths, subMonths, isSameMonth, parseISO,
  startOfYear, endOfYear, addYears, subYears, isSameYear, getMonth, isValid
} from 'date-fns'
import * as XLSX from 'xlsx'
import { Pie, Line } from 'vue-chartjs'

// --- 状态定义 ---
const currentLedgerId = ref(localStorage.getItem('currentLedgerId'))
const allTransactions = ref([]) 
const currentDate = ref(new Date()) 
const viewMode = ref('month') // 'month' | 'year'
const currentTab = ref('dashboard') // 'dashboard' | 'list'
const isLoading = ref(false)
const fileInput = ref(null)

// 模态框状态
const showModal = ref(false)              // 记账/编辑
const showExportModal = ref(false)        // 导出
const showImportModal = ref(false)        // 导入确认
const showImportSuccessModal = ref(false) // 导入成功提示 (新增)
const showDeleteConfirm = ref(false)      // 删除确认
const isEditing = ref(false)

// 操作 ID
const editingId = ref(null)
const deleteId = ref(null)

// 导入预览数据
const importPreview = ref({ count: 0, data: [] })

// 表单数据
const form = reactive({
  amount: '',
  category: '必要饮食',
  type: '支出',
  date: format(new Date(), 'yyyy-MM-dd'),
  note: ''
})

// 预设配置
const expenseCategories = ['必要饮食', '次要饮食', '交通出行', '休闲娱乐', '生活消费', '医疗保健']
const categoryColors = {
  '必要饮食': 'bg-orange-100 text-orange-600',
  '次要饮食': 'bg-yellow-100 text-yellow-600',
  '交通出行': 'bg-blue-100 text-blue-600',
  '休闲娱乐': 'bg-purple-100 text-purple-600',
  '生活消费': 'bg-pink-100 text-pink-600',
  '医疗保健': 'bg-red-100 text-red-600',
  '收入': 'bg-emerald-100 text-emerald-600',
  'default': 'bg-stone-100 text-stone-600'
}
const getCategoryColor = (cat, type) => type === '收入' ? categoryColors['收入'] : (categoryColors[cat] || categoryColors['default'])

// --- 核心数据逻辑 ---

const fetchData = async () => {
  if (!currentLedgerId.value) return
  isLoading.value = true
  try {
    const result = await pb.collection('transactions').getFullList({
      filter: `ledger_id = "${currentLedgerId.value}"`,
      sort: '-date,-created'
    })
    allTransactions.value = result
  } catch (e) {
    console.error(e)
  } finally {
    isLoading.value = false
  }
}

// 核心筛选器
const filteredTransactions = computed(() => {
  return allTransactions.value.filter(t => {
    const tDate = parseISO(t.date)
    if (viewMode.value === 'month') {
      return isSameMonth(tDate, currentDate.value)
    } else {
      return isSameYear(tDate, currentDate.value)
    }
  })
})

// --- 时间导航 ---
const prevDate = () => { currentDate.value = viewMode.value === 'month' ? subMonths(currentDate.value, 1) : subYears(currentDate.value, 1) }
const nextDate = () => { currentDate.value = viewMode.value === 'month' ? addMonths(currentDate.value, 1) : addYears(currentDate.value, 1) }
const resetDate = () => { currentDate.value = new Date() }
watch(viewMode, () => { currentDate.value = new Date() })

// --- 增删改查 ---
const openAddModal = () => {
  isEditing.value = false
  form.amount = ''
  form.category = '必要饮食'
  form.type = '支出'
  form.date = format(new Date(), 'yyyy-MM-dd')
  form.note = ''
  showModal.value = true
}

const openEditModal = (t) => {
  isEditing.value = true
  editingId.value = t.id
  form.amount = t.amount
  form.category = t.category
  form.type = t.type
  form.date = t.date.slice(0, 10)
  form.note = t.note
  showModal.value = true
}

const handleSubmit = async () => {
  if (!form.amount || !currentLedgerId.value) return
  const finalCategory = form.type === '收入' ? '工资薪金' : form.category
  const submitData = { ...form, category: finalCategory, ledger_id: currentLedgerId.value }

  try {
    if (isEditing.value) await pb.collection('transactions').update(editingId.value, submitData)
    else await pb.collection('transactions').create(submitData)
    showModal.value = false
    await fetchData()
  } catch (e) { alert('保存失败: ' + e.message) }
}

// 删除功能修复：确保状态正确传递
const confirmDelete = (id) => {
  console.log('点击删除，ID:', id) // 调试用
  deleteId.value = id
  showDeleteConfirm.value = true
}

const executeDelete = async () => {
  if (!deleteId.value) return
  await pb.collection('transactions').delete(deleteId.value)
  showDeleteConfirm.value = false
  deleteId.value = null // 重置
  await fetchData()
}

// --- 统计与图表 ---
const stats = computed(() => {
  let income = 0, expense = 0
  filteredTransactions.value.forEach(t => {
    if (t.type === '收入') income += t.amount
    else expense += t.amount
  })
  return { income, expense, balance: income - expense }
})

const rightPanelData = computed(() => {
  if (viewMode.value === 'month') {
    const start = startOfMonth(currentDate.value)
    const end = endOfMonth(currentDate.value)
    const days = eachDayOfInterval({ start, end })
    const recordDates = new Set(filteredTransactions.value.map(t => t.date.slice(0, 10)))
    return days.map(day => ({
      type: 'day', label: format(day, 'd'), date: day,
      hasRecord: recordDates.has(format(day, 'yyyy-MM-dd')), isHighlight: isSameDay(day, new Date())
    }))
  } else {
    const monthStats = Array(12).fill(0).map((_, i) => ({ month: i + 1, income: 0, expense: 0 }))
    filteredTransactions.value.forEach(t => {
      const m = getMonth(parseISO(t.date))
      t.type === '收入' ? monthStats[m].income += t.amount : monthStats[m].expense += t.amount
    })
    return monthStats.map(m => ({
      type: 'month', label: `${m.month}月`, income: m.income, expense: m.expense, balance: m.income - m.expense,
      isHighlight: m.month === getMonth(new Date()) + 1 && isSameYear(currentDate.value, new Date())
    }))
  }
})

const pieChartData = computed(() => {
  const categoryMap = {}
  filteredTransactions.value.forEach(t => {
    if (t.type === '支出') categoryMap[t.category] = (categoryMap[t.category] || 0) + t.amount
  })
  return {
    labels: Object.keys(categoryMap),
    datasets: [{
      backgroundColor: ['#FCA5A5', '#FDBA74', '#FDE047', '#86EFAC', '#93C5FD', '#C4B5FD', '#E5E7EB'],
      data: Object.values(categoryMap), borderWidth: 0
    }]
  }
})

const lineChartData = computed(() => {
  let labels = [], incomeData = [], expenseData = []
  if (viewMode.value === 'month') {
    const start = startOfMonth(currentDate.value)
    const end = endOfMonth(currentDate.value)
    const days = eachDayOfInterval({ start, end })
    labels = days.map(d => format(d, 'd'))
    const dateMap = {}; days.forEach(d => dateMap[format(d, 'yyyy-MM-dd')] = { income: 0, expense: 0 })
    filteredTransactions.value.forEach(t => {
      const d = t.date.slice(0, 10)
      if (dateMap[d]) t.type === '收入' ? dateMap[d].income += t.amount : dateMap[d].expense += t.amount
    })
    incomeData = Object.values(dateMap).map(v => v.income)
    expenseData = Object.values(dateMap).map(v => v.expense)
  } else {
    labels = Array.from({length: 12}, (_, i) => `${i+1}月`)
    const monthMap = Array(12).fill(0).map(() => ({ income: 0, expense: 0 }))
    filteredTransactions.value.forEach(t => {
      const m = getMonth(parseISO(t.date))
      t.type === '收入' ? monthMap[m].income += t.amount : monthMap[m].expense += t.amount
    })
    incomeData = monthMap.map(v => v.income); expenseData = monthMap.map(v => v.expense)
  }
  return {
    labels, datasets: [
      { label: '收入', data: incomeData, borderColor: '#34D399', backgroundColor: '#34D399', tension: 0.3, pointRadius: 2 },
      { label: '支出', data: expenseData, borderColor: '#F87171', backgroundColor: '#F87171', tension: 0.3, pointRadius: 2 }
    ]
  }
})

const pieOptions = { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right', labels: { boxWidth: 12, usePointStyle: true } } } }
const lineOptions = { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'top', align: 'end' } }, scales: { x: { grid: { display: false } }, y: { grid: { borderDash: [4, 4], color: '#f3f4f6' } } } }

// --- 导入导出逻辑 ---
const handleExport = (scope) => {
  const sourceData = scope === 'current' ? filteredTransactions.value : allTransactions.value
  if (sourceData.length === 0) return alert('没有数据可导出')
  const data = sourceData.map(t => ({ 日期: t.date.slice(0, 10), 类型: t.type, 分类: t.category, 金额: t.amount, 备注: t.note }))
  const ws = XLSX.utils.json_to_sheet(data)
  const wb = XLSX.utils.book_new()
  const name = scope === 'current' ? (viewMode.value === 'month' ? format(currentDate.value, 'yyyy年MM月') : format(currentDate.value, 'yyyy年')) : '全部'
  XLSX.utils.book_append_sheet(wb, ws, "Sheet1")
  XLSX.writeFile(wb, `FlashLedger_${name}.xlsx`)
  showExportModal.value = false
}

const triggerImport = () => { fileInput.value.click() }

const parseExcelDate = (dateVal) => {
  if (!dateVal) return format(new Date(), 'yyyy-MM-dd')
  if (typeof dateVal === 'number') {
    const date = new Date((dateVal - (25567 + 2)) * 86400 * 1000)
    return format(date, 'yyyy-MM-dd')
  }
  if (typeof dateVal === 'string') {
    if (dateVal.includes('/') || dateVal.includes('-')) {
      const d = new Date(dateVal)
      if (isValid(d)) return format(d, 'yyyy-MM-dd')
    }
  }
  return format(new Date(), 'yyyy-MM-dd')
}

const handleImportFile = (event) => {
  const file = event.target.files[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const data = new Uint8Array(e.target.result)
      const workbook = XLSX.read(data, { type: 'array' })
      const worksheet = workbook.Sheets[workbook.SheetNames[0]]
      const json = XLSX.utils.sheet_to_json(worksheet)
      if (json.length === 0) return alert('Excel 文件为空')
      importPreview.value = { count: json.length, data: json }
      showImportModal.value = true
    } catch (err) {
      console.error(err)
      alert('读取文件失败，请检查格式')
    } finally {
      fileInput.value.value = ''
    }
  }
  reader.readAsArrayBuffer(file)
}

const confirmImport = async () => {
  if (importPreview.value.count === 0) return
  isLoading.value = true
  try {
    const promises = importPreview.value.data.map(row => {
      // { requestKey: null } 防止自动取消
      return pb.collection('transactions').create({
        ledger_id: currentLedgerId.value,
        date: parseExcelDate(row['日期']),
        type: row['类型'] || '支出',
        category: row['分类'] || '其他',
        amount: parseFloat(row['金额']) || 0,
        note: row['备注'] || ''
      }, { requestKey: null }) 
    })
    
    await Promise.all(promises)
    showImportModal.value = false
    showImportSuccessModal.value = true // 成功后显示模态框
    await fetchData()
  } catch (err) {
    console.error(err)
    alert('导入过程中出错：' + (err.message || '未知错误'))
  } finally {
    isLoading.value = false
  }
}

// 监听
const handleLedgerChange = (e) => { currentLedgerId.value = e.detail; fetchData() }
onMounted(() => { window.addEventListener('ledger-changed', handleLedgerChange); if(currentLedgerId.value) fetchData() })
onUnmounted(() => window.removeEventListener('ledger-changed', handleLedgerChange))
</script>

<template>
  <div class="flex flex-col h-full bg-[#FFFBF0] text-stone-600 font-sans relative">
    
    <input type="file" ref="fileInput" accept=".xlsx, .xls" class="hidden" @change="handleImportFile" />

    <div v-if="isLoading" class="absolute inset-0 z-[60] bg-white/50 backdrop-blur-sm flex items-center justify-center">
      <div class="animate-spin rounded-full h-10 w-10 border-4 border-stone-200 border-t-teal-500"></div>
    </div>

    <div v-if="!currentLedgerId" class="flex-1 flex flex-col items-center justify-center text-stone-400 gap-4">
      <div class="text-6xl opacity-20">📒</div>
      <p>请在左侧选择一个账本</p>
    </div>

    <template v-else>
      <!-- Header -->
      <header class="px-8 pt-8 pb-4 space-y-6">
        <!-- Top Bar: 导航与控制 -->
        <div class="flex items-center justify-between">
          
          <!-- 左侧：功能导航 (Tab) -->
          <div class="flex bg-stone-200/50 p-1 rounded-xl">
             <button @click="currentTab = 'dashboard'" class="px-5 py-2 rounded-lg text-sm font-bold transition-all flex items-center gap-2" :class="currentTab === 'dashboard' ? 'bg-white shadow text-stone-800' : 'text-stone-500 hover:text-stone-700'">
               <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
               仪表盘
             </button>
             <button @click="currentTab = 'list'" class="px-5 py-2 rounded-lg text-sm font-bold transition-all flex items-center gap-2" :class="currentTab === 'list' ? 'bg-white shadow text-stone-800' : 'text-stone-500 hover:text-stone-700'">
               <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg>
               账单明细
             </button>
          </div>

          <!-- 中间：时间控制 -->
          <div class="flex gap-2">
            <!-- 模式切换 -->
            <div class="flex bg-white border border-stone-200 rounded-xl p-1 shadow-sm">
               <button @click="viewMode = 'month'" class="px-3 py-1.5 rounded-lg text-xs font-bold transition-all" :class="viewMode === 'month' ? 'bg-teal-50 text-teal-700' : 'text-stone-400'">月视图</button>
               <button @click="viewMode = 'year'" class="px-3 py-1.5 rounded-lg text-xs font-bold transition-all" :class="viewMode === 'year' ? 'bg-teal-50 text-teal-700' : 'text-stone-400'">年视图</button>
            </div>
            <!-- 时间选择 -->
            <div class="flex items-center gap-3 bg-white px-3 py-1 rounded-xl shadow-sm border border-stone-200 min-w-[160px] justify-between">
              <button @click="prevDate" class="text-stone-400 hover:text-stone-800 px-2 font-bold">‹</button>
              <div class="flex flex-col items-center cursor-pointer" @click="resetDate">
                <span v-if="viewMode === 'month'" class="text-[10px] text-stone-400 font-bold uppercase leading-tight">{{ format(currentDate, 'yyyy') }}</span>
                <span class="text-sm font-bold text-stone-800 leading-tight">
                  {{ viewMode === 'month' ? format(currentDate, 'MM月') : format(currentDate, 'yyyy年') }}
                </span>
              </div>
              <button @click="nextDate" class="text-stone-400 hover:text-stone-800 px-2 font-bold">›</button>
            </div>
          </div>

          <!-- 右侧：操作按钮 -->
          <div class="flex gap-3">
             <button @click="triggerImport" class="px-4 py-2 bg-white text-stone-600 border border-stone-200 rounded-xl hover:bg-stone-50 text-sm font-bold shadow-sm transition flex items-center gap-2">
               <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-stone-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
               导入
             </button>
             <button @click="showExportModal = true" class="px-4 py-2 bg-white text-stone-600 border border-stone-200 rounded-xl hover:bg-stone-50 text-sm font-bold shadow-sm transition flex items-center gap-2">
               <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-stone-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
               导出
             </button>
             <button @click="openAddModal" class="px-6 py-2 bg-stone-800 text-[#FAFAF9] rounded-xl shadow-lg hover:shadow-stone-400/50 hover:-translate-y-0.5 transition font-bold flex items-center gap-2">
              <span class="text-lg leading-none mb-0.5">+</span> 记一笔
            </button>
          </div>
        </div>

        <!-- 概览卡片 -->
        <div class="grid grid-cols-3 gap-6">
          <div class="bg-red-50 p-5 rounded-3xl border border-red-100/50 relative overflow-hidden group">
            <div class="text-xs text-red-400 font-bold uppercase mb-1 relative z-10">{{ viewMode === 'month' ? '本月' : '本年' }}支出</div>
            <div class="text-3xl font-bold text-stone-800 relative z-10">¥ {{ stats.expense.toFixed(2) }}</div>
          </div>
          <div class="bg-emerald-50 p-5 rounded-3xl border border-emerald-100/50 relative overflow-hidden group">
            <div class="text-xs text-emerald-500 font-bold uppercase mb-1 relative z-10">{{ viewMode === 'month' ? '本月' : '本年' }}收入</div>
            <div class="text-3xl font-bold text-stone-800 relative z-10">¥ {{ stats.income.toFixed(2) }}</div>
          </div>
          <div class="bg-white p-5 rounded-3xl border border-stone-100 relative overflow-hidden">
            <div class="text-xs text-stone-400 font-bold uppercase mb-1">结余</div>
            <div class="text-3xl font-bold" :class="stats.balance >= 0 ? 'text-stone-800' : 'text-red-500'">¥ {{ stats.balance.toFixed(2) }}</div>
          </div>
        </div>
      </header>

      <!-- Main Content -->
      <main class="flex-1 overflow-hidden px-8 pb-8">
        
        <!-- 视图 1: 仪表盘 -->
        <div v-if="currentTab === 'dashboard'" class="h-full overflow-y-auto pb-20 space-y-6 custom-scrollbar">
          <!-- 折线图 -->
          <div class="bg-white p-6 rounded-3xl shadow-sm border border-stone-100 h-80 w-full">
            <h3 class="font-bold text-stone-700 mb-4 flex items-center gap-2">📈 {{ viewMode === 'month' ? '每日' : '每月' }}收支趋势</h3>
            <div class="h-60"><Line :data="lineChartData" :options="lineOptions" /></div>
          </div>
          <!-- 饼图 + 右侧信息 -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
             <div class="bg-white p-6 rounded-3xl shadow-sm border border-stone-100 h-80">
                <h3 class="font-bold text-stone-700 mb-4">🍕 支出结构</h3>
                <div class="h-60 relative">
                   <Pie :data="pieChartData" :options="pieOptions" />
                   <div v-if="stats.expense === 0" class="absolute inset-0 flex items-center justify-center text-stone-300 text-sm">暂无支出</div>
                </div>
             </div>
             <!-- 右侧面板 -->
             <div class="bg-white p-6 rounded-3xl shadow-sm border border-stone-100 h-80 overflow-y-auto custom-scrollbar">
                <!-- 记账日历 -->
                <div v-if="viewMode === 'month'">
                  <h3 class="font-bold text-stone-700 mb-4 flex justify-between">
                    <span>📅 记账日历</span>
                    <span class="text-xs text-stone-400 bg-stone-100 px-2 py-1 rounded">记录: <b class="text-teal-600">{{ rightPanelData.filter(d=>d.hasRecord).length }}</b> 天</span>
                  </h3>
                  <div class="grid grid-cols-7 gap-2 text-center">
                    <div v-for="d in ['日','一','二','三','四','五','六']" :key="d" class="text-xs text-stone-300 font-bold mb-1">{{ d }}</div>
                    <div v-for="day in rightPanelData" :key="day.date" 
                      class="aspect-square flex flex-col items-center justify-center rounded-xl text-sm font-medium transition relative"
                      :class="[day.isHighlight ? 'bg-stone-800 text-white shadow-lg' : 'text-stone-600 hover:bg-stone-50']">
                      {{ day.label }}
                      <div v-if="day.hasRecord" class="w-1.5 h-1.5 rounded-full mt-1" :class="day.isHighlight ? 'bg-orange-400' : 'bg-teal-400'"></div>
                    </div>
                  </div>
                </div>
                <!-- 年度月报表 -->
                <div v-else>
                   <h3 class="font-bold text-stone-700 mb-4">🗓️ 月度收支表</h3>
                   <div class="space-y-3">
                     <div v-for="m in rightPanelData" :key="m.label" class="flex items-center justify-between p-3 rounded-xl" :class="m.isHighlight ? 'bg-stone-50 border border-stone-200' : ''">
                       <div class="font-bold w-12">{{ m.label }}</div>
                       <div class="text-xs text-stone-400 flex-1 px-2 text-right">
                         <span v-if="m.income > 0" class="text-emerald-500 mr-2">+{{ m.income }}</span>
                         <span v-if="m.expense > 0" class="text-red-400">-{{ m.expense }}</span>
                       </div>
                       <div class="font-mono font-bold w-20 text-right" :class="m.balance >=0 ? 'text-stone-800' : 'text-red-500'">{{ m.balance }}</div>
                     </div>
                   </div>
                </div>
             </div>
          </div>
        </div>

        <!-- 视图 2: 账单明细列表 -->
        <div v-else class="h-full bg-white rounded-3xl shadow-sm border border-stone-100 overflow-hidden flex flex-col">
          <div class="flex-1 overflow-auto custom-scrollbar">
            <table class="w-full text-left border-collapse">
              <thead class="sticky top-0 bg-stone-50 text-stone-400 text-xs uppercase tracking-wider z-20">
                <tr><th class="p-5 font-medium">日期</th><th class="p-5 font-medium">分类</th><th class="p-5 font-medium">备注</th><th class="p-5 font-medium text-right">金额</th><th class="p-5 text-center w-32">操作</th></tr>
              </thead>
              <tbody class="divide-y divide-stone-100">
                <tr v-for="t in filteredTransactions" :key="t.id" class="hover:bg-[#FFFBF0]/50 transition group">
                  <td class="p-5 text-stone-600 font-medium">{{ t.date.slice(0, 10) }}</td>
                  <td class="p-5"><span class="px-3 py-1 rounded-full text-xs font-bold shadow-sm" :class="getCategoryColor(t.category, t.type)">{{ t.category }}</span></td>
                  <td class="p-5 text-stone-400 text-sm max-w-xs truncate">{{ t.note || '-' }}</td>
                  <td class="p-5 text-right font-mono font-bold text-lg" :class="t.type === '收入' ? 'text-emerald-500' : 'text-stone-700'">{{ t.type === '收入' ? '+' : '-' }}{{ t.amount }}</td>
                  <td class="p-5 flex justify-center gap-2">
                    <button @click="openEditModal(t)" class="text-xs px-3 py-1 bg-white border border-stone-200 text-stone-500 rounded-lg hover:bg-stone-100 transition shadow-sm">修改</button>
                    <!-- 删除按钮 -->
                    <button @click="confirmDelete(t.id)" class="text-xs px-3 py-1 bg-red-50 text-red-500 border border-red-100 rounded-lg hover:bg-red-100 transition shadow-sm cursor-pointer z-10 relative">删除</button>
                  </td>
                </tr>
                <tr v-if="filteredTransactions.length === 0"><td colspan="5" class="p-10 text-center text-stone-300">本范围内没有记录</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </main>

      <!-- 记账 Modal -->
      <div v-if="showModal" class="fixed inset-0 bg-stone-800/40 backdrop-blur-sm flex items-center justify-center z-50">
        <div class="bg-[#FFFBF0] rounded-[2rem] shadow-2xl w-96 overflow-hidden border-4 border-white transform transition-all">
          <div class="px-8 py-6 bg-white flex justify-between items-center border-b border-stone-100">
            <span class="font-bold text-xl text-stone-800">{{ isEditing ? '修改记录' : '记一笔' }} </span>
            <button @click="showModal = false" class="text-stone-300 hover:text-stone-500 text-2xl">×</button>
          </div>
          <div class="p-8 space-y-6">
            <div class="flex bg-stone-200 p-1 rounded-2xl">
              <button @click="form.type = '支出'" class="flex-1 py-2 rounded-xl text-sm font-bold transition-all" :class="form.type === '支出' ? 'bg-white text-stone-800 shadow-sm' : 'text-stone-500'">支出</button>
              <button @click="form.type = '收入'" class="flex-1 py-2 rounded-xl text-sm font-bold transition-all" :class="form.type === '收入' ? 'bg-emerald-100 text-emerald-700 shadow-sm' : 'text-stone-500'">收入</button>
            </div>
            <div class="relative">
              <span class="absolute left-0 bottom-2 text-2xl font-bold text-stone-300">¥</span>
              <input type="number" v-model.number="form.amount" class="w-full bg-transparent text-4xl font-bold text-stone-800 border-b-2 border-stone-200 focus:border-stone-800 outline-none py-1 pl-8 text-right" placeholder="0.00">
            </div>
            <div v-if="form.type === '支出'" class="space-y-2">
              <label class="text-xs font-bold text-stone-400 uppercase">分类</label>
              <div class="grid grid-cols-3 gap-2">
                <div v-for="c in expenseCategories" :key="c" @click="form.category = c"
                  class="cursor-pointer text-center py-2 rounded-xl text-xs font-bold transition-all border-2"
                  :class="form.category === c ? 'border-stone-800 bg-stone-800 text-white' : 'border-stone-100 bg-white text-stone-500 hover:border-stone-300'">
                  {{ c }}
                </div>
              </div>
            </div>
            <div class="flex gap-4">
              <input type="date" v-model="form.date" class="flex-1 bg-white border border-stone-200 p-3 rounded-xl text-sm text-stone-600 outline-none focus:border-stone-400">
              <input type="text" v-model="form.note" class="flex-[1.5] bg-white border border-stone-200 p-3 rounded-xl text-sm text-stone-600 outline-none focus:border-stone-400" placeholder="备注...">
            </div>
          </div>
          <div class="p-6 pt-0">
            <button @click="handleSubmit" class="w-full bg-stone-800 text-[#FAFAF9] py-4 rounded-2xl font-bold text-lg hover:bg-stone-900 shadow-xl transition">确认</button>
          </div>
        </div>
      </div>

      <!-- 导出 Modal -->
      <div v-if="showExportModal" class="fixed inset-0 bg-stone-800/40 backdrop-blur-sm flex items-center justify-center z-50">
        <div class="bg-white p-6 rounded-3xl shadow-2xl w-80">
          <h3 class="font-bold text-stone-800 text-lg mb-4">选择导出范围</h3>
          <div class="space-y-3">
            <button @click="handleExport('current')" class="w-full py-4 px-4 bg-teal-50 text-teal-700 rounded-xl hover:bg-teal-100 font-bold flex items-center justify-between group transition">
              <span>导出当前视图 ({{ viewMode==='month'?format(currentDate,'MM月'):format(currentDate,'yyyy年') }})</span>
              <span class="opacity-0 group-hover:opacity-100 transition-opacity">↓</span>
            </button>
            <button @click="handleExport('all')" class="w-full py-4 px-4 bg-stone-50 text-stone-700 rounded-xl hover:bg-stone-100 font-bold flex items-center justify-between group transition">
              <span>导出所有数据</span>
              <span class="opacity-0 group-hover:opacity-100 transition-opacity">↓</span>
            </button>
          </div>
          <button @click="showExportModal = false" class="mt-6 w-full text-stone-400 hover:text-stone-600 text-sm">取消</button>
        </div>
      </div>

      <!-- 导入确认 Modal -->
      <div v-if="showImportModal" class="fixed inset-0 bg-stone-800/40 backdrop-blur-sm flex items-center justify-center z-50">
        <div class="bg-white p-6 rounded-3xl shadow-2xl w-80">
          <h3 class="font-bold text-stone-800 text-lg mb-4">确认导入?</h3>
          <p class="text-stone-500 mb-2">文件解析成功，准备导入：</p>
          <div class="text-4xl font-bold text-teal-600 mb-2">{{ importPreview.count }} <span class="text-sm text-stone-400 font-normal">条记录</span></div>
          <p class="text-xs text-stone-400 mb-6">请确认数据无误，导入过程不可逆。</p>
          <div class="flex justify-end gap-3">
            <button @click="showImportModal = false" class="px-4 py-2 text-stone-400 hover:text-stone-600 text-sm font-bold">取消</button>
            <button @click="confirmImport" class="px-6 py-2 bg-stone-800 text-white rounded-xl hover:bg-stone-900 font-bold text-sm transition shadow-lg">确认导入</button>
          </div>
        </div>
      </div>

      <!-- 导入成功提示 Modal (新增) -->
      <div v-if="showImportSuccessModal" class="fixed inset-0 bg-stone-800/40 backdrop-blur-sm flex items-center justify-center z-[60]">
        <div class="bg-white p-8 rounded-[2rem] shadow-2xl w-80 text-center transform transition-all scale-100">
          <div class="w-16 h-16 bg-emerald-100 text-emerald-500 rounded-full flex items-center justify-center mx-auto mb-4 text-3xl">✓</div>
          <h3 class="font-bold text-stone-800 text-xl mb-2">导入成功!</h3>
          <p class="text-stone-500 mb-6">数据已安全写入数据库。</p>
          <button @click="showImportSuccessModal = false" class="w-full py-3 bg-stone-800 text-white rounded-xl font-bold hover:bg-stone-900 transition">知道了</button>
        </div>
      </div>

      <!-- 删除确认 Modal -->
      <div v-if="showDeleteConfirm" class="fixed inset-0 bg-stone-900/20 backdrop-blur-sm flex items-center justify-center z-[70]">
        <div class="bg-white p-6 rounded-3xl shadow-xl w-80">
          <h3 class="font-bold text-stone-800 text-lg mb-2">确认删除?</h3>
          <p class="text-sm text-stone-500 mb-6">删除后无法恢复。</p>
          <div class="flex justify-end gap-3">
            <button @click="showDeleteConfirm = false" class="px-4 py-2 text-stone-400 hover:text-stone-600 font-bold text-sm">取消</button>
            <button @click="executeDelete" class="px-6 py-2 bg-red-50 text-red-500 rounded-xl hover:bg-red-100 font-bold text-sm transition">删除</button>
          </div>
        </div>
      </div>

    </template>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background-color: #e5e7eb; border-radius: 20px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background-color: #d1d5db; }
</style>