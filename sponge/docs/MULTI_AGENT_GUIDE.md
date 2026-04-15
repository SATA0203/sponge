# Sponge 多智能体协作指南

## 概述

Sponge 使用多个专业 AI Agent 协作完成代码开发任务。每个 Agent 都有特定的职责和技能，通过 LangGraph 工作流引擎协调工作。

---

## Agent 角色

### 1. Planner Agent（规划师）

**职责**: 分析需求，制定执行计划

**技能**:
- 需求分析
- 任务分解
- 架构设计
- 技术选型

**工作流程**:
```
输入：用户需求描述
  ↓
分析需求关键点
  ↓
识别技术挑战
  ↓
制定分步计划
  ↓
输出：详细的执行计划（JSON 格式）
```

**示例输出**:
```json
{
  "summary": "使用 FastAPI 创建 REST API",
  "steps": [
    {
      "step_number": 1,
      "description": "创建项目结构和依赖配置",
      "agent": "coder",
      "estimated_complexity": "low"
    },
    {
      "step_number": 2,
      "description": "实现数据模型和数据库连接",
      "agent": "coder",
      "estimated_complexity": "medium"
    },
    {
      "step_number": 3,
      "description": "创建 API 路由和端点",
      "agent": "coder",
      "estimated_complexity": "medium"
    },
    {
      "step_number": 4,
      "description": "编写单元测试",
      "agent": "tester",
      "estimated_complexity": "medium"
    }
  ]
}
```

---

### 2. Coder Agent（程序员）

**职责**: 根据计划编写高质量代码

**技能**:
- 多语言编程（Python、JavaScript 等）
- 代码结构设计
- 最佳实践应用
- 文档编写

**工作流程**:
```
输入：计划和需求
  ↓
理解每个步骤
  ↓
编写代码实现
  ↓
添加注释和文档
  ↓
输出：完整的代码文件
```

**编码规范**:
- 遵循 PEP 8（Python）或相应语言规范
- 添加类型注解
- 编写清晰的函数和变量名
- 包含 docstring

**示例输出**:
```python
"""
User authentication module using JWT
"""

from fastapi import HTTPException, status
from datetime import datetime, timedelta
from jose import jwt

class AuthManager:
    """Manage user authentication and JWT tokens"""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def create_token(self, data: dict, expires_delta: timedelta) -> str:
        """Create JWT token with expiration"""
        to_encode = data.copy()
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> dict:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
```

---

### 3. Reviewer Agent（审查员）

**职责**: 代码审查和质量保证

**技能**:
- 代码规范检查
- Bug 检测
- 性能分析
- 安全审计
- 最佳实践验证

**工作流程**:
```
输入：编写的代码
  ↓
静态代码分析
  ↓
规范检查
  ↓
安全问题扫描
  ↓
性能评估
  ↓
输出：审查报告和改进建议
```

**审查清单**:

#### 代码质量
- [ ] 命名是否清晰？
- [ ] 函数是否单一职责？
- [ ] 是否有重复代码？
- [ ] 错误处理是否完善？

#### 安全性
- [ ] 是否有 SQL 注入风险？
- [ ] 敏感信息是否加密？
- [ ] 输入是否验证？
- [ ] 权限检查是否到位？

#### 性能
- [ ] 是否有不必要的循环？
- [ ] 数据库查询是否优化？
- [ ] 是否合理使用缓存？
- [ ] 资源是否正确释放？

**示例输出**:
```json
{
  "passed": false,
  "score": 75,
  "issues": [
    {
      "type": "security",
      "severity": "high",
      "location": "auth.py:45",
      "message": "Password stored in plain text",
      "suggestion": "Use bcrypt or argon2 for password hashing"
    },
    {
      "type": "performance",
      "severity": "medium",
      "location": "user_service.py:23",
      "message": "N+1 query detected in loop",
      "suggestion": "Use batch query or join"
    }
  ],
  "positive_feedback": [
    "Good function naming",
    "Proper error handling",
    "Clear documentation"
  ]
}
```

---

### 4. Tester Agent（测试员）

**职责**: 编写和执行测试

**技能**:
- 单元测试
- 集成测试
- 边界条件测试
- 回归测试

**工作流程**:
```
输入：代码和功能需求
  ↓
分析测试场景
  ↓
编写测试用例
  ↓
执行测试
  ↓
输出：测试报告和覆盖率
```

**测试类型**:

#### 单元测试
```python
import pytest
from app.auth import AuthManager

def test_create_token():
    auth = AuthManager(secret_key="test-key")
    token = auth.create_token({"user_id": 1}, timedelta(hours=1))
    assert token is not None
    assert isinstance(token, str)

def test_verify_valid_token():
    auth = AuthManager(secret_key="test-key")
    token = auth.create_token({"user_id": 1}, timedelta(hours=1))
    payload = auth.verify_token(token)
    assert payload["user_id"] == 1

def test_verify_expired_token():
    auth = AuthManager(secret_key="test-key")
    token = auth.create_token({"user_id": 1}, timedelta(seconds=-1))
    with pytest.raises(HTTPException):
        auth.verify_token(token)
```

#### 集成测试
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_login_success():
    response = client.post("/api/login", json={
        "email": "test@example.com",
        "password": "correct_password"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_wrong_password():
    response = client.post("/api/login", json={
        "email": "test@example.com",
        "password": "wrong_password"
    })
    assert response.status_code == 401
```

**测试覆盖目标**:
- 语句覆盖率：≥ 80%
- 分支覆盖率：≥ 70%
- 关键路径：100%

---

## 协作流程

### 标准工作流

```
┌─────────────┐
│   Planner   │ 分析需求，制定计划
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Coder    │ 根据计划编写代码
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Executor  │ 在沙箱中执行代码
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Reviewer  │ 审查代码质量
└──────┬──────┘
       │
       ├───────→ 通过 ───────→ 完成
       │
       └───────→ 需改进 ─────→ 返回 Coder
```

### 迭代机制

当 Reviewer 发现代码问题时，会触发迭代：

1. Reviewer 提供详细的问题列表和改进建议
2. 系统增加迭代计数器
3. Coder 根据反馈修改代码
4. 重新执行和审查
5. 最多迭代 N 次（默认 3 次）

**迭代决策逻辑**:
```python
def _should_continue(state: WorkflowState) -> str:
    iterations = state.get("iterations", 0)
    max_iterations = state.get("max_iterations", 3)
    review_passed = state.get("review_result", {}).get("passed", False)
    
    if review_passed:
        return "end"
    
    if iterations >= max_iterations:
        return "end"  # 达到最大迭代次数
    
    return "continue"  # 继续迭代
```

---

## Agent 通信协议

### 状态共享

所有 Agent 通过共享的 `WorkflowState` 进行通信：

```python
class WorkflowState(TypedDict):
    task_id: str              # 任务 ID
    description: str          # 任务描述
    language: str             # 编程语言
    plan: Dict                # Planner 生成的计划
    code: Dict                # Coder 生成的代码
    execution_result: Dict    # Executor 的执行结果
    review_result: Dict       # Reviewer 的审查结果
    iterations: int           # 当前迭代次数
    max_iterations: int       # 最大迭代次数
    error: str                # 错误信息
    status: str               # 当前状态
```

### 消息传递

每个节点返回需要更新的状态字段：

```python
async def planner_node(state: WorkflowState) -> dict:
    # 只返回需要更新的字段
    return {
        "plan": generated_plan,
        "status": "planning_completed"
    }

async def coder_node(state: WorkflowState) -> dict:
    return {
        "code": generated_code,
        "iterations": state["iterations"] + 1,
        "status": "coding_completed"
    }
```

---

## Agent 配置

### LLM 配置

不同 Agent 可以使用不同的 LLM 配置：

```python
# Planner - 需要强大的推理能力
planner_llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.3,  # 较低温度，更稳定
    max_tokens=4096
)

# Coder - 需要精确的代码生成
coder_llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.2,  # 很低温度，确保准确性
    max_tokens=8192
)

# Reviewer - 需要细致的分析
reviewer_llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.1,  # 极低温度，最稳定
    max_tokens=4096
)
```

### 系统提示定制

每个 Agent 有专门的系统提示：

```python
# Planner 系统提示
PLANNER_SYSTEM_PROMPT = """
You are an expert software architect.
Analyze requirements and create detailed, actionable plans.
Break down complex tasks into clear steps.
Identify potential challenges and edge cases.
"""

# Coder 系统提示
CODER_SYSTEM_PROMPT = """
You are a senior software engineer.
Write clean, efficient, and well-documented code.
Follow best practices and coding standards.
Include type hints and docstrings.
"""

# Reviewer 系统提示
REVIEWER_SYSTEM_PROMPT = """
You are a meticulous code reviewer.
Check for bugs, security issues, and performance problems.
Provide constructive feedback.
Ensure code follows best practices.
"""
```

---

## 冲突解决

### 意见分歧

当不同 Agent 对同一问题有不同意见时：

1. **优先级规则**: Reviewer > Coder > Planner
2. **投票机制**: 多个 Reviewer 投票决定
3. **人工介入**: 严重分歧时请求人工审查

### 版本控制

代码修改遵循版本控制原则：

```python
class CodeVersion:
    version: int
    content: str
    timestamp: datetime
    author: str  # Agent name
    changes: str  # Change description
```

---

## 性能优化

### 并行处理

独立的 Agent 任务可以并行执行：

```python
# 并行执行多个文件的代码生成
results = await asyncio.gather(
    coder.generate_file(file1_spec),
    coder.generate_file(file2_spec),
    coder.generate_file(file3_spec),
)
```

### 缓存机制

缓存 Agent 的响应以减少 LLM 调用：

```python
@cache(ttl=3600)
async def get_plan(description: str) -> dict:
    return await planner.execute(description)
```

### 批处理

将多个小任务批量处理：

```python
# 批量审查多个文件
review_results = await reviewer.batch_review(code_files)
```

---

## 监控与调试

### 日志记录

```python
from loguru import logger

logger.info(f"Planner started for task {task_id}")
logger.debug(f"Plan generated: {plan}")
logger.warning(f"Iteration {iteration} exceeded threshold")
logger.error(f"Agent failed: {error}", exc_info=True)
```

### 指标收集

```python
# 收集 Agent 执行指标
metrics = {
    "agent_name": "planner",
    "execution_time": duration,
    "tokens_used": token_count,
    "success": True,
    "iteration": 1
}
```

### 调试模式

启用详细日志和中间状态输出：

```python
workflow = WorkflowManager(debug=True)
# 输出每个节点的输入输出
```

---

## 最佳实践

### 1. 明确分工

- Planner 专注于宏观规划
- Coder 专注于代码实现
- Reviewer 专注于质量保证
- 各司其职，不越界

### 2. 充分沟通

- 计划要详细具体
- 代码要有清晰注释
- 审查意见要明确可执行

### 3. 迭代改进

- 接受多次迭代
- 每次迭代都要有进步
- 设置合理的迭代上限

### 4. 质量保证

- 不通过审查的代码不接受
- 测试覆盖率要达标
- 安全问题零容忍

---

## 扩展指南

### 添加新 Agent 类型

1. 定义新的 Agent 类继承 `BaseAgent`
2. 实现特定的 `execute()` 方法
3. 定义系统提示
4. 在工作流图中添加节点
5. 编写测试用例

### 自定义工作流

```python
# 创建自定义工作流
custom_workflow = StateGraph(WorkflowState)

# 添加自定义节点
custom_workflow.add_node("custom_agent", custom_node)

# 定义自定义边
custom_workflow.add_edge("planner", "custom_agent")
custom_workflow.add_edge("custom_agent", "coder")
```

---

## 参考文档

- [架构设计](./ARCHITECTURE.md)
- [API 参考](./API_REFERENCE.md)
- [开发指南](./DEVELOPMENT.md)
