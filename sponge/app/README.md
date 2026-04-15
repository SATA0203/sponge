# Sponge App - 多智能体协作系统核心应用

[English](#english) | [中文](#中文)

## 📋 概述

`app/` 目录包含 Sponge 多智能体协作系统的核心后端应用代码，基于 FastAPI 构建，提供 RESTful API 接口、智能体管理、工作流引擎和任务调度功能。

## 🏗️ 架构概览

```
app/
├── __init__.py          # 包初始化
├── main.py              # FastAPI 应用入口
├── celery_app.py        # Celery 异步任务配置
├── agents/              # 智能体模块
│   ├── base_agent.py    # 基础智能体类
│   ├── coder_agent.py   # 代码编写智能体
│   ├── reviewer_agent.py # 代码审查智能体
│   └── manager_agent.py # 任务管理智能体
├── api/                 # API 路由模块
│   ├── routes/          # API 路由定义
│   ├── deps.py          # 依赖注入
│   └── errors.py        # 错误处理
├── core/                # 核心功能模块
│   ├── config.py        # 配置管理
│   ├── security.py      # 安全认证
│   └── logging.py       # 日志配置
├── db/                  # 数据库模块
│   ├── database.py      # 数据库连接
│   ├── models.py        # SQLAlchemy 模型
│   └── crud.py          # CRUD 操作
├── schemas/             # Pydantic 数据模型
│   ├── task.py          # 任务相关模式
│   ├── agent.py         # 智能体相关模式
│   └── workflow.py      # 工作流相关模式
├── tools/               # 工具函数库
│   ├── code_parser.py   # 代码解析工具
│   ├── file_utils.py    # 文件操作工具
│   └── git_utils.py     # Git 操作工具
└── workflow/            # 工作流引擎
    ├── engine.py        # 工作流引擎核心
    ├── nodes.py         # 工作流节点定义
    └── state.py         # 状态管理
```

## 🚀 核心模块说明

### 1. 智能体模块 (`agents/`)

实现多种专用智能体，每个智能体具有特定职责：

- **BaseAgent**: 所有智能体的抽象基类
- **CoderAgent**: 负责代码生成和修改
- **ReviewerAgent**: 负责代码审查和质量检查
- **ManagerAgent**: 负责任务分解和协调

```python
# 示例：使用智能体
from app.agents import CoderAgent

agent = CoderAgent()
response = await agent.execute("实现一个快速排序算法")
```

### 2. API 模块 (`api/`)

提供完整的 RESTful API 接口：

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/tasks` | POST | 创建新任务 |
| `/api/v1/tasks/{id}` | GET | 获取任务详情 |
| `/api/v1/agents` | GET | 列出所有智能体 |
| `/api/v1/workflows` | POST | 执行工作流 |
| `/api/v1/health` | GET | 健康检查 |

### 3. 核心模块 (`core/`)

系统核心配置和功能：

- **配置管理**: 支持环境变量和配置文件
- **安全认证**: JWT Token 认证机制
- **日志系统**: 结构化日志记录

### 4. 数据库模块 (`db/`)

数据持久化层：

- **Models**: SQLAlchemy ORM 模型定义
- **CRUD**: 通用增删改查操作
- **Migrations**: 数据库迁移脚本

### 5. 数据模式 (`schemas/`)

Pydantic 模型用于：

- 请求/响应数据验证
- API 文档自动生成
- 类型安全检查

### 6. 工具模块 (`tools/`)

实用工具函数：

- **代码解析**: AST 分析、代码格式化
- **文件操作**: 读写、路径处理
- **Git 集成**: 版本控制操作

### 7. 工作流模块 (`workflow/`)

LangGraph 驱动的工作流引擎：

- **状态图**: 定义智能体协作流程
- **条件边**: 基于结果的动态路由
- **记忆管理**: 跨步骤上下文保持

## 🛠️ 技术栈

- **Web 框架**: FastAPI 0.104+
- **异步运行时**: asyncio + uvloop
- **任务队列**: Celery + Redis
- **数据库**: SQLite / PostgreSQL
- **ORM**: SQLAlchemy 2.0+
- **验证**: Pydantic v2
- **工作流**: LangGraph
- **AI SDK**: LangChain

## 📦 安装与运行

### 前置要求

- Python 3.10+
- Redis (用于 Celery)
- 虚拟环境 (推荐)

### 安装步骤

```bash
# 进入 sponge 目录
cd sponge

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入必要的配置

# 初始化数据库
python -c "from app.db.database import init_db; init_db()"

# 启动主应用
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 启动 Celery Worker (另开终端)
celery -A app.celery_app worker --loglevel=info
```

### Docker 运行

```bash
# 使用 docker-compose
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 🔧 配置说明

主要配置项在 `.env` 文件中：

```bash
# 应用配置
APP_NAME=Sponge
DEBUG=true
SECRET_KEY=your-secret-key-here

# 数据库配置
DATABASE_URL=sqlite:///./sponge.db
# 或
DATABASE_URL=postgresql://user:pass@localhost:5432/sponge

# Redis 配置 (Celery)
REDIS_URL=redis://localhost:6379/0

# AI 模型配置
OPENAI_API_KEY=sk-xxx
MODEL_NAME=gpt-4

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=server.log
```

## 🧪 测试

```bash
# 运行所有测试
pytest tests/

# 运行特定模块测试
pytest tests/test_agents.py -v

# 带覆盖率报告
pytest --cov=app tests/
```

## 📝 开发指南

### 添加新智能体

1. 在 `agents/` 目录创建新文件
2. 继承 `BaseAgent` 类
3. 实现 `execute()` 方法
4. 在注册表中注册

```python
# app/agents/new_agent.py
from .base_agent import BaseAgent

class NewAgent(BaseAgent):
    async def execute(self, task: str) -> str:
        # 实现逻辑
        return result
```

### 添加新 API 端点

1. 在 `api/routes/` 创建路由文件
2. 定义路径操作函数
3. 在主应用中包含路由

```python
# app/api/routes/items.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/items")
async def list_items():
    return {"items": []}
```

### 扩展工作流

1. 定义新的状态图
2. 添加节点和边
3. 注册到工作流引擎

## 🔍 调试技巧

### 启用详细日志

```bash
export LOG_LEVEL=DEBUG
```

### 使用交互式调试器

```python
import pdb; pdb.set_trace()
```

### 监控 Celery 任务

```bash
# 查看活跃任务
celery -A app.celery_app inspect active

# 查看统计信息
celery -A app.celery_app inspect stats
```

## 📊 性能优化

- 使用异步数据库操作
- 启用查询缓存
- 优化大模型调用频率
- 使用连接池

## 🔒 安全考虑

- 所有 API 端点需要认证（除健康检查）
- 敏感信息使用环境变量
- 输入数据严格验证
- SQL 注入防护（使用 ORM）

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目采用 MIT 许可证

---

## English

### Overview

The `app/` directory contains the core backend application code for the Sponge Multi-Agent Collaboration System, built with FastAPI, providing RESTful APIs, agent management, workflow engine, and task scheduling capabilities.

### Quick Start

```bash
cd sponge
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

For more details, see the sections above.
