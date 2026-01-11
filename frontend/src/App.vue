<script setup>
import { ref, onMounted, computed, reactive, watch } from 'vue'
import { 
  format, startOfMonth, endOfMonth, eachDayOfInterval, 
  parseISO, isValid, isWithinInterval, differenceInCalendarDays, max 
} from 'date-fns'
import * as XLSX from 'xlsx'
import { Pie, Line } from 'vue-chartjs'
import { 
  Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, 
  LinearScale, PointElement, LineElement, Filler 
} from 'chart.js'

// 注册 ChartJS 组件
ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, PointElement, LineElement, Filler)

// --- 自定义 ChartJS 插件：在平均线上绘制数值 ---
const drawAverageLabels = {
  id: 'drawAverageLabels',
  afterDatasetsDraw(chart) {
    const { ctx, data, chartArea: { left, right, top, bottom, width, height } } = chart
    
    chart.data.datasets.forEach((dataset, i) => {
      // 只针对 label 包含 "平均" 的数据集绘制
      if (dataset.label && dataset.label.includes('平均') && !dataset.hidden) {
        const meta = chart.getDatasetMeta(i)
        // 获取最后一点的 Y 轴坐标（因为是水平线，Y轴是一样的）
        // 如果数据全被隐藏了，meta.data 可能为空
        if(meta.data.length > 0) {
           const y = meta.data[0].y
           const value = dataset.data[0]
           
           if(value > 0) {
             ctx.save()
             ctx.fillStyle = '#9ca3af' // text-stone-400
             ctx.font = 'bold 10px sans-serif'
             ctx.textAlign = 'right'
             ctx.textBaseline = 'bottom'
             // 在线条最右侧上方绘制
             ctx.fillText(value.toFixed(1), right - 5, y - 5)
             ctx.restore()
           }
        }
      }
    })
  }
}

// 注册插件
ChartJS.register(drawAverageLabels)

// --- 全局配置 ---
const API_BASE = `http://${window.location.hostname}:8000`

// ==========================================
// 1. 状态管理
// ==========================================
const ledgers = ref([])
const currentLedger = ref(null) 
const allTransactions = ref([])
const isLoading = ref(false)

const currentTab = ref('dashboard')
const dateRange = reactive({
  start: format(startOfMonth(new Date()), 'yyyy-MM-dd'),
  end: format(endOfMonth(new Date()), 'yyyy-MM-dd')
})

// 筛选状态
const searchQuery = ref('')
const filterMinAmount = ref('')
const filterMaxAmount = ref('')
const filterCategories = ref([])
const showFilters = ref(false)

// 模态框状态
const showCreateLedgerModal = ref(false)
const showDeleteLedgerModal = ref(false)
const showBudgetModal = ref(false) 
const showTransactionModal = ref(false)
const showExportModal = ref(false)
const showImportModal = ref(false)
const showImportSuccessModal = ref(false)
const showDeleteTransConfirm = ref(false)

// 编辑/操作中介
const newLedgerName = ref('')
const editingBudget = ref(0)
const ledgerToDelete = ref(null)
const isEditing = ref(false)
const editingTransId = ref(null)
const deleteTransId = ref(null)
const importPreview = ref({ count: 0, data: [] })
const fileInput = ref(null)

// 表单数据
const form = reactive({
  amount: '',
  category: '必要饮食',
  type: '支出',
  date: format(new Date(), 'yyyy-MM-dd'),
  note: ''
})

// 配置常量 (根据要求精简)
const expenseCategories = ['必要饮食', '次要饮食', '交通出行', '休闲娱乐', '生活消费', '医疗保健']
// 收入分类逻辑上只保留工资薪金，UI上不展示选择
const INCOME_DEFAULT_CATEGORY = '工资薪金'

const categoryColors = {
  '必要饮食': 'bg-orange-100 text-orange-600',
  '次要饮食': 'bg-yellow-100 text-yellow-600',
  '交通出行': 'bg-blue-100 text-blue-600',
  '休闲娱乐': 'bg-purple-100 text-purple-600',
  '生活消费': 'bg-pink-100 text-pink-600',
  '医疗保健': 'bg-red-100 text-red-600',
  '工资薪金': 'bg-emerald-100 text-emerald-600',
  'default': 'bg-stone-100 text-stone-600'
}

const getCategoryColor = (cat, type) => {
  if (type === '收入') return categoryColors['工资薪金']
  return categoryColors[cat] || categoryColors['default']
}

// ==========================================
// 2. 核心逻辑
// ==========================================

// 日期验证与修复
const validateDateRange = () => {
  if (!dateRange.start || !dateRange.end) return
  const start = parseISO(dateRange.start)
  const end = parseISO(dateRange.end)
  
  if (isValid(start) && isValid(end) && start > end) {
    // 自动交换
    const temp = dateRange.start
    dateRange.start = dateRange.end
    dateRange.end = temp
  }
}

const loadLedgers = async () => {
  try {
    const res = await fetch(`${API_BASE}/ledgers`)
    if (res.ok) {
      ledgers.value = await res.json()
      const cachedId = localStorage.getItem('currentLedgerId')
      if (cachedId) {
        const found = ledgers.value.find(l => l.id == cachedId)
        if (found) selectLedger(found)
        else if (ledgers.value.length > 0) selectLedger(ledgers.value[0])
      } else if (ledgers.value.length > 0) {
        selectLedger(ledgers.value[0])
      }
    }
  } catch (err) { console.error(err) }
}

const selectLedger = (ledger) => {
  currentLedger.value = ledger
  localStorage.setItem('currentLedgerId', ledger.id)
  fetchData()
}

const createLedger = async () => {
  if (!newLedgerName.value) return
  try {
    await fetch(`${API_BASE}/ledgers`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newLedgerName.value, budget: 0 })
    })
    newLedgerName.value = ''
    showCreateLedgerModal.value = false
    await loadLedgers()
  } catch (e) { alert(e.message) }
}

const deleteLedger = async () => {
  if (!ledgerToDelete.value) return
  try {
    await fetch(`${API_BASE}/ledgers/${ledgerToDelete.value}`, { method: 'DELETE' })
    if (currentLedger.value?.id === ledgerToDelete.value) {
      currentLedger.value = null
      allTransactions.value = []
      localStorage.removeItem('currentLedgerId')
    }
    showDeleteLedgerModal.value = false
    await loadLedgers()
  } catch (e) { alert(e.message) }
}

const updateBudget = async () => {
  if (!currentLedger.value) return
  try {
    const res = await fetch(`${API_BASE}/ledgers/${currentLedger.value.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ budget: parseFloat(editingBudget.value) })
    })
    if (res.ok) {
      const updated = await res.json()
      currentLedger.value.budget = updated.budget
      const idx = ledgers.value.findIndex(l => l.id === updated.id)
      if (idx !== -1) ledgers.value[idx] = updated
      showBudgetModal.value = false
    }
  } catch (e) { alert('更新预算失败') }
}

const fetchData = async () => {
  if (!currentLedger.value) return
  isLoading.value = true
  try {
    const res = await fetch(`${API_BASE}/transactions?ledger_id=${currentLedger.value.id}`)
    if (res.ok) allTransactions.value = await res.json()
  } finally { isLoading.value = false }
}

// ==========================================
// 3. 计算与图表
// ==========================================

const filteredTransactions = computed(() => {
  if (!allTransactions.value.length) return []
  const start = parseISO(dateRange.start)
  const end = parseISO(dateRange.end)
  // 简单保护，防止 crash
  if (!isValid(start) || !isValid(end) || start > end) return []

  return allTransactions.value.filter(t => {
    const tDate = parseISO(t.date)
    if (!isValid(tDate) || !isWithinInterval(tDate, { start, end })) return false
    
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase()
      const match = t.note?.toLowerCase().includes(q) || 
                    t.category.toLowerCase().includes(q) || 
                    t.amount.toString().includes(q)
      if (!match) return false
    }
    if (filterMinAmount.value && t.amount < parseFloat(filterMinAmount.value)) return false
    if (filterMaxAmount.value && t.amount > parseFloat(filterMaxAmount.value)) return false
    if (filterCategories.value.length > 0 && !filterCategories.value.includes(t.category)) return false
    return true
  })
})

const stats = computed(() => {
  let income = 0, expense = 0
  filteredTransactions.value.forEach(t => {
    if (t.type === '收入') income += t.amount
    else expense += t.amount
  })
  return { income, expense, balance: income - expense }
})

const budgetProgress = computed(() => {
  if (!currentLedger.value || currentLedger.value.budget <= 0) return 0
  const pct = (stats.value.expense / currentLedger.value.budget) * 100
  return Math.min(pct, 100)
})

const budgetColor = computed(() => {
  const p = budgetProgress.value
  if (p < 80) return 'bg-emerald-400'
  if (p < 100) return 'bg-amber-400'
  return 'bg-red-500'
})

// 热力图数据
const heatmapData = computed(() => {
  const start = parseISO(dateRange.start)
  const end = parseISO(dateRange.end)
  if (!isValid(start) || !isValid(end) || start > end) return []
  
  const days = eachDayOfInterval({ start, end })
  const dailyMap = {}
  let totalExpense = 0
  let expenseDaysCount = 0

  days.forEach(d => { dailyMap[format(d, 'yyyy-MM-dd')] = { income: 0, expense: 0, date: d } })

  filteredTransactions.value.forEach(t => {
    const dStr = t.date.slice(0, 10)
    if (dailyMap[dStr]) {
      if (t.type === '收入') dailyMap[dStr].income += t.amount
      else dailyMap[dStr].expense += t.amount
    }
  })

  Object.values(dailyMap).forEach(v => {
    if (v.expense > 0) {
      totalExpense += v.expense
      expenseDaysCount++
    }
  })
  const avgExpense = expenseDaysCount > 0 ? (totalExpense / expenseDaysCount) : 0

  return days.map(day => {
    const dStr = format(day, 'yyyy-MM-dd')
    const data = dailyMap[dStr]
    const exp = data.expense
    let colorClass = 'bg-stone-100 text-stone-400' 
    
    if (exp > 0) {
      if (exp > avgExpense * 2) colorClass = 'bg-red-500 text-white shadow-md shadow-red-200'
      else if (exp > avgExpense * 1.2) colorClass = 'bg-rose-300 text-rose-900'
      else if (exp > avgExpense * 0.5) colorClass = 'bg-orange-200 text-orange-800'
      else colorClass = 'bg-amber-100 text-amber-800'
    } else if (data.income > 0) {
      colorClass = 'bg-teal-50 text-teal-600 border border-teal-100'
    }

    return { date: day, label: format(day, 'd'), dateStr: dStr, income: data.income, expense: data.expense, colorClass }
  })
})

const pieChartData = computed(() => {
  const map = {}
  filteredTransactions.value.forEach(t => {
    if (t.type === '支出') map[t.category] = (map[t.category] || 0) + t.amount
  })
  return {
    labels: Object.keys(map),
    datasets: [{
      backgroundColor: ['#FCA5A5', '#FDBA74', '#FDE047', '#86EFAC', '#93C5FD', '#C4B5FD', '#F9A8D4', '#E5E7EB'],
      data: Object.values(map), borderWidth: 0
    }]
  }
})

// 折线图数据 (核心修改：平均值逻辑)
const lineChartData = computed(() => {
  const start = parseISO(dateRange.start)
  const end = parseISO(dateRange.end)
  if (!isValid(start) || !isValid(end) || start > end) return { labels: [], datasets: [] }

  const days = eachDayOfInterval({ start, end })
  const labels = days.map(d => format(d, 'MM-dd'))
  const dataMap = {}
  days.forEach(d => dataMap[format(d, 'yyyy-MM-dd')] = { income: 0, expense: 0 })
  
  // 找出记录中的最大日期，用于计算平均值
  let lastRecordDate = start
  let hasRecords = false

  filteredTransactions.value.forEach(t => {
    const d = t.date.slice(0, 10)
    const tDateObj = parseISO(t.date)
    hasRecords = true
    if (tDateObj > lastRecordDate) lastRecordDate = tDateObj // 更新最晚日期
    
    if (dataMap[d]) t.type === '收入' ? dataMap[d].income += t.amount : dataMap[d].expense += t.amount
  })

  const incomeData = Object.values(dataMap).map(v => v.income)
  const expenseData = Object.values(dataMap).map(v => v.expense)

  // 计算天数：从 start 到 lastRecordDate (包含两端)
  const daysCount = hasRecords ? (differenceInCalendarDays(lastRecordDate, start) + 1) : 0

  const avgIncome = daysCount > 0 ? (stats.value.income / daysCount) : 0
  const avgExpense = daysCount > 0 ? (stats.value.expense / daysCount) : 0

  return {
    labels,
    datasets: [
      { label: '收入', data: incomeData, borderColor: '#34D399', backgroundColor: '#34D399', tension: 0.3, pointRadius: 2 },
      { label: '支出', data: expenseData, borderColor: '#F87171', backgroundColor: '#F87171', tension: 0.3, pointRadius: 2 },
      { 
        label: '平均收入', 
        data: Array(days.length).fill(avgIncome), 
        borderColor: '#34D399', borderDash: [5, 5], pointRadius: 0, borderWidth: 1.5,
        hidden: stats.value.income === 0
      },
      { 
        label: '平均支出', 
        data: Array(days.length).fill(avgExpense), 
        borderColor: '#F87171', borderDash: [5, 5], pointRadius: 0, borderWidth: 1.5,
        hidden: stats.value.expense === 0
      }
    ]
  }
})

const groupedTransactions = computed(() => {
  const groups = {}
  filteredTransactions.value.forEach(t => {
    const d = t.date.slice(0, 10)
    if (!groups[d]) groups[d] = { date: d, income: 0, expense: 0, items: [] }
    if (t.type === '收入') groups[d].income += t.amount
    else groups[d].expense += t.amount
    groups[d].items.push(t)
  })
  return Object.values(groups).sort((a, b) => b.date.localeCompare(a.date))
})

// ==========================================
// 4. 操作逻辑
// ==========================================
const openAddModal = () => {
  isEditing.value = false
  form.amount = ''
  form.category = '必要饮食' // 支出默认分类
  form.type = '支出'
  form.date = format(new Date(), 'yyyy-MM-dd')
  form.note = ''
  showTransactionModal.value = true
}

const openEditModal = (t) => {
  isEditing.value = true
  editingTransId.value = t.id
  form.amount = t.amount
  form.type = t.type
  // 如果是收入，category 其实在界面不显示，但数据要有
  form.category = t.category 
  form.date = t.date.slice(0, 10)
  form.note = t.note
  showTransactionModal.value = true
}

const handleSubmit = async () => {
  if (!form.amount || !currentLedger.value) return
  // 核心逻辑：收入强制设为 '工资薪金'
  const finalCategory = form.type === '收入' ? INCOME_DEFAULT_CATEGORY : form.category
  
  const submitData = { ...form, category: finalCategory, ledger_id: currentLedger.value.id }

  try {
    let url = `${API_BASE}/transactions`
    let method = 'POST'
    if (isEditing.value) {
      url = `${API_BASE}/transactions/${editingTransId.value}`
      method = 'PUT'
    }
    const res = await fetch(url, {
      method: method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(submitData)
    })
    if (!res.ok) throw new Error('保存失败')
    showTransactionModal.value = false
    await fetchData()
  } catch (e) { alert('保存失败: ' + e.message) }
}

const confirmDeleteTrans = (id) => {
  deleteTransId.value = id
  showDeleteTransConfirm.value = true
}

const executeDeleteTrans = async () => {
  if (!deleteTransId.value) return
  try {
    const res = await fetch(`${API_BASE}/transactions/${deleteTransId.value}`, { method: 'DELETE' })
    if (!res.ok) throw new Error('删除失败')
    showDeleteTransConfirm.value = false
    deleteTransId.value = null 
    await fetchData()
  } catch (e) { alert(e.message) }
}

const handleExport = (scope) => {
  const sourceData = scope === 'current' ? filteredTransactions.value : allTransactions.value
  if (sourceData.length === 0) return alert('没有数据可导出')
  const data = sourceData.map(t => ({ 日期: t.date.slice(0, 10), 类型: t.type, 分类: t.category, 金额: t.amount, 备注: t.note }))
  const ws = XLSX.utils.json_to_sheet(data)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, "Sheet1")
  XLSX.writeFile(wb, `FlashLedger_${scope}.xlsx`)
  showExportModal.value = false
}

const handleImportFile = (event) => {
  const file = event.target.files[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const data = new Uint8Array(e.target.result)
      const workbook = XLSX.read(data, { type: 'array' })
      const json = XLSX.utils.sheet_to_json(workbook.Sheets[workbook.SheetNames[0]])
      importPreview.value = { count: json.length, data: json }
      showImportModal.value = true
    } catch (err) { alert('文件读取失败') }
    fileInput.value.value = ''
  }
  reader.readAsArrayBuffer(file)
}

const confirmImport = async () => {
  isLoading.value = true
  try {
    for (const row of importPreview.value.data) {
      await fetch(`${API_BASE}/transactions`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          ledger_id: currentLedger.value.id,
          date: row['日期'] || format(new Date(), 'yyyy-MM-dd'),
          type: row['类型'] || '支出',
          category: row['分类'] || '其他',
          amount: row['金额'] || 0,
          note: row['备注'] || ''
        })
      })
    }
    showImportModal.value = false
    showImportSuccessModal.value = true
    await fetchData()
  } finally { isLoading.value = false }
}

onMounted(() => {
  loadLedgers()
})
</script>

<template>
  <div class="flex h-screen w-screen bg-[#FFFBF0] text-stone-600 font-sans overflow-hidden">
    <input type="file" ref="fileInput" accept=".xlsx, .xls" class="hidden" @change="handleImportFile" />
    
    <!-- Loading -->
    <div v-if="isLoading" class="fixed inset-0 z-[100] bg-white/50 backdrop-blur-sm flex items-center justify-center">
      <div class="animate-spin rounded-full h-10 w-10 border-4 border-stone-200 border-t-teal-500"></div>
    </div>

    <!-- Sidebar -->
    <aside class="w-64 flex-shrink-0 bg-[#FAFAF9] border-r border-stone-200 flex flex-col h-full z-20">
      <div class="p-6">
        <div class="flex items-center gap-2 select-none">
          <img src="/logo.png" alt="Logo" class="w-8 h-8 object-contain" />
          <span class="font-bold text-lg bg-gradient-to-r from-amber-400 to-orange-500 bg-clip-text text-transparent translate-y-[2px]">FlashLedger</span>
        </div>
      </div>
      
      <div class="flex-1 overflow-y-auto px-4 space-y-2 custom-scrollbar">
        <div class="text-xs font-bold text-stone-400 mb-3 px-2">我的账本</div>
        <div v-for="ledger in ledgers" :key="ledger.id"
          @click="selectLedger(ledger)"
          class="group flex justify-between items-center p-3 rounded-2xl cursor-pointer transition-all duration-300"
          :class="currentLedger?.id === ledger.id ? 'bg-white shadow-md text-teal-600' : 'hover:bg-stone-100 text-stone-600'">
          <div class="flex items-center gap-3 truncate">
            <div class="w-2 h-2 rounded-full flex-shrink-0" :class="currentLedger?.id === ledger.id ? 'bg-teal-400' : 'bg-stone-300'"></div>
            <span class="font-medium truncate">{{ ledger.name }}</span>
          </div>
          <button @click.stop="ledgerToDelete = ledger.id; showDeleteLedgerModal = true" 
            class="opacity-0 group-hover:opacity-100 text-stone-300 hover:text-red-400 px-2">×</button>
        </div>
      </div>

      <!-- Sidebar Bottom -->
      <div class="p-4 border-t border-stone-100 bg-stone-50/50">
        <button @click="showFilters = !showFilters" class="w-full py-2 bg-white border border-stone-200 rounded-xl text-xs font-bold text-stone-500 hover:text-stone-800 flex items-center justify-center gap-2 shadow-sm">
          <span>{{ showFilters ? '收起筛选' : '展开高级筛选' }}</span>
          <span>{{ showFilters ? '↓' : '↑' }}</span>
        </button>
        
        <div v-if="showFilters" class="mt-3 space-y-3 transition-all">
          <input v-model="searchQuery" placeholder="搜索备注/分类/金额..." class="w-full text-xs p-2 rounded-lg border border-stone-200 outline-none focus:border-teal-300">
          <div class="flex gap-2">
            <input v-model="filterMinAmount" type="number" placeholder="Min" class="w-1/2 text-xs p-2 rounded-lg border border-stone-200 outline-none">
            <input v-model="filterMaxAmount" type="number" placeholder="Max" class="w-1/2 text-xs p-2 rounded-lg border border-stone-200 outline-none">
          </div>
          <div class="max-h-32 overflow-y-auto custom-scrollbar p-1 bg-white rounded-lg border border-stone-200">
             <div class="text-[10px] text-stone-400 mb-1 px-1">按分类筛选:</div>
             <div v-for="cat in expenseCategories" :key="cat" class="flex items-center gap-2 px-1 py-0.5">
               <input type="checkbox" :value="cat" v-model="filterCategories" class="rounded text-teal-500 focus:ring-0">
               <span class="text-xs">{{ cat }}</span>
             </div>
          </div>
        </div>
      </div>

      <div class="p-4">
        <button @click="showCreateLedgerModal = true" class="w-full bg-stone-800 text-[#FAFAF9] py-3 rounded-xl shadow-lg hover:-translate-y-0.5 transition font-bold text-sm">+ 新建账本</button>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 flex flex-col h-full overflow-hidden relative">
      <div v-if="!currentLedger" class="flex-1 flex flex-col items-center justify-center text-stone-400 gap-4">
        <div class="text-6xl opacity-20">📒</div>
        <p>请选择或创建一个账本</p>
      </div>

      <template v-else>
        <!-- Header -->
        <header class="px-8 pt-8 pb-4 space-y-6 flex-shrink-0">
          <div class="flex items-center justify-between">
            <div class="flex bg-stone-200/50 p-1 rounded-xl">
               <button @click="currentTab = 'dashboard'" class="px-5 py-2 rounded-lg text-sm font-bold transition-all flex items-center gap-2" :class="currentTab === 'dashboard' ? 'bg-white shadow text-stone-800' : 'text-stone-500 hover:text-stone-700'">📊 仪表盘</button>
               <button @click="currentTab = 'list'" class="px-5 py-2 rounded-lg text-sm font-bold transition-all flex items-center gap-2" :class="currentTab === 'list' ? 'bg-white shadow text-stone-800' : 'text-stone-500 hover:text-stone-700'">📝 账单明细</button>
            </div>

            <!-- 日期范围选择器 (修复：添加 @change 验证) -->
            <div class="flex items-center gap-2 bg-white p-1.5 rounded-xl border border-stone-200 shadow-sm">
              <input type="date" v-model="dateRange.start" @change="validateDateRange" class="text-xs font-bold text-stone-600 bg-transparent outline-none cursor-pointer hover:bg-stone-50 rounded px-1">
              <span class="text-stone-300">➜</span>
              <input type="date" v-model="dateRange.end" @change="validateDateRange" class="text-xs font-bold text-stone-600 bg-transparent outline-none cursor-pointer hover:bg-stone-50 rounded px-1">
            </div>

            <div class="flex gap-3">
               <button @click="fileInput.click()" class="px-4 py-2 bg-white border border-stone-200 rounded-xl hover:bg-stone-50 text-xs font-bold shadow-sm">导入</button>
               <button @click="showExportModal = true" class="px-4 py-2 bg-white border border-stone-200 rounded-xl hover:bg-stone-50 text-xs font-bold shadow-sm">导出</button>
               <button @click="openAddModal" class="px-5 py-2 bg-stone-800 text-white rounded-xl shadow-lg hover:-translate-y-0.5 transition font-bold text-sm">+ 记一笔</button>
            </div>
          </div>

          <!-- 概览卡片 -->
          <div class="grid grid-cols-4 gap-6 h-28">
            <div class="bg-red-50 p-4 rounded-3xl border border-red-100 flex flex-col justify-between">
              <div class="text-xs text-red-400 font-bold uppercase">总支出</div>
              <div class="text-2xl font-bold text-stone-800">¥ {{ stats.expense.toFixed(2) }}</div>
            </div>
            <div class="bg-emerald-50 p-4 rounded-3xl border border-emerald-100 flex flex-col justify-between">
              <div class="text-xs text-emerald-500 font-bold uppercase">总收入</div>
              <div class="text-2xl font-bold text-stone-800">¥ {{ stats.income.toFixed(2) }}</div>
            </div>
            <div class="bg-white p-4 rounded-3xl border border-stone-100 flex flex-col justify-between">
              <div class="text-xs text-stone-400 font-bold uppercase">结余</div>
              <div class="text-2xl font-bold" :class="stats.balance >= 0 ? 'text-stone-800' : 'text-red-500'">¥ {{ stats.balance.toFixed(2) }}</div>
            </div>
            
            <!-- 预算卡片 -->
            <div class="bg-white p-4 rounded-3xl border border-stone-100 flex flex-col justify-between relative overflow-hidden group">
              <div class="flex justify-between items-start z-10">
                <div class="text-xs text-stone-400 font-bold uppercase">本月预算</div>
                <button @click="editingBudget = currentLedger.budget; showBudgetModal = true" class="text-xs text-stone-300 hover:text-stone-600 underline">设置</button>
              </div>
              <div class="z-10">
                <div class="flex justify-between items-end mb-1">
                  <span class="text-xl font-bold text-stone-800">¥ {{ currentLedger.budget.toFixed(0) }}</span>
                  <span class="text-xs text-stone-400">{{ budgetProgress.toFixed(0) }}%</span>
                </div>
                <div class="w-full h-2 bg-stone-100 rounded-full overflow-hidden">
                  <div class="h-full transition-all duration-500" :class="budgetColor" :style="{ width: `${budgetProgress}%` }"></div>
                </div>
              </div>
            </div>
          </div>
        </header>

        <!-- 内容区域 -->
        <div class="flex-1 overflow-hidden px-8 pb-8">
          
          <!-- 仪表盘 -->
          <div v-if="currentTab === 'dashboard'" class="h-full overflow-y-auto pb-20 space-y-6 custom-scrollbar pr-2">
            <div class="bg-white p-6 rounded-3xl shadow-sm border border-stone-100 h-80 w-full">
              <h3 class="font-bold text-stone-700 mb-4 text-sm">📈 收支趋势</h3>
              <div class="h-64"><Line :data="lineChartData" :options="{ responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'top', align: 'end' } }, scales: { x: { grid: { display: false } }, y: { grid: { borderDash: [4, 4], color: '#f3f4f6' } } } }" /></div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
               <div class="bg-white p-6 rounded-3xl shadow-sm border border-stone-100 h-80">
                  <h3 class="font-bold text-stone-700 mb-4 text-sm">🍕 支出结构</h3>
                  <div class="h-60 relative">
                     <Pie :data="pieChartData" :options="{ responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right', labels: { boxWidth: 12, usePointStyle: true } } } }" />
                     <div v-if="stats.expense === 0" class="absolute inset-0 flex items-center justify-center text-stone-300 text-sm">暂无支出</div>
                  </div>
               </div>

               <div class="bg-white p-6 rounded-3xl shadow-sm border border-stone-100 h-80 overflow-y-auto custom-scrollbar">
                  <div class="flex justify-between items-center mb-4">
                    <h3 class="font-bold text-stone-700 text-sm">📅 记账热力图</h3>
                    <div class="flex gap-1 text-[10px] text-stone-400">
                      <span class="px-1 bg-amber-100 text-amber-800 rounded">低</span>
                      <span class="px-1 bg-orange-200 text-orange-800 rounded">中</span>
                      <span class="px-1 bg-rose-300 text-rose-900 rounded">高</span>
                      <span class="px-1 bg-red-500 text-white rounded">极高</span>
                    </div>
                  </div>
                  
                  <div class="flex flex-wrap gap-2 content-start">
                    <div v-for="day in heatmapData" :key="day.dateStr" 
                      class="relative group w-10 h-10 rounded-lg flex items-center justify-center text-xs font-bold cursor-default transition hover:scale-110 shadow-sm"
                      :class="day.colorClass">
                      {{ day.label }}
                      <div class="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 bg-stone-800 text-white text-[10px] px-2 py-1 rounded shadow-lg opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-10 transition-opacity">
                        <div class="font-bold text-stone-300">{{ day.dateStr }}</div>
                        <div v-if="day.expense > 0" class="text-rose-300">支: {{ day.expense }}</div>
                        <div v-if="day.income > 0" class="text-emerald-300">收: {{ day.income }}</div>
                        <div v-if="day.income===0 && day.expense===0">无记录</div>
                      </div>
                    </div>
                  </div>
               </div>
            </div>
          </div>

          <!-- 分组列表视图 -->
          <div v-else class="h-full bg-white rounded-3xl shadow-sm border border-stone-100 overflow-hidden flex flex-col">
            <div class="flex-1 overflow-auto custom-scrollbar p-6">
              <div v-if="groupedTransactions.length === 0" class="text-center text-stone-300 py-20">这里空空如也</div>
              <div v-else class="space-y-6">
                <div v-for="group in groupedTransactions" :key="group.date" class="border border-stone-100 rounded-2xl overflow-hidden shadow-sm">
                  <div class="bg-stone-50 px-5 py-3 flex justify-between items-center border-b border-stone-100">
                    <div class="flex items-center gap-2">
                      <span class="font-bold text-stone-700">{{ group.date }}</span>
                      <span class="text-xs text-stone-400">{{ format(parseISO(group.date), 'EEEE', { locale: undefined }) }}</span>
                    </div>
                    <div class="flex gap-4 text-xs font-mono font-bold">
                      <span v-if="group.income > 0" class="text-emerald-500">+{{ group.income.toFixed(2) }}</span>
                      <span v-if="group.expense > 0" class="text-red-400">-{{ group.expense.toFixed(2) }}</span>
                    </div>
                  </div>
                  <div class="divide-y divide-stone-50">
                    <div v-for="t in group.items" :key="t.id" class="p-4 flex items-center hover:bg-[#FFFBF0] transition group/item">
                      <div class="w-10 h-10 rounded-full flex items-center justify-center text-lg mr-4" :class="getCategoryColor(t.category, t.type).split(' ')[0]">
                        {{ t.category[0] }}
                      </div>
                      <div class="flex-1">
                        <div class="flex items-center gap-2">
                          <span class="text-sm font-bold text-stone-700">{{ t.category }}</span>
                          <span v-if="t.type==='收入'" class="text-[10px] bg-emerald-100 text-emerald-600 px-1 rounded">收</span>
                        </div>
                        <div class="text-xs text-stone-400 mt-0.5 max-w-[200px] truncate">{{ t.note || '无备注' }}</div>
                      </div>
                      <div class="font-mono font-bold mr-6" :class="t.type === '收入' ? 'text-emerald-500' : 'text-stone-700'">
                        {{ t.amount.toFixed(2) }}
                      </div>
                      <div class="flex gap-2 opacity-0 group-hover/item:opacity-100 transition">
                         <button @click="openEditModal(t)" class="p-1.5 text-stone-400 hover:text-teal-500 bg-white border border-stone-200 rounded-lg">✎</button>
                         <button @click="confirmDeleteTrans(t.id)" class="p-1.5 text-stone-400 hover:text-red-500 bg-white border border-stone-200 rounded-lg">🗑</button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </main>

    <!-- Modals -->
    <!-- 1. 新建账本 -->
    <div v-if="showCreateLedgerModal" class="fixed inset-0 bg-stone-900/30 backdrop-blur-sm flex items-center justify-center z-[80]">
      <div class="bg-white p-6 rounded-3xl shadow-2xl w-80">
        <h3 class="font-bold text-stone-700 mb-4">新建账本</h3>
        <input v-model="newLedgerName" class="w-full bg-stone-50 p-3 rounded-xl mb-6 outline-none focus:ring-2 focus:ring-teal-200" placeholder="例如: 2025生活账..." autofocus @keyup.enter="createLedger">
        <div class="flex justify-end gap-3">
          <button @click="showCreateLedgerModal = false" class="text-stone-400 hover:text-stone-600 text-sm">取消</button>
          <button @click="createLedger" class="px-5 py-2 bg-stone-800 text-white rounded-xl shadow-lg text-sm font-bold">创建</button>
        </div>
      </div>
    </div>

    <!-- 2. 删除账本 -->
    <div v-if="showDeleteLedgerModal" class="fixed inset-0 bg-stone-900/30 backdrop-blur-sm flex items-center justify-center z-[80]">
      <div class="bg-white p-6 rounded-3xl shadow-2xl w-80">
        <h3 class="font-bold text-stone-800 mb-2">删除账本?</h3>
        <p class="text-xs text-stone-500 mb-6">所有数据将永久消失。</p>
        <div class="flex justify-end gap-3">
          <button @click="showDeleteLedgerModal = false" class="text-stone-400 hover:text-stone-600 text-sm">取消</button>
          <button @click="deleteLedger" class="px-5 py-2 bg-red-500 text-white rounded-xl shadow-lg text-sm font-bold">删除</button>
        </div>
      </div>
    </div>

    <!-- 3. 设置预算 -->
    <div v-if="showBudgetModal" class="fixed inset-0 bg-stone-900/30 backdrop-blur-sm flex items-center justify-center z-[80]">
      <div class="bg-white p-6 rounded-3xl shadow-2xl w-80">
        <h3 class="font-bold text-stone-800 mb-4">设置本月预算</h3>
        <div class="relative mb-6">
           <span class="absolute left-3 top-2.5 text-stone-400">¥</span>
           <input type="number" v-model="editingBudget" class="w-full bg-stone-50 pl-8 p-2 rounded-xl outline-none font-bold text-stone-700 border border-stone-200 focus:border-stone-800">
        </div>
        <div class="flex justify-end gap-3">
          <button @click="showBudgetModal = false" class="text-stone-400 hover:text-stone-600 text-sm">取消</button>
          <button @click="updateBudget" class="px-5 py-2 bg-stone-800 text-white rounded-xl shadow-lg text-sm font-bold">保存</button>
        </div>
      </div>
    </div>

    <!-- 4. 记账弹窗 (核心修改：精简分类) -->
    <div v-if="showTransactionModal" class="fixed inset-0 bg-stone-800/40 backdrop-blur-sm flex items-center justify-center z-[80]">
      <div class="bg-[#FFFBF0] rounded-[2rem] shadow-2xl w-96 overflow-hidden border-4 border-white">
        <div class="px-8 py-4 bg-white flex justify-between items-center border-b border-stone-100">
          <span class="font-bold text-lg text-stone-800">{{ isEditing ? '修改' : '记一笔' }}</span>
          <button @click="showTransactionModal = false" class="text-stone-300 hover:text-stone-500 text-2xl">×</button>
        </div>
        <div class="p-8 space-y-6">
          <div class="flex bg-stone-200 p-1 rounded-2xl">
            <button @click="form.type = '支出'" class="flex-1 py-2 rounded-xl text-sm font-bold transition" :class="form.type === '支出' ? 'bg-white text-stone-800 shadow-sm' : 'text-stone-500'">支出</button>
            <button @click="form.type = '收入'" class="flex-1 py-2 rounded-xl text-sm font-bold transition" :class="form.type === '收入' ? 'bg-emerald-100 text-emerald-700 shadow-sm' : 'text-stone-500'">收入</button>
          </div>
          <div class="relative">
            <span class="absolute left-0 bottom-2 text-2xl font-bold text-stone-300">¥</span>
            <input type="number" v-model.number="form.amount" class="w-full bg-transparent text-4xl font-bold text-stone-800 border-b-2 border-stone-200 focus:border-stone-800 outline-none py-1 pl-8 text-right" placeholder="0.00">
          </div>
          
          <!-- 分类选择：如果是收入，直接隐藏 -->
          <div v-if="form.type === '支出'" class="space-y-2">
            <label class="text-[10px] font-bold text-stone-400 uppercase">分类</label>
            <div class="grid grid-cols-3 gap-2">
              <div v-for="c in expenseCategories" :key="c" @click="form.category = c"
                class="cursor-pointer text-center py-1.5 rounded-lg text-[10px] font-bold transition border"
                :class="form.category === c ? 'border-stone-800 bg-stone-800 text-white' : 'border-stone-100 bg-white text-stone-500 hover:border-stone-300'">
                {{ c }}
              </div>
            </div>
          </div>
          <div v-else class="text-center text-sm text-stone-400 py-4">
             默认分类：<span class="text-emerald-600 font-bold">工资薪金</span>
          </div>

          <div class="flex gap-4">
            <input type="date" v-model="form.date" class="flex-1 bg-white border border-stone-200 p-2 rounded-xl text-sm outline-none">
            <input type="text" v-model="form.note" class="flex-[1.5] bg-white border border-stone-200 p-2 rounded-xl text-sm outline-none" placeholder="备注...">
          </div>
        </div>
        <div class="p-6 pt-0">
          <button @click="handleSubmit" class="w-full bg-stone-800 text-[#FAFAF9] py-3 rounded-2xl font-bold text-lg hover:bg-stone-900 shadow-xl transition">确认</button>
        </div>
      </div>
    </div>

    <!-- 5. 导出/导入/确认弹窗 -->
    <div v-if="showExportModal" class="fixed inset-0 bg-stone-800/40 backdrop-blur-sm flex items-center justify-center z-[80]">
      <div class="bg-white p-6 rounded-3xl shadow-2xl w-72 space-y-3">
        <h3 class="font-bold text-stone-800 mb-2">导出 Excel</h3>
        <button @click="handleExport('current')" class="w-full py-3 bg-teal-50 text-teal-700 rounded-xl hover:bg-teal-100 font-bold text-sm text-left px-4">导出当前筛选视图</button>
        <button @click="handleExport('all')" class="w-full py-3 bg-stone-50 text-stone-700 rounded-xl hover:bg-stone-100 font-bold text-sm text-left px-4">导出全部数据</button>
        <button @click="showExportModal = false" class="w-full text-center text-stone-400 text-xs mt-2">取消</button>
      </div>
    </div>

    <div v-if="showImportModal" class="fixed inset-0 bg-stone-800/40 backdrop-blur-sm flex items-center justify-center z-[80]">
      <div class="bg-white p-6 rounded-3xl shadow-2xl w-80">
        <h3 class="font-bold text-stone-800 mb-2">确认导入</h3>
        <div class="text-3xl font-bold text-teal-600 mb-4">{{ importPreview.count }} <span class="text-sm text-stone-400 font-normal">条</span></div>
        <div class="flex justify-end gap-3">
          <button @click="showImportModal = false" class="text-stone-400 hover:text-stone-600 text-sm">取消</button>
          <button @click="confirmImport" class="px-5 py-2 bg-stone-800 text-white rounded-xl text-sm font-bold">确认</button>
        </div>
      </div>
    </div>

    <div v-if="showImportSuccessModal" class="fixed inset-0 bg-stone-800/40 backdrop-blur-sm flex items-center justify-center z-[80]">
       <div class="bg-white p-6 rounded-3xl w-64 text-center">
         <div class="text-4xl mb-2">🎉</div>
         <h3 class="font-bold text-stone-800 mb-4">导入成功</h3>
         <button @click="showImportSuccessModal = false" class="w-full py-2 bg-stone-800 text-white rounded-xl text-sm font-bold">好的</button>
       </div>
    </div>

    <div v-if="showDeleteTransConfirm" class="fixed inset-0 bg-stone-900/20 backdrop-blur-sm flex items-center justify-center z-[80]">
      <div class="bg-white p-6 rounded-3xl shadow-xl w-72">
        <h3 class="font-bold text-stone-800 mb-2">删除此记录?</h3>
        <div class="flex justify-end gap-3 mt-4">
          <button @click="showDeleteTransConfirm = false" class="text-stone-400 hover:text-stone-600 text-sm">取消</button>
          <button @click="executeDeleteTrans" class="px-4 py-2 bg-red-500 text-white rounded-xl font-bold text-sm">删除</button>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background-color: #e5e7eb; border-radius: 20px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background-color: #d1d5db; }
</style>