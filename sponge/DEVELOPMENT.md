# Sponge Development Guide

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
cd sponge

# 复制环境变量文件
cp .env.example .env

# 编辑 .env 文件，填入你的 API 密钥等配置
```

### 2. 使用 Docker Compose 启动（推荐）

```bash
# 启动所有服务（PostgreSQL, Redis, API, Worker）
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 3. 本地开发模式

```bash
# 安装依赖
pip install -r requirements.txt

# 启动 PostgreSQL 和 Redis（使用 Docker）
docker-compose up -d postgres redis

# 运行数据库迁移
# alembic upgrade head

# 启动 API 服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 启动 Celery Worker（新终端）
celery -A app.celery_app worker --loglevel=info --concurrency=4
```

## 📁 项目结构

```
sponge/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用入口
│   ├── celery_app.py        # Celery 配置
│   ├── core/                # 核心配置
│   │   ├── config.py        # 环境配置
│   │   └── __init__.py
│   ├── schemas/             # Pydantic 数据模型
│   │   └── __init__.py
│   ├── agents/              # Agent 实现
│   │   ├── planner.py       # 规划 Agent
│   │   ├── coder.py         # 编码 Agent
│   │   ├── reviewer.py      # 审查 Agent
│   │   └── __init__.py
│   ├── tools/               # 工具函数
│   │   ├── file_tools.py    # 文件操作
│   │   ├── code_executor.py # 代码执行
│   │   ├── code_analyzer.py # 代码分析
│   │   └── __init__.py
│   ├── workflow/            # LangGraph 工作流
│   │   ├── graph.py         # 图定义
│   │   ├── nodes.py         # 节点实现
│   │   └── __init__.py
│   └── api/                 # API 路由
│       ├── tasks.py         # 任务接口
│       ├── files.py         # 文件接口
│       └── __init__.py
├── tests/                   # 测试用例
├── sandbox/                 # 沙箱配置
├── configs/                 # 配置文件
├── docker-compose.yml       # Docker 编排
├── Dockerfile               # Docker 镜像
├── requirements.txt         # Python 依赖
├── .env.example             # 环境变量示例
└── README.md                # 项目说明
```

## 🔧 核心模块说明

### Agents (智能体)

Sponge 使用多个专业 Agent 协作完成开发任务：

- **Planner Agent**: 分析需求，拆解任务，制定开发计划
- **Coder Agent**: 根据计划编写代码
- **Reviewer Agent**: 代码审查，质量检查
- **Tester Agent**: 编写和运行测试
- **Deployer Agent**: 部署和发布

### Workflow (工作流)

基于 LangGraph 的状态机工作流：

```
用户请求 → Planner → Coder → Reviewer → Tester → 完成
                    ↑          ↓
                    └──────────┘ (迭代)
```

### Tools (工具)

Agent 可调用的工具：

- `read_file`: 读取文件内容
- `write_file`: 写入文件
- `execute_code`: 执行代码
- `run_tests`: 运行测试
- `search_code`: 搜索代码
- `analyze_code`: 代码分析

## 📡 API 使用

### 创建任务

```bash
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "创建计算器模块",
    "description": "实现一个支持加减乘除的计算器",
    "priority": 8
  }'
```

### 查询任务状态

```bash
curl http://localhost:8000/api/v1/tasks/{task_id}
```

### 获取文件列表

```bash
curl http://localhost:8000/api/v1/tasks/{task_id}/files
```

### 查看文件内容

```bash
curl http://localhost:8000/api/v1/tasks/{task_id}/files?path=main.py
```

## 🧪 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定模块测试
pytest tests/test_agents.py -v

# 生成覆盖率报告
pytest tests/ --cov=app --cov-report=html
```

## 🔍 调试技巧

### 查看日志

```bash
# API 日志
docker-compose logs api

# Worker 日志
docker-compose logs worker

# 实时追踪
docker-compose logs -f api worker
```

### 进入容器调试

```bash
# 进入 API 容器
docker-compose exec api bash

# 进入 Worker 容器
docker-compose exec worker bash

# 连接数据库
docker-compose exec postgres psql -U sponge -d sponge_db
```

## 🛠️ 开发新 Agent

1. 在 `app/agents/` 创建新的 Agent 类
2. 实现 `process()` 方法
3. 在 `app/workflow/graph.py` 中注册节点
4. 添加测试用例

示例：

```python
# app/agents/custom_agent.py
from langchain_core.messages import BaseMessage

class CustomAgent:
    def __init__(self, llm):
        self.llm = llm
    
    def process(self, state: dict) -> dict:
        # 实现你的逻辑
        return {"messages": [...]}
```

## 📝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## ❓ 常见问题

**Q: LLM API 调用失败？**
- 检查 `.env` 中的 API 密钥是否正确
- 确认网络连接正常
- 查看日志中的详细错误信息

**Q: 沙箱执行超时？**
- 调整 `SANDBOX_TIMEOUT` 环境变量
- 优化代码性能
- 检查是否有死循环

**Q: 数据库连接失败？**
- 确认 PostgreSQL 容器正在运行
- 检查 `DATABASE_URL` 配置
- 验证数据库凭据

## 📚 更多文档

- [架构设计](ARCHITECTURE.md)
- [API 文档](API.md)
- [多 Agent 协作](MULTI_AGENT.md)
- [PRD 文档](PRD_Sponge.md)
