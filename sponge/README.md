# Sponge Code Agent

<div align="center">

**基于 LangGraph 的多智能体协作代码开发系统**

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-orange.svg)](https://github.com/langchain-ai/langgraph)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

🤖 多智能体协作 | 🔄 自动化工作流 | 🛡️ 安全沙箱执行 | ⚡ 异步任务处理

</div>

---

## 📖 目录

- [产品概述](#-产品概述)
- [核心特性](#-核心特性)
- [快速开始](#-快速开始)
- [系统架构](#-系统架构)
- [技术栈](#-技术栈)
- [项目结构](#-项目结构)
- [API 文档](#-api-文档)
- [使用指南](#-使用指南)
- [开发指南](#-开发指南)
- [路线图](#-路线图)
- [贡献指南](#-贡献指南)
- [许可证](#-许可证)

---

## 🎯 产品概述

**Sponge Code Agent** 是一款智能化的编程助手，基于大语言模型（LLM）和 LangGraph 工作流引擎构建。它能够接收自然语言描述的开发任务，自主完成从需求分析到代码交付的完整流程：

- 📋 **需求分析** - 理解用户意图，拆解复杂任务
- 💻 **代码生成** - 自动生成高质量、可运行的代码
- ▶️ **执行测试** - 在安全沙箱中运行和验证代码
- 📊 **结果评估** - 智能评估输出质量和正确性
- 🔧 **自我修正** - 识别问题并迭代优化直至满足要求

### 核心价值

| 价值维度 | 说明 |
|---------|------|
| **效率提升** | 自动化重复性编程任务，开发者聚焦创造性工作 |
| **质量保障** | 通过自动测试和评估机制确保代码质量 |
| **自我进化** | 具备反思和修正能力，从错误中学习改进 |
| **降低门槛** | 帮助非专业开发者实现复杂编程需求 |

---

## ✨ 核心特性

### 🤖 多智能体协作系统

Sponge 采用 specialized agents 分工协作的架构：

| Agent | 职责 | 功能 |
|-------|------|------|
| **📋 Planner** | 规划师 | 需求分析、任务拆解、制定实施计划 |
| **💻 Coder** | 程序员 | 根据规范生成代码实现 |
| **🔍 Reviewer** | 审查员 | 代码审查、质量检查、最佳实践验证 |
| **🧪 Tester** | 测试员 | 生成测试用例、执行验证、报告问题 |

### 🔄 自动化工作流

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Planner   │────▶│    Coder     │────▶│  Reviewer   │
└─────────────┘     └──────────────┘     └─────────────┘
      ▲                                        │
      │                                        ▼
      │                              ┌─────────────┐
      │                              │   Tester    │
      │                              └─────────────┘
      │                                        │
      │         ┌──────────────┐              │
      └─────────│   Reflector  │◀─────────────┘
                └──────────────┘
                       │
                       ▼
                ┌──────────────┐
                │    Done ✅   │
                └──────────────┘
```

### 🛡️ 安全执行环境

- **Docker 沙箱** - 隔离的代码执行环境，防止恶意代码影响主机
- **资源限制** - CPU、内存、网络访问严格控制
- **超时保护** - 防止无限循环和长时间运行
- **权限管理** - 最小权限原则，限制文件系统访问

### ⚡ 高性能架构

- **异步处理** - Celery + Redis 任务队列支持并发执行
- **状态持久化** - PostgreSQL 数据库存储任务和结果
- **实时反馈** - WebSocket 推送任务进度和日志
- **断点续传** - 支持长任务中断后恢复执行

---

## 🚀 快速开始

### 方式一：Docker 一键部署（推荐）

```bash
# 克隆项目
cd /workspace/sponge

# 配置环境变量
cp docker/.env.example .env
# 编辑 .env 文件，设置你的 LLM_API_KEY

# 启动所有服务
docker-compose -f docker/docker-compose.yml up -d

# 查看服务状态
docker-compose -f docker/docker-compose.yml ps

# 访问前端界面
open http://localhost:8501

# 查看 API 文档
open http://localhost:8000/docs
```

### 方式二：本地开发部署

#### 1. 环境准备

```bash
# Python 3.9+
python --version

# 安装依赖
pip install -r requirements.txt

# 启动 Redis（用于 Celery）
docker run -d -p 6379:6379 redis:alpine

# 启动 PostgreSQL（可选，默认使用 SQLite）
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:15
```

#### 2. 配置环境变量

```bash
# 复制环境配置模板
cp .env.example .env

# 编辑 .env 文件，设置必要的环境变量
export LLM_API_KEY="your-api-key-here"
export LLM_MODEL="gpt-4"  # 或 claude-3-opus 等
export DATABASE_URL="sqlite:///./sponge.db"
export REDIS_URL="redis://localhost:6379/0"
```

#### 3. 启动服务

```bash
# 终端 1：启动 FastAPI 服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 终端 2：启动 Celery Worker
celery -A app.celery_app worker --loglevel=info --pool=solo

# 终端 3：启动前端（可选）
cd frontend
streamlit run app.py
```

### 验证安装

```bash
# 健康检查
curl http://localhost:8000/health

# 创建测试任务
curl -X POST http://localhost:8000/api/v1/tasks/ \
  -H "Content-Type: application/json" \
  -d '{"description": "创建一个计算斐波那契数列的 Python 函数"}'
```

---

## 🏗️ 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────┐
│                    用户界面层                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ Streamlit   │  │   REST API  │  │  WebSocket  │     │
│  │   Frontend  │  │   Client    │  │   Client    │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP / WebSocket
┌────────────────────▼────────────────────────────────────┐
│                  FastAPI 应用层                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │  Tasks   │  │  Files   │  │  Health  │  API Routers │
│  └──────────┘  └──────────┘  └──────────┘              │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│               Celery 分布式任务队列                        │
│         (异步智能体协调与任务调度)                          │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│            LangGraph 工作流引擎                           │
│  ┌──────────────────────────────────────────────────┐  │
│  │  State Machine: Planner → Coder → Reviewer      │  │
│  │              ↑                            ↓      │  │
│  │              └──── Iteration Loop ────────┘      │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                 工具层 & 沙箱环境                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │  File    │  │  Code    │  │  Docker  │              │
│  │  Tools   │  │ Executor │  │ Sandbox │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────────────────────────────────────────┘
```

### 核心组件

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| **Web 框架** | FastAPI | 高性能异步 API 服务 |
| **工作流引擎** | LangGraph | 状态机驱动的智能体编排 |
| **任务队列** | Celery + Redis | 分布式异步任务处理 |
| **数据库** | PostgreSQL / SQLite | 数据和状态持久化 |
| **ORM** | SQLAlchemy 2.0 | 数据库对象关系映射 |
| **沙箱执行** | Docker | 安全的代码执行环境 |
| **前端** | Streamlit | 交互式 Web 界面 |
| **LLM** | OpenAI / Anthropic | 大语言模型后端 |

---

## 🛠️ 技术栈

### 后端技术

| 类别 | 技术 | 版本 |
|------|------|------|
| **编程语言** | Python | 3.9+ |
| **Web 框架** | FastAPI | >=0.115.0 |
| **AI 框架** | LangChain + LangGraph | >=0.3.0 / >=0.2.0 |
| **任务队列** | Celery | >=5.4.0 |
| **消息代理** | Redis | >=5.0.0 |
| **数据库** | PostgreSQL / SQLite | - |
| **ORM** | SQLAlchemy | >=2.0.0 |
| **数据验证** | Pydantic | >=2.9.0 |

### AI 模型支持

- ✅ **OpenAI GPT-4** / GPT-4 Turbo
- ✅ **Anthropic Claude 3** (Opus/Sonnet/Haiku)
- ✅ **兼容 OpenAI API 的其他模型**

### 开发工具

| 工具 | 用途 |
|------|------|
| **pytest** | 单元测试框架 |
| **black** | 代码格式化 |
| **flake8** | 代码风格检查 |
| **mypy** | 静态类型检查 |

---

## 📁 项目结构

```
sponge/
├── app/                          # 核心应用代码
│   ├── __init__.py
│   ├── main.py                   # FastAPI 应用入口
│   ├── celery_app.py             # Celery 配置
│   ├── core/                     # 核心配置
│   │   ├── config.py             # 全局配置
│   │   ├── security.py           # 安全认证
│   │   └── logging.py            # 日志配置
│   ├── api/                      # API 路由
│   │   ├── v1/
│   │   │   ├── tasks.py          # 任务管理端点
│   │   │   ├── files.py          # 文件管理端点
│   │   │   └── health.py         # 健康检查端点
│   ├── agents/                   # 智能体实现
│   │   ├── base.py               # 智能体基类
│   │   ├── planner.py            # 规划师智能体
│   │   ├── coder.py              # 程序员智能体
│   │   ├── reviewer.py           # 审查员智能体
│   │   └── tester.py             # 测试员智能体
│   ├── workflow/                 # LangGraph 工作流
│   │   ├── graph.py              # 图结构定义
│   │   ├── state.py              # 状态管理
│   │   └── nodes.py              # 节点实现
│   ├── tools/                    # 工具函数
│   │   ├── file_tools.py         # 文件操作工具
│   │   ├── code_executor.py      # 代码执行器
│   │   └── sandbox.py            # 沙箱管理
│   ├── db/                       # 数据库
│   │   ├── models.py             # 数据模型
│   │   ├── schemas.py            # Pydantic 模式
│   │   └── database.py           # 数据库连接
│   └── schemas/                  # 数据模式
├── frontend/                     # Streamlit 前端
│   ├── app.py                    # 前端主程序
│   └── requirements.txt          # 前端依赖
├── docker/                       # Docker 配置
│   ├── docker-compose.yml        # 服务编排
│   ├── Dockerfile.api            # API 镜像
│   ├── Dockerfile.frontend       # 前端镜像
│   └── .env.example              # 环境变量模板
├── tests/                        # 测试套件
│   ├── test_agents.py            # 智能体测试
│   ├── test_workflow.py          # 工作流测试
│   └── test_api.py               # API 测试
├── docs/                         # 项目文档
│   ├── API_REFERENCE.md          # API 参考文档
│   ├── ARCHITECTURE.md           # 架构说明
│   └── DEVELOPMENT_GUIDE.md      # 开发指南
├── requirements.txt              # Python 依赖
├── QUICKSTART.md                 # 快速启动指南
├── DEVELOPMENT.md                # 开发文档
└── README.md                     # 本文件
```

---

## 📡 API 文档

### 基础信息

- **Base URL**: `http://localhost:8000`
- **API Version**: `v1`
- **Interactive Docs**: `http://localhost:8000/docs` (Swagger UI)
- **Alternative Docs**: `http://localhost:8000/redoc` (ReDoc)

### 认证方式

当前版本支持 API Key 认证：

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" http://localhost:8000/api/v1/tasks/
```

### 核心端点

#### 任务管理

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/api/v1/tasks/` | 创建新任务 |
| `GET` | `/api/v1/tasks/` | 获取任务列表 |
| `GET` | `/api/v1/tasks/{id}` | 获取任务详情 |
| `POST` | `/api/v1/tasks/{id}/cancel` | 取消任务 |
| `DELETE` | `/api/v1/tasks/{id}` | 删除任务 |

**示例：创建任务**

```bash
curl -X POST http://localhost:8000/api/v1/tasks/ \
  -H "Content-Type: application/json" \
  -d '{
    "description": "创建一个 Python 函数，计算两个数的最大公约数",
    "language": "python",
    "priority": "normal"
  }'
```

**响应示例：**

```json
{
  "id": "task_123456",
  "description": "创建一个 Python 函数，计算两个数的最大公约数",
  "status": "pending",
  "created_at": "2026-04-15T10:30:00Z",
  "updated_at": "2026-04-15T10:30:00Z"
}
```

#### 文件管理

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/v1/files/` | 列出文件 |
| `GET` | `/api/v1/files/content` | 获取文件内容 |
| `POST` | `/api/v1/files/update` | 更新文件 |
| `GET` | `/api/v1/files/exists` | 检查文件是否存在 |

#### 健康检查

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/health/` | 整体健康状态 |
| `GET` | `/health/ready` | 就绪状态检查 |
| `GET` | `/health/live` | 存活状态检查 |

---

## 💡 使用指南

### 基本使用流程

1. **创建任务**
   ```python
   import requests
   
   response = requests.post(
       "http://localhost:8000/api/v1/tasks/",
       json={
           "description": "实现一个快速排序算法",
           "language": "python"
       }
   )
   task_id = response.json()["id"]
   ```

2. **查询任务状态**
   ```python
   response = requests.get(f"http://localhost:8000/api/v1/tasks/{task_id}")
   print(response.json())
   ```

3. **获取生成的代码**
   ```python
   response = requests.get(f"http://localhost:8000/api/v1/tasks/{task_id}")
   result = response.json()
   print(result["code"])
   print(result["tests"])
   ```

### 高级用法

#### 自定义工作流

可以通过继承基类创建自定义智能体：

```python
from app.agents.base import BaseAgent

class CustomAgent(BaseAgent):
    async def process(self, state: dict) -> dict:
        # 实现自定义逻辑
        return state
```

#### 批量任务处理

```python
tasks = [
    {"description": "任务 1", "language": "python"},
    {"description": "任务 2", "language": "javascript"},
]

for task in tasks:
    requests.post("http://localhost:8000/api/v1/tasks/", json=task)
```

---

## 🧪 测试

### 运行测试套件

```bash
# 安装测试依赖
pip install pytest pytest-cov pytest-asyncio

# 运行所有测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/test_workflow.py -v

# 查看测试覆盖率
pytest --cov=app tests/ --cov-report=html

# 打开覆盖率报告
open htmlcov/index.html
```

### 编写测试

```python
# tests/test_agents.py
import pytest
from app.agents.planner import PlannerAgent

@pytest.mark.asyncio
async def test_planner_analysis():
    agent = PlannerAgent()
    result = await agent.analyze("创建一个计算器")
    assert "plan" in result
```

---

## 📚 开发指南

### 开发环境设置

详见 [DEVELOPMENT.md](DEVELOPMENT.md)

### 代码规范

- 遵循 [PEP 8](https://pep8.org/) 编码规范
- 使用 type hints 进行类型注解
- 所有公共函数必须有 docstring
- 提交前运行 black 格式化代码

```bash
# 代码格式化
black app/ tests/

# 代码检查
flake8 app/ tests/

# 类型检查
mypy app/
```

### 添加新智能体

1. 在 `app/agents/` 目录下创建新文件
2. 继承 `BaseAgent` 类
3. 实现 `process()` 方法
4. 在工作流图中注册新节点

### 贡献流程

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启 Pull Request

---

## 🗺️ 路线图

### Phase 1 (MVP) - 当前阶段

- [x] 项目脚手架搭建
- [x] 核心配置系统
- [x] API 基础结构
- [x] 文件操作工具
- [ ] 智能体完整实现
- [ ] 工作流引擎集成
- [ ] 代码执行沙箱

### Phase 2 - 功能完善

- [ ] 数据库集成（PostgreSQL）
- [ ] 高级代码分析
- [ ] 测试用例自动生成
- [ ] CI/CD 集成
- [ ] 人类介入支持（Human-in-the-loop）

### Phase 3 - 生态扩展

- [ ] Web UI 增强
- [ ] 插件系统
- [ ] 多语言支持（JavaScript, Java, Go 等）
- [ ] 团队协作功能
- [ ] 知识库和记忆系统

---

## 🤝 贡献指南

我们欢迎各种形式的贡献！

### 如何贡献

1. **报告 Bug** - 通过 GitHub Issues 提交
2. **功能建议** - 创建 Feature Request
3. **代码贡献** - 提交 Pull Request
4. **文档改进** - 帮助完善文档

### 开发环境设置

```bash
# Fork 并克隆项目
git clone https://github.com/your-username/sponge.git
cd sponge

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装开发依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 开发工具

# 创建开发分支
git checkout -b feature/your-feature
```

### 提交规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
feat: 添加新功能
fix: 修复 Bug
docs: 文档更新
style: 代码格式调整
refactor: 重构代码
test: 测试相关
chore: 构建/工具链相关
```

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

---

## 🙏 致谢

感谢以下优秀的开源项目：

- [FastAPI](https://fastapi.tiangolo.com/) - 现代高性能 Web 框架
- [LangGraph](https://github.com/langchain-ai/langgraph) - 图结构工作流引擎
- [LangChain](https://github.com/langchain-ai/langchain) - LLM 应用开发框架
- [Streamlit](https://streamlit.io/) - 快速数据应用构建工具
- [Celery](https://docs.celeryq.dev/) - 分布式任务队列
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL 工具包

---

## 📞 联系我们

- **GitHub Issues**: [提交问题和建议](https://github.com/your-org/sponge/issues)
- **讨论区**: [GitHub Discussions](https://github.com/your-org/sponge/discussions)

---

<div align="center">

**Sponge** - 吸收复杂，产出代码 🧽✨

Made with ❤️ by AI Engineering Team

</div>
