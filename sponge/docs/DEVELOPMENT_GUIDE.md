# Sponge 开发指南

## 目录

1. [快速开始](#快速开始)
2. [环境配置](#环境配置)
3. [项目结构](#项目结构)
4. [开发工作流](#开发工作流)
5. [代码规范](#代码规范)
6. [测试指南](#测试指南)
7. [调试技巧](#调试技巧)
8. [部署指南](#部署指南)
9. [故障排除](#故障排除)

---

## 快速开始

### 前置要求

- Python 3.9+
- Docker & Docker Compose
- Git

### 5 分钟快速启动

```bash
# 1. 克隆项目
cd /workspace/sponge

# 2. 复制环境变量
cp .env.example .env

# 3. 编辑 .env 文件，填入 API Key
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-...

# 4. 启动所有服务
docker-compose up -d

# 5. 访问 API 文档
open http://localhost:8000/docs
```

### 验证安装

```bash
# 健康检查
curl http://localhost:8000/health/

# 预期输出
{
  "status": "healthy",
  "service": "Sponge",
  "version": "0.1.0"
}
```

---

## 环境配置

### 环境变量

创建 `.env` 文件（基于 `.env.example`）：

```bash
# 应用配置
APP_NAME=Sponge
DEBUG=True
VERSION=0.1.0

# LLM 配置
LLM_PROVIDER=openai
OPENAI_API_KEY=your-api-key-here
MODEL_NAME=gpt-4o
TEMPERATURE=0.7

# 数据库
DATABASE_URL=postgresql://sponge:sponge_password@localhost:5432/sponge_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# 沙箱
SANDBOX_ENABLED=True
SANDBOX_TYPE=docker
SANDBOX_TIMEOUT=300
```

### 开发环境

#### 本地开发设置

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 启动基础设施（Docker）
docker-compose up -d postgres redis

# 初始化数据库
python -c "from app.db import init_db; init_db()"

# 启动 API 服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 启动 Celery Worker（新终端）
celery -A app.celery_app worker --loglevel=info --concurrency=4
```

#### 预提交钩子

```bash
# 安装 pre-commit
pip install pre-commit

# 配置钩子
pre-commit install

# 运行所有钩子
pre-commit run --all-files
```

---

## 项目结构

```
sponge/
├── app/                          # 主应用包
│   ├── __init__.py
│   ├── main.py                   # FastAPI 入口
│   ├── celery_app.py             # Celery 配置
│   │
│   ├── core/                     # 核心模块
│   │   ├── __init__.py
│   │   ├── config.py             # 配置管理
│   │   └── llm_service.py        # LLM 服务
│   │
│   ├── db/                       # 数据库层
│   │   ├── __init__.py
│   │   ├── database.py           # 数据库连接
│   │   ├── models.py             # SQLAlchemy 模型
│   │   └── task_manager.py       # 任务管理
│   │
│   ├── schemas/                  # Pydantic 模型
│   │   └── __init__.py
│   │
│   ├── agents/                   # Agent 实现
│   │   ├── __init__.py
│   │   ├── base_agent.py         # Agent 基类
│   │   ├── planner_agent.py      # 规划 Agent
│   │   ├── coder_agent.py        # 编码 Agent
│   │   └── reviewer_agent.py     # 审查 Agent
│   │
│   ├── tools/                    # 工具函数
│   │   ├── __init__.py
│   │   ├── file_tools.py         # 文件操作
│   │   ├── code_executor.py      # 代码执行
│   │   └── code_analyzer.py      # 代码分析
│   │
│   ├── workflow/                 # 工作流引擎
│   │   ├── __init__.py
│   │   ├── nodes.py              # 节点定义
│   │   └── workflow_graph.py     # 图定义
│   │
│   └── api/                      # API 路由
│       ├── __init__.py
│       ├── tasks.py              # 任务接口
│       ├── files.py              # 文件接口
│       └── health.py             # 健康检查
│
├── tests/                        # 测试用例
│   ├── __init__.py
│   └── test_sponge.py
│
├── docs/                         # 文档
│   ├── API_REFERENCE.md
│   ├── ARCHITECTURE.md
│   ├── DEVELOPMENT_GUIDE.md
│   └── MULTI_AGENT_GUIDE.md
│
├── docker-compose.yml            # Docker 编排
├── Dockerfile                    # Docker 镜像
├── requirements.txt              # Python 依赖
├── .env.example                  # 环境变量模板
├── .gitignore                    # Git 忽略文件
└── README.md                     # 项目说明
```

---

## 开发工作流

### 1. 创建新功能

```bash
# 创建功能分支
git checkout -b feature/new-agent-type

# 开发功能
# ... 编写代码 ...

# 运行测试
pytest tests/ -v

# 提交更改
git add .
git commit -m "feat: add new agent type"

# 推送分支
git push origin feature/new-agent-type
```

### 2. 添加新的 Agent

#### 步骤 1: 创建 Agent 类

```python
# app/agents/tester_agent.py
from typing import Any, Dict
from langchain_core.language_models import BaseLanguageModel

from .base_agent import BaseAgent


class TesterAgent(BaseAgent):
    """Agent for writing and running tests"""
    
    def __init__(self, llm: BaseLanguageModel, name: str = "Tester"):
        super().__init__(llm=llm, name=name, role="tester")
    
    def _default_system_prompt(self) -> str:
        return """You are an expert software tester.
Write comprehensive tests including unit tests, integration tests, and edge cases.
Ensure high code coverage.
"""
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        code = input_data.get("code", "")
        requirements = input_data.get("requirements", "")
        
        # 生成测试代码
        messages = self._build_messages(
            user_input=f"Write tests for this code:\n{code}",
            context={"requirements": requirements}
        )
        
        response = await self._invoke_llm(messages)
        
        return {
            "tests": response,
            "test_coverage": 85  # 示例
        }
```

#### 步骤 2: 添加到工作流

```python
# app/workflow/workflow_graph.py
from .nodes import tester_node

workflow.add_node("tester", tester_node)
workflow.add_edge("reviewer", "tester")
```

#### 步骤 3: 编写测试

```python
# tests/test_tester_agent.py
import pytest
from app.agents.tester_agent import TesterAgent


@pytest.mark.asyncio
async def test_tester_agent():
    agent = TesterAgent(llm=mock_llm)
    result = await agent.execute({
        "code": "def add(a, b): return a + b",
        "requirements": "Test addition function"
    })
    assert "tests" in result
```

### 3. 修改现有功能

```bash
# 查看当前分支
git branch

# 切换到主分支
git checkout main

# 拉取最新代码
git pull origin main

# 创建修复分支
git checkout -b fix/api-error-handling

# 进行修改
# ... 编辑代码 ...

# 运行测试确保没有破坏现有功能
pytest tests/ -v

# 提交
git commit -m "fix: improve API error handling"
```

---

## 代码规范

### Python 风格指南

遵循 [PEP 8](https://pep8.org/) 标准：

```python
# ✅ 好的代码
def calculate_total(items: list[float]) -> float:
    """Calculate total sum of items.
    
    Args:
        items: List of numeric values
        
    Returns:
        Total sum
        
    Raises:
        ValueError: If items is empty
    """
    if not items:
        raise ValueError("Items list cannot be empty")
    
    return sum(items)


# ❌ 不好的代码
def calc(l):
    if len(l) == 0:
        raise Exception("bad")
    return sum(l)
```

### 类型注解

所有函数必须有类型注解：

```python
from typing import Optional, List, Dict, Any


async def process_task(
    task_id: str,
    priority: int = 5,
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    ...
```

### 文档字符串

所有公共函数和类必须有文档字符串：

```python
class WorkflowManager:
    """Manages the multi-agent workflow execution.
    
    This class handles the orchestration of multiple AI agents
    through a LangGraph-based state machine.
    
    Attributes:
        graph: Compiled LangGraph workflow
        max_iterations: Maximum refinement iterations
    """
    
    async def execute(self, description: str) -> dict:
        """Execute the workflow for a given task.
        
        Args:
            description: Task description
            
        Returns:
            Final workflow state with results
            
        Raises:
            WorkflowError: If execution fails
        """
        ...
```

### 错误处理

使用自定义异常和适当的错误处理：

```python
from fastapi import HTTPException, status


class WorkflowError(Exception):
    """Custom exception for workflow errors"""
    pass


async def get_task(task_id: str) -> dict:
    try:
        task = db.query(TaskModel).filter(TaskModel.uuid == task_id).first()
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        return task
    except Exception as e:
        logger.error(f"Failed to get task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
```

---

## 测试指南

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定模块
pytest tests/test_agents.py -v

# 运行特定测试
pytest tests/test_agents.py::test_planner_agent -v

# 生成覆盖率报告
pytest tests/ --cov=app --cov-report=html

# 查看覆盖率
open htmlcov/index.html
```

### 编写单元测试

```python
# tests/test_planner_agent.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.planner_agent import PlannerAgent


@pytest.fixture
def mock_llm():
    """Create mock LLM for testing"""
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value="Mock response")
    return llm


@pytest.mark.asyncio
async def test_planner_agent_create_plan(mock_llm):
    """Test planner agent creates valid plan"""
    agent = PlannerAgent(llm=mock_llm)
    
    result = await agent.execute({
        "description": "Create a calculator",
        "language": "python"
    })
    
    assert "plan" in result
    assert "summary" in result["plan"]
    assert isinstance(result["plan"]["steps"], list)


@pytest.mark.asyncio
async def test_planner_agent_missing_description():
    """Test planner agent handles missing description"""
    agent = PlannerAgent(llm=MagicMock())
    
    with pytest.raises(ValueError, match="description is required"):
        await agent.execute({})
```

### 编写集成测试

```python
# tests/test_workflow.py
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


def test_create_task(client):
    """Test task creation endpoint"""
    response = client.post("/api/v1/tasks/", json={
        "title": "Test Task",
        "description": "Test description",
        "priority": "high"
    })
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["title"] == "Test Task"


def test_get_task_list(client):
    """Test task list endpoint"""
    response = client.get("/api/v1/tasks/")
    
    assert response.status_code == 200
    data = response.json()
    assert "tasks" in data
    assert "total" in data
```

### 测试最佳实践

1. **测试隔离**: 每个测试独立运行
2. **使用夹具**: 复用测试设置
3. **命名清晰**: 测试名称描述行为
4. **测试边界**: 包括边界条件和错误情况
5. **保持快速**: 测试应该快速执行

---

## 调试技巧

### 日志记录

```python
from loguru import logger

# 配置日志
logger.add("logs/app.log", rotation="1 MB", retention="7 days")

# 不同级别
logger.debug("Debug info")
logger.info("General info")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical issue")

# 带上下文
logger.bind(task_id="123").info("Processing task")

# 带异常
try:
    risky_operation()
except Exception as e:
    logger.exception("Operation failed")
```

### 调试模式

```bash
# 启用调试模式
export DEBUG=True

# 启动 API（自动重载）
uvicorn app.main:app --reload

# 查看详细日志
docker-compose logs -f api worker
```

### 进入容器调试

```bash
# 进入 API 容器
docker-compose exec api bash

# 进入数据库
docker-compose exec postgres psql -U sponge -d sponge_db

# 查看 Redis
docker-compose exec redis redis-cli
```

### 使用断点

```python
# 代码中设置断点
import pdb; pdb.set_trace()

# 或使用 breakpoint() (Python 3.7+)
breakpoint()

# 运行后进入交互模式
python -m pdb app/main.py
```

---

## 部署指南

### Docker 部署

```bash
# 构建镜像
docker-compose build

# 启动所有服务
docker-compose up -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 清理数据卷
docker-compose down -v
```

### 生产环境配置

```bash
# 生产环境变量
export DEBUG=False
export DATABASE_URL=postgresql://user:pass@prod-db:5432/sponge
export REDIS_URL=redis://prod-redis:6379/0
export SECRET_KEY=production-secret-key-change-me
```

### 数据库迁移

```bash
# 使用 Alembic 进行迁移
alembic revision --autogenerate -m "Add new column"
alembic upgrade head

# 回滚
alembic downgrade -1
```

---

## 故障排除

### 常见问题

#### 1. LLM API 调用失败

**症状**: 收到 401 或 429 错误

**解决方案**:
```bash
# 检查 API Key
echo $OPENAI_API_KEY

# 验证网络连接
curl https://api.openai.com/v1/models

# 检查配额
# 登录 OpenAI dashboard 查看使用情况
```

#### 2. 数据库连接失败

**症状**: 无法连接到 PostgreSQL

**解决方案**:
```bash
# 检查数据库是否运行
docker-compose ps postgres

# 查看数据库日志
docker-compose logs postgres

# 测试连接
psql -h localhost -U sponge -d sponge_db
```

#### 3. Celery Worker 不处理任务

**症状**: 任务一直处于 pending 状态

**解决方案**:
```bash
# 检查 Worker 状态
docker-compose logs worker

# 重启 Worker
docker-compose restart worker

# 检查 Redis
docker-compose exec redis redis-cli ping
```

#### 4. 沙箱执行超时

**症状**: 代码执行超过 300 秒

**解决方案**:
```bash
# 增加超时时间
export SANDBOX_TIMEOUT=600

# 优化代码性能
# 检查是否有死循环
```

### 获取帮助

- 📖 查看文档：`docs/` 目录
- 🐛 报告问题：GitHub Issues
- 💬 讨论：GitHub Discussions

---

## 贡献指南

### 提交流程

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### 提交信息规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` 新功能
- `fix:` 修复 bug
- `docs:` 文档更新
- `style:` 代码格式
- `refactor:` 重构
- `test:` 测试相关
- `chore:` 构建/工具

---

## 参考资源

- [API 参考文档](./API_REFERENCE.md)
- [架构设计文档](./ARCHITECTURE.md)
- [多智能体指南](./MULTI_AGENT_GUIDE.md)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)

---

**Happy Coding!** 🚀
