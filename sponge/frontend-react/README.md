# 🧽 Sponge Frontend - React 现代化前端

## 技术栈

- **框架**: React 18 + TypeScript
- **构建工具**: Vite 5
- **状态管理**: Zustand
- **数据获取**: TanStack Query (React Query)
- **路由**: React Router v6
- **样式**: Tailwind CSS
- **HTTP 客户端**: Axios
- **通知**: React Hot Toast
- **图标**: Lucide React
- **图表**: Recharts

## 快速开始

### 前置要求

- Node.js >= 18
- npm >= 9

### 安装依赖

```bash
cd frontend-react
npm install
```

### 配置环境变量

复制环境变量示例文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置 API 地址：

```env
VITE_API_BASE_URL=http://localhost:8000
```

### 开发模式

```bash
npm run dev
```

访问 http://localhost:3000

### 生产构建

```bash
npm run build
npm run preview
```

## 项目结构

```
frontend-react/
├── public/              # 静态资源
├── src/
│   ├── components/      # React 组件
│   │   ├── common.tsx   # 通用 UI 组件
│   │   ├── LoginPage.tsx
│   │   └── Dashboard.tsx
│   ├── pages/           # 页面组件
│   ├── hooks/           # 自定义 Hooks
│   │   ├── useTasks.ts  # 任务相关 Hooks
│   │   └── useUtils.ts  # 工具函数
│   ├── services/        # API 服务层
│   │   ├── api.ts       # Axios 配置
│   │   └── taskService.ts
│   ├── store/           # Zustand 状态管理
│   │   └── index.ts
│   ├── styles/          # 样式文件
│   │   └── index.css
│   └── main.tsx         # 入口文件
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
└── postcss.config.js
```

## 核心功能

### 1. 用户认证
- JWT Token 认证
- 登录/登出
- 受保护的路由

### 2. 任务管理
- 创建新任务
- 查看任务列表
- 任务详情展示
- 实时状态更新

### 3. 系统监控
- API 健康检查
- 任务统计
- Worker 状态（待实现）

### 4. 多智能体协作展示
- Planner/Coder/Reviewer/Tester 执行结果
- 代码高亮显示
- 文件下载

## API 集成

前端通过 Axios 与后端 FastAPI 通信，所有 API 请求都包含：

- JWT Token 认证头
- 统一的错误处理
- 请求/响应拦截器

## 状态管理

使用 Zustand 进行全局状态管理：

- **AuthStore**: 用户认证状态
- **TaskStore**: 任务相关状态
- **UIStore**: UI 状态（暗色模式、侧边栏等）

## 开发规范

### 代码风格

- 使用 TypeScript 严格模式
- 遵循 ESLint 规则
- 组件使用函数式写法
- 使用 Tailwind CSS 进行样式开发

### 提交规范

```bash
feat: 新功能
fix: 修复 bug
docs: 文档更新
style: 代码格式调整
refactor: 重构
test: 测试相关
chore: 构建/工具链相关
```

## 后续计划

### 第三阶段功能

- [ ] 任务模板市场
- [ ] 可视化工作流编辑器
- [ ] 实时日志流
- [ ] 团队协作功能
- [ ] 权限管理系统
- [ ] 审计日志
- [ ] 企业级 SSO 集成

### 性能优化

- [ ] 代码分割
- [ ] 懒加载
- [ ] 虚拟滚动
- [ ] Service Worker 缓存

## 故障排查

### 常见问题

**无法连接 API**
- 检查后端服务是否启动
- 确认 `.env` 中的 API 地址正确
- 检查 CORS 配置

**登录失败**
- 确认后端 auth 接口正常工作
- 检查数据库用户数据
- 默认账号：admin / admin123

## 许可证

MIT License
