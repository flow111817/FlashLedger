import axios from 'axios'
// 这里的 IP 地址稍后通过 .env 配置
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const api = axios.create({ baseURL: API_URL })
export default api