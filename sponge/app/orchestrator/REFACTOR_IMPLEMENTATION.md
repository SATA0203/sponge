# Architecture Refactor: From "三省六部" to Orchestrator-Worker Pattern

## Executive Summary

This document outlines the implementation of Phase 1 of the architecture refactor, moving from the problematic role-based流水线 (assembly line) pattern to the Anthropic-style orchestrator-worker pattern with external state management.

**Status**: Phase 1 Complete ✅  
**Next**: Phase 2 - Migration and Testing

---

## Problem Statement

The current workflow implements the "三省六部" pattern criticized in the architecture analysis:

### Current Issues
1. **流水线 Handoffs**: Planner → Coder → Executor → Reviewer → Tester
2. **Information Compression**: WorkflowState passes only conclusions, not reasoning
3. **False Role Boundaries**: Agents are limited by artificial "job descriptions"
4. **Reasoning Drift**: Each handoff loses context and accumulates errors
5. **Local Optimization**: Each node looks correct but整体 drifts from goal

---

## Solution: Three-Phase Refactor

### Phase 1: External State System ✅ COMPLETE

**Implemented Files:**
- `app/core/task_progress.py` - TaskProgress class for persistent state
- `app/orchestrator/orchestrator_agent.py` - OrchestratorAgent and WorkerAgent
- `app/orchestrator/validator_agent.py` - Pure adversarial validator
- `app/orchestrator/workflow.py` - New workflow engine
- `app/orchestrator/__init__.py` - Module exports

**Key Features:**

#### 1. TaskProgress - External State Manager

Four categories of persistent state:

```python
# 1. Task Goal (Immutable)
task_progress.write_spec(
    goal="Build a REST API",
    constraints=["Use FastAPI", "PostgreSQL"],
    metadata={"language": "python"}
)

# 2. Completed Steps (Append-only)
task_progress.add_completed_step(
    step_number=1,
    description="Designed API schema",
    outcome="Schema defined with 5 endpoints",
    reasoning="Chose REST over GraphQL because...",
    artifacts={"schema_file": "/path/to/schema.json"}
)

# 3. Current Status (Overwrite)
task_progress.update_current_status(
    current_step="Implementing user authentication",
    status="in_progress",
    details={"progress": 0.6},
    last_updated_by="worker_auth"
)

# 4. Known Issues (Append-only)
task_progress.add_known_issue(
    issue="Database connection timeout",
    workaround="Increase pool size to 20",
    severity="high",
    discovered_at_step=3
)
```

#### 2. OrchestratorAgent - Single Intent Holder

```python
orchestrator = OrchestratorAgent(llm=llm, task_progress=task_progress)

# Planning phase
plan = await orchestrator.execute({
    "task_id": "task-123",
    "goal": "Build REST API",
    "current_phase": "planning"
})

# Delegates subtasks
for subtask in plan["subtasks"]:
    result = await orchestrator.delegate_subtask(
        subtask_name=subtask["name"],
        subtask_description=subtask["description"]
    )

# Synthesizes all results
synthesis = await orchestrator.synthesize_results()
```

#### 3. WorkerAgent - Generic Executor

```python
worker = WorkerAgent(llm=llm, name="api_design", task_progress=task_progress)

result = await worker.execute({
    "task_description": "Design REST API schema",
    "full_task_context": task_progress.get_full_context_for_agent()
})

# Returns structured result with reasoning
{
    "result": "...",
    "reasoning": "Chose this approach because...",
    "confidence": "high",
    "issues": ["Edge case not handled..."],
    "suggestions": ["Consider adding rate limiting"]
}
```

#### 4. ValidatorAgent - Pure Adversarial Checker

```python
validator = ValidatorAgent(llm=llm, task_progress=task_progress)

validation = await validator.execute({
    "artifact": code_or_design,
    "task_goal": original_goal,
    "validation_focus": ["security", "performance"]
})

# Only finds problems, never fixes
{
    "passed": False,
    "issues": [
        {
            "title": "SQL Injection Vulnerability",
            "severity": "critical",
            "evidence": "Line 42: f-string in SQL query",
            "recommendation": "Use parameterized queries"
        }
    ],
    "summary": "Found 3 critical issues"
}
```

### Key Architectural Differences

| Aspect | Old (三省六部) | New (Orchestrator-Worker) |
|--------|---------------|---------------------------|
| **Information Flow** | 流水线 handoff | Return to orchestrator |
| **State Management** | In-memory dict | External files |
| **Role Boundaries** | Fixed (Planner/Coder/etc.) | Dynamic (Orchestrator/Worker) |
| **Validation** | Reviewer passes to Tester | Validator reports to Orchestrator |
| **Reasoning Chain** | Lost at each handoff | Preserved in TaskProgress |
| **Parallelization** | Sequential only | Parallel subtasks possible |

---

## Phase 2: Migration Plan (Next)

### Step 1: Dual-Run Comparison

Run both workflows in parallel for comparison:

```python
# Old workflow
from app.workflow.workflow_graph import get_workflow_manager
old_result = await old_workflow.execute(description="...")

# New workflow
from app.orchestrator.workflow import get_orchestrator_workflow
new_result = await new_workflow.execute(goal="...")

# Compare results
compare_workflows(old_result, new_result)
```

### Step 2: API Compatibility Layer

Create adapter to maintain backward compatibility during migration:

```python
class WorkflowAdapter:
    """Adapter to make new workflow look like old one"""
    
    async def execute(self, description: str, **kwargs):
        # Translate old API to new
        result = await new_workflow.execute(
            goal=description,
            **kwargs
        )
        # Translate result back to old format
        return adapt_result(result)
```

### Step 3: Gradual Feature Migration

Migrate features one at a time:
1. Simple code generation tasks
2. Tasks with validation
3. Multi-iteration refinement
4. Complex multi-step projects

### Step 4: Deprecation Timeline

- Week 1-2: Dual-run, collect metrics
- Week 3-4: Migrate 50% of tasks to new workflow
- Week 5-6: Migrate remaining tasks
- Week 7+: Deprecate old workflow

---

## Phase 3: Advanced Features (Future)

### Parallel Worker Execution

```python
import asyncio

# Execute multiple workers in parallel
worker_tasks = [
    worker.execute({"task_description": desc})
    for desc in subtask_descriptions
]
results = await asyncio.gather(*worker_tasks)
```

### Cross-Session Continuity

```python
# Session 1 ends
task_progress.save_checkpoint("end_of_session_1", state)

# Session 2 starts
task_progress = TaskProgress(task_id)
previous_state = task_progress.load_checkpoint("end_of_session_1")
context = task_progress.get_full_context_for_agent()
```

### Skill Library

Reusable worker configurations:

```python
class SkillLibrary:
    def get_skill(self, skill_name: str) -> Dict:
        return {
            "system_prompt": "...",
            "tools": ["file_read", "code_execute"],
            "validation_rules": [...]
        }

worker = WorkerAgent(
    llm=llm,
    system_prompt=skills.get_skill("python_expert")["system_prompt"]
)
```

---

## Metrics for Success

### Quantitative
- **Task Completion Rate**: % of tasks that reach successful completion
- **Iteration Count**: Average iterations before passing validation
- **Context Size**: Average token count in agent prompts
- **Execution Time**: End-to-end task duration

### Qualitative
- **Goal Alignment**: Does final output match original intent?
- **Reasoning Quality**: Are decisions well-documented and logical?
- **Issue Detection**: How many problems caught by validator?
- **Drift Measurement**: How much does output deviate from initial goal?

---

## File Structure

```
sponge/app/
├── core/
│   ├── task_progress.py          # NEW: External state manager
│   └── llm_service.py
├── orchestrator/                  # NEW: Orchestrator module
│   ├── __init__.py
│   ├── orchestrator_agent.py     # Orchestrator + Worker agents
│   ├── validator_agent.py        # Adversarial validator
│   └── workflow.py               # New workflow engine
├── workflow/                      # OLD: To be deprecated
│   ├── workflow_graph.py
│   └── nodes.py
└── agents/                        # OLD: Role-based agents
    ├── planner_agent.py
    ├── coder_agent.py
    ├── reviewer_agent.py
    └── tester_agent.py
```

---

## Usage Examples

### Basic Task

```python
from app.orchestrator.workflow import create_orchestrator_workflow

workflow = create_orchestrator_workflow(enable_validation=True)

result = await workflow.execute(
    goal="Create a Python function to calculate fibonacci numbers",
    constraints=["Must be iterative, not recursive", "Include type hints"],
    metadata={"language": "python", "difficulty": "easy"}
)

print(f"Status: {result['status']}")
print(f"Synthesis: {result['synthesis']}")
```

### Accessing State Files

```python
# After execution, state files are available
task_progress = workflow.get_task_progress()

# Read the full context
full_context = task_progress.get_full_context_for_agent()

# Access state file paths
spec_file = task_progress.spec_file  # spec.md
progress_file = task_progress.progress_file  # task_progress.md
history_file = task_progress.history_file  # history.jsonl
```

### Custom Validation

```python
from app.orchestrator.validator_agent import create_validator

validator = create_validator(
    llm=get_llm(),
    task_progress=task_progress,
    validation_type="security"  # Focus on security issues
)

result = await validator.execute({
    "artifact": code,
    "task_goal": goal,
    "validation_focus": ["sql_injection", "xss", "csrf"]
})
```

---

## Next Actions

1. **Test the new workflow** with simple tasks
2. **Compare results** against old workflow
3. **Gather metrics** on quality and performance
4. **Iterate on implementation** based on findings
5. **Plan Phase 2 migration** timeline

---

## References

- Anthropic Engineering: Building Effective Agents
- Anthropic: Effective Context Engineering
- OpenAI: Run Long Horizon Tasks with Codex
- Google: Conductor - Context-Driven Development
