# Sponge API 文档

## 概述

Sponge 提供 RESTful API 用于管理多智能体协作的代码开发任务。所有 API 端点都支持 JSON 格式的请求和响应。

**基础 URL**: `http://localhost:8000`  
**API 版本**: `v1`  
**文档地址**: 
- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`

---

## 认证

当前版本支持通过 HTTP Header 传递 API Key：

```
X-API-Key: your-api-key-here
```

> ⚠️ **注意**: 生产环境中请配置有效的 API Key 并启用 HTTPS。

---

## 健康检查接口

### 1. 基础健康检查

```http
GET /health/
```

**响应示例**:
```json
{
  "status": "healthy",
  "service": "Sponge",
  "version": "0.1.0"
}
```

### 2. 就绪检查

```http
GET /health/ready
```

检查服务是否准备好接收请求（数据库连接、Redis 等）。

**响应示例**:
```json
{
  "ready": true,
  "checks": {
    "database": "connected",
    "redis": "connected",
    "llm_service": "available"
  }
}
```

### 3. 存活检查

```http
GET /health/live
```

检查服务进程是否存活。

---

## 任务管理接口

### 1. 创建任务

```http
POST /api/v1/tasks/
Content-Type: application/json
```

**请求体**:
```json
{
  "title": "创建用户认证模块",
  "description": "实现基于 JWT 的用户登录和注册功能",
  "requirements": "需要支持邮箱验证、密码加密、Token 刷新",
  "priority": "high",
  "tags": ["authentication", "security", "backend"],
  "language": "python",
  "max_iterations": 3
}
```

**字段说明**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | ✅ | 任务标题 |
| description | string | ✅ | 任务详细描述 |
| requirements | string | ❌ | 额外需求说明 |
| priority | string | ❌ | 优先级：low/medium/high |
| tags | array | ❌ | 标签列表 |
| language | string | ❌ | 目标编程语言，默认 python |
| max_iterations | integer | ❌ | 最大迭代次数，默认 3 |

**成功响应 (201)**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "创建用户认证模块",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00Z",
  "message": "Task created successfully"
}
```

### 2. 获取任务列表

```http
GET /api/v1/tasks/
```

**查询参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| status | string | 按状态过滤 |
| priority | string | 按优先级过滤 |
| limit | integer | 返回数量限制，默认 20 |
| offset | integer | 分页偏移量 |

**响应示例**:
```json
{
  "total": 15,
  "tasks": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "创建用户认证模块",
      "status": "coding",
      "priority": "high",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### 3. 获取任务详情

```http
GET /api/v1/tasks/{task_id}
```

**响应示例**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "title": "创建用户认证模块",
  "description": "实现基于 JWT 的用户登录和注册功能",
  "status": "completed",
  "current_step": "code_review",
  "iterations": 2,
  "plan": {
    "summary": "使用 FastAPI + JWT 实现认证",
    "steps": [
      {
        "step_number": 1,
        "description": "创建用户模型",
        "agent": "coder",
        "status": "completed"
      }
    ]
  },
  "code": {
    "files": [
      {
        "path": "auth.py",
        "content": "..."
      }
    ]
  },
  "review_result": {
    "passed": true,
    "comments": ["代码结构清晰", "建议添加更多测试"]
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T11:45:00Z"
}
```

### 4. 取消任务

```http
POST /api/v1/tasks/{task_id}/cancel
```

**响应示例**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "cancelled",
  "message": "Task cancelled successfully"
}
```

### 5. 删除任务

```http
DELETE /api/v1/tasks/{task_id}
```

**响应示例**:
```json
{
  "message": "Task deleted successfully"
}
```

---

## 文件管理接口

### 1. 获取任务文件列表

```http
GET /api/v1/files/?task_id={task_id}
```

**响应示例**:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "files": [
    {
      "uuid": "file-uuid-1",
      "filename": "auth.py",
      "filepath": "/workspace/tasks/550e8400/auth.py",
      "file_type": "python",
      "size": 2048,
      "created_at": "2024-01-15T10:35:00Z"
    }
  ]
}
```

### 2. 获取文件内容

```http
GET /api/v1/files/content?task_id={task_id}&path=auth.py
```

**响应示例**:
```json
{
  "filename": "auth.py",
  "filepath": "/workspace/tasks/550e8400/auth.py",
  "content": "from fastapi import ...\n\nclass AuthManager:\n    ...",
  "file_type": "python",
  "size": 2048
}
```

### 3. 更新文件

```http
POST /api/v1/files/update
Content-Type: application/json
```

**请求体**:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "path": "auth.py",
  "content": "updated code content...",
  "mode": "overwrite"
}
```

**模式说明**:
- `overwrite`: 覆盖整个文件
- `append`: 追加到文件末尾
- `insert`: 在指定位置插入（需指定 `line_number`）

### 4. 检查文件是否存在

```http
GET /api/v1/files/exists?task_id={task_id}&path=auth.py
```

**响应示例**:
```json
{
  "exists": true,
  "path": "/workspace/tasks/550e8400/auth.py"
}
```

---

## 工作流执行接口

### 1. 直接执行工作流

```http
POST /api/v1/workflow/execute
Content-Type: application/json
```

**请求体**:
```json
{
  "description": "创建一个快速排序算法实现",
  "language": "python",
  "max_iterations": 3,
  "enable_review": true,
  "enable_tests": true
}
```

**响应示例**:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "message": "Workflow started. Use task_id to check progress."
}
```

### 2. 获取工作流状态

```http
GET /api/v1/workflow/{task_id}/status
```

**响应示例**:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "reviewing",
  "current_node": "reviewer",
  "progress": {
    "planner": "completed",
    "coder": "completed",
    "executor": "completed",
    "reviewer": "running"
  },
  "iterations": 1,
  "estimated_completion": "2024-01-15T11:50:00Z"
}
```

---

## 错误响应

所有接口在发生错误时返回统一的错误格式：

```json
{
  "error": {
    "code": "TASK_NOT_FOUND",
    "message": "Task with ID 'xxx' not found",
    "details": {}
  }
}
```

**常见错误码**:

| 错误码 | HTTP 状态码 | 说明 |
|--------|------------|------|
| TASK_NOT_FOUND | 404 | 任务不存在 |
| INVALID_REQUEST | 400 | 请求参数无效 |
| UNAUTHORIZED | 401 | 未授权访问 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |
| LLM_SERVICE_UNAVAILABLE | 503 | LLM 服务不可用 |
| SANDBOX_TIMEOUT | 504 | 沙箱执行超时 |

---

## WebSocket 实时通知

Sponge 支持 WebSocket 连接以接收任务状态实时更新：

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/tasks/{task_id}');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Task update:', data);
};
```

**消息格式**:
```json
{
  "type": "status_update",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "coding",
  "timestamp": "2024-01-15T10:35:00Z",
  "data": {
    "current_step": "implementing_function",
    "progress_percent": 45
  }
}
```

---

## 速率限制

| 端点类型 | 限制 |
|---------|------|
| 任务创建 | 10 次/分钟 |
| 任务查询 | 60 次/分钟 |
| 文件操作 | 30 次/分钟 |
| 工作流执行 | 5 次/分钟 |

超过限制将返回 `429 Too Many Requests` 错误。

---

## 最佳实践

### 1. 轮询任务状态

```python
import time
import httpx

async def wait_for_task(task_id: str, timeout: int = 300):
    """Poll task status until completion"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = await httpx.get(f"http://localhost:8000/api/v1/tasks/{task_id}")
        data = response.json()
        
        if data["status"] in ["completed", "failed", "cancelled"]:
            return data
        
        await asyncio.sleep(5)
    
    raise TimeoutError("Task did not complete within timeout")
```

### 2. 批量创建任务

```python
tasks = [
    {"title": "Task 1", "description": "..."},
    {"title": "Task 2", "description": "..."},
]

async with httpx.AsyncClient() as client:
    responses = await asyncio.gather(*[
        client.post("http://localhost:8000/api/v1/tasks/", json=task)
        for task in tasks
    ])
```

### 3. 错误处理

```python
try:
    response = await client.post("/api/v1/tasks/", json=payload)
    response.raise_for_status()
except httpx.HTTPStatusError as e:
    error_data = e.response.json()
    print(f"API Error: {error_data['error']['message']}")
```

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0.0 | 2024-01 | 初始版本 |

---

## 联系支持

- GitHub Issues: [提交问题](https://github.com/sponge/issues)
- 文档：[完整文档](./DEVELOPMENT.md)
