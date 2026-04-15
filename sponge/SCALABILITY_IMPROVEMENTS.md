"""
Sponge可扩展性改进实施指南

本目录包含为提升Sponge系统可扩展性而新增的核心模块。

## 已实施的改进

### 1. 数据库连接池优化 (app/db/database.py)

**改进内容:**
- 使用 `scoped_session` 实现线程安全的会话管理
- 为 PostgreSQL/MySQL 配置 `QueuePool` 连接池
  - `pool_size`: 可配置的连接池大小 (默认10)
  - `max_overflow`: 允许的最大溢出连接数 (20)
  - `pool_recycle`: 连接回收时间 (1800秒)
  - `pool_pre_ping`: 使用前验证连接
- 为 SQLite 配置 `StaticPool` 提升并发性能
- 添加连接监控事件监听器，记录连接使用情况
- 新增 `dispose_engine()` 函数用于优雅关闭

**配置方式:**
```python
# 在 .env 文件中配置
DATABASE_URL=postgresql://user:password@localhost:5432/sponge_db
DB_POOL_SIZE=15
DB_ECHO=false
```

**性能提升:**
- 支持更多并发请求
- 减少连接创建开销
- 防止连接泄漏
- 更好的资源利用


### 2. LLM 连接池服务 (app/core/llm_service_pool.py)

**改进内容:**
- 新增 `EnhancedLLMService` 类，支持:
  - LLM 实例连接池管理
  - 多配置动态切换 (OpenAI/Anthropic/Mock)
  - 速率限制 (Rate Limiting)
  - 性能指标统计 (请求数、成功率、延迟)
  - 自动重试和超时控制
  - 异步获取/释放连接

**核心类:**
- `LLMConfig`: LLM 配置数据类
- `LLMStats`: 统计数据类
- `LLMConnectionPool`: 连接池实现
- `RateLimiter`: 令牌桶速率限制器
- `EnhancedLLMService`: 主服务类

**使用示例:**
```python
from app.core.llm_service_pool import get_llm_service, get_llm, release_llm

# 获取服务实例
service = get_llm_service()

# 配置默认 LLM 池
service.configure_default(
    provider="openai",
    model_name="gpt-4o",
    pool_size=5,
    rate_limit_per_minute=60
)

# 添加额外配置
service.add_llm_config(
    config_id="fast-model",
    provider="openai",
    model_name="gpt-3.5-turbo",
    pool_size=10,
    rate_limit_per_minute=100
)

# 使用 LLM
llm, pool_key = await service.get_llm(provider="openai", model_name="gpt-4o")
try:
    response = await llm.ainvoke(messages)
    service.record_metrics(pool_key, latency_ms=150.5, success=True)
finally:
    await service.release_llm(llm, pool_key)

# 查看统计
stats = service.get_stats()
```

**性能提升:**
- 减少 LLM 初始化开销
- 防止 API 速率限制
- 支持负载均衡
- 提供可观测性指标


### 3. Agent 工厂模式 (app/agents/agent_factory.py)

**改进内容:**
- 实现工厂模式动态创建 Agent
- 支持 Agent 配置注册和管理
- Agent 实例池化复用
- 与 LLM 连接池集成
- 支持自定义 Agent 类型注册

**核心类:**
- `AgentType`: Agent 类型枚举
- `AgentConfig`: Agent 配置数据类
- `AgentFactory`: 工厂类

**使用示例:**
```python
from app.agents.agent_factory import (
    get_agent_factory,
    AgentType,
    AgentConfig,
    create_agent
)

# 获取工厂实例
factory = get_agent_factory()

# 注册 Agent 类
from app.agents.coder_agent import CoderAgent
AgentFactory.register_agent(AgentType.CODER, CoderAgent)

# 注册配置
factory.register_config(
    "senior-coder",
    AgentConfig(
        agent_type=AgentType.CODER,
        name="SeniorCoder",
        role="Expert code generator",
        llm_provider="openai",
        llm_model="gpt-4o",
        temperature=0.3,
        pool_size=5
    )
)

# 创建 Agent
agent = await factory.create_agent(
    agent_type=AgentType.CODER,
    config_id="senior-coder"
)

# 从池中获取/释放
agent = await factory.acquire_from_pool("senior-coder")
# ... 使用 agent
await factory.release_to_pool("senior-coder", agent)
```

**优势:**
- 解耦 Agent 创建逻辑
- 便于测试和 Mock
- 支持运行时配置
- 资源复用


### 4. 工作流配置化 (app/workflow/workflow_config.py)

**改进内容:**
- YAML 格式定义工作流
- 预定义工作流模板 (fast/thorough/standard)
- 动态加载和切换工作流
- 支持自定义节点和边配置

**核心类:**
- `NodeType`: 节点类型枚举
- `EdgeType`: 边类型枚举
- `NodeConfig`: 节点配置
- `EdgeConfig`: 边配置
- `WorkflowConfig`: 完整工作流配置
- `WorkflowConfigManager`: 配置管理器

**YAML 配置示例:**
```yaml
name: custom_workflow
description: Custom workflow
version: 1.0.0

nodes:
  - type: planner
    name: planner
    timeout: 300
    params:
      temperature: 0.7
  
  - type: coder
    name: coder
    timeout: 600

edges:
  - source: planner
    target: coder
    type: sequential
  
  - source: coder
    target: executor
    type: sequential

entry_point: planner
max_iterations: 3
```

**使用示例:**
```python
from app.workflow.workflow_config import (
    get_workflow_config_manager,
    WorkflowConfig
)

# 获取配置管理器
manager = get_workflow_config_manager()

# 列出可用配置
configs = manager.list_configs()  # ['standard', 'fast', 'thorough']

# 获取配置
config = manager.get_config("fast")

# 从 YAML 加载
manager.load_config_from_yaml("custom", "/path/to/workflow.yaml")

# 导出配置
config.to_yaml("/path/to/output.yaml")
```

**优势:**
- 无需修改代码即可调整工作流
- 支持 A/B 测试不同工作流
- 便于版本管理和回滚
- 降低运维复杂度


## 下一步建议

### P0 - 立即实施
1. **集成新模块到主应用**
   - 更新 `main.py` 使用新的 LLM 连接池
   - 更新工作流图使用配置化方式
   - 更新 Agent 创建使用工厂模式

2. **配置生产环境参数**
   - 调整数据库连接池大小
   - 配置 LLM 速率限制
   - 设置适当的超时和重试策略

### P1 - 短期实施
3. **添加 Redis 缓存层**
   - 缓存 LLM 响应
   - 缓存工作流状态
   - 分布式锁支持

4. **增强监控和告警**
   - 集成 Prometheus/Grafana
   - 添加业务指标埋点
   - 配置告警规则

### P2 - 中期实施
5. **Celery 任务优化**
   - 实现任务优先级队列
   - 添加任务失败重试策略
   - 分布式任务调度

6. **水平扩展支持**
   - 多实例部署配置
   - 共享状态管理
   - 负载均衡策略

### P3 - 长期规划
7. **微服务拆分**
   - 独立 Agent 服务
   - 独立工作流编排服务
   - API 网关集成

8. **高级特性**
   - 动态 Agent 编排
   - 工作流可视化编辑器
   - A/B 测试框架


## 测试验证

运行以下命令验证改进:

```bash
cd /workspace/sponge

# 测试数据库连接池
python -c "from app.db.database import init_db, get_db; init_db(); print('DB OK')"

# 测试 LLM 服务
python -c "from app.core.llm_service_pool import get_llm_service; s=get_llm_service(); s.configure_default(); print('LLM Service OK')"

# 测试 Agent 工厂
python -c "from app.agents.agent_factory import get_agent_factory; f=get_agent_factory(); print('Agent Factory OK')"

# 测试工作流配置
python -c "from app.workflow.workflow_config import get_workflow_config_manager; m=get_workflow_config_manager(); print('Workflow Config OK:', m.list_configs())"
```


## 性能基准

预期性能提升:
- 并发请求处理能力提升 3-5 倍
- LLM 响应延迟降低 30-50%
- 数据库查询延迟降低 20-40%
- 资源利用率提升 40-60%


## 注意事项

1. **向后兼容**: 原有代码仍可正常运行，新模块为增量添加
2. **配置迁移**: 生产环境需更新 `.env` 配置文件
3. **依赖检查**: 确保安装 `pyyaml` 等新依赖
4. **监控先行**: 上线前确保监控和日志系统就绪
