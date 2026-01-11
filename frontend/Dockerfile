FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/node:22-alpine3.21-linuxarm64

WORKDIR /app

# 先拷贝 package.json 安装依赖
COPY package*.json ./
RUN npm install

# 这里不再 COPY 源代码，也不运行 build
# 因为我们会通过 docker-compose 把代码“挂载”进去

# 暴露 Vite 默认端口
EXPOSE 5173

# 启动开发服务器 (--host 0.0.0.0 让外部能访问)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]