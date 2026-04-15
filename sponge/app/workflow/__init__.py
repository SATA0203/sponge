"""
Sponge Workflow Module - Multi-agent workflow system

This module now supports both:
1. LEGACY: LangGraph-based linear pipeline (Planner -> Coder -> Executor -> Reviewer -> Tester)
2. NEW: Orchestrator-Worker pattern with external state management

The new architecture provides:
- Better continuity across sessions via external state files
- Parallel execution of independent sub-tasks
- Clearer separation of concerns (Orchestrator holds intent, Workers execute)
- Adversarial validation that doesn't take ownership
"""

from .workflow_graph import create_workflow, WorkflowManager, get_workflow_manager
from .nodes import (
    planner_node,
    coder_node,
    executor_node,
    reviewer_node,
    tester_node,
)

# New orchestrator-worker workflow
from .orchestrator_workflow import OrchestratorWorkflow, run_workflow

__all__ = [
    # Legacy workflow
    "create_workflow",
    "WorkflowManager",
    "get_workflow_manager",
    "planner_node",
    "coder_node",
    "executor_node",
    "reviewer_node",
    "tester_node",
    
    # New workflow
    "OrchestratorWorkflow",
    "run_workflow",
]