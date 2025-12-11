# ⚡ FlashLedger

> **极致速度 · 绝对隐私 · 极简主义**
>
> 一款基于 Windows 本地的个人记账应用，拒绝云端上传，数据完全掌握在自己手中。

## 📖 项目简介

**FlashLedger** 是一款专为 Windows 用户打造的本地化记账工具。它结合了 **Vue 3** 的现代化交互体验与 **PocketBase** 的轻量级后端能力。

**核心理念：**

*   **隐私第一**：所有数据存储在本地（Localhost），无需联网，没有隐私泄露风险。
*   **极致轻量**：基于单一 `.exe` 后端和静态前端，双击即用，零延迟启动。
*   **温和交互**：摒弃冰冷的金融感，采用柔和色调，圆角设计，让记账充满生活气息。

**演示：**

<video src="E:\desktop\Project\FlashLedger\demo.mp4"></video>

## ✨ 核心功能

### 📊 数据可视化与仪表盘
*   **多维度图表**：收支趋势折线图、支出结构饼状图。
*   **记账日历**：在仪表盘直观展示每月记账打卡情况（月视图）。
*   **全景视图**：支持切换 **月度 / 年度 / 总览** 视图，跨度分析财务状况。

### 📒 账本与分类管理
*   **多账本支持**：工作、生活、旅行账本独立管理。
*   **自定义分类**：灵活配置收入/支出分类，满足不同记账习惯。

### 📝 极速记账体验
*   **快捷录入**：支持全键盘操作，模态对话框快速记一笔。
*   **智能纠错**：收入/支出类型自动匹配，防止分类混淆。
*   **CRUD**：账单明细支持行内**编辑**与**删除**（二次确认），操作便捷。

### 💾 数据导入与导出
*   **Excel 导出**：支持导出选中月份或全部账单为 `.xlsx` 文件。
*   **Excel 导入**：支持将备份文件一键还原，数据迁移无忧。

---

## 🛠️ 技术栈

*   **前端**：Vue 3 + ECharts (图表)
*   **后端/数据库**：PocketBase (Go语言编写的单文件后端，集成 SQLite)
*   **脚本**：Windows Batch Script (.bat) 实现一键自动化启动

---

## 🚀 快速启动 (Quick Start)

本项目设计为开箱即用，只需简单几步即可运行。

### 1. 环境准备
*   [Git](https://git-scm.com/)

### 2. 获取代码
```bash
git clone https://github.com/flow111817/FlashLedger.git
cd FlashLedger
```

### 3. 安装npm
1.  **安装前端依赖**：
  
    ```bash
    cd flash-ledger-web
    # 下载对应版本msi安装包
    curl -o node.msi https://nodejs.org/dist/v24.11.1/node-v24.11.1-x64.msi
    # 后台安装 Node.js
    msiexec /i node.msi /passive
    ```

### 4. 一键启动
在项目根目录下，直接双击运行脚本：

👉 **`run.bat`** 

脚本将自动执行以下操作：
1.  启动 PocketBase 后端服务。
2.  启动 Vue 前端开发服务器。
3.  自动打开默认浏览器访问 `http://localhost:5173`。

---

## 📂 目录结构

```text
FlashLedger/
├── flash-ledger-web/      # 前端源代码 (Vue 3)
│   ├── src/               # 页面、组件、逻辑
│   ├── public/            # 静态资源
│   └── package.json       # 依赖配置
├── pocketbase/            # 后端程序目录
│   ├── pocketbase.exe     # 后端核心程序
│   └── pb_data/           # [自动生成] 数据库文件，你的所有账单都在这里
└── run.bat # 一键启动脚本
```

---

## ⚠️ 常见问题

**Q: 启动脚本后，显示 'npm' 不是内部或外部命令？**
A: 请确保你安装了 Node.js，并且重启了电脑或命令行窗口以刷新环境变量。

**Q: 导入 Excel 失败？**
A: 请确保导入的 Excel 格式与导出的格式保持一致。

**Q: 如何备份数据？**
A: 只需复制 `pocketbase/pb_data` 文件夹即可备份所有数据。或者使用应用内的“导出”功能。

## 🗺️ 产品规划 (Roadmap)

- [x] **v1.0**: 基础记账、多账本、图表分析、Excel导入导出。
- [ ] **v1.1**: 添加主题自定义，分类自定义功能（开发中。。。）

## 📄 License

MIT License. Designed for personal use.

