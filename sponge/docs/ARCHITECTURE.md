# Sponge 架构设计文档

## 系统概述

Sponge 是一个多智能体协作的代码开发系统，通过 LangGraph 工作流引擎协调多个专业 AI Agent 完成代码分析、编写、审查和测试任务。

---

## 架构架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      用户界面层                               │
│              (REST API / WebSocket / CLI)                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    FastAPI 应用层                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Task API   │  │  File API   │  │ Health API  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                  业务逻辑层                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Workflow Manager                        │    │
│  │  ┌────────┐ ┌────────┐ ┌──────────┐ ┌──────────┐   │    │
│  │  │Planner │ → │ Coder  │ → │Executor │ → │Reviewer  │   │    │
│  │  └────────┘ └────────┘ └──────────┘ └──────────┘   │    │
│  │       ↑                                      │      │    │
│  │       └──────────── Iteration ───────────────┘      │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                   Agent 层                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │BaseAgent     │  │PlannerAgent  │  │CoderAgent    │      │
│  │ - llm        │  │ - plan()     │  │ - code()     │      │
│  │ - system_prompt│ │ - steps[]    │  │ - files[]    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                   工具层                                     │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │FileTools   │  │CodeExecutor│  │CodeAnalyzer│            │
│  │- read_file │  │- docker    │  │- syntax    │            │
│  │- write_file│  │- timeout   │  │- quality   │            │
│  └────────────┘  └────────────┘  └────────────┘            │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                 基础设施层                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │PostgreSQL  │  │   Redis    │  │   Docker   │            │
│  │(数据库)    │  │(缓存/队列) │  │(沙箱)      │            │
│  └────────────┘  └────────────┘  └────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

---

## 核心组件

### 1. FastAPI 应用层

**文件**: `app/main.py`

负责 HTTP 请求处理、路由分发和中间件管理。

**关键功能**:
- RESTful API 端点
- CORS 配置
- 生命周期管理（启动/关闭）
- 异常处理

**主要端点**:
```python
/app/main.py
├── GET  /                          # 根路径
├── GET  /docs                      # Swagger UI
├── GET  /health/                   # 健康检查
├── POST /api/v1/tasks/             # 创建任务
├── GET  /api/v1/tasks/{id}         # 获取任务
└── GET  /api/v1/files/             # 文件操作
```

### 2. 配置管理

**文件**: `app/core/config.py`

使用 Pydantic Settings 管理环境变量和配置。

**配置项**:
```python
class Settings(BaseSettings):
    # 应用
    APP_NAME: str = "Sponge"
    VERSION: str = "0.1.0"
    
    # LLM
    LLM_PROVIDER: str = "openai"
    MODEL_NAME: str = "gpt-4o"
    
    # 数据库
    DATABASE_URL: str
    DB_POOL_SIZE: int = 10
    
    # Redis & Celery
    REDIS_URL: str
    CELERY_BROKER_URL: str
    
    # 沙箱
    SANDBOX_ENABLED: bool = True
    SANDBOX_TIMEOUT: int = 300
```

### 3. 数据库层

**文件**: `app/db/`

#### 模型定义 (`models.py`)

```python
TaskModel:
├── id: Integer (PK)
├── uuid: String (unique)
├── title: String
├── description: Text
├── status: Enum (PENDING, PLANNING, CODING, ...)
├── current_step: String
├── iterations: Integer
├── plan: JSON
├── code: JSON
├── review_result: JSON
└── created_at: DateTime

FileModel:
├── id: Integer (PK)
├── uuid: String (unique)
├── task_uuid: String (FK)
├── filename: String
├── filepath: String
├── content: Text
└── file_type: String
```

#### 数据库初始化 (`database.py`)

```python
- Base: SQLAlchemy 基类
- engine: 数据库引擎
- SessionLocal: 会话工厂
- init_db(): 初始化数据库表
```

### 4. Agent 层

#### 基类 (`agents/base_agent.py`)

```python
class BaseAgent:
    def __init__(self, llm, name, role):
        self.llm = llm
        self.name = name
        self.role = role
    
    def _default_system_prompt(self) -> str:
        """定义 Agent 的系统提示"""
    
    async def execute(self, input_data: dict) -> dict:
        """执行 Agent 的主要逻辑"""
    
    def _build_messages(self, user_input, context) -> list:
        """构建 LLM 消息"""
    
    async def _invoke_llm(self, messages) -> str:
        """调用 LLM"""
```

#### Planner Agent (`agents/planner_agent.py`)

**职责**: 分析需求，创建执行计划

**输入**:
```json
{
  "description": "任务描述",
  "requirements": "额外需求",
  "language": "python"
}
```

**输出**:
```json
{
  "plan": {
    "summary": "计划摘要",
    "steps": [
      {
        "step_number": 1,
        "description": "步骤描述",
        "agent": "coder",
        "estimated_complexity": "medium"
      }
    ]
  }
}
```

#### Coder Agent (`agents/coder_agent.py`)

**职责**: 根据计划编写代码

**功能**:
- 生成代码文件
- 实现函数和类
- 添加注释和文档

#### Reviewer Agent (`agents/reviewer_agent.py`)

**职责**: 代码审查和质量检查

**检查项**:
- 代码规范
- 潜在 bug
- 性能问题
- 安全漏洞

### 5. 工作流引擎

**文件**: `app/workflow/`

#### 状态定义 (`nodes.py`)

```python
from typing import TypedDict, List, Dict, Any

class WorkflowState(TypedDict):
    task_id: str
    description: str
    language: str
    plan: Dict[str, Any]
    code: Dict[str, Any]
    execution_result: Dict[str, Any]
    review_result: Dict[str, Any]
    iterations: int
    max_iterations: int
    error: str
    status: str
```

#### 节点实现 (`nodes.py`)

```python
async def planner_node(state: WorkflowState) -> dict:
    """规划节点"""
    planner = PlannerAgent(llm)
    result = await planner.execute({...})
    return {"plan": result["plan"]}

async def coder_node(state: WorkflowState) -> dict:
    """编码节点"""
    coder = CoderAgent(llm)
    result = await coder.execute({...})
    return {"code": result["code"]}

async def executor_node(state: WorkflowState) -> dict:
    """执行节点"""
    # 在沙箱中执行代码
    ...

async def reviewer_node(state: WorkflowState) -> dict:
    """审查节点"""
    reviewer = ReviewerAgent(llm)
    result = await reviewer.execute({...})
    return {"review_result": result}
```

#### 图定义 (`workflow_graph.py`)

```python
class WorkflowManager:
    def _build_graph(self):
        workflow = StateGraph(WorkflowState)
        
        # 添加节点
        workflow.add_node("planner", planner_node)
        workflow.add_node("coder", coder_node)
        workflow.add_node("executor", executor_node)
        workflow.add_node("reviewer", reviewer_node)
        
        # 定义边
        workflow.set_entry_point("planner")
        workflow.add_edge("planner", "coder")
        workflow.add_edge("coder", "executor")
        workflow.add_edge("executor", "reviewer")
        
        # 条件边（迭代）
        workflow.add_conditional_edges(
            "reviewer",
            self._should_continue,
            {"continue": "coder", "end": END}
        )
        
        return workflow.compile(checkpointer=MemorySaver())
```

### 6. 工具层

#### 文件工具 (`tools/file_tools.py`)

```python
def read_file(path: str) -> str:
    """读取文件内容"""

def write_file(path: str, content: str, mode: str = "w"):
    """写入文件"""

def file_exists(path: str) -> bool:
    """检查文件是否存在"""

def list_files(directory: str) -> List[str]:
    """列出目录中的文件"""
```

#### 代码执行器 (`tools/code_executor.py`)

```python
class CodeExecutor:
    def __init__(self, sandbox_type="docker"):
        self.sandbox_type = sandbox_type
    
    async def execute(self, code: str, language: str = "python") -> dict:
        """在沙箱中执行代码"""
        return {
            "stdout": "...",
            "stderr": "...",
            "exit_code": 0,
            "execution_time": 1.23
        }
```

#### 代码分析器 (`tools/code_analyzer.py`)

```python
class CodeAnalyzer:
    def analyze_syntax(self, code: str, language: str) -> dict:
        """语法分析"""
    
    def check_quality(self, code: str) -> dict:
        """代码质量检查"""
    
    def detect_security_issues(self, code: str) -> list:
        """安全问题检测"""
```

### 7. LLM 服务

**文件**: `app/core/llm_service.py`

```python
class LLMService:
    def __init__(self, provider="openai"):
        self.provider = provider
        self.client = self._create_client()
    
    def get_model(self, model_name: str):
        """获取 LLM 模型实例"""
    
    async def chat(self, messages: list) -> str:
        """发送聊天请求"""
```

---

## 数据流

### 任务执行流程

```
1. 用户创建任务
   ↓
2. API 接收请求，保存到数据库
   ↓
3. 触发工作流执行
   ↓
4. Planner Agent 分析需求 → 生成计划
   ↓
5. Coder Agent 根据计划 → 编写代码
   ↓
6. Executor → 在沙箱中执行代码
   ↓
7. Reviewer Agent → 审查代码
   ↓
8. 判断是否需要迭代
   ├─ 是 → 返回步骤 5
   └─ 否 → 完成
   ↓
9. 保存结果到数据库
   ↓
10. 返回结果给用户
```

### 状态转换

```
PENDING → PLANNING → CODING → EXECUTING → REVIEWING → COMPLETED
                              ↑              ↓
                              └──────────────┘ (迭代)
```

---

## 部署架构

### Docker Compose 部署

```yaml
services:
  postgres:    # PostgreSQL 数据库
  redis:       # Redis 缓存和消息队列
  api:         # FastAPI 应用
  worker:      # Celery Worker
  beat:        # Celery Beat 调度器
```

### 网络拓扑

```
┌─────────────────┐
│   User/Client   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────┐
│  API Server     │────▶│  PostgreSQL  │
│  (port 8000)    │     └──────────────┘
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────┐
│  Celery Worker  │────▶│     Redis    │
└────────┬────────┘     └──────────────┘
         │
         ▼
┌─────────────────┐
│  Docker Sandbox │
└─────────────────┘
```

---

## 安全考虑

### 1. 代码沙箱

- 使用 Docker 容器隔离代码执行
- 限制资源使用（CPU、内存）
- 设置执行超时
- 禁止网络访问

### 2. API 安全

- API Key 认证
- CORS 配置
- 请求速率限制
- 输入验证

### 3. 数据安全

- 数据库连接加密
- 敏感信息环境变量存储
- 定期备份

---

## 扩展性设计

### 添加新 Agent

1. 继承 `BaseAgent` 类
2. 实现 `execute()` 方法
3. 定义系统提示
4. 在工作流图中注册节点

### 添加新工具

1. 在 `app/tools/` 创建工具模块
2. 实现工具函数
3. 在 Agent 中调用工具

### 支持新语言

1. 扩展代码执行器
2. 添加语言特定的分析器
3. 配置 LLM 提示

---

## 性能优化

### 1. 数据库

- 连接池配置
- 索引优化
- 查询优化

### 2. 缓存

- Redis 缓存常用数据
- LLM 响应缓存
- 文件内容缓存

### 3. 异步处理

- Celery 异步任务
- 异步 I/O 操作
- 并发工作流执行

---

## 监控与日志

### 日志系统

```python
from loguru import logger

logger.info("Task started")
logger.warning("Iteration limit approaching")
logger.error("Workflow failed", exc_info=True)
```

### 监控指标

- 任务完成率
- 平均执行时间
- 迭代次数分布
- LLM 调用延迟
- 错误率

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 0.1.0 | 2024-01 | 初始架构设计 |

---

## 参考文档

- [API 参考](./API_REFERENCE.md)
- [开发指南](./DEVELOPMENT.md)
- [快速开始](../GET_STARTED.md)
