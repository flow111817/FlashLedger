// src/lib/pb.js
import PocketBase from 'pocketbase';

// 连接本地后端的地址
export const pb = new PocketBase('http://127.0.0.1:8090');