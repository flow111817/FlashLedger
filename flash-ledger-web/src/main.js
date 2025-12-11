// src/main.js
import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'

// 引入图表核心
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
} from 'chart.js'

// 注册图表组件
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
)

const app = createApp(App)
app.use(router)
app.mount('#app')