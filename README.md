# Orchestrator-Worker AI Agent System

一个基于 **Orchestrator-Worker** 架构的多 Agent 协作系统，专为解决长周期、高复杂度任务设计。

## 🏗️ 架构理念

本系统摒弃了传统的"三省六部"式角色分工架构（如 PM→Dev→QA 流水线），采用 Anthropic、OpenAI、Google 等厂商推荐的 **Orchestrator-Worker** 模式：

- **推理链连续性**：通过外部状态文件锚定推理过程，避免信息在传递中丢失
- **显式状态管理**：不依赖模型记忆，所有关键状态持久化到文件系统
- **并行探索而非分工**：Worker Agents 并行执行子任务，结果回流到 Orchestrator 综合
- **对抗性验证**：Validator Agent 专门寻找问题，而非接棒修复

## 🚀 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行工作流
python -m app.main --task "Build a REST API with auth"
```

## 📐 核心架构

### 组件概览

```
┌─────────────────────────────────────────────────────────────┐
│                    OrchestratorAgent                        │
│  (持有完整任务意图，负责任务分解、协调、综合)                │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  WorkerAgent    │  │  WorkerAgent    │  │  WorkerAgent    │
│  (并行执行)     │  │  (并行执行)     │  │  (并行执行)     │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ▼
                     ┌─────────────────┐
                     │ ValidatorAgent  │
                     │ (对抗性验证)    │
                     └─────────────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │ External State  │
                     │ (spec.md,       │
                     │  history.jsonl) │
                     └─────────────────┘
```

### 核心模块

| 模块 | 路径 | 职责 |
|-----|------|------|
| **OrchestratorAgent** | `app/orchestrator/agent.py` | 主协调器，持有完整意图，不传递所有权 |
| **WorkerAgent** | `app/orchestrator/worker.py` | 通用执行者，支持 6 种动态任务类型 |
| **ValidatorAgent** | `app/orchestrator/validator.py` | 纯对抗性验证，只找问题不接棒 |
| **TaskProgress** | `app/core/task_progress.py` | 外部状态管理系统 |
| **StateAwareFileTools** | `app/tools/file_tools.py` | 增强型文件工具，支持状态感知 |
| **OrchestratorWorkflow** | `app/orchestrator/workflow.py` | 四阶段工作流引擎 |

## 📁 外部状态系统

系统通过以下文件维护跨 Session 的状态连续性：

| 文件 | 类型 | 用途 |
|-----|------|------|
| `spec.md` | Immutable | 任务目标，防止漂移 |
| `history.jsonl` | Append-only | 推理链历史，保留 reasoning 过程 |
| `current_status.json` | Overwrite | 当前执行状态 |
| `known_issues.json` | Append-only | 已知问题清单，避免重复踩坑 |

## 🔧 使用示例

### 基础用法

```python
from app.orchestrator.workflow import run_workflow

result = await run_workflow(
    task_id="task-123",
    description="Build a REST API with authentication",
    language="python",
    constraints=["Use FastAPI", "Include JWT auth", "Add unit tests"]
)
```

### 自定义 Worker 任务类型

```python
from app.orchestrator.worker import WorkerAgent

worker = WorkerAgent()

# 支持的 task_type:
# - research, design, implement, test, review, refactor
await worker.execute(
    task_type="implement",
    instruction="Implement the user registration endpoint",
    context={"spec": "...", "design": "..."}
)
```

### 状态查询

```python
from app.core.task_progress import TaskProgress

progress = TaskProgress("task-123")

# 读取 spec
spec = progress.read_spec()

# 追加历史记录
progress.append_to_history({
    "step": "implemented_auth",
    "reasoning": "Used JWT because...",
    "timestamp": "2024-01-15T10:30:00Z"
})

# 获取已知问题
issues = progress.get_known_issues()
```

## 📊 架构对比

| 维度 | 旧架构 (三省六部) | 新架构 (Orchestrator-Worker) |
|-----|------------------|----------------------------|
| 信息流转 | 流水线 A→B→C | 回流到 Orchestrator |
| 状态管理 | 内存传递 | 外部文件持久化 |
| 角色边界 | 固定角色 (PM/Dev/QA) | 动态任务类型 |
| 验证方式 | Reviewer 接棒修复 | Validator 只找问题 |
| 推理连续性 | 依赖模型记忆 | 外部状态锚定 |
| 并行能力 | 顺序执行 | 支持并行子任务 |

## 🎯 适用场景

### ✅ 推荐使用
- 长周期任务（>1 小时）
- 需要跨 Session 保持上下文连续性
- 需要并行探索多个独立方向
- 对目标漂移敏感的任务

### ❌ 不推荐使用
- 简单单次查询任务
- 不需要状态持久化的临时任务
- 低延迟实时交互场景

## 📈 监控与指标

系统内置以下监控指标：

- **状态文件完整性**：检查 spec/history/status/issues 是否完整
- **推理链断裂检测**：识别 history.jsonl 中的 gaps
- **目标漂移检测**：对比当前输出与 spec.md 的一致性
- **Token 效率**：追踪用于推理 vs 用于交接的 token 比例

## 🔮 架构演化

本架构设计遵循**可演化性原则**：

- 不硬编码模型特定行为（如 context anxiety workaround）
- 工具接口与模型能力解耦
- 状态文件格式版本化，支持向后兼容

随着模型能力提升，部分 workaround 可能被移除，但核心架构原则保持不变。

## 📚 参考资料

- [Anthropic: Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
- [Anthropic: Effective Context Engineering](https://www.anthropic.com/research/effective-context-engineering)
- [OpenAI: Run Long Horizon Tasks with Codex](https://platform.openai.com/docs/guides/long-tasks)
- [Google: Conductor - Context-Driven Development](https://developers.googleblog.com/conductor)

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request。请在提交前确保：

1. 新增功能符合 Orchestrator-Worker 架构原则
2. 所有状态变更都有外部持久化
3. 不引入固定角色边界的代码
4. 添加相应的单元测试

## 📄 许可证

MIT License
