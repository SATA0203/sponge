# Sponge Agent 架构重构方案

## 一、现状问题分析

### 1.1 当前架构问题

当前项目采用了典型的"三省六部"式架构，存在以下根本性缺陷：

**问题 1：流水线式分工导致信息损耗**
```
Planner → Coder → Executor → Reviewer → Tester
```
- 每个 Agent 只接收压缩后的结论，丢失推理过程
- 任务在 Agent 间传递时，原始意图衰减，隐含假设丢失
- 造成"局部正确但整体漂移"的风险

**问题 2：角色标签制造假边界**
- Planner、Coder、Reviewer、Tester 被限定在特定职责
- Agent 可能拒绝越界处理边界问题（如 Coder 看到架构问题直接跳过）
- 最有价值的推理往往发生在边界上，但系统封死了这个可能性

**问题 3：WorkflowState 传递的是结果而非推理链**
```python
class WorkflowState(TypedDict):
    plan: Dict[str, Any]        # 只存储计划结论
    code: Dict[str, Any]        # 只存储代码结果
    execution_result: Dict      # 只存储执行结果
    review_result: Dict         # 只存储评审结论
    test_result: Dict           # 只存储测试结果
```
- 缺少推理过程的记录
- 下一个节点无法理解上一个节点的思考过程
- 迭代改进时缺乏上下文依据

### 1.2 与文章原则的对比

| 文章建议 | 当前实现 | 差距 |
|---------|---------|------|
| 推理链不能断，只能分叉再合并 | 流水线传递，每步都是断点 | ❌ |
| 显式外部状态，不靠模型记住 | 仅内存中的 WorkflowState | ❌ |
| 多 Agent 价值是并行覆盖，非分工 | 职能性分工（Planner→Coder→Reviewer） | ❌ |
| 验证 Agent 应为否定者，非接棒者 | Reviewer/Test 后传给下一棒 | ❌ |
| 工具是工具，不是角色 | 按角色划分 Agent | ❌ |

---

## 二、重构目标

### 2.1 核心原则

1. **Orchestrator-Worker 架构**：单一主 Agent 持有完整任务意图，Worker 用于并行探索
2. **显式外部状态**：使用持久化文件（task_progress.md）记录推理链
3. **推理链连续**：同一任务的增量日志，下一个 session 读取完整历史
4. **对抗性检验**：验证 Agent 唯一任务是找问题，不是接棒继续做

### 2.2 架构对比

**当前架构（三省六部）**：
```
┌─────────┐    ┌───────┐    ┌──────────┐    ┌──────────┐    ┌────────┐
│Planner  │───▶│ Coder │───▶│ Executor │───▶│ Reviewer │───▶│ Tester │
└─────────┘    └───────┘    └──────────┘    └──────────┘    └────────┘
     ↓              ↓              ↓              ↓              ↓
  分解任务       写代码        执行代码        审查代码        测试代码
  (传递给 Coder)  (传递给 Exec)  (传递给 Rev)    (传递给 Test)   (结束)
```

**目标架构（Orchestrator-Worker）**：
```
                    ┌─────────────────┐
                    │  Orchestrator   │
                    │  (主 Agent)     │
                    │  持有完整意图   │
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
            ▼                ▼                ▼
     ┌───────────┐    ┌───────────┐    ┌───────────┐
     │  Planning │    │  Coding   │    │  Testing  │
     │  Worker   │    │  Worker   │    │  Worker   │
     └─────┬─────┘    └─────┬─────┘    └─────┬─────┘
           │                │                │
           └────────────────┴────────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │  task_progress  │
                   │  (外部状态文件) │
                   └─────────────────┘
```

---

## 三、重构方案

### 3.1 第一阶段：建立外部状态系统（优先级最高）

#### 3.1.1 创建状态文件管理器

```python
# sponge/app/core/state_manager.py

from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
import json
from loguru import logger


class TaskProgress:
    """
    外部状态文件管理类
    对应文章中的 progress.txt/spec 文件/runbook
    """
    
    def __init__(self, task_id: str, project_root: str = "./tasks"):
        self.task_id = task_id
        self.project_root = Path(project_root)
        self.progress_file = self.project_root / task_id / "task_progress.md"
        self.spec_file = self.project_root / task_id / "spec.md"
        self._ensure_task_dir()
    
    def _ensure_task_dir(self):
        """确保任务目录存在"""
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
    
    def initialize(self, task_description: str, requirements: List[str] = None):
        """
        初始化任务状态文件
        只在第一个 session 运行，建立环境和 feature list
        """
        spec_content = f"""# Task Specification

## Task ID
{self.task_id}

## Task Description
{task_description}

## Requirements
"""
        if requirements:
            for req in requirements:
                spec_content += f"- {req}\n"
        
        self.spec_file.write_text(spec_content)
        
        progress_content = f"""# Task Progress Log

## Task Goal (不变，防止漂移)
{task_description}

## Completed Steps (追加，保留完整历史)
<!-- 已完成的步骤将追加到这里 -->

## Current Status (覆盖，反映最新进展)
- Status: initialized
- Last Updated: {datetime.now().isoformat()}

## Known Issues (追加，避免重复踩坑)
<!-- 已知问题将追加到这里 -->
"""
        self.progress_file.write_text(progress_content)
        logger.info(f"Task {self.task_id} initialized with spec and progress files")
    
    def append_step(self, step_number: int, description: str, result: Dict[str, Any]):
        """
        追加已完成步骤（不覆盖，保留完整历史）
        """
        content = self.progress_file.read_text()
        
        step_entry = f"""
### Step {step_number}: {description}
- Completed At: {datetime.now().isoformat()}
- Result: {json.dumps(result, ensure_ascii=False, indent=2)}
"""
        
        # 找到"Completed Steps"部分并追加
        marker = "## Completed Steps (追加，保留完整历史)"
        if marker in content:
            parts = content.split(marker, 1)
            content = parts[0] + marker + step_entry + "\n" + parts[1]
        
        self.progress_file.write_text(content)
    
    def update_status(self, status: str, details: str = ""):
        """
        更新当前状态（覆盖，反映最新进展）
        """
        content = self.progress_file.read_text()
        
        new_status = f"""## Current Status (覆盖，反映最新进展)
- Status: {status}
- Details: {details}
- Last Updated: {datetime.now().isoformat()}
"""
        
        # 替换 Current Status 部分
        import re
        pattern = r"## Current Status.*?(?=##|\Z)"
        content = re.sub(pattern, new_status, content, flags=re.DOTALL)
        
        self.progress_file.write_text(content)
    
    def add_known_issue(self, issue: str, workaround: str = ""):
        """
        追加已知问题（避免下一个 session 重复踩坑）
        """
        content = self.progress_file.read_text()
        
        issue_entry = f"""
### Issue: {issue}
- Reported At: {datetime.now().isoformat()}
- Workaround: {workaround or "None"}
"""
        
        marker = "## Known Issues (追加，避免重复踩坑)"
        if marker in content:
            parts = content.split(marker, 1)
            content = parts[0] + marker + issue_entry + "\n" + parts[1]
        
        self.progress_file.write_text(content)
    
    def get_full_context(self) -> str:
        """
        获取完整的任务上下文
        供下一个 session 读取完整历史
        """
        context_parts = []
        
        # 读取 spec
        if self.spec_file.exists():
            context_parts.append("# Task Specification\n")
            context_parts.append(self.spec_file.read_text())
        
        # 读取 progress
        if self.progress_file.exists():
            context_parts.append("\n# Task Progress\n")
            context_parts.append(self.progress_file.read_text())
        
        return "\n".join(context_parts)
    
    def load(self) -> Dict[str, Any]:
        """
        加载当前状态
        """
        if not self.progress_file.exists():
            return {}
        
        content = self.progress_file.read_text()
        # 简单解析 Markdown（实际可使用更复杂的解析器）
        return {
            "content": content,
            "task_id": self.task_id,
        }
```

#### 3.1.2 修改 WorkflowState 增加状态文件引用

```python
# sponge/app/workflow/nodes.py (修改)

class WorkflowState(TypedDict):
    task_id: str
    description: str
    language: str
    
    # 保留原有字段用于向后兼容
    plan: Dict[str, Any]
    code: Dict[str, Any]
    execution_result: Dict[str, Any]
    review_result: Dict[str, Any]
    test_result: Dict[str, Any]
    
    # 新增：外部状态管理
    iterations: int
    max_iterations: int
    error: str
    status: str
    
    # 新增：状态文件路径
    progress_file_path: str  # task_progress.md 的路径
    spec_file_path: str      # spec.md 的路径
```

---

### 3.2 第二阶段：重构为 Orchestrator-Worker 架构

#### 3.2.1 创建 Orchestrator Agent

```python
# sponge/app/orchestrator/orchestrator_agent.py

from typing import Any, Dict, List, Optional
from langchain_core.language_models import BaseLanguageModel
from loguru import logger
from app.core.state_manager import TaskProgress


class OrchestratorAgent:
    """
    主协调 Agent - 持有完整任务意图
    负责任务分解、Worker 调度、结果综合
    """
    
    def __init__(self, llm: BaseLanguageModel, name: str = "Orchestrator"):
        self.llm = llm
        self.name = name
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        return """You are an expert orchestrator agent managing a complex coding task.

Your responsibilities:
1. Hold the complete understanding of the task goal and requirements
2. Decompose tasks into independent subtasks that can be explored in parallel
3. Coordinate worker agents to execute subtasks
4. Synthesize results from workers into a coherent solution
5. Maintain reasoning continuity across sessions via external state files

Key principles:
- Never lose the original task intent - always refer back to the spec
- When decomposing tasks, ensure subtasks are truly independent
- Results from workers should flow back to you, not to other workers
- Use external state files (task_progress.md) to maintain continuity
- You are the only agent that sees the complete picture

Output format:
Return JSON with:
- current_phase: planning/coding/reviewing/testing/completed
- next_actions: List of actions to take
- worker_assignments: Tasks to assign to workers (if any)
- synthesis: Combined results from workers (if applicable)
"""
    
    async def execute(
        self,
        task_id: str,
        description: str,
        progress: Optional[TaskProgress] = None,
        worker_results: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Execute orchestration logic
        
        Args:
            task_id: Task identifier
            description: Task description
            progress: External state manager
            worker_results: Results from worker agents (if any)
        
        Returns:
            Orchestration decision with next steps
        """
        # Build context from external state
        context = self._build_context(description, progress, worker_results)
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": context},
        ]
        
        response = await self.llm.ainvoke(messages)
        return self._parse_response(response.content)
    
    def _build_context(
        self,
        description: str,
        progress: Optional[TaskProgress],
        worker_results: Optional[List[Dict[str, Any]]],
    ) -> str:
        """Build complete context for orchestration"""
        context_parts = [f"Task Description: {description}\n"]
        
        if progress:
            context_parts.append("\n=== Task Progress (from external state) ===")
            context_parts.append(progress.get_full_context())
        
        if worker_results:
            context_parts.append("\n=== Worker Results ===")
            for i, result in enumerate(worker_results):
                context_parts.append(f"\nWorker {i+1} Result:")
                context_parts.append(str(result))
        
        return "\n".join(context_parts)
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response"""
        import json
        import re
        
        # Try to extract JSON
        start_idx = response.find("{")
        end_idx = response.rfind("}") + 1
        
        if start_idx >= 0 and end_idx > start_idx:
            json_str = response[start_idx:end_idx]
            return json.loads(json_str)
        
        # Fallback
        return {
            "current_phase": "planning",
            "next_actions": ["Continue analysis"],
            "worker_assignments": [],
            "synthesis": response,
        }
```

#### 3.2.2 创建通用 Worker Agent

```python
# sponge/app/orchestrator/worker_agent.py

from typing import Any, Dict, Optional
from langchain_core.language_models import BaseLanguageModel
from loguru import logger


class WorkerAgent:
    """
    通用 Worker Agent - 执行具体子任务
    没有固定角色标签，根据任务动态调整行为
    """
    
    def __init__(self, llm: BaseLanguageModel, name: str = "Worker"):
        self.llm = llm
        self.name = name
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        return """You are a versatile worker agent executing a specific subtask.

Your characteristics:
1. No fixed role - adapt to whatever the subtask requires
2. Focus deeply on the assigned subtask
3. Report results back to the orchestrator, not to other workers
4. If you notice issues outside your subtask scope, mention them but don't try to fix them
5. Provide detailed reasoning, not just conclusions

Important: Your work will be synthesized by the orchestrator with other workers' results.
Ensure your output is self-contained and clearly explains your reasoning process.
"""
    
    async def execute(
        self,
        subtask_description: str,
        context: str,
        tools: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Execute a subtask
        
        Args:
            subtask_description: What needs to be done
            context: Relevant context from orchestrator
            tools: Available tools for this task
        
        Returns:
            Subtask result with reasoning
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nSubtask:\n{subtask_description}"},
        ]
        
        response = await self.llm.ainvoke(messages)
        
        return {
            "subtask": subtask_description,
            "result": response.content,
            "reasoning_process": self._extract_reasoning(response.content),
        }
    
    def _extract_reasoning(self, content: str) -> str:
        """Extract reasoning process from response"""
        # In practice, we might want to prompt the model to explicitly
        # separate reasoning from conclusions
        return content  # For now, return full content as reasoning
```

#### 3.2.3 重构 Reviewer 为纯否定者

```python
# sponge/app/orchestrator/validator_agent.py

from typing import Any, Dict
from langchain_core.language_models import BaseLanguageModel
from loguru import logger


class ValidatorAgent:
    """
    验证 Agent - 唯一任务是找问题，不接棒继续做
    对抗性检验，不是流水线传递
    """
    
    def __init__(self, llm: BaseLanguageModel, name: str = "Validator"):
        self.llm = llm
        self.name = name
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        return """You are a critical validator agent. Your ONLY job is to find problems.

Your responsibilities:
1. Critically analyze the provided solution
2. Identify bugs, edge cases, security issues, and design flaws
3. Provide specific, actionable feedback
4. Do NOT attempt to fix the issues yourself
5. Do NOT pass the work to another agent

You are an adversary, not a collaborator.
Your success is measured by how many issues you find, not by being nice.

Output format:
Return JSON with:
- passed: Boolean (true only if NO issues found)
- critical_issues: List of must-fix problems
- warnings: List of should-fix problems
- suggestions: List of optional improvements
- detailed_analysis: Your reasoning
"""
    
    async def validate(
        self,
        solution: str,
        requirements: str,
        context: str = "",
    ) -> Dict[str, Any]:
        """
        Validate a solution
        
        Args:
            solution: The solution to validate
            requirements: Original requirements
            context: Additional context
        
        Returns:
            Validation result with issues found
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""Requirements:
{requirements}

Solution to validate:
{solution}

Additional context:
{context}

Find all issues with this solution."""},
        ]
        
        response = await self.llm.ainvoke(messages)
        return self._parse_validation(response.content)
    
    def _parse_validation(self, response: str) -> Dict[str, Any]:
        """Parse validation response"""
        import json
        
        try:
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                return json.loads(response[start_idx:end_idx])
        except:
            pass
        
        # Fallback
        return {
            "passed": False,
            "critical_issues": ["Manual review required"],
            "warnings": [],
            "suggestions": [],
            "detailed_analysis": response,
        }
```

---

### 3.3 第三阶段：重构工作流图

#### 3.3.1 新的工作流设计

```python
# sponge/app/orchestrator/orchestrator_workflow.py

from typing import Any, Dict, List, Optional
from loguru import logger
from app.core.state_manager import TaskProgress
from app.orchestrator.orchestrator_agent import OrchestratorAgent
from app.orchestrator.worker_agent import WorkerAgent
from app.orchestrator.validator_agent import ValidatorAgent


class OrchestratorWorkflow:
    """
    新的工作流：Orchestrator 持有完整意图，Worker 并行执行
    """
    
    def __init__(self, llm, enable_validation: bool = True):
        self.llm = llm
        self.enable_validation = enable_validation
        self.orchestrator = OrchestratorAgent(llm)
        self.worker = WorkerAgent(llm)
        self.validator = ValidatorAgent(llm) if enable_validation else None
    
    async def execute(
        self,
        task_id: str,
        description: str,
        language: str = "python",
        max_iterations: int = 3,
    ) -> Dict[str, Any]:
        """
        Execute task using orchestrator-worker pattern
        
        Key differences from old workflow:
        1. Single orchestrator holds complete intent throughout
        2. Workers execute in parallel when possible
        3. All results flow back to orchestrator, not to each other
        4. External state file maintains continuity
        5. Validator only finds issues, doesn't pass work along
        """
        
        # Initialize external state
        progress = TaskProgress(task_id)
        progress.initialize(description, [f"Language: {language}"])
        
        iteration = 0
        final_result = None
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Starting iteration {iteration}/{max_iterations}")
            
            # Update status
            progress.update_status(f"iteration_{iteration}", "Orchestrator analyzing")
            
            # Get orchestrator decision
            orchestrator_result = await self.orchestrator.execute(
                task_id=task_id,
                description=description,
                progress=progress,
            )
            
            phase = orchestrator_result.get("current_phase", "planning")
            logger.info(f"Orchestrator phase: {phase}")
            
            # Execute based on phase
            if phase == "planning":
                # Assign parallel planning workers
                assignments = orchestrator_result.get("worker_assignments", [])
                if assignments:
                    worker_results = await self._execute_workers_parallel(assignments)
                    progress.append_step(iteration, "Parallel planning exploration", {
                        "workers": len(worker_results),
                        "results_summary": [r["subtask"] for r in worker_results],
                    })
                    
                    # Feed results back to orchestrator
                    orchestrator_result = await self.orchestrator.execute(
                        task_id=task_id,
                        description=description,
                        progress=progress,
                        worker_results=worker_results,
                    )
            
            elif phase == "coding":
                # Similar pattern for coding
                assignments = orchestrator_result.get("worker_assignments", [])
                if assignments:
                    worker_results = await self._execute_workers_parallel(assignments)
                    progress.append_step(iteration, "Parallel coding", {
                        "workers": len(worker_results),
                    })
                    
                    orchestrator_result = await self.orchestrator.execute(
                        task_id=task_id,
                        description=description,
                        progress=progress,
                        worker_results=worker_results,
                    )
            
            elif phase == "reviewing" and self.validator:
                # Validator only finds issues
                solution = orchestrator_result.get("synthesis", "")
                validation_result = await self.validator.validate(
                    solution=solution,
                    requirements=description,
                )
                
                if validation_result.get("passed", False):
                    progress.update_status("validation_passed", "All checks passed")
                    final_result = orchestrator_result
                    break
                else:
                    progress.add_known_issue(
                        validation_result.get("critical_issues", ["Validation failed"]),
                        "Returning to orchestrator for revision",
                    )
                    # Feed validation back to orchestrator
                    orchestrator_result = await self.orchestrator.execute(
                        task_id=task_id,
                        description=description,
                        progress=progress,
                        worker_results=[{"type": "validation", **validation_result}],
                    )
            
            elif phase == "completed":
                final_result = orchestrator_result
                progress.update_status("completed", "Task finished successfully")
                break
            
            # Save orchestrator synthesis
            if "synthesis" in orchestrator_result:
                progress.append_step(iteration, "Orchestrator synthesis", {
                    "phase": phase,
                    "summary": str(orchestrator_result["synthesis"])[:500],
                })
        
        if final_result is None:
            final_result = orchestrator_result
            progress.update_status("max_iterations_reached", "Stopping after max iterations")
        
        return {
            **final_result,
            "progress_file": str(progress.progress_file),
            "spec_file": str(progress.spec_file),
        }
    
    async def _execute_workers_parallel(self, assignments: List[Dict]) -> List[Dict]:
        """Execute multiple workers in parallel"""
        import asyncio
        
        async def run_worker(assignment):
            return await self.worker.execute(
                subtask_description=assignment.get("description", ""),
                context=assignment.get("context", ""),
            )
        
        results = await asyncio.gather(*[run_worker(a) for a in assignments])
        return results
```

---

## 四、实施路线图

### 阶段 1：外部状态系统（1-2 天）
- [ ] 实现 `TaskProgress` 类
- [ ] 修改 `WorkflowState` 增加状态文件路径
- [ ] 在每个 node 中集成状态文件更新
- [ ] 验证跨 session 连续性

### 阶段 2：Orchestrator-Worker 原型（3-5 天）
- [ ] 实现 `OrchestratorAgent`
- [ ] 实现通用 `WorkerAgent`
- [ ] 实现 `ValidatorAgent`（纯否定者）
- [ ] 创建新的工作流引擎

### 阶段 3：渐进式迁移（5-10 天）
- [ ] 保留旧 workflow 用于向后兼容
- [ ] 新任务默认使用新架构
- [ ] 收集两种架构的对比数据
- [ ] 优化新架构性能

### 阶段 4：完全切换（10-15 天）
- [ ] 弃用旧 Agent 类（Planner/Coder/Reviewer/Tester）
- [ ] 清理旧 workflow 代码
- [ ] 更新文档和示例
- [ ] 性能基准测试

---

## 五、预期收益

### 5.1 质量提升
- **减少信息损耗**：外部状态文件保留完整推理链
- **避免整体漂移**：Orchestrator 始终持有完整意图
- **更好的边界推理**：Worker 不被角色限制，可以跨边界思考

### 5.2 效率提升
- **并行覆盖**：真正独立的子任务可并行执行
- **减少冗余 token**：不再浪费在 Agent 间交接文件
- **更快的迭代**：Validator 直接反馈给 Orchestrator，无需多轮传递

### 5.3 可维护性提升
- **清晰的职责分离**：Orchestrator 负责决策，Worker 负责执行
- **易于调试**：外部状态文件提供完整审计日志
- **可扩展性**：添加新 Worker 类型不影响整体架构

---

## 六、风险与缓解

| 风险 | 影响 | 缓解措施 |
|-----|------|---------|
| 迁移期间系统不稳定 | 高 | 保留旧架构，渐进式切换 |
| Orchestrator 成为瓶颈 | 中 | 使用更大上下文窗口模型，优化 prompt |
| 外部状态文件管理复杂 | 中 | 提供完善的状态管理 API，自动化清理 |
| 团队学习曲线 | 低 | 详细文档 + 示例代码 + 培训 |

---

## 七、关键指标

重构后需要监控的指标：

1. **任务完成率**：新旧架构对比
2. **平均迭代次数**：达到合格结果所需轮数
3. **Token 使用效率**：有效推理 vs 交接开销
4. **问题检出率**：Validator 发现的问题数量
5. **用户满意度**：输出质量的主观评价

---

## 八、参考实现

文章提到的三家厂商实践：

- **Anthropic**: progress.txt + orchestrator-worker + 功能性并行
- **OpenAI**: spec 文件 + runbook + compaction
- **Google**: Conductor + Context-driven Development + Thought Signatures

本方案融合了这些最佳实践，针对 Sponge 项目进行了适配。
